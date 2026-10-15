"""Bounded process metrics and privacy-preserving OpenTelemetry trace contexts."""

import json
import logging
import math
import os
import re
import secrets
import threading
import time
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from urllib.parse import urlsplit

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

PROPAGATOR = TraceContextTextMapPropagator()
ACTIVE_TRACING = ContextVar("substrata_tracing", default=None)
BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30)
METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "CONNECT", "TRACE"}


def configure_logging():
    logger = logging.getLogger("substrata")
    logger.setLevel(logging.INFO)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)


def parent_context(value):
    # Accept traceparent only: neither vendor tracestate nor arbitrary baggage
    # crosses the tenant boundary or enters stored jobs/third-party requests.
    carrier = {"traceparent": value} if isinstance(value, str) and len(value) <= 512 else {}
    return PROPAGATOR.extract(carrier=carrier, context=Context())


def trace_headers():
    carrier = {}
    PROPAGATOR.inject(carrier)
    return {"traceparent": carrier["traceparent"]} if "traceparent" in carrier else {}


def outbound_headers(headers=None):
    return {
        **{
            key: value
            for key, value in (headers or {}).items()
            if key.lower() not in {"traceparent", "tracestate", "baggage"}
        },
        **trace_headers(),
    }


class Tracing:
    def __init__(self, provider=None, *, owned=False):
        self.provider = provider
        self.tracer = provider.get_tracer("substrata", "0.1.0") if provider else None
        self.owned = owned

    @contextmanager
    def activate(self):
        token = ACTIVE_TRACING.set(self)
        try:
            yield
        finally:
            ACTIVE_TRACING.reset(token)

    @contextmanager
    def span(self, name, *, parent=None, kind=trace.SpanKind.INTERNAL, attributes=None):
        if self.tracer:
            span = self.tracer.start_span(name, context=parent, kind=kind, attributes=attributes)
        else:
            incoming = trace.get_current_span(parent).get_span_context()
            span = trace.NonRecordingSpan(
                trace.SpanContext(
                    trace_id=incoming.trace_id if incoming.is_valid else secrets.randbits(128) or 1,
                    span_id=secrets.randbits(64) or 1,
                    is_remote=False,
                    trace_flags=incoming.trace_flags if incoming.is_valid else trace.TraceFlags(0),
                )
            )
        with (
            self.activate(),
            trace.use_span(
                span, end_on_exit=True, record_exception=False, set_status_on_exception=False
            ),
        ):
            try:
                yield span
            except BaseException as error:
                # Exception strings/stack traces can contain credentials or documents.
                span.set_attribute("error.type", type(error).__name__)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                raise

    def shutdown(self):
        if self.owned and self.provider:
            self.provider.shutdown()


FALLBACK_TRACING = Tracing()


def operation_span(name, **kwargs):
    return (ACTIVE_TRACING.get() or FALLBACK_TRACING).span(name, **kwargs)


def configured_tracing(service_name="substrata-api"):
    endpoint = os.environ.get("SUBSTRATA_OTLP_TRACES_ENDPOINT", "").strip()
    if not endpoint:
        return Tracing()
    parsed = urlsplit(endpoint)
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if (
        len(endpoint) > 2048
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not (
            parsed.scheme == "https"
            or (
                parsed.scheme == "http"
                and local
                and os.environ.get("SUBSTRATA_ENV", "development") == "development"
            )
        )
    ):
        raise ValueError(
            "OTLP traces require HTTPS; loopback HTTP is development-only. "
            "URL credentials/query are refused."
        )
    ratio = float(os.environ.get("SUBSTRATA_TRACE_SAMPLE_RATIO", "0.1"))
    if not math.isfinite(ratio) or not 0 <= ratio <= 1:
        raise ValueError("Trace sample ratio must be between zero and one.")
    service = os.environ.get("OTEL_SERVICE_NAME", service_name)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", service):
        raise ValueError("Telemetry service name must be a bounded ASCII identifier.")
    headers = {}
    header_file = os.environ.get("SUBSTRATA_OTLP_HEADERS_FILE")
    if header_file:
        contents = Path(header_file).read_bytes()
        if len(contents) > 32768:
            raise ValueError("OTLP header file exceeds 32 KB.")
        headers = json.loads(contents)
        if not isinstance(headers, dict) or any(
            not isinstance(key, str)
            or not re.fullmatch(r"[A-Za-z0-9-]{1,96}", key)
            or not isinstance(value, str)
            or len(value) > 8192
            or any(ord(char) < 32 or ord(char) > 126 for char in value)
            for key, value in headers.items()
        ):
            raise ValueError(
                "OTLP headers must be bounded ASCII strings without control characters."
            )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

    # Sampling is locally bounded even if a remote client sends sampled=1.
    provider = TracerProvider(
        resource=Resource({"service.name": service, "service.version": "0.1.0"}),
        sampler=TraceIdRatioBased(ratio),
        shutdown_on_exit=False,
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=endpoint, headers=headers, timeout=5),
            max_queue_size=1024,
            max_export_batch_size=128,
            schedule_delay_millis=1000,
            export_timeout_millis=5000,
        )
    )
    return Tracing(provider, owned=True)


