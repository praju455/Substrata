"""Trace causality, privacy, streaming durations, metrics and real local OTLP export."""

import asyncio
import io
import json
import os
import subprocess
import sys
import urllib.error
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from test_platform_api import KEY
from test_platform_api import headers as auth_headers

from substrata.app import create_app
from substrata.observability import (
    HTTPMetrics,
    HTTPObservability,
    Tracing,
    configured_tracing,
    parent_context,
    trace_headers,
)
from substrata.platform.auth import Principal, TokenVerifier
from substrata.platform.connectors import read_json
from substrata.platform.jobs import JobInput, enqueue, run_next
from substrata.platform.providers import request_json
from substrata.platform.seeds import generate

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


def test_outbound_calls_have_child_spans_and_propagate_only_traceparent(recording, monkeypatch):
    tracing, exporter = recording
    outgoing = []

    class Response(io.BytesIO):
        status = 200

    class Opener:
        def open(self, request, timeout):
            outgoing.append({key.lower(): value for key, value in request.header_items()})
            return Response(b'{"ok":true}')

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    with tracing.span("parent-operation", parent=parent_context(PARENT)) as parent:
        headers = {
            "Authorization": "Bearer private-provider-key",
            "tracestate": "private-state",
            "baggage": "private-baggage",
            "traceparent": "forged",
        }
        assert request_json(
            "https://provider.example/v1/messages?private=query",
            {"private": "document"},
            headers,
            5,
        ) == {"ok": True}
        assert read_json("https://connector.example/vendors?private=query", headers=headers) == {
            "ok": True
        }
    clients = [span for span in exporter.get_finished_spans() if span.kind == trace.SpanKind.CLIENT]
    assert [span.name for span in clients] == ["provider.request", "connector.read"]
    for span, headers in zip(clients, outgoing, strict=True):
        assert span.parent.span_id == parent.get_span_context().span_id
        assert span.context.trace_id == int(REMOTE_TRACE, 16)
        assert span.attributes["http.response.status_code"] == 200
        assert headers["traceparent"] == f"00-{REMOTE_TRACE}-{span.context.span_id:016x}-01"
        assert headers["authorization"] == "Bearer private-provider-key"
        assert "tracestate" not in headers and "baggage" not in headers
        assert "private" not in str(span.attributes)


@pytest.mark.parametrize("client", ["provider", "connector"])
def test_outbound_http_failures_are_closed_and_export_status_without_secrets(
    recording, monkeypatch, client
):
    tracing, exporter = recording
    response = io.BytesIO(b"private-error-body")

    class Opener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(request.full_url, 429, "private-error", {}, response)

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    with tracing.activate(), pytest.raises(ValueError):
        if client == "provider":
            request_json(
                "https://provider.example/v1/messages", {}, {"Authorization": "private"}, 5
            )
        else:
            read_json("https://connector.example/vendors")
    (span,) = exporter.get_finished_spans()
    assert span.status.status_code == trace.StatusCode.ERROR
    assert span.attributes["http.response.status_code"] == 429
    assert response.closed
    assert span.events == ()
    assert "private" not in str(span.attributes)


def queued_assessment(platform, *, key="synthetic-queue-key"):
    now = datetime.now(UTC)
    platform.save("alpha", generate("pharma", as_of=now), "analyst", expected_version=0)
    return JobInput(
        kind="assessment",
        idempotency_key=key,
        payload={
            "graph_version": 1,
            "assessment": {
                "source_id": "upstream",
                "severity": 0.8,
                "as_of": now.isoformat(),
                "max_depth": 4,
            },
        },
    )


