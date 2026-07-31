"""Unit tests for FR-012 M0 submission models and evidence rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from career_intelligence.submission import (
    PackageRef,
    SubmissionAttempt,
    SubmissionEvidence,
    SubmissionValidationError,
    new_submission_attempt_id,
    validate_evidence_for_status,
)
from tests.unit.submission.helpers import (
    ATTEMPT_A,
    FIXED_CREATED,
    FIXED_PREPARED,
    OPP_A,
    OPP_B,
    make_attempt,
    make_evidence,
)


def test_attempt_id_pattern() -> None:
    attempt_id = new_submission_attempt_id()
    assert attempt_id.startswith("sub_")
    assert len(attempt_id) == 30
    SubmissionAttempt.model_validate(make_attempt(attempt_id=attempt_id).model_dump())


def test_rejects_invalid_attempt_id() -> None:
    with pytest.raises(ValidationError):
        make_attempt(attempt_id="attempt_not_ulid")


def test_package_must_match_opportunity() -> None:
    with pytest.raises(ValidationError):
        SubmissionAttempt(
            attempt_id=ATTEMPT_A,
            opportunity_id=OPP_A,
            package=PackageRef(opportunity_id=OPP_B, prepared_at=FIXED_PREPARED),
            channel="fake",
            mode="adapter_action",
            destination=None,
            status="ready",
            created_at=FIXED_CREATED,
            updated_at=FIXED_CREATED,
            evidence=make_evidence(),
        )


def test_evidence_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SubmissionEvidence.model_validate(
            {
                "owner_approved_submit": True,
                "screenshot_path": "/tmp/x.png",
            }
        )


def test_ready_allows_sparse_evidence() -> None:
    validate_evidence_for_status(
        "ready",
        make_evidence(owner_approved_submit=False),
        completed_at=None,
    )


def test_leaving_ready_requires_approval_and_result() -> None:
    with pytest.raises(SubmissionValidationError) as exc:
        validate_evidence_for_status(
            "in_progress",
            make_evidence(owner_approved_submit=False),
            completed_at=None,
        )
    locs = {error.loc for error in exc.value.errors}
    assert ("evidence", "owner_approved_submit") in locs
    assert ("evidence", "result_code") in locs
    assert ("evidence", "message") in locs


def test_failed_requires_failure_reason() -> None:
    completed = datetime(2026, 7, 31, 5, 0, 0, tzinfo=UTC)
    with pytest.raises(SubmissionValidationError) as exc:
        validate_evidence_for_status(
            "failed",
            make_evidence(
                owner_approved_submit=True,
                result_code="adapter_error",
                message="adapter raised",
            ),
            completed_at=completed,
        )
    assert any(error.loc == ("evidence", "failure_reason") for error in exc.value.errors)


def test_success_rejects_failure_reason() -> None:
    completed = datetime(2026, 7, 31, 5, 0, 0, tzinfo=UTC)
    with pytest.raises(SubmissionValidationError) as exc:
        validate_evidence_for_status(
            "submitted",
            make_evidence(
                owner_approved_submit=True,
                result_code="ok",
                message="submitted",
                failure_reason="should not be set",
            ),
            completed_at=completed,
        )
    assert any(error.loc == ("evidence", "failure_reason") for error in exc.value.errors)


def test_terminal_requires_completed_at() -> None:
    with pytest.raises(SubmissionValidationError) as exc:
        validate_evidence_for_status(
            "cancelled",
            make_evidence(
                owner_approved_submit=True,
                result_code="cancelled",
                message="owner cancelled",
            ),
            completed_at=None,
        )
    assert any(error.loc == ("completed_at",) for error in exc.value.errors)
