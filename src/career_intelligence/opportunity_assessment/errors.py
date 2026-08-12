"""Stable public errors for opportunity-assessment operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# FR-019 M1.1 — selective retry codes for stochastic *generated assessment* output.
# Unknown / unclassified validation types remain unrecoverable (fail closed).
RETRYABLE_ASSESSMENT_VALIDATION_TYPES: frozenset[str] = frozenset(
    {
        "judgment_material_inconsistency",
        "evidence_ref_name_mismatch",
        "evidence_ref_index_out_of_range",
    }
)

UNRECOVERABLE_ASSESSMENT_VALIDATION_TYPES: frozenset[str] = frozenset(
    {
        "forbidden_embedded_input",
    }
)


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


class OpportunityAssessmentError(Exception):
    """Base error for the public opportunity-assessment API."""


class OpportunityAssessmentValidationError(OpportunityAssessmentError):
    """Raised when an assessor payload does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__(self._format_message(errors))

    @staticmethod
    def _format_message(errors: list[ErrorDetail]) -> str:
        if not errors:
            return "Opportunity assessment validation failed"
        rendered = "; ".join(
            f"{_format_loc(item.loc)}: {item.msg}" for item in errors[:5]
        )
        suffix = "" if len(errors) <= 5 else f" (+{len(errors) - 5} more)"
        return f"Opportunity assessment validation failed ({rendered}{suffix})"


def assessment_validation_is_retryable(
    error: OpportunityAssessmentValidationError,
) -> bool:
    """Return True only when every detail is an approved stochastic output code.

    Unknown types, mixed trust-boundary errors, and empty error lists fail closed
    (unrecoverable). Does not inspect free-text messages.
    """
    if not error.errors:
        return False
    types = {item.type for item in error.errors}
    if types & UNRECOVERABLE_ASSESSMENT_VALIDATION_TYPES:
        return False
    return types <= RETRYABLE_ASSESSMENT_VALIDATION_TYPES


def _format_loc(loc: tuple[str | int, ...]) -> str:
    return ".".join(str(part) for part in loc) if loc else "(root)"
