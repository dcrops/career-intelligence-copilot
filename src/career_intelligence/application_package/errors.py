"""Stable public errors for application package preparation (FR-010)."""

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


class ApplicationPackageError(Exception):
    """Base error for the public application-package API."""


class ApplicationPackageNotFoundError(ApplicationPackageError):
    """Raised when no package manifest exists for an opportunity."""


class ApplicationPackageEligibilityError(ApplicationPackageError):
    """Raised when an Opportunity is not eligible for package preparation."""


class ApplicationPackageValidationError(ApplicationPackageError):
    """Raised when package data does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Application package validation failed")


class ApplicationPackageStorageError(ApplicationPackageError):
    """Raised when package manifest persistence fails."""


class ApplicationPackageIntegrityError(ApplicationPackageError):
    """Raised when a persisted package references missing or unreadable drafts."""
