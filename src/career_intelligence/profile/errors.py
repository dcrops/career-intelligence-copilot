"""Stable public errors for career-profile operations."""

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


class ProfileError(Exception):
    """Base error for the public profile API."""


class ProfileNotFoundError(ProfileError):
    """Raised when the configured profile does not exist."""


class ProfileValidationError(ProfileError):
    """Raised when profile data does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Career profile validation failed")


class ProfileStorageError(ProfileError):
    """Raised when profile persistence fails."""


class UnknownSectionError(ProfileError):
    """Raised when a requested profile section is unknown."""
