"""Cooperative whole-job deadlines shared by bounded outbound operations."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime

_deadline: ContextVar[datetime | None] = ContextVar("substrata_job_deadline", default=None)


class JobDeadlineExceeded(TimeoutError):
    """The durable job's frozen whole-run deadline has elapsed."""


@contextmanager
def job_deadline(value: datetime | None):
    token = _deadline.set(value)
    try:
        yield
    finally:
        _deadline.reset(token)


def require_time() -> None:
    value = _deadline.get()
    if value is not None and datetime.now(UTC) >= value:
        raise JobDeadlineExceeded("Whole-job deadline exceeded.")


def bounded_timeout(requested: float) -> float:
    value = _deadline.get()
    if value is None:
        return requested
    remaining = (value - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        raise JobDeadlineExceeded("Whole-job deadline exceeded.")
    return max(0.05, min(requested, remaining))
