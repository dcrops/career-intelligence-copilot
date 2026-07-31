"""Deterministic SubmissionAttempt status transitions (FR-012 M0).

Illegal transitions fail closed. Terminal statuses never advance. Uncertain
outcomes are never promoted to success on the same attempt.
"""

from __future__ import annotations

from datetime import datetime

from .errors import SubmissionTransitionError, SubmissionValidationError, ErrorDetail
from .models import (
    FAILURE_LIKE_STATUSES,
    SUCCESS_SUBMISSION_STATUSES,
    SUBMISSION_STATUSES,
    TERMINAL_SUBMISSION_STATUSES,
    SubmissionAttempt,
    SubmissionEvidence,
    SubmissionStatus,
)

# Allowed forward moves. Same-status is rejected (no-op updates are not transitions).
_ALLOWED: dict[SubmissionStatus, frozenset[SubmissionStatus]] = {
    "ready": frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset(
        {
            "submitted",
            "manual_completed",
            "manual_action_required",
            "failed",
            "outcome_unknown",
            "cancelled",
        }
    ),
    "manual_action_required": frozenset(
        {
            "submitted",
            "manual_completed",
            "failed",
            "outcome_unknown",
            "cancelled",
        }
    ),
    "submitted": frozenset(),
    "manual_completed": frozenset(),
    "failed": frozenset(),
    "outcome_unknown": frozenset(),
    "cancelled": frozenset(),
}


def validate_status_transition(
    current: SubmissionStatus,
    new: SubmissionStatus,
) -> None:
    """Raise ``SubmissionTransitionError`` when ``current -> new`` is invalid."""
    if current == new:
        raise SubmissionTransitionError(
            f"Status is already '{current}'; same-status updates are not transitions"
        )
    if current not in SUBMISSION_STATUSES or new not in SUBMISSION_STATUSES:
        raise SubmissionTransitionError(
            f"Unknown submission status transition: {current!r} -> {new!r}"
        )
    if current in TERMINAL_SUBMISSION_STATUSES:
        raise SubmissionTransitionError(
            f"Cannot change status from terminal state '{current}' to '{new}'"
        )
    allowed = _ALLOWED[current]
    if new not in allowed:
        raise SubmissionTransitionError(
            f"Invalid status transition: '{current}' -> '{new}'. "
            f"Allowed: {', '.join(sorted(allowed)) or '(none — terminal)'}"
        )


def validate_evidence_for_status(
    status: SubmissionStatus,
    evidence: SubmissionEvidence,
    *,
    completed_at: datetime | None,
) -> None:
    """Fail closed when evidence is insufficient for the attempt status."""
    errors: list[ErrorDetail] = []

    if status != "ready" and not evidence.owner_approved_submit:
        errors.append(
            ErrorDetail(
                loc=("evidence", "owner_approved_submit"),
                msg="owner_approved_submit must be true once an attempt leaves ready",
                type="value_error",
            )
        )

    if status in TERMINAL_SUBMISSION_STATUSES and completed_at is None:
        errors.append(
            ErrorDetail(
                loc=("completed_at",),
                msg="completed_at is required for terminal submission statuses",
                type="value_error",
            )
        )

    if status not in ("ready",) and evidence.result_code is None:
        errors.append(
            ErrorDetail(
                loc=("evidence", "result_code"),
                msg="result_code is required after an attempt leaves ready",
                type="value_error",
            )
        )

    if status not in ("ready",) and evidence.message is None:
        errors.append(
            ErrorDetail(
                loc=("evidence", "message"),
                msg="message is required after an attempt leaves ready",
                type="value_error",
            )
        )

    if status in FAILURE_LIKE_STATUSES and evidence.failure_reason is None:
        errors.append(
            ErrorDetail(
                loc=("evidence", "failure_reason"),
                msg="failure_reason is required for failed and outcome_unknown",
                type="value_error",
            )
        )

    if status in SUCCESS_SUBMISSION_STATUSES and evidence.failure_reason is not None:
        errors.append(
            ErrorDetail(
                loc=("evidence", "failure_reason"),
                msg="failure_reason must be absent for successful submission outcomes",
                type="value_error",
            )
        )

    if errors:
        raise SubmissionValidationError(errors)


def apply_status_transition(
    attempt: SubmissionAttempt,
    new_status: SubmissionStatus,
    *,
    evidence: SubmissionEvidence,
    updated_at: datetime,
    completed_at: datetime | None = None,
) -> SubmissionAttempt:
    """Return a new attempt with validated status and evidence (immutable update)."""
    validate_status_transition(attempt.status, new_status)
    terminal_completed = (
        completed_at
        if completed_at is not None
        else (updated_at if new_status in TERMINAL_SUBMISSION_STATUSES else None)
    )
    validate_evidence_for_status(
        new_status,
        evidence,
        completed_at=terminal_completed,
    )
    return attempt.model_copy(
        update={
            "status": new_status,
            "evidence": evidence,
            "updated_at": updated_at,
            "completed_at": terminal_completed,
        }
    )
