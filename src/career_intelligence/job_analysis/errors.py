"""Stable public errors for job-analysis operations."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorDetail:
    loc: tuple[str | int, ...]
    msg: str
    type: str

    @classmethod
    def from_pydantic(cls, error: dict[str, Any]) -> "ErrorDetail":
        return cls(
            loc=tuple(error.get("loc", ())),
            msg=str(error.get("msg", "Invalid value")),
            type=str(error.get("type", "value_error")),
        )


class JobAnalysisError(Exception):
    """Base error for the public job-analysis API."""


class JobAnalysisValidationError(JobAnalysisError):
    """Raised when extracted analysis does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Job analysis validation failed")
