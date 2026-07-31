"""Typed contracts for Submission Assistance (FR-012 M0).

Foundation only: attempt identity, evidence, channel/mode/status. No adapters,
no orchestration behaviour, no PipelineStatus, no network.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from career_intelligence.opportunities.models import OpportunityId

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SubmissionAttemptId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^sub_[0-9A-HJKMNP-TV-Z]{26}$"),
]

SubmissionChannel = Literal["manual_assisted", "fake"]
SubmissionMode = Literal["assist_only", "adapter_action"]
SubmissionStatus = Literal[
    "ready",
    "in_progress",
    "submitted",
    "manual_completed",
    "manual_action_required",
    "failed",
    "outcome_unknown",
    "cancelled",
]

SUBMISSION_STATUSES: tuple[SubmissionStatus, ...] = (
    "ready",
    "in_progress",
    "submitted",
    "manual_completed",
    "manual_action_required",
    "failed",
    "outcome_unknown",
    "cancelled",
)

TERMINAL_SUBMISSION_STATUSES: frozenset[SubmissionStatus] = frozenset(
    {
        "submitted",
        "manual_completed",
        "failed",
        "outcome_unknown",
        "cancelled",
    }
)

SUCCESS_SUBMISSION_STATUSES: frozenset[SubmissionStatus] = frozenset(
    {"submitted", "manual_completed"}
)

FAILURE_LIKE_STATUSES: frozenset[SubmissionStatus] = frozenset(
    {"failed", "outcome_unknown"}
)


class SubmissionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PackageRef(SubmissionModel):
    """Reference to the Application Package used for this attempt (FR-010)."""

    opportunity_id: OpportunityId
    prepared_at: datetime
    manifest_hash: NonEmptyString | None = None


class SubmissionEvidence(SubmissionModel):
    """Minimum audit fields for a submission attempt.

    Screenshots, receipts, and external confirmation URLs are deferred.
    """

    owner_approved_submit: bool
    result_code: NonEmptyString | None = None
    message: NonEmptyString | None = None
    failure_reason: NonEmptyString | None = None


class SubmissionReadinessReport(SubmissionModel):
    """Read-only readiness probe for owner inspection (FR-012 M2).

    Produced by ``SubmissionOrchestrator.check_readiness`` — never creates attempts.
    """

    opportunity_id: OpportunityId
    ready: bool
    decision: NonEmptyString | None = None
    package_verified: bool
    package_prepared_at: datetime | None = None
    available_channels: list[SubmissionChannel] = Field(default_factory=list)
    messages: list[NonEmptyString] = Field(default_factory=list)


class SubmissionAttempt(SubmissionModel):
    """One append-only attempt to submit (or record) an application.

    Opportunity remains the business system of record. Attempts are audit /
    recovery data under ``data/submission_attempts/``.
    """

    attempt_id: SubmissionAttemptId
    opportunity_id: OpportunityId
    package: PackageRef
    channel: SubmissionChannel
    mode: SubmissionMode
    destination: NonEmptyString | None = None
    status: SubmissionStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    evidence: SubmissionEvidence = Field(...)

    @model_validator(mode="after")
    def _package_matches_opportunity(self) -> SubmissionAttempt:
        if self.package.opportunity_id != self.opportunity_id:
            raise ValueError(
                "package.opportunity_id must match attempt opportunity_id"
            )
        return self
