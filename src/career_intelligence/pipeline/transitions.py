"""Deterministic pipeline status changes and event evidence rules (FR-013 M1).

Normal advances reuse the Opportunity M2 allow-list. Corrections may leave
terminal statuses only when ``correction=True`` and a note is present on the
event (validated separately). Same-status is not a status_transition.

SubmissionAttempt success is never consulted here — citing an attempt id is
evidence only (ADR-005).
"""

from __future__ import annotations

from career_intelligence.opportunities.errors import OpportunityTransitionError
from career_intelligence.opportunities.models import (
    PIPELINE_STATUSES,
    TERMINAL_STATUSES,
    PipelineStatus,
)
from career_intelligence.opportunities.transitions import validate_status_transition

from .errors import ErrorDetail, PipelineTransitionError, PipelineValidationError
from .models import PipelineEvent, PipelineEvidence

# Forward moves allowed under a correction (including reopen from terminal).
# Same-status is rejected — corrections must change something observable.
_CORRECTION_TARGETS: frozenset[PipelineStatus] = frozenset(PIPELINE_STATUSES)


def validate_pipeline_status_change(
    current: PipelineStatus,
    new: PipelineStatus,
    *,
    correction: bool = False,
) -> None:
    """Raise ``PipelineTransitionError`` when ``current -> new`` is invalid.

    ``correction=False``: M2 forward allow-list (same-status rejected here).
    ``correction=True``: any distinct known status, including leaving terminal.
    """
    if current == new:
        raise PipelineTransitionError(
            f"Status is already '{current}'; same-status is not a status change"
        )
    if current not in PIPELINE_STATUSES or new not in PIPELINE_STATUSES:
        raise PipelineTransitionError(
            f"Unknown pipeline status change: {current!r} -> {new!r}"
        )
    if correction:
        if new not in _CORRECTION_TARGETS:
            raise PipelineTransitionError(
                f"Invalid correction target status: {new!r}"
            )
        return
    if current in TERMINAL_STATUSES:
        raise PipelineTransitionError(
            f"Cannot change status from terminal state '{current}' to '{new}' "
            "without correction=True"
        )
    try:
        validate_status_transition(current, new)
    except OpportunityTransitionError as error:
        raise PipelineTransitionError(str(error)) from error


def validate_event_contract(event: PipelineEvent) -> None:
    """Fail closed when event kind, status fields, and evidence disagree."""
    errors: list[ErrorDetail] = []
    kind = event.kind
    evidence = event.evidence

    if kind == "status_transition":
        if event.from_status is None or event.to_status is None:
            errors.append(
                ErrorDetail(
                    loc=("from_status",),
                    msg="status_transition requires from_status and to_status",
                    type="value_error",
                )
            )
        else:
            try:
                validate_pipeline_status_change(
                    event.from_status,
                    event.to_status,
                    correction=False,
                )
            except PipelineTransitionError as error:
                errors.append(
                    ErrorDetail(
                        loc=("to_status",),
                        msg=str(error),
                        type="value_error",
                    )
                )
        if event.to_status == "submitted" and not _submit_evidence_ok(evidence):
            errors.append(
                ErrorDetail(
                    loc=("evidence",),
                    msg=(
                        "transition to submitted requires at least one of: "
                        "note, channel, submission_attempt_id, package, submitted_at"
                    ),
                    type="value_error",
                )
            )

    elif kind == "correction":
        if evidence.note is None:
            errors.append(
                ErrorDetail(
                    loc=("evidence", "note"),
                    msg="correction requires evidence.note",
                    type="value_error",
                )
            )
        if event.from_status is None or event.to_status is None:
            errors.append(
                ErrorDetail(
                    loc=("from_status",),
                    msg="correction requires from_status and to_status",
                    type="value_error",
                )
            )
        else:
            try:
                validate_pipeline_status_change(
                    event.from_status,
                    event.to_status,
                    correction=True,
                )
            except PipelineTransitionError as error:
                errors.append(
                    ErrorDetail(
                        loc=("to_status",),
                        msg=str(error),
                        type="value_error",
                    )
                )

    elif kind == "interview_stage_change":
        if event.interview_stage is None:
            errors.append(
                ErrorDetail(
                    loc=("interview_stage",),
                    msg="interview_stage_change requires interview_stage",
                    type="value_error",
                )
            )

    elif kind == "outcome_change":
        if event.outcome is None:
            errors.append(
                ErrorDetail(
                    loc=("outcome",),
                    msg="outcome_change requires outcome",
                    type="value_error",
                )
            )

    elif kind == "evidence_added":
        if not evidence.has_substantive_fields():
            errors.append(
                ErrorDetail(
                    loc=("evidence",),
                    msg="evidence_added requires at least one evidence field",
                    type="value_error",
                )
            )

    elif kind == "follow_up_set":
        if event.follow_up_date is None and not event.clear_follow_up_date:
            errors.append(
                ErrorDetail(
                    loc=("follow_up_date",),
                    msg=(
                        "follow_up_set requires follow_up_date or "
                        "clear_follow_up_date=True"
                    ),
                    type="value_error",
                )
            )
        if event.follow_up_date is not None and event.clear_follow_up_date:
            errors.append(
                ErrorDetail(
                    loc=("clear_follow_up_date",),
                    msg="cannot set follow_up_date and clear_follow_up_date together",
                    type="value_error",
                )
            )

    elif kind == "note":
        if evidence.note is None:
            errors.append(
                ErrorDetail(
                    loc=("evidence", "note"),
                    msg="note events require evidence.note",
                    type="value_error",
                )
            )

    if kind != "correction" and event.supersedes_event_id is not None:
        errors.append(
            ErrorDetail(
                loc=("supersedes_event_id",),
                msg="supersedes_event_id is only valid on correction events",
                type="value_error",
            )
        )

    if errors:
        raise PipelineValidationError(errors)


def _submit_evidence_ok(evidence: PipelineEvidence) -> bool:
    return any(
        (
            evidence.note is not None,
            evidence.channel is not None,
            evidence.submission_attempt_id is not None,
            evidence.package is not None,
            evidence.submitted_at is not None,
        )
    )
