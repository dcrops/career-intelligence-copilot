"""Typed contracts for FR-016 multi-agent orchestration (M1).

Foundation only: goals, observations, handoffs, orchestration runs, OBS briefs,
delegation proposals, and audit events. No supervisor runtime, specialist
executors, CLI, persistence stores, or framework integration.
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

from career_intelligence.agent.models import AgentRunId
from career_intelligence.agent.types import ReadinessStateClass
from career_intelligence.opportunities.models import OpportunityId

from .types import (
    DEFAULT_MAX_ORCHESTRATION_STEPS,
    DEFAULT_MAX_VISITS_PER_SPECIALIST,
    BriefingNeedClass,
    DelegationDecisionKind,
    HandoffAcceptance,
    ObsAction,
    OrchestrationAuditEventKind,
    OrchestrationGoalKind,
    OrchestrationRunStatus,
    OrchestrationStopReason,
    RecommendedNextStep,
    SpecialistId,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

OrchestrationRunId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^orr_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

HandoffId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^hof_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

OrchestrationAuditEventId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^oae_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

OperationalBriefId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^obr_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]


class OrchestrationGoal(BaseModel):
    """Owner-declared orchestration goal (typed; never free-form chat authority)."""

    model_config = ConfigDict(extra="forbid")

    goal_kind: OrchestrationGoalKind
    opportunity_id: OpportunityId
    owner_notes: str | None = Field(
        default=None,
        description="Optional short notes; never tool or delegation authority.",
    )
    brief_only: bool = Field(
        default=False,
        description=(
            "When true with coordinate goal, forces OBS-first brief and blocks "
            "BOPA until owner explicitly approves mutate path (M2+)."
        ),
    )
    synthesize_after_prepare: bool = Field(
        default=False,
        description=(
            "When true on coordinate goals, DOS invokes OBS once after BOPA "
            "completes for an owner-facing synthesis brief."
        ),
    )

    @model_validator(mode="after")
    def _consistency(self) -> OrchestrationGoal:
        if self.goal_kind == "brief_opportunity_readiness" and not self.brief_only:
            # brief_only is implied for brief goals; allow either representation.
            pass
        return self


class OrchestrationObservation(BaseModel):
    """Derived cross-surface observation for DOS routing.

    Not a source of truth. Opportunity, package, truth, pipeline, submission,
    workflow, and AgentRun records remain authoritative elsewhere.
    """

    model_config = ConfigDict(extra="forbid")

    opportunity_id: OpportunityId
    decision: NonEmptyString | None = None
    readiness_primary_state_class: ReadinessStateClass | None = None
    package_status: NonEmptyString | None = None
    truth_status: NonEmptyString | None = None
    pipeline_status: NonEmptyString | None = None
    owner_approvals_present: bool = False
    prior_agent_run_ids: tuple[AgentRunId, ...] = ()
    prior_orchestration_run_id: OrchestrationRunId | None = None
    truth_blocking_labels: tuple[NonEmptyString, ...] = ()
    contradictory_flags: tuple[str, ...] = ()
    briefing_need_classes: tuple[BriefingNeedClass, ...] = ()
    observation_hash: NonEmptyString | None = None
    observed_at: datetime


class ObsActionProposal(BaseModel):
    """Structured OBS action proposal (proposer fills in M2+; M1 is data shape)."""

    model_config = ConfigDict(extra="forbid")

    action: ObsAction
    rationale: NonEmptyString = Field(..., max_length=2000)
    evidence_refs: tuple[NonEmptyString, ...] = ()


class ObsPolicyDecision(BaseModel):
    """Result of deterministic OBS ToolPolicy evaluation."""

    model_config = ConfigDict(extra="forbid")

    decision: DelegationDecisionKind
    action: ObsAction | None = None
    approved_actions: tuple[ObsAction, ...]
    deny_reason: NonEmptyString | None = None
    stop_reason: OrchestrationStopReason | None = None

    @model_validator(mode="after")
    def _consistency(self) -> ObsPolicyDecision:
        if self.decision == "allow" and self.action is None:
            raise ValueError("allow requires action")
        if self.decision == "deny" and self.deny_reason is None:
            raise ValueError("deny requires deny_reason")
        if self.decision == "allow" and self.deny_reason is not None:
            raise ValueError("allow must not set deny_reason")
        return self


class SpecialistDelegationProposal(BaseModel):
    """Proposal to invoke a specialist (from deterministic matrix or optional LLM)."""

    model_config = ConfigDict(extra="forbid")

    target_specialist: SpecialistId
    rationale: NonEmptyString = Field(..., max_length=2000)
    requested_goal_kind: NonEmptyString
    evidence_refs: tuple[NonEmptyString, ...] = ()


class DelegationDecision(BaseModel):
    """Result of deterministic DelegationPolicy evaluation."""

    model_config = ConfigDict(extra="forbid")

    decision: DelegationDecisionKind
    target_specialist: SpecialistId | None = None
    approved_specialists: tuple[SpecialistId, ...]
    deny_reason: NonEmptyString | None = None
    stop_reason: OrchestrationStopReason | None = None

    @model_validator(mode="after")
    def _consistency(self) -> DelegationDecision:
        if self.decision == "allow" and self.target_specialist is None:
            raise ValueError("allow requires target_specialist")
        if self.decision == "deny" and self.deny_reason is None:
            raise ValueError("deny requires deny_reason")
        if self.decision == "allow" and self.deny_reason is not None:
            raise ValueError("allow must not set deny_reason")
        return self


class OperationalBrief(BaseModel):
    """OBS output: owner-facing read-only briefing (derived; not SoT).

    Captures cross-surface synthesis that BOPA must not absorb by broadening its
    mutating ``prepare_for_owner_review`` responsibility.
    """

    model_config = ConfigDict(extra="forbid")

    brief_id: OperationalBriefId
    opportunity_id: OpportunityId
    orchestration_run_id: OrchestrationRunId | None = None
    briefing_need_classes: tuple[BriefingNeedClass, ...]
    readiness_primary_state_class: ReadinessStateClass | None = None
    pipeline_status: NonEmptyString | None = None
    pipeline_note: NonEmptyString | None = Field(
        default=None,
        description="Advisory only — never pipeline authority.",
    )
    truth_blocker_labels: tuple[NonEmptyString, ...] = ()
    package_status: NonEmptyString | None = None
    prior_agent_run_ids: tuple[AgentRunId, ...] = ()
    recommended_next_step: RecommendedNextStep
    recommended_specialist: SpecialistId | None = None
    owner_action_summary: NonEmptyString
    evidence_refs: tuple[NonEmptyString, ...] = ()
    observation_hash: NonEmptyString | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _consistency(self) -> OperationalBrief:
        if self.recommended_next_step == "invoke_bopa" and self.recommended_specialist not in {
            None,
            "bopa",
        }:
            raise ValueError("invoke_bopa requires recommended_specialist bopa or None")
        if self.recommended_next_step == "invoke_obs" and self.recommended_specialist not in {
            None,
            "obs",
        }:
            raise ValueError("invoke_obs requires recommended_specialist obs or None")
        if "no_briefing_delta" in self.briefing_need_classes and len(self.briefing_need_classes) > 1:
            raise ValueError("no_briefing_delta cannot combine with other need classes")
        return self


class Handoff(BaseModel):
    """Typed, append-only specialist handoff record.

    Free-form chat is never an authoritative handoff. Acceptance is policy-gated.
    """

    model_config = ConfigDict(extra="forbid")

    handoff_id: HandoffId
    orchestration_run_id: OrchestrationRunId
    source: NonEmptyString = Field(
        ...,
        description="Always 'supervisor' for executable handoffs in FR-016.",
    )
    target_specialist: SpecialistId
    opportunity_id: OpportunityId
    requested_goal_kind: NonEmptyString
    observed_state_hash: NonEmptyString | None = None
    input_artefact_refs: tuple[NonEmptyString, ...] = ()
    preconditions: tuple[NonEmptyString, ...] = ()
    expected_output_kind: NonEmptyString
    owner_approval_status: NonEmptyString
    policy_decision: DelegationDecisionKind
    policy_deny_reason: NonEmptyString | None = None
    reason: NonEmptyString
    acceptance: HandoffAcceptance = "pending"
    acceptance_reason: NonEmptyString | None = None
    child_agent_run_id: AgentRunId | None = None
    child_brief_id: OperationalBriefId | None = None
    idempotency_key: NonEmptyString | None = Field(
        default=None,
        description=(
            "Stable key: orchestration_run_id|target|goal|state_hash. "
            "Duplicate accepted handoffs with the same key are rejected."
        ),
    )
    created_at: datetime
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def _consistency(self) -> Handoff:
        if self.source != "supervisor":
            raise ValueError("executable handoffs must source from supervisor")
        if self.policy_decision == "deny" and self.policy_deny_reason is None:
            raise ValueError("deny policy_decision requires policy_deny_reason")
        if self.policy_decision == "allow" and self.policy_deny_reason is not None:
            raise ValueError("allow must not set policy_deny_reason")
        if self.acceptance in {
            "accepted",
            "executing",
            "completed",
            "stopped",
        } and self.policy_decision != "allow":
            raise ValueError(f"{self.acceptance} handoff requires prior allow decision")
        if self.acceptance in {
            "rejected",
            "stale",
            "cancelled",
            "policy_blocked",
            "stopped",
        } and self.acceptance_reason is None:
            raise ValueError(f"{self.acceptance} requires acceptance_reason")
        if self.target_specialist == "bopa" and self.child_brief_id is not None:
            raise ValueError("bopa handoff must not carry child_brief_id")
        return self


class SpecialistVisitRecord(BaseModel):
    """Visit accounting for loop prevention."""

    model_config = ConfigDict(extra="forbid")

    specialist_id: SpecialistId
    visit_count: int = Field(..., ge=0)
    last_handoff_id: HandoffId | None = None
    last_observation_hash: NonEmptyString | None = None
    completed_output_refs: tuple[NonEmptyString, ...] = ()


class OrchestrationAuditEvent(BaseModel):
    """Append-only orchestration audit event."""

    model_config = ConfigDict(extra="forbid")

    event_id: OrchestrationAuditEventId
    kind: OrchestrationAuditEventKind
    at: datetime
    specialist_id: SpecialistId | None = None
    handoff_id: HandoffId | None = None
    policy_decision: DelegationDecisionKind | None = None
    stop_reason: OrchestrationStopReason | None = None
    message: NonEmptyString | None = None
    refs: tuple[NonEmptyString, ...] = ()


class OrchestrationRun(BaseModel):
    """Parent orchestration run (audit/recovery only — not Opportunity SoT)."""

    model_config = ConfigDict(extra="forbid")

    orchestration_run_id: OrchestrationRunId
    goal: OrchestrationGoal
    status: OrchestrationRunStatus
    step_count: int = Field(default=0, ge=0)
    max_steps: int = Field(default=DEFAULT_MAX_ORCHESTRATION_STEPS, ge=1)
    max_visits_per_specialist: int = Field(
        default=DEFAULT_MAX_VISITS_PER_SPECIALIST,
        ge=1,
    )
    active_specialist: SpecialistId | None = None
    active_handoff_id: HandoffId | None = None
    last_observation: OrchestrationObservation | None = None
    last_brief_id: OperationalBriefId | None = None
    child_agent_run_ids: tuple[AgentRunId, ...] = ()
    handoff_ids: tuple[HandoffId, ...] = ()
    specialist_visits: tuple[SpecialistVisitRecord, ...] = ()
    stop_reason: OrchestrationStopReason | None = None
    owner_action_required: NonEmptyString | None = None
    checkpoint_ref: NonEmptyString | None = None
    events: tuple[OrchestrationAuditEvent, ...] = ()
    owner_approvals_present: bool = False
    provider_available: bool = True
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _consistency(self) -> OrchestrationRun:
        if self.goal.opportunity_id and self.last_observation is not None:
            if self.last_observation.opportunity_id != self.goal.opportunity_id:
                raise ValueError("last_observation opportunity_id must match goal")
        if self.status in {"completed", "failed", "cancelled"} and self.stop_reason is None:
            raise ValueError(f"terminal status {self.status!r} requires stop_reason")
        if self.status == "awaiting_owner" and self.stop_reason is None:
            raise ValueError("awaiting_owner requires stop_reason")
        if self.status == "running" and self.stop_reason is not None:
            raise ValueError("running status must not set stop_reason")
        if self.step_count > self.max_steps:
            raise ValueError("step_count cannot exceed max_steps")
        if self.active_specialist is not None and self.active_handoff_id is None:
            raise ValueError("active_specialist requires active_handoff_id")
        return self
