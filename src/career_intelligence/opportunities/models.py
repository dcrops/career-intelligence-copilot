"""Typed domain models for durable Opportunity persistence (M1).

Index records stay lightweight. Full FR-002–FR-005 graphs live as immutable
artifact snapshots under the opportunity id. Decision/outcome fields are optional
placeholders for M2 — M1 does not implement transitions.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from career_intelligence.application_strategy.models import (
    ApplicationTier,
    PracticalValue,
    PursuitPosture,
)
from career_intelligence.opportunity_assessment.models import FitJudgment

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

OpportunityId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^opp_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

SourceKind = Literal[
    "seek",
    "linkedin",
    "indeed",
    "manual",
    "import",
    "recruiter",
    "other",
]

PipelineStatus = Literal[
    "assessed",
    "deferred",
    "preparing",
    "submitted",
    "interviewing",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
]

OwnerDecisionKind = Literal["apply", "skip", "defer"]

InterviewStage = Literal[
    "none",
    "recruiter",
    "hiring_manager",
    "technical",
    "other",
    "unknown",
]

ARTIFACT_FILENAMES: tuple[str, ...] = (
    "posting.json",
    "job_analysis.json",
    "assessment.json",
    "portfolio_match.json",
    "strategy.json",
)


class OpportunityModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OpportunityIdentity(OpportunityModel):
    """Canonical durable identity plus facets for future FR-014 (not matching)."""

    opportunity_id: OpportunityId
    created_at: datetime
    source_kind: SourceKind
    platform_job_id: NonEmptyString | None = None
    canonical_url: AnyHttpUrl | None = None
    source_url: AnyHttpUrl | None = None
    company: NonEmptyString | None = None
    title: NonEmptyString | None = None
    location_text: NonEmptyString | None = None
    content_fingerprint: NonEmptyString | None = None


class StrategySummary(OpportunityModel):
    """Minimum trusted FR-003–FR-005 facts for later comparison (M4)."""

    pursuit_posture: PursuitPosture
    application_tier: ApplicationTier
    practical_value: PracticalValue
    technical_fit: FitJudgment
    commercial_fit: FitJudgment
    portfolio_fit: FitJudgment


class OwnerDecisionRecord(OpportunityModel):
    """Optional M2 placeholder — unused by M1 workflows."""

    decision: OwnerDecisionKind
    decided_at: datetime
    notes: NonEmptyString | None = None


class OutcomeRecord(OpportunityModel):
    """Optional M2 placeholder — unused by M1 workflows."""

    interview_stage: InterviewStage = "none"
    follow_up_date: date | None = None
    notes: NonEmptyString | None = None
    updated_at: datetime


class Opportunity(OpportunityModel):
    """Durable opportunity aggregate (index record)."""

    identity: OpportunityIdentity
    status: PipelineStatus = "assessed"
    decision: OwnerDecisionRecord | None = None
    outcome: OutcomeRecord | None = None
    strategy_summary: StrategySummary
    artifact_paths: dict[str, NonEmptyString] = Field(default_factory=dict)
    updated_at: datetime

    @field_validator("artifact_paths")
    @classmethod
    def artifact_keys_are_known(cls, value: dict[str, str]) -> dict[str, str]:
        allowed = set(ARTIFACT_FILENAMES)
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(f"unknown artifact keys: {', '.join(unknown)}")
        return value

    @property
    def opportunity_id(self) -> str:
        return self.identity.opportunity_id
