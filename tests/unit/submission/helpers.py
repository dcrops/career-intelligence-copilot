"""Shared builders for FR-012 submission contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

from career_intelligence.submission import (
    PackageRef,
    SubmissionAttempt,
    SubmissionEvidence,
    new_submission_attempt_id,
)

OPP_A = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"
OPP_B = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAB"
ATTEMPT_A = "sub_01ARZ3NDEKTSV4RRFFQ69G5FAA"
ATTEMPT_B = "sub_01ARZ3NDEKTSV4RRFFQ69G5FAB"

FIXED_CREATED = datetime(2026, 7, 31, 4, 0, 0, tzinfo=UTC)
FIXED_PREPARED = datetime(2026, 7, 31, 3, 0, 0, tzinfo=UTC)


def make_evidence(
    *,
    owner_approved_submit: bool = True,
    result_code: str | None = None,
    message: str | None = None,
    failure_reason: str | None = None,
) -> SubmissionEvidence:
    return SubmissionEvidence(
        owner_approved_submit=owner_approved_submit,
        result_code=result_code,
        message=message,
        failure_reason=failure_reason,
    )


def make_attempt(
    *,
    attempt_id: str = ATTEMPT_A,
    opportunity_id: str = OPP_A,
    status: str = "ready",
    channel: str = "manual_assisted",
    mode: str = "assist_only",
    destination: str | None = "https://example.com/jobs/1",
    evidence: SubmissionEvidence | None = None,
    completed_at: datetime | None = None,
    updated_at: datetime | None = None,
    created_at: datetime = FIXED_CREATED,
) -> SubmissionAttempt:
    return SubmissionAttempt(
        attempt_id=attempt_id,
        opportunity_id=opportunity_id,
        package=PackageRef(
            opportunity_id=opportunity_id,
            prepared_at=FIXED_PREPARED,
            manifest_hash="abc123",
        ),
        channel=channel,  # type: ignore[arg-type]
        mode=mode,  # type: ignore[arg-type]
        destination=destination,
        status=status,  # type: ignore[arg-type]
        created_at=created_at,
        updated_at=updated_at or created_at,
        completed_at=completed_at,
        evidence=evidence or make_evidence(owner_approved_submit=True),
    )


def fresh_attempt_id() -> str:
    return new_submission_attempt_id()
