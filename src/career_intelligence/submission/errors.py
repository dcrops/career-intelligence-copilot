"""Stable public errors for submission assistance contracts (FR-012)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorDetail:
    loc: tuple[str | int, ...]
    msg: str
    type: str

    @classmethod
    def from_pydantic(cls, error: dict[str, Any]) -> ErrorDetail:
        return cls(
            loc=tuple(error.get("loc", ())),
            msg=str(error.get("msg", "Invalid value")),
            type=str(error.get("type", "value_error")),
        )


class SubmissionError(Exception):
    """Base error for the public submission API."""


class SubmissionAttemptNotFoundError(SubmissionError):
    """Raised when a submission attempt id is not in the store."""


class SubmissionValidationError(SubmissionError):
    """Raised when submission data does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Submission validation failed")


class SubmissionStorageError(SubmissionError):
    """Raised when submission-attempt persistence fails."""


class SubmissionTransitionError(SubmissionError):
    """Raised when an attempt status transition is illegal."""


class SubmissionAppendOnlyError(SubmissionError):
    """Raised when a write would violate append-only attempt identity."""


class SubmissionGateError(SubmissionError):
    """Raised when a submission precondition or approval gate fails."""


class SubmissionDuplicateError(SubmissionError):
    """Raised when a new attempt would violate duplicate / idempotency policy."""


class SubmissionChannelError(SubmissionError):
    """Raised when the requested channel is unknown or not registered."""
