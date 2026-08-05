"""Typed contracts for Bounded Opportunity Preparation Agent (FR-015 M1).

Foundation only: goals, readiness snapshots, action proposals, runs, audit events,
and stop reasons. No agent runtime, tool adapters, provider calls, or CLI.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from career_intelligence.opportunities.models import OpportunityId

from .types import (
    DEFAULT_MAX_STEPS,
    AgentAction,
    AgentGoalKind,
    AgentRunStatus,
    AgentStopReason,
    AuditEventKind,
    OwnerDecisionKind,
    PackageStatus,
    PolicyDecisionKind,
    ReadinessStateClass,
    TruthStatus,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

AgentRunId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^agr_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

AgentStepId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^ags_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

AgentAuditEventId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^aae_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]


class AgentGoal(BaseModel):
    """Owner-declared bounded goal for one Opportunity."""

    model_config = ConfigDict(extra="forbid")

    goal_kind: AgentGoalKind = "prepare_for_owner_review"
    opportunity_id: OpportunityId
    owner_notes: str | None = Field(
        default=None,
        description="Optional short notes; never tool authority.",
    )


class ArtefactPresence(BaseModel):
    """Which FR-002–FR-005 artefacts are present on the Opportunity."""

    model_config = ConfigDict(extra="forbid")

    job_analysis: bool
    assessment: bool
    portfolio_match: bool
    strategy: bool

    @property
    def all_present(self) -> bool:
        return (
            self.job_analysis
            and self.assessment
            and self.portfolio_match
            and self.strategy
        )


class PackageReadiness(BaseModel):
    """Observed application-package readiness (derived; not SoT)."""

    model_config = ConfigDict(extra="forbid")

    status: PackageStatus
    cv_present: bool = False
    cover_letter_present: bool = False
    manifest_ref: NonEmptyString | None = None

    @model_validator(mode="after")
    def _consistency(self) -> PackageReadiness:
        if self.status == "absent":
            if self.cv_present or self.cover_letter_present:
                raise ValueError("absent package cannot report cv/cover letter present")
            if self.manifest_ref is not None:
                raise ValueError("absent package cannot have manifest_ref")
        if self.status == "incomplete" and self.cv_present and self.cover_letter_present:
            raise ValueError("incomplete package cannot have both drafts present")
        if self.status == "present" and not (self.cv_present and self.cover_letter_present):
            raise ValueError("present package requires cv and cover letter present")
        if self.status == "integrity_failed" and self.manifest_ref is None:
            raise ValueError("integrity_failed package requires manifest_ref")
        return self


class TruthReadiness(BaseModel):
    """Observed FR-014 truth readiness for the package (derived; not SoT)."""

    model_config = ConfigDict(extra="forbid")

    status: TruthStatus
    report_ref: NonEmptyString | None = None
    owner_edited_markdown_since_validation: bool = False
    blocking_finding_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _consistency(self) -> TruthReadiness:
        if self.status == "absent" and self.report_ref is not None:
            raise ValueError("absent truth status cannot have report_ref")
        if self.status in {"pass", "fail", "stale", "review_required", "warning"}:
            if self.report_ref is None:
                raise ValueError(f"truth status {self.status!r} requires report_ref")
        if self.owner_edited_markdown_since_validation and self.status == "pass":
            raise ValueError(
                "owner-edited Markdown since validation cannot remain truth status pass"
            )
        return self


class ReadinessSnapshot(BaseModel):
    """Typed observation of domain readiness for one Opportunity.

    Derived projection only. Opportunity, package, truth, workflow, submission,
    and pipeline records remain authoritative elsewhere.
    """

    model_config = ConfigDict(extra="forbid")

    opportunity_id: OpportunityId
    decision: OwnerDecisionKind | None
    artefacts: ArtefactPresence
    package: PackageReadiness
    truth: TruthReadiness
    owner_approvals_present: bool = False
    clarification_required: bool = False
    clarification_message: NonEmptyString | None = None
    provider_available: bool = True
    contradictory_flags: tuple[str, ...] = ()
    prior_agent_run_id: AgentRunId | None = None
    prior_agent_run_incomplete: bool = False
    snapshot_hash: NonEmptyString | None = Field(
        default=None,
        description="Optional content hash of normalised snapshot fields for loop detection.",
    )
    observed_at: datetime

    @model_validator(mode="after")
    def _consistency(self) -> ReadinessSnapshot:
        if self.clarification_required and self.clarification_message is None:
            raise ValueError("clarification_required requires clarification_message")
        if not self.clarification_required and self.clarification_message is not None:
            raise ValueError("clarification_message requires clarification_required")
        if self.prior_agent_run_incomplete and self.prior_agent_run_id is None:
            raise ValueError("prior_agent_run_incomplete requires prior_agent_run_id")
        return self


class AgentActionProposal(BaseModel):
    """Structured next-action proposal (from ActionProposer in M2+)."""

    model_config = ConfigDict(extra="forbid")

    action: AgentAction
    rationale: NonEmptyString = Field(..., max_length=2000)
    evidence_refs: tuple[NonEmptyString, ...] = ()
    primary_state_class: ReadinessStateClass | None = None


class PolicyDecision(BaseModel):
    """Result of deterministic ToolPolicy evaluation."""

    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecisionKind
    action: AgentAction | None = None
    primary_state_class: ReadinessStateClass
    applicable_state_classes: tuple[ReadinessStateClass, ...]
    approved_actions: tuple[AgentAction, ...]
    deny_reason: NonEmptyString | None = None
    stop_reason: AgentStopReason | None = None

    @model_validator(mode="after")
    def _consistency(self) -> PolicyDecision:
        if self.decision == "allow" and self.action is None:
            raise ValueError("allow requires action")
        if self.decision == "deny" and self.deny_reason is None:
            raise ValueError("deny requires deny_reason")
        if self.decision == "allow" and self.deny_reason is not None:
            raise ValueError("allow must not set deny_reason")
        return self


class ProviderMetadata(BaseModel):
    """Optional model/provider metadata (filled when a proposer is used)."""

    model_config = ConfigDict(extra="forbid")

    provider: NonEmptyString | None = None
    model: NonEmptyString | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class AgentAuditEvent(BaseModel):
    """Append-only audit event within an AgentRun."""

    model_config = ConfigDict(extra="forbid")

    event_id: AgentAuditEventId
    kind: AuditEventKind
    at: datetime
    step_id: AgentStepId | None = None
    state_class: ReadinessStateClass | None = None
    action: AgentAction | None = None
    policy_decision: PolicyDecisionKind | None = None
    stop_reason: AgentStopReason | None = None
    message: NonEmptyString | None = None
    refs: tuple[NonEmptyString, ...] = ()
    provider: ProviderMetadata | None = None


class AgentStep(BaseModel):
    """One policy-gated step inside an AgentRun."""

    model_config = ConfigDict(extra="forbid")

    step_id: AgentStepId
    index: int = Field(..., ge=0)
    snapshot: ReadinessSnapshot
    primary_state_class: ReadinessStateClass
    proposal: AgentActionProposal | None = None
    policy: PolicyDecision
    executed: bool = False
    skipped_as_idempotent: bool = False
    service_result_summary: NonEmptyString | None = None
    error_summary: NonEmptyString | None = None


class CompletedOperationRecord(BaseModel):
    """Record that a mutating service operation already succeeded in this run."""

    model_config = ConfigDict(extra="forbid")

    action: AgentAction
    at: datetime
    result_ref: NonEmptyString | None = None
    skipped_as_idempotent: bool = False


class AgentRun(BaseModel):
    """Durable agent-run record (audit/recovery only — not Opportunity SoT)."""

    model_config = ConfigDict(extra="forbid")

    agent_run_id: AgentRunId
    goal: AgentGoal
    status: AgentRunStatus
    step_count: int = Field(default=0, ge=0)
    max_steps: int = Field(default=DEFAULT_MAX_STEPS, ge=1)
    last_snapshot: ReadinessSnapshot | None = None
    primary_state_class: ReadinessStateClass | None = None
    stop_reason: AgentStopReason | None = None
    checkpoint_ref: NonEmptyString | None = None
    events: tuple[AgentAuditEvent, ...] = ()
    steps: tuple[AgentStep, ...] = ()
    completed_operations: tuple[CompletedOperationRecord, ...] = ()
    provider: ProviderMetadata | None = None
    owner_approvals_present: bool = False
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _consistency(self) -> AgentRun:
        if self.goal.opportunity_id and self.last_snapshot is not None:
            if self.last_snapshot.opportunity_id != self.goal.opportunity_id:
                raise ValueError("last_snapshot opportunity_id must match goal")
        if self.status in {"completed", "failed", "cancelled"} and self.stop_reason is None:
            raise ValueError(f"terminal status {self.status!r} requires stop_reason")
        if self.status == "awaiting_owner" and self.stop_reason is None:
            raise ValueError("awaiting_owner requires stop_reason")
        if self.status == "running" and self.stop_reason is not None:
            raise ValueError("running status must not set stop_reason")
        if self.step_count > self.max_steps:
            raise ValueError("step_count cannot exceed max_steps")
        if self.steps and len(self.steps) != self.step_count:
            raise ValueError("steps length must equal step_count when steps are set")
        return self
