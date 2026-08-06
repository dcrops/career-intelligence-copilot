"""Thin BOPA adapter for FR-016 DOS (M2).

Translates typed handoffs into existing AgentRuntime calls. Does not change
BOPA allow-list, ToolPolicy, or responsibilities.
"""

from __future__ import annotations

from dataclasses import dataclass

from career_intelligence.agent.errors import AgentProviderError, AgentRuntimeError
from career_intelligence.agent.models import AgentGoal, AgentRun
from career_intelligence.agent.runtime import AgentRuntime
from career_intelligence.agent.models import AgentRunId
from career_intelligence.agent.types import AgentStopReason

from .models import Handoff


@dataclass(frozen=True, slots=True)
class BopaSpecialistResult:
    """Typed result from a BOPA child run."""

    agent_run: AgentRun
    stop_reason: AgentStopReason | None
    status: str
    skipped_as_idempotent: bool = False


class BopaSpecialistAdapter:
    """Adapter: MultiAgent Handoff → AgentRuntime → AgentRun reference."""

    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    def execute(
        self,
        handoff: Handoff,
        *,
        owner_approvals_present: bool,
        provider_available: bool = True,
        resume_agent_run_id: str | None = None,
    ) -> BopaSpecialistResult:
        if handoff.target_specialist != "bopa":
            raise AgentRuntimeError("BopaSpecialistAdapter only accepts bopa handoffs")
        if handoff.source != "supervisor":
            raise AgentRuntimeError("BOPA adapter rejects non-supervisor handoffs")

        try:
            if resume_agent_run_id is not None:
                run = self._runtime.resume(
                    resume_agent_run_id,
                    owner_approvals_present=owner_approvals_present,
                    provider_available=provider_available,
                )
                skipped = any(op.skipped_as_idempotent for op in run.completed_operations)
            else:
                goal = AgentGoal(
                    goal_kind="prepare_for_owner_review",
                    opportunity_id=handoff.opportunity_id,
                    owner_notes=None,
                )
                run = self._runtime.start(
                    goal,
                    owner_approvals_present=owner_approvals_present,
                    provider_available=provider_available,
                )
                skipped = False
        except AgentProviderError:
            raise
        except AgentRuntimeError:
            raise

        return BopaSpecialistResult(
            agent_run=run,
            stop_reason=run.stop_reason,
            status=run.status,
            skipped_as_idempotent=skipped,
        )
