"""Typed domain models for durable Opportunity persistence (M1–M4).

Index records stay lightweight. Full FR-002–FR-005 graphs live as immutable
artifact snapshots under the opportunity id. M2 adds owner decision and outcome
logging. M3 allows incomplete legacy imports without fabricating assessments.
M4 ranking consumes StrategySummary and lifecycle fields via a separate
comparison package.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, get_args

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

OutcomeKind = Literal[
    "pending",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    "unknown",
]

InterviewStage = Literal[
    "none",
    "recruiter",
    "hiring_manager",
    "technical",
    "other",
    "unknown",
]

PIPELINE_STATUSES: tuple[PipelineStatus, ...] = get_args(PipelineStatus)
OWNER_DECISION_KINDS: tuple[OwnerDecisionKind, ...] = get_args(OwnerDecisionKind)
OUTCOME_KINDS: tuple[OutcomeKind, ...] = get_args(OutcomeKind)
INTERVIEW_STAGES: tuple[InterviewStage, ...] = get_args(InterviewStage)

TERMINAL_STATUSES: frozenset[PipelineStatus] = frozenset(
    {"accepted", "rejected", "withdrawn"}
)

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
    """What the owner chose to do (human decision — independent of status/outcome)."""

    decision: OwnerDecisionKind
    decided_at: datetime
    notes: NonEmptyString | None = None


class OutcomeRecord(OpportunityModel):
    """Historical result details (independent of owner decision and pipeline status)."""

    outcome: OutcomeKind = "pending"
    interview_stage: InterviewStage = "none"
    follow_up_date: date | None = None
    notes: NonEmptyString | None = None
    updated_at: datetime


class LegacyImportProvenance(OpportunityModel):
    """Migration provenance for one-time legacy tracker CSV imports (M3)."""

    source_file: NonEmptyString
    source_row_number: int = Field(ge=1)
    import_fingerprint: NonEmptyString
    imported_at: datetime
    legacy_status: NonEmptyString | None = None
    legacy_outcome: NonEmptyString | None = None
    legacy_source: NonEmptyString | None = None


class Opportunity(OpportunityModel):
    """Durable opportunity aggregate (index record)."""

    identity: OpportunityIdentity
    status: PipelineStatus = "assessed"
    decision: OwnerDecisionRecord | None = None
    outcome: OutcomeRecord | None = None
    # None for legacy imports that never ran FR-003–FR-005 (honest incomplete record).
    strategy_summary: StrategySummary | None = None
    artifact_paths: dict[str, NonEmptyString] = Field(default_factory=dict)
    legacy_import: LegacyImportProvenance | None = None
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
