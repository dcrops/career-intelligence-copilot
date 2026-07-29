"""Typed workflow state — orchestration control plane (FR-008 M0).

Holds run control, acquisition provenance, domain artefact slots, approval
state, and execution metadata. Does not replace FR-001–FR-007 domain models
or Opportunity persistence (ADR-002).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis, JobPosting
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile.models import CareerProfile

from .events import WorkflowEvent
from .types import (
    AcquisitionSourceKind,
    ApprovalKind,
    FailureClassification,
    NodeKind,
    OwnerDecisionKind,
    RetryNextAction,
    TERMINAL_WORKFLOW_STATUSES,
    WorkflowStatus,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

WorkflowRunId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^wfr_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

OpportunityIdRef = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^opp_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]


class OrchestrationModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorkflowErrorInfo(OrchestrationModel):
    """Last failure recorded on the control plane (not an exception)."""

    message: NonEmptyString
    recoverable: bool = False
    node_id: NonEmptyString | None = None
    detail: NonEmptyString | None = None


class WorkflowControl(OrchestrationModel):
    """Mutable run cursor and lifecycle status."""

    run_id: WorkflowRunId
    status: WorkflowStatus = "running"
    current_node: NonEmptyString | None = None
    last_error: WorkflowErrorInfo | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class AcquisitionEnvelope(OrchestrationModel):
    """How a job entered the system — separate from Job Analysis content."""

    source_kind: AcquisitionSourceKind
    source_identifier: NonEmptyString | None = None
    source_url: AnyHttpUrl | None = None
    acquired_at: datetime
    raw_content: NonEmptyString
    normalised_content: NonEmptyString | None = None
    warnings: list[NonEmptyString] = Field(default_factory=list)
    title: NonEmptyString | None = None
    company: NonEmptyString | None = None


class DomainArtefacts(OrchestrationModel):
    """Trusted FR-001–FR-005 slots (append-once; None until produced).

    Package/submission slots are reserved for FR-010/FR-011 and remain unset
    in the FR-008 vertical slice.
    """

    profile: CareerProfile | None = None
    posting: JobPosting | None = None
    job_analysis: JobAnalysis | None = None
    assessment: OpportunityAssessment | None = None
    portfolio_match: PortfolioMatch | None = None
    strategy: ApplicationStrategy | None = None
    opportunity_id: OpportunityIdRef | None = None


class CompletedNodeRecord(OrchestrationModel):
    """Record that a node finished successfully (for resume / labelling)."""

    node_id: NonEmptyString
    kind: NodeKind
    completed_at: datetime


class RetryState(OrchestrationModel):
    """Active bounded-retry cursor for one failed eligible node.

    Survives process exit via checkpoints. Cleared when the node later succeeds.
    Does not store provider payloads or secrets.
    """

    node_id: NonEmptyString
    attempts_used: int = Field(ge=1)
    max_attempts: int = Field(ge=1)
    last_classification: FailureClassification
    last_message: NonEmptyString
    exhausted: bool = False
    next_action: RetryNextAction = "retry_node"

    @model_validator(mode="after")
    def attempts_consistent(self) -> RetryState:
        if self.attempts_used > self.max_attempts:
            raise ValueError("attempts_used must be <= max_attempts")
        if self.exhausted and self.next_action != "fail_closed":
            raise ValueError("exhausted retry state requires next_action=fail_closed")
        if not self.exhausted and self.next_action != "retry_node":
            raise ValueError("active retry state requires next_action=retry_node")
        return self


class ExecutionMetadata(OrchestrationModel):
    """Append-only execution history and completed-node labels."""

    events: list[WorkflowEvent] = Field(default_factory=list)
    completed_nodes: list[CompletedNodeRecord] = Field(default_factory=list)
    schema_version: NonEmptyString = "1"


class ApprovalState(OrchestrationModel):
    """Owner-approval interrupt and recorded decision."""

    pending_kind: ApprovalKind | None = None
    pending_options: list[OwnerDecisionKind] = Field(default_factory=list)
    pending_message: NonEmptyString | None = None
    pending_requested_at: datetime | None = None
    owner_decision: OwnerDecisionKind | None = None
    decided_at: datetime | None = None

    @model_validator(mode="after")
    def pending_fields_are_consistent(self) -> ApprovalState:
        has_pending = self.pending_kind is not None
        if has_pending:
            if not self.pending_options:
                raise ValueError("pending approval requires pending_options")
            if self.pending_requested_at is None:
                raise ValueError("pending approval requires pending_requested_at")
        else:
            if self.pending_options:
                raise ValueError("pending_options require pending_kind")
            if self.pending_message is not None:
                raise ValueError("pending_message requires pending_kind")
            if self.pending_requested_at is not None:
                raise ValueError("pending_requested_at requires pending_kind")

        if self.owner_decision is not None and self.decided_at is None:
            raise ValueError("owner_decision requires decided_at")
        if self.decided_at is not None and self.owner_decision is None:
            raise ValueError("decided_at requires owner_decision")
        return self


class WorkflowState(OrchestrationModel):
    """Shared typed state for one application workflow run."""

    control: WorkflowControl
    acquisition: AcquisitionEnvelope | None = None
    artefacts: DomainArtefacts = Field(default_factory=DomainArtefacts)
    execution: ExecutionMetadata = Field(default_factory=ExecutionMetadata)
    approval: ApprovalState = Field(default_factory=ApprovalState)
    retry: RetryState | None = None

    @model_validator(mode="after")
    def lifecycle_invariants(self) -> WorkflowState:
        status = self.control.status

        if status == "awaiting_owner":
            if self.approval.pending_kind is None:
                raise ValueError(
                    "status 'awaiting_owner' requires approval.pending_kind"
                )

        if status in TERMINAL_WORKFLOW_STATUSES:
            if self.control.completed_at is None:
                raise ValueError(f"status '{status}' requires control.completed_at")
            if self.approval.pending_kind is not None:
                raise ValueError(
                    f"status '{status}' must not leave a pending approval"
                )

        if status == "running" and self.approval.pending_kind is not None:
            raise ValueError("status 'running' must not have pending approval")

        if self.control.last_error is not None and status not in {
            "failed",
            "running",
            "awaiting_owner",
        }:
            # Allow last_error retained after recovery while running/awaiting;
            # terminal completed/cancelled should clear it.
            if status in {"completed", "cancelled"}:
                raise ValueError(
                    f"status '{status}' must clear control.last_error"
                )

        event_run_ids = {event.run_id for event in self.execution.events}
        if event_run_ids and event_run_ids != {self.control.run_id}:
            raise ValueError("execution events must use the same run_id as control")

        return self

    @property
    def run_id(self) -> str:
        return self.control.run_id

    @property
    def status(self) -> WorkflowStatus:
        return self.control.status
