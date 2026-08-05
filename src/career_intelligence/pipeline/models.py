"""Typed contracts for Application Pipeline Tracking (FR-013 M1).

Foundation only: PipelineEvent identity, evidence refs, event kinds.
No Opportunity status writes, no tracking service, no CLI.

Invariant (ADR-005): SubmissionAttempt success does not automatically create
pipeline events or advance Opportunity.status. Events may *cite* a submission
attempt id as evidence when the owner explicitly records progress.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from career_intelligence.opportunities.models import (
    InterviewStage,
    OpportunityId,
    OutcomeKind,
    PipelineStatus,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

PipelineEventId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^ple_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

SubmissionAttemptIdRef = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^sub_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

PipelineEventKind = Literal[
    "status_transition",
    "interview_stage_change",
    "outcome_change",
    "evidence_added",
    "follow_up_set",
    "correction",
    "note",
]

PIPELINE_EVENT_KINDS: tuple[PipelineEventKind, ...] = get_args(PipelineEventKind)


class PipelineModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PackageEvidenceRef(PipelineModel):
    """Reference to the Application Package cited as pipeline evidence (FR-010)."""

    opportunity_id: OpportunityId
    prepared_at: datetime
    manifest_hash: NonEmptyString | None = None


class PipelineEvidence(PipelineModel):
    """Structured evidence attached to one PipelineEvent.

    Keep required surface small. Salary and recruiter PII are out of core M1.
    Presence of ``submission_attempt_id`` never implies an automatic status write.
    """

    note: NonEmptyString | None = None
    channel: NonEmptyString | None = None
    submission_attempt_id: SubmissionAttemptIdRef | None = None
    package: PackageEvidenceRef | None = None
    submitted_at: datetime | None = None
    rejection_reason: NonEmptyString | None = None
    offer_detail: NonEmptyString | None = None

    def has_substantive_fields(self) -> bool:
        return any(
            (
                self.note is not None,
                self.channel is not None,
                self.submission_attempt_id is not None,
                self.package is not None,
                self.submitted_at is not None,
                self.rejection_reason is not None,
                self.offer_detail is not None,
            )
        )


class PipelineEvent(PipelineModel):
    """One immutable pipeline audit event for an Opportunity.

    Opportunity remains the business system of record (stored current status).
    Events under ``data/pipeline_events/`` are append-only audit only (ADR-005).
    """

    event_id: PipelineEventId
    opportunity_id: OpportunityId
    occurred_at: datetime
    recorded_at: datetime
    kind: PipelineEventKind
    from_status: PipelineStatus | None = None
    to_status: PipelineStatus | None = None
    outcome: OutcomeKind | None = None
    interview_stage: InterviewStage | None = None
    follow_up_date: date | None = None
    clear_follow_up_date: bool = False
    evidence: PipelineEvidence = Field(default_factory=PipelineEvidence)
    actor: NonEmptyString = "owner"
    supersedes_event_id: PipelineEventId | None = None

    @field_validator("actor")
    @classmethod
    def actor_must_be_owner_or_agent(cls, value: str) -> str:
        if value == "owner" or value.startswith("agent:"):
            return value
        raise ValueError("actor must be 'owner' or 'agent:<id>'")

    @model_validator(mode="after")
    def _package_matches_opportunity(self) -> PipelineEvent:
        package = self.evidence.package
        if package is not None and package.opportunity_id != self.opportunity_id:
            raise ValueError(
                "evidence.package.opportunity_id must match event opportunity_id"
            )
        return self

    @model_validator(mode="after")
    def _supersede_not_self(self) -> PipelineEvent:
        if (
            self.supersedes_event_id is not None
            and self.supersedes_event_id == self.event_id
        ):
            raise ValueError("supersedes_event_id must not equal event_id")
        return self