def test_authenticated_http_queue_and_worker_execution_share_causal_trace(
    platform, recording, caplog
):
    tracing, exporter = recording
    caplog.set_level("INFO", logger="substrata")
    body = queued_assessment(platform, key="private-client-key")
    app = create_app(
        platform_store=platform,
        tracing=tracing,
        auth_verifier=TokenVerifier(
            issuer="test-issuer", audience="substrata", key=KEY, algorithm="HS256"
        ),
    )
    with TestClient(app) as client:
        response = client.post(
            "/platform/jobs",
            json=body.model_dump(mode="json"),
            headers={**auth_headers(), "traceparent": PARENT},
        )
    assert response.status_code == 200
    queued = response.json()
    with tracing.activate():
        result = run_next(
            platform, Principal(subject="worker", tenant_id="alpha", roles={"analyst"})
        )
    assert result["status"] == "succeeded"
    spans = exporter.get_finished_spans()
    (producer,) = [span for span in spans if span.kind == trace.SpanKind.PRODUCER]
    (consumer,) = [span for span in spans if span.kind == trace.SpanKind.CONSUMER]
    (server,) = [span for span in spans if span.kind == trace.SpanKind.SERVER]
    assert producer.parent.span_id == server.context.span_id
    assert consumer.parent.span_id == producer.context.span_id
    assert consumer.context.trace_id == int(REMOTE_TRACE, 16)
    assert (
        queued["payload"]["traceparent"] == f"00-{REMOTE_TRACE}-{producer.context.span_id:016x}-01"
    )
    assert consumer.attributes["job.type"] == "assessment"
    assert consumer.attributes["job.attempt"] == 1
    (event,) = [json.loads(line) for line in caplog.messages if '"event":"job.execution"' in line]
    assert event["trace_id"] == REMOTE_TRACE
    assert event["span_id"] == f"{consumer.context.span_id:016x}"
    assert "private-client-key" not in caplog.text + str(consumer.attributes)
    assert trace_headers() == {}


def test_retry_attempt_span_records_failure_class_without_failure_message(
    platform, recording, monkeypatch, caplog
):
    tracing, exporter = recording
    caplog.set_level("INFO", logger="substrata")
    body = queued_assessment(platform)
    worker = Principal(subject="worker", tenant_id="alpha", roles={"analyst"})
    with tracing.activate():
        enqueue(platform, worker, body)

    def unavailable(*args, **kwargs):
        raise TimeoutError("private-customer-document-and-credential")

    monkeypatch.setattr("substrata.platform.governance.save_assessment", unavailable)
    with tracing.activate():
        assert run_next(platform, worker)["status"] == "retry_scheduled"
    (consumer,) = [
        span for span in exporter.get_finished_spans() if span.kind == trace.SpanKind.CONSUMER
    ]
    assert consumer.status.status_code == trace.StatusCode.ERROR
    assert consumer.attributes["error.type"] == "TimeoutError"
    assert consumer.events == ()
    assert "private-customer-document-and-credential" not in caplog.text + str(consumer.attributes)


@pytest.fixture
def worker_collector():
    received = []

    class Collector(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Collector)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("export", [False, True])
def test_worker_process_logs_summary_without_dumping_persisted_graph_inputs(
    platform, export, worker_collector
):
    server, received = worker_collector
    body = queued_assessment(platform, key="private-client-key")
    worker = Principal(subject="worker", tenant_id="alpha", roles={"analyst"})
    queued = enqueue(platform, worker, body)
    script = Path(__file__).resolve().parents[1] / "scripts/platform_worker.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--tenant", "alpha", "--once"],
        capture_output=True,
        text=True,
        timeout=20,
        env={
            **os.environ,
            "SUBSTRATA_ENV": "development",
            "SUBSTRATA_OTLP_TRACES_ENDPOINT": (
                f"http://127.0.0.1:{server.server_port}/v1/traces" if export else ""
            ),
            "SUBSTRATA_TRACE_SAMPLE_RATIO": "1",
            "SUBSTRATA_OTLP_HEADERS_FILE": "",
            "OTEL_SERVICE_NAME": "substrata-worker",
            "SUBSTRATA_PLATFORM_DATABASE_URL": platform.engine.url.render_as_string(
                hide_password=False
            ),
        },
    )
    assert completed.returncode == 0, completed.stderr
    entries = [json.loads(line) for line in completed.stderr.splitlines()]
    (event,) = [entry for entry in entries if entry["event"] == "job.execution"]
    assert event["status"] == "succeeded"
    assert event["trace_id"] == queued["payload"]["traceparent"][3:35]
    output = completed.stdout + completed.stderr
    for private in ("private-client-key", "upstream", "input_snapshot", "inventory", "payload"):
        assert private not in output
    if export:
        assert len(received) == 1
        exported = ExportTraceServiceRequest.FromString(received[0])
        spans = [
            span
            for resource in exported.resource_spans
            for scope in resource.scope_spans
            for span in scope.spans
        ]
        assert len(spans) == 1 and spans[0].name == "job.execute"
        assert spans[0].trace_id.hex() == queued["payload"]["traceparent"][3:35]
        assert spans[0].parent_span_id.hex() == queued["payload"]["traceparent"][36:52]
        assert b"upstream" not in received[0] and b"private-client-key" not in received[0]
    else:
        assert received == []
