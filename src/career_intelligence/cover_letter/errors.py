"""Stable public errors for cover letter generation (FR-007)."""

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


class CoverLetterError(Exception):
    """Base error for the public cover-letter API."""


class CoverLetterPlanValidationError(CoverLetterError):
    """Raised when a planner payload does not satisfy the CoverLetterPlan schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Cover letter plan validation failed")


class CoverLetterPlanGateError(CoverLetterError):
    """Raised when planning is refused by owner-approval or material-benefit gates."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CoverLetterGenerationValidationError(CoverLetterError):
    """Raised when a rendered cover letter does not satisfy schema or fidelity rules."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Cover letter generation validation failed")


class CoverLetterGenerationGateError(CoverLetterError):
    """Raised when generation is refused (missing plan approval or mismatched inputs)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
