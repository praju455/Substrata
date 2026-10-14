"""Trace causality, privacy, streaming durations, metrics and real local OTLP export."""

import asyncio
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from substrata.app import create_app
from substrata.observability import (
    HTTPMetrics,
    HTTPObservability,
    Tracing,
    configured_tracing,
    trace_headers,
)

REMOTE_TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
REMOTE_PARENT = "00f067aa0ba902b7"
PARENT = f"00-{REMOTE_TRACE}-{REMOTE_PARENT}-01"


@pytest.fixture
def recording():
    exporter = InMemorySpanExporter()
    provider = TracerProvider(shutdown_on_exit=False)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield Tracing(provider), exporter
    provider.shutdown()


def test_remote_parent_response_headers_and_logs_exclude_business_data(recording, caplog):
    tracing, exporter = recording
    app = create_app(tracing=tracing)
    caplog.set_level("INFO", logger="substrata.http")

    @app.post("/private/{supplier}")
    async def private(supplier: str):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.post(
            "/private/private-supplier?token=secret-query",
            content="private-document-text",
            headers={
                "traceparent": PARENT,
                "tracestate": "vendor=private-vendor-data",
                "baggage": "customer=private-customer",
                "Authorization": "Bearer secret-access-token",
                "X-Request-ID": "check-123",
            },
        )
    assert response.status_code == 200
    (span,) = exporter.get_finished_spans()
    assert span.name == "POST /private/{supplier}"
    assert span.kind == trace.SpanKind.SERVER
    assert f"{span.context.trace_id:032x}" == REMOTE_TRACE
    assert f"{span.parent.span_id:016x}" == REMOTE_PARENT
    assert response.headers["traceparent"] == f"00-{REMOTE_TRACE}-{span.context.span_id:016x}-01"
    assert response.headers["X-Request-ID"] == "check-123"
    assert not span.context.trace_state
    entry = json.loads(caplog.messages[-1])
    assert entry["trace_id"] == REMOTE_TRACE
    assert entry["path"] == "/private/{supplier}"
    assert entry["span_id"] == f"{span.context.span_id:016x}"
    serialized = json.dumps(dict(span.attributes)) + caplog.text
    for secret in (
        "private-supplier",
        "secret-query",
        "private-document-text",
        "secret-access-token",
        "private-vendor-data",
        "private-customer",
    ):
        assert secret not in serialized
    assert trace_headers() == {}, "Request trace context leaked outside its lifetime."


@pytest.mark.parametrize(
    "parent",
    [
        "malformed",
        f"00-{'0' * 32}-{REMOTE_PARENT}-01",
        f"00-{REMOTE_TRACE}-{'0' * 16}-01",
        PARENT.upper(),
        "x" * 513,
    ],
)
def test_invalid_traceparents_start_independent_roots(recording, parent):
    tracing, exporter = recording
    with TestClient(create_app(tracing=tracing)) as client:
        response = client.get("/health", headers={"traceparent": parent, "X-Request-ID": "bad id"})
        next_response = client.get("/health")
    spans = exporter.get_finished_spans()
    assert all(span.parent is None for span in spans)
    assert all(span.context.is_valid for span in spans)
    assert response.headers["traceparent"][3:35] != REMOTE_TRACE
    assert next_response.headers["traceparent"][3:35] != response.headers["traceparent"][3:35]
    assert response.headers["X-Request-ID"] != "bad id"


def test_streaming_span_and_duration_finish_after_last_response_body(recording, monkeypatch):
    tracing, exporter = recording
    metrics = HTTPMetrics()
    clock = iter((1.0, 3.0))
    monkeypatch.setattr("substrata.observability.time.perf_counter", lambda: next(clock))
    sent = []

    async def streaming(scope, receive, send):
        scope["route"] = SimpleNamespace(path="/stream/{id}")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"first", "more_body": True})
        assert exporter.get_finished_spans() == ()
        assert metrics.in_flight == 1
        assert metrics.requests == 0
        await asyncio.sleep(0)
        await send({"type": "http.response.body", "body": b"last", "more_body": False})

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {"type": "http", "method": "GET", "headers": [], "path": "/stream/private"}
    asyncio.run(
        HTTPObservability(streaming, tracing=tracing, metrics=metrics)(scope, receive, send)
    )
    (span,) = exporter.get_finished_spans()
    assert span.name == "GET /stream/{id}"
    assert sent[-1]["body"] == b"last"
    output = metrics.render()
    assert "substrata_http_in_flight 0" in output
    assert 'route="/stream/{id}",le="1"} 0' in output
    assert 'route="/stream/{id}",le="2.5"} 1' in output
    assert 'route="/stream/{id}"} 2.000000000' in output


