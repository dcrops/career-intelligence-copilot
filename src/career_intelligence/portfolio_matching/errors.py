"""Stable public errors for portfolio-matching operations."""

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


class PortfolioMatchingError(Exception):
    """Base error for the public portfolio-matching API."""


class PortfolioMatchingValidationError(PortfolioMatchingError):
    """Raised when a matcher payload does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Portfolio matching validation failed")
