"""Stable public errors for application preparation orchestration (FR-011)."""

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


class ApplicationPreparationError(Exception):
    """Base error for the public application-preparation API."""


class PreparationRunNotFoundError(ApplicationPreparationError):
    """Raised when a preparation run id is not in the store."""


class ApplicationPreparationValidationError(ApplicationPreparationError):
    """Raised when preparation-run data does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Application preparation validation failed")


class ApplicationPreparationStorageError(ApplicationPreparationError):
    """Raised when preparation-run persistence fails."""
