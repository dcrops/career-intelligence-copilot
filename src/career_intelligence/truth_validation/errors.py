"""Stable public errors for truth-validation contracts (FR-014 M1)."""

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


class TruthValidationError(Exception):
    """Base error for the public truth-validation API."""


class TruthContractError(TruthValidationError):
    """Raised when a TruthReport or catalogue violates contract invariants."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Truth validation contract failed")


class TruthSchemaError(TruthValidationError):
    """Raised when truth-validation data does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Truth validation schema failed")
