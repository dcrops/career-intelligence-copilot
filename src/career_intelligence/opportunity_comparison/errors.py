"""Errors for opportunity comparison (M4)."""

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


class OpportunityComparisonError(Exception):
    """Base error for the public comparison API."""


class OpportunityComparisonValidationError(OpportunityComparisonError):
    """Raised when comparison input or output fails validation."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Opportunity comparison validation failed")
