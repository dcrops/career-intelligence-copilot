"""Unit tests for FR-013 M1 pipeline status transitions and evidence rules."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from career_intelligence.pipeline import (
    PipelineTransitionError,
    PipelineValidationError,
    validate_event_contract,
    validate_pipeline_status_change,
)
from tests.unit.pipeline.helpers import (
    ATTEMPT_A,
    EVENT_B,
    make_event,
    make_evidence,
    make_package_ref,
)

NOW = datetime(2026, 8, 5, 3, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("assessed", "deferred"),
        ("assessed", "preparing"),
        ("assessed", "submitted"),
        ("assessed", "withdrawn"),
        ("deferred", "assessed"),
        ("deferred", "preparing"),
        ("deferred", "submitted"),
        ("preparing", "submitted"),
        ("preparing", "deferred"),
        ("preparing", "withdrawn"),
        ("submitted", "interviewing"),
        ("submitted", "offer"),
        ("submitted", "rejected"),
        ("submitted", "withdrawn"),
        ("interviewing", "offer"),
        ("interviewing", "rejected"),
        ("offer", "accepted"),
        ("offer", "rejected"),
        ("offer", "withdrawn"),
    ],
)
def test_allowed_forward_transitions(current: str, new: str) -> None:
    validate_pipeline_status_change(current, new)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("assessed", "interviewing"),
        ("assessed", "assessed"),
        ("preparing", "offer"),
        ("submitted", "preparing"),
        ("rejected", "submitted"),
        ("accepted", "offer"),
        ("withdrawn", "assessed"),
        ("interviewing", "preparing"),
    ],
)
def test_illegal_forward_transitions(current: str, new: str) -> None:
    with pytest.raises(PipelineTransitionError):
        validate_pipeline_status_change(current, new)  # type: ignore[arg-type]


def test_correction_may_leave_terminal() -> None:
    validate_pipeline_status_change(
        "rejected",
        "submitted",
        correction=True,
    )


def test_correction_rejects_same_status() -> None:
    with pytest.raises(PipelineTransitionError):
        validate_pipeline_status_change(
            "rejected",
            "rejected",
            correction=True,
        )


def test_status_transition_event_valid() -> None:
    validate_event_contract(
        make_event(
            kind="status_transition",
            from_status="preparing",
            to_status="submitted",
            evidence=make_evidence(
                submission_attempt_id=ATTEMPT_A,
                submitted_at=NOW,
                package=make_package_ref(),
            ),
        )
    )


def test_submitted_requires_evidence() -> None:
    with pytest.raises(PipelineValidationError):
        validate_event_contract(
            make_event(
                kind="status_transition",
                from_status="preparing",
                to_status="submitted",
                evidence=make_evidence(),
            )
        )


def test_correction_requires_note_and_statuses() -> None:
    with pytest.raises(PipelineValidationError):
        validate_event_contract(
            make_event(
                kind="correction",
                from_status="rejected",
                to_status="submitted",
                evidence=make_evidence(),
            )
        )
    validate_event_contract(
        make_event(
            kind="correction",
            from_status="rejected",
            to_status="submitted",
            supersedes_event_id=EVENT_B,
            evidence=make_evidence(note="mistaken rejection"),
        )
    )


def test_supersedes_only_on_correction() -> None:
    with pytest.raises(PipelineValidationError):
        validate_event_contract(
            make_event(
                kind="note",
                supersedes_event_id=EVENT_B,
                evidence=make_evidence(note="x"),
            )
        )


def test_interview_outcome_follow_up_and_evidence_kinds() -> None:
    validate_event_contract(
        make_event(
            kind="interview_stage_change",
            interview_stage="recruiter",
            evidence=make_evidence(note="screen booked"),
        )
    )
    validate_event_contract(
        make_event(
            kind="outcome_change",
            outcome="pending",
            evidence=make_evidence(note="awaiting reply"),
        )
    )
    validate_event_contract(
        make_event(
            kind="follow_up_set",
            follow_up_date=date(2026, 8, 12),
            evidence=make_evidence(),
        )
    )
    validate_event_contract(
        make_event(
            kind="follow_up_set",
            clear_follow_up_date=True,
            evidence=make_evidence(),
        )
    )
    validate_event_contract(
        make_event(
            kind="evidence_added",
            evidence=make_evidence(channel="linkedin_easy_apply"),
        )
    )


def test_illegal_status_transition_event() -> None:
    with pytest.raises(PipelineValidationError) as raised:
        validate_event_contract(
            make_event(
                kind="status_transition",
                from_status="assessed",
                to_status="interviewing",
                evidence=make_evidence(note="skip"),
            )
        )
    assert raised.value.errors
