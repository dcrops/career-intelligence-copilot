"""Typed domain models for durable Opportunity persistence (M1–M4, FR-009 M0).

Index records stay lightweight. Full FR-002–FR-005 graphs live as immutable
artifact snapshots under the opportunity id. M2 adds owner decision and outcome
logging. M3 allows incomplete legacy imports without fabricating assessments.
M4 ranking consumes StrategySummary and lifecycle fields via a separate
comparison package.

FR-009 M0 adds owner review metadata and an optional duplicate relationship as
additive contracts (ADR-004). An Opportunity is the durable record of a
successfully analysed job candidate that may require an owner decision — it does
not imply the owner chose to apply. Review metadata, owner decision, pipeline
status, and duplicate state stay separate fields because they answer different
questions and change at different times.
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
    model_validator,
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

DuplicateEvidenceKind = Literal[
    "platform_job_id",
    "canonical_url",
    "identity_facets",
    "content_fingerprint",
    "owner_judgment",
]

PIPELINE_STATUSES: tuple[PipelineStatus, ...] = get_args(PipelineStatus)
OWNER_DECISION_KINDS: tuple[OwnerDecisionKind, ...] = get_args(OwnerDecisionKind)
OUTCOME_KINDS: tuple[OutcomeKind, ...] = get_args(OutcomeKind)
INTERVIEW_STAGES: tuple[InterviewStage, ...] = get_args(InterviewStage)
DUPLICATE_EVIDENCE_KINDS: tuple[DuplicateEvidenceKind, ...] = get_args(
    DuplicateEvidenceKind
)

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
    """Canonical durable identity plus facets for future FR-009 matching (not matching yet)."""

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


class OpportunityReview(OpportunityModel):
    """Owner-authored review metadata for the FR-009 queue (ADR-004).

    Orthogonal flags rather than one lifecycle enum: an Opportunity can be
    reviewed and pinned, or unreviewed and deferred, without enumerating every
    combination. Defaults describe a never-reviewed record, so records written
    before FR-009 read back unchanged in meaning.

    ``defer_until`` is a date (matching ``OutcomeRecord.follow_up_date``) so
    "currently deferred" is decidable without timezone arithmetic. None of these
    fields is a pipeline status: application progress stays on
    ``Opportunity.status`` and belongs to FR-012.
    """

    reviewed_at: datetime | None = None
    pinned: bool = False
    defer_until: date | None = None
    archived_at: datetime | None = None

    @model_validator(mode="after")
    def archived_records_are_not_pinned(self) -> OpportunityReview:
        if self.archived_at is not None and self.pinned:
            raise ValueError(
                "pinned=True contradicts archived_at: archiving hides a record "
                "from active review, so the pin must be cleared"
            )
        return self


class DuplicateRelation(OpportunityModel):
    """Owner-confirmed link from a duplicate record to its canonical record.

    Non-destructive by contract: the duplicate keeps its own identity,
    provenance, and artifacts, and remains auditable. ``evidence`` records why
    the link was accepted. Detection is not implemented in FR-009 M0.
    """

    duplicate_of: OpportunityId
    confirmed_at: datetime
    evidence: tuple[DuplicateEvidenceKind, ...] = ()


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
    review: OpportunityReview = Field(default_factory=OpportunityReview)
    duplicate: DuplicateRelation | None = None
    updated_at: datetime

    @field_validator("artifact_paths")
    @classmethod
    def artifact_keys_are_known(cls, value: dict[str, str]) -> dict[str, str]:
        allowed = set(ARTIFACT_FILENAMES)
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(f"unknown artifact keys: {', '.join(unknown)}")
        return value

    @model_validator(mode="after")
    def duplicate_does_not_point_at_itself(self) -> Opportunity:
        if (
            self.duplicate is not None
            and self.duplicate.duplicate_of == self.identity.opportunity_id
        ):
            raise ValueError(
                "duplicate.duplicate_of must reference a different opportunity_id"
            )
        return self

    @property
    def opportunity_id(self) -> str:
        return self.identity.opportunity_id
