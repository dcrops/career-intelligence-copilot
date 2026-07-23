"""Stable public errors for CV generation (FR-006 Phase A/B)."""

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


class CvGenerationError(Exception):
    """Base error for the public CV-generation API."""


class TailoringPlanValidationError(CvGenerationError):
    """Raised when a planner payload does not satisfy the TailoringPlan schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Tailoring plan validation failed")


class TailoringPlanGateError(CvGenerationError):
    """Raised when planning is refused by owner-approval or material-benefit gates."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CvGenerationValidationError(CvGenerationError):
    """Raised when a rendered CV does not satisfy schema or fidelity rules."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("CV generation validation failed")


class CvGenerationGateError(CvGenerationError):
    """Raised when generation is refused (missing plan approval or mismatched inputs)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
