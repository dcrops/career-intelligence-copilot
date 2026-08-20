"""Errors for bounded CV positioning (M3). Fail closed — never a generic success."""

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


class CvPositioningError(Exception):
    """Base error for bounded CV positioning."""


class CvPositioningValidationError(CvPositioningError):
    """Structured output or claim validation failed."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("CV positioning validation failed")


class CvPositioningProviderError(CvPositioningError):
    """LLM/provider failure. Not a successful generic-summary package."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CoverLetterPositioningError(Exception):
    """Base error for bounded cover-letter positioning (M4)."""


class CoverLetterPositioningValidationError(CoverLetterPositioningError):
    """Structured output, claim, or quality validation failed."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Cover-letter positioning validation failed")


class CoverLetterPositioningProviderError(CoverLetterPositioningError):
    """LLM/provider failure. Not a successful generic-letter package."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
