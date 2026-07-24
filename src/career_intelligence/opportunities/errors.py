"""Stable public errors for opportunity persistence (M1)."""

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


class OpportunityError(Exception):
    """Base error for the public opportunity API."""


class OpportunityNotFoundError(OpportunityError):
    """Raised when an opportunity id is not in the store."""


class OpportunityValidationError(OpportunityError):
    """Raised when opportunity data does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Opportunity validation failed")


class OpportunityStorageError(OpportunityError):
    """Raised when opportunity persistence fails."""


class OpportunityArtifactExistsError(OpportunityStorageError):
    """Raised when an immutable artifact path already exists."""


class OpportunityTransitionError(OpportunityError):
    """Raised when a pipeline status transition is not allowed."""
