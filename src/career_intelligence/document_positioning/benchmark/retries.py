"""Retry helper frozen before comparative judgement. Quality retries are forbidden."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from career_intelligence.document_positioning.benchmark.protocol import MAX_PROVIDER_RETRIES

T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    def __init__(self, message: str, *, attempts: int, last_error: BaseException) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


def run_with_provider_retries(
    operation: Callable[[], T],
    *,
    retryable: tuple[type[BaseException], ...],
    max_retries: int = MAX_PROVIDER_RETRIES,
    label: str,
) -> tuple[T, int]:
    """Return (result, retries_used). Does not retry to improve quality."""
    attempts = max_retries + 1
    last_error: BaseException | None = None
    for index in range(attempts):
        try:
            return operation(), index
        except retryable as error:
            last_error = error
    assert last_error is not None
    detail = _format_error(last_error)
    raise RetryExhaustedError(
        f"{label} failed after {attempts} attempt(s): {detail}",
        attempts=attempts,
        last_error=last_error,
    )


def _format_error(error: BaseException) -> str:
    details = getattr(error, "errors", None)
    if details:
        parts = []
        for item in details:
            loc = getattr(item, "loc", ())
            msg = getattr(item, "msg", str(item))
            parts.append(f"{loc}: {msg}")
        return f"{error}; " + "; ".join(parts)
    return str(error)
