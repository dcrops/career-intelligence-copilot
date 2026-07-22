"""Stable public errors for opportunity-assessment operations."""

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


class OpportunityAssessmentError(Exception):
    """Base error for the public opportunity-assessment API."""


class OpportunityAssessmentValidationError(OpportunityAssessmentError):
    """Raised when an assessor payload does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Opportunity assessment validation failed")