def _labels(**values):
    def escape(value):
        return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

    return ",".join(f'{key}="{escape(value)}"' for key, value in values.items())


class HTTPMetrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.requests = self.errors = self.in_flight = 0
        self.responses = Counter()
        self.latencies = {}

    def begin(self):
        with self.lock:
            self.in_flight += 1

    def observe(self, method, route, status, duration, failed=False):
        with self.lock:
            self.in_flight -= 1
            self.requests += 1
            self.errors += int(status >= 500 or failed)
            self.responses[method, route, status] += 1
            counts, count, total = self.latencies.get((method, route), ([0] * len(BUCKETS), 0, 0.0))
            for index, bound in enumerate(BUCKETS):
                counts[index] += int(duration <= bound)
            self.latencies[method, route] = counts, count + 1, total + duration

    def render(self):
        with self.lock:
            lines = [
                "# HELP substrata_http_requests_total HTTP requests handled by this process.",
                "# TYPE substrata_http_requests_total counter",
                f"substrata_http_requests_total {self.requests}",
                "# HELP substrata_http_errors_total HTTP 5xx or aborted requests "
                "handled by this process.",
                "# TYPE substrata_http_errors_total counter",
                f"substrata_http_errors_total {self.errors}",
                "# HELP substrata_http_in_flight HTTP requests currently being handled.",
                "# TYPE substrata_http_in_flight gauge",
                f"substrata_http_in_flight {self.in_flight}",
                "# HELP substrata_http_responses_total Completed HTTP responses by route template.",
                "# TYPE substrata_http_responses_total counter",
            ]
            for (method, route, status), count in sorted(self.responses.items()):
                label = _labels(method=method, route=route, status_code=status)
                lines.append(f"substrata_http_responses_total{{{label}}} {count}")
            lines.extend(
                [
                    "# HELP substrata_http_request_duration_seconds Complete HTTP response "
                    "duration by route template.",
                    "# TYPE substrata_http_request_duration_seconds histogram",
                ]
            )
            for (method, route), (counts, count, total) in sorted(self.latencies.items()):
                label = _labels(method=method, route=route)
                metric = "substrata_http_request_duration_seconds"
                for bound, cumulative in zip(BUCKETS, counts, strict=True):
                    lines.append(f'{metric}_bucket{{{label},le="{bound}"}} {cumulative}')
                lines.extend(
                    [
                        f'{metric}_bucket{{{label},le="+Inf"}} {count}',
                        f"{metric}_count{{{label}}} {count}",
                        f"{metric}_sum{{{label}}} {total:.9f}",
                    ]
                )
            return "\n".join(lines) + "\n"


class HTTPObservability:
    """ASGI middleware measures streaming bodies and exceptions, not just headers."""

    def __init__(self, app, *, tracing, metrics):
        self.app, self.tracing, self.metrics = app, tracing, metrics

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        candidate = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = (
            candidate if re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", candidate) else secrets.token_hex(16)
        )
        method = scope["method"] if scope["method"] in METHODS else "OTHER"
        context = parent_context(headers.get(b"traceparent", b"").decode("latin-1"))
        started = time.perf_counter()
        status, failed = 500, False
        self.metrics.begin()
        with self.tracing.span("HTTP request", parent=context, kind=trace.SpanKind.SERVER) as span:
            ids = span.get_span_context()
            outgoing_trace = trace_headers()

            async def observed_send(message):
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                    outgoing = [
                        (k, v)
                        for k, v in message.get("headers", [])
                        if k.lower() not in {b"x-request-id", b"traceparent"}
                    ]
                    outgoing.append((b"x-request-id", request_id.encode("ascii")))
                    outgoing.extend(
                        (key.encode("ascii"), value.encode("ascii"))
                        for key, value in outgoing_trace.items()
                    )
                    message = {**message, "headers": outgoing}
                await send(message)

            try:
                await self.app(scope, receive, observed_send)
            except BaseException:
                failed = True
                raise
            finally:
                duration = time.perf_counter() - started
                route = getattr(scope.get("route"), "path", "<unmatched>")
                span.update_name(f"{method} {route}")
                span.set_attribute("http.request.method", method)
                span.set_attribute("http.route", route)
                span.set_attribute("http.response.status_code", status)
                if status >= 500 or failed:
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                self.metrics.observe(method, route, status, duration, failed)
                logging.getLogger("substrata.http").info(
                    json.dumps(
                        {
                            "event": "http.request",
                            "request_id": request_id,
                            "trace_id": f"{ids.trace_id:032x}",
                            "span_id": f"{ids.span_id:016x}",
                            "method": method,
                            "path": route,
                            "status_code": status,
                            "duration_ms": round(duration * 1000, 2),
                            "aborted": failed,
                        },
                        separators=(",", ":"),
                    )
                )
