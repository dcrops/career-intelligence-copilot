"""Typed submission adapter contract (FR-012 M1).

Adapters execute channel-specific behaviour and return structured results.
They must not persist attempts, enforce approval, or verify packages.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from career_intelligence.opportunities.models import OpportunityId

from .models import PackageRef, SubmissionChannel, SubmissionMode, SubmissionStatus

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

AdapterOutcomeStatus = Literal[
    "submitted",
    "manual_action_required",
    "failed",
    "outcome_unknown",
    "cancelled",
]

# Adapter outcomes that the orchestrator may persist (never manual_completed).
ADAPTER_OUTCOME_STATUSES: frozenset[AdapterOutcomeStatus] = frozenset(
    {
        "submitted",
        "manual_action_required",
        "failed",
        "outcome_unknown",
        "cancelled",
    }
)


class AdapterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SubmissionAdapterRequest(AdapterModel):
    """Inputs the orchestrator passes to an adapter after all gates pass."""

    attempt_id: NonEmptyString
    opportunity_id: OpportunityId
    package: PackageRef
    channel: SubmissionChannel
    mode: SubmissionMode
    destination: NonEmptyString | None = None


class SubmissionAdapterResult(AdapterModel):
    """Structured adapter outcome — orchestrator maps this onto attempt state."""

    status: AdapterOutcomeStatus
    result_code: NonEmptyString
    message: NonEmptyString
    failure_reason: NonEmptyString | None = None

    def as_attempt_status(self) -> SubmissionStatus:
        return self.status  # type: ignore[return-value]


@runtime_checkable
class SubmissionAdapter(Protocol):
    """Minimum adapter surface required by ``SubmissionOrchestrator``."""

    @property
    def channel(self) -> SubmissionChannel:
        """Registered channel identifier for this adapter."""

    @property
    def mode(self) -> SubmissionMode:
        """Default mode this adapter runs under."""

    @property
    def requires_destination(self) -> bool:
        """When True, orchestrator refuses submit without a destination."""

    def execute(self, request: SubmissionAdapterRequest) -> SubmissionAdapterResult:
        """Perform the channel action. Must not persist attempts."""
