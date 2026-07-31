"""Unit tests for FR-012 M0 submission status transitions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from career_intelligence.submission import (
    SubmissionTransitionError,
    SubmissionValidationError,
    apply_status_transition,
    validate_status_transition,
)
from tests.unit.submission.helpers import make_attempt, make_evidence

NOW = datetime(2026, 7, 31, 6, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("ready", "in_progress"),
        ("ready", "cancelled"),
        ("in_progress", "submitted"),
        ("in_progress", "manual_completed"),
        ("in_progress", "manual_action_required"),
        ("in_progress", "failed"),
        ("in_progress", "outcome_unknown"),
        ("in_progress", "cancelled"),
        ("manual_action_required", "submitted"),
        ("manual_action_required", "manual_completed"),
        ("manual_action_required", "failed"),
        ("manual_action_required", "outcome_unknown"),
        ("manual_action_required", "cancelled"),
    ],
)
def test_allowed_transitions(current: str, new: str) -> None:
    validate_status_transition(current, new)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("ready", "submitted"),
        ("ready", "failed"),
        ("ready", "ready"),
        ("submitted", "failed"),
        ("failed", "submitted"),
        ("outcome_unknown", "submitted"),
        ("cancelled", "in_progress"),
        ("manual_completed", "manual_action_required"),
        ("in_progress", "ready"),
    ],
)
def test_illegal_transitions(current: str, new: str) -> None:
    with pytest.raises(SubmissionTransitionError):
        validate_status_transition(current, new)  # type: ignore[arg-type]


def test_apply_transition_sets_completed_at_for_terminal() -> None:
    attempt = make_attempt(status="in_progress", evidence=make_evidence(
        result_code="running",
        message="adapter started",
    ))
    updated = apply_status_transition(
        attempt,
        "submitted",
        evidence=make_evidence(
            result_code="ok",
            message="confirmed",
        ),
        updated_at=NOW,
    )
    assert updated.status == "submitted"
    assert updated.completed_at == NOW
    assert updated.updated_at == NOW


def test_apply_transition_rejects_bad_evidence() -> None:
    attempt = make_attempt(status="in_progress", evidence=make_evidence(
        result_code="running",
        message="adapter started",
    ))
    with pytest.raises(SubmissionValidationError):
        apply_status_transition(
            attempt,
            "failed",
            evidence=make_evidence(
                result_code="err",
                message="boom",
            ),
            updated_at=NOW,
        )


def test_outcome_unknown_never_becomes_success_on_same_attempt() -> None:
    with pytest.raises(SubmissionTransitionError):
        validate_status_transition("outcome_unknown", "submitted")