def test_errors_are_counted_without_exporting_exception_secrets(recording):
    tracing, exporter = recording
    app = create_app(tracing=tracing)

    @app.get("/failure/{id}")
    async def fail(id: str):
        raise RuntimeError("secret-document-and-credential")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/failure/private").status_code == 500
        assert client.get("/unknown/private-token").status_code == 404
        output = client.get("/metrics").text
    failure, unmatched, _ = exporter.get_finished_spans()
    assert failure.status.status_code == trace.StatusCode.ERROR
    assert failure.status.description is None
    assert failure.attributes["error.type"] == "RuntimeError"
    assert failure.events == ()
    assert unmatched.name == "GET <unmatched>"
    assert "secret-document-and-credential" not in output + str(failure.attributes)
    assert "private-token" not in output
    assert "substrata_http_errors_total 1" in output
    assert 'method="GET",route="/failure/{id}",status_code="500"} 1' in output


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://collector.example/v1/traces",
        "https://user:key@collector.example/v1/traces",
        "https://collector.example/v1/traces?key=private",
        "https://collector.example/v1/traces#private",
    ],
)
def test_collector_configuration_rejects_plaintext_or_embedded_secrets(monkeypatch, endpoint):
    monkeypatch.setenv("SUBSTRATA_OTLP_TRACES_ENDPOINT", endpoint)
    with pytest.raises(ValueError, match="HTTPS"):
        configured_tracing()


def test_sampling_is_bounded_locally_and_production_rejects_loopback_http(monkeypatch):
    monkeypatch.setenv("SUBSTRATA_OTLP_TRACES_ENDPOINT", "http://127.0.0.1:4318/v1/traces")
    monkeypatch.setenv("SUBSTRATA_ENV", "production")
    with pytest.raises(ValueError, match="HTTPS"):
        configured_tracing()
    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    monkeypatch.setenv("SUBSTRATA_TRACE_SAMPLE_RATIO", "nan")
    with pytest.raises(ValueError, match="ratio"):
        configured_tracing()
    monkeypatch.setenv("SUBSTRATA_TRACE_SAMPLE_RATIO", "0")
    tracing = configured_tracing()
    try:
        with TestClient(create_app(tracing=tracing)) as client:
            response = client.get("/health", headers={"traceparent": PARENT})
            assert response.headers["traceparent"].endswith("-00")
    finally:
        tracing.shutdown()


def test_real_otlp_http_export_flushes_on_shutdown_and_uses_secret_header_file(
    monkeypatch, tmp_path
):
    received = []

    class Collector(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((self.path, self.headers.get("Authorization"), body))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Collector)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    headers = tmp_path / "collector.secret"
    headers.write_text(json.dumps({"Authorization": "Bearer test-only-collector-key"}))
    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    monkeypatch.setenv(
        "SUBSTRATA_OTLP_TRACES_ENDPOINT", f"http://127.0.0.1:{server.server_port}/v1/traces"
    )
    monkeypatch.setenv("SUBSTRATA_OTLP_HEADERS_FILE", str(headers))
    monkeypatch.setenv("SUBSTRATA_TRACE_SAMPLE_RATIO", "1")
    try:
        with TestClient(create_app()) as client:
            assert (
                client.get("/health?private=query", headers={"traceparent": PARENT}).status_code
                == 200
            )
        assert received
        path, authorization, body = received[0]
        assert path == "/v1/traces"
        assert authorization == "Bearer test-only-collector-key"
        exported = ExportTraceServiceRequest.FromString(body)
        spans = [
            span
            for resource in exported.resource_spans
            for scope in resource.scope_spans
            for span in scope.spans
        ]
        assert len(spans) == 1
        assert spans[0].trace_id.hex() == REMOTE_TRACE
        assert spans[0].parent_span_id.hex() == REMOTE_PARENT
        assert spans[0].name == "GET /health"
        assert b"private" not in body and b"collector-key" not in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
