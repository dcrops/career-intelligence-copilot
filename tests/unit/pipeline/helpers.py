"""Shared builders for FR-013 pipeline contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

from career_intelligence.pipeline import (
    PackageEvidenceRef,
    PipelineEvent,
    PipelineEvidence,
    new_pipeline_event_id,
)

OPP_A = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"
OPP_B = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAB"
EVENT_A = "ple_01ARZ3NDEKTSV4RRFFQ69G5FAA"
EVENT_B = "ple_01ARZ3NDEKTSV4RRFFQ69G5FAB"
ATTEMPT_A = "sub_01ARZ3NDEKTSV4RRFFQ69G5FAA"

FIXED_OCCURRED = datetime(2026, 8, 5, 2, 0, 0, tzinfo=UTC)
FIXED_RECORDED = datetime(2026, 8, 5, 2, 5, 0, tzinfo=UTC)
FIXED_PREPARED = datetime(2026, 8, 5, 1, 0, 0, tzinfo=UTC)


def make_evidence(**kwargs: object) -> PipelineEvidence:
    return PipelineEvidence(**kwargs)  # type: ignore[arg-type]


def make_package_ref(
    *,
    opportunity_id: str = OPP_A,
) -> PackageEvidenceRef:
    return PackageEvidenceRef(
        opportunity_id=opportunity_id,
        prepared_at=FIXED_PREPARED,
        manifest_hash="pkghash1",
    )


def make_event(
    *,
    event_id: str = EVENT_A,
    opportunity_id: str = OPP_A,
    kind: str = "note",
    from_status: str | None = None,
    to_status: str | None = None,
    outcome: str | None = None,
    interview_stage: str | None = None,
    follow_up_date=None,
    clear_follow_up_date: bool = False,
    evidence: PipelineEvidence | None = None,
    actor: str = "owner",
    supersedes_event_id: str | None = None,
    occurred_at: datetime = FIXED_OCCURRED,
    recorded_at: datetime = FIXED_RECORDED,
) -> PipelineEvent:
    return PipelineEvent(
        event_id=event_id,
        opportunity_id=opportunity_id,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        kind=kind,  # type: ignore[arg-type]
        from_status=from_status,  # type: ignore[arg-type]
        to_status=to_status,  # type: ignore[arg-type]
        outcome=outcome,  # type: ignore[arg-type]
        interview_stage=interview_stage,  # type: ignore[arg-type]
        follow_up_date=follow_up_date,
        clear_follow_up_date=clear_follow_up_date,
        evidence=evidence or make_evidence(note="owner note"),
        actor=actor,
        supersedes_event_id=supersedes_event_id,  # type: ignore[arg-type]
    )


def fresh_event_id() -> str:
    return new_pipeline_event_id()
