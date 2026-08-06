"""Build OrchestrationObservation from readiness snapshots (FR-016 M2).

Derived projection only — does not mutate domain state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from career_intelligence.agent.models import AgentRunId, ReadinessSnapshot
from career_intelligence.agent.readiness import ReadinessBuilder
from career_intelligence.agent.state_classes import primary_state_class

from .briefing import classify_briefing_needs
from .hashing import compute_observation_hash
from .models import OrchestrationGoal, OrchestrationObservation, OrchestrationRunId


class ObservationBuilder(Protocol):
    def build(
        self,
        goal: OrchestrationGoal,
        *,
        owner_approvals_present: bool,
        provider_available: bool = True,
        prior_agent_run_ids: tuple[AgentRunId, ...] = (),
        prior_orchestration_run_id: OrchestrationRunId | None = None,
        observed_at: datetime | None = None,
    ) -> OrchestrationObservation: ...


def observation_from_snapshot(
    snapshot: ReadinessSnapshot,
    goal: OrchestrationGoal,
    *,
    prior_agent_run_ids: tuple[AgentRunId, ...] = (),
    prior_orchestration_run_id: OrchestrationRunId | None = None,
) -> OrchestrationObservation:
    """Map a BOPA readiness snapshot into an orchestration observation."""
    labels = tuple(
        f"blocker:{code}" for code in snapshot.truth.blocking_finding_codes
    )
    # Prefer human-facing labels when codes look like labels already.
    if snapshot.truth.blocking_finding_codes:
        labels = snapshot.truth.blocking_finding_codes

    obs = OrchestrationObservation(
        opportunity_id=snapshot.opportunity_id,
        decision=snapshot.decision,
        readiness_primary_state_class=primary_state_class(snapshot),
        package_status=snapshot.package.status,
        truth_status=snapshot.truth.status,
        pipeline_status=snapshot.pipeline_status,
        owner_approvals_present=snapshot.owner_approvals_present,
        prior_agent_run_ids=prior_agent_run_ids
        or (
            (snapshot.prior_agent_run_id,)
            if snapshot.prior_agent_run_id is not None
            else ()
        ),
        prior_orchestration_run_id=prior_orchestration_run_id,
        truth_blocking_labels=labels,
        contradictory_flags=snapshot.contradictory_flags,
        briefing_need_classes=(),
        observation_hash=None,
        observed_at=snapshot.observed_at,
    )
    needs = classify_briefing_needs(obs, goal)
    obs = obs.model_copy(update={"briefing_need_classes": needs})
    return obs.model_copy(update={"observation_hash": compute_observation_hash(obs)})


class ReadinessObservationBuilder:
    """Live/static observation builder over a ReadinessBuilder."""

    def __init__(self, readiness: ReadinessBuilder) -> None:
        self._readiness = readiness

    def build(
        self,
        goal: OrchestrationGoal,
        *,
        owner_approvals_present: bool,
        provider_available: bool = True,
        prior_agent_run_ids: tuple[AgentRunId, ...] = (),
        prior_orchestration_run_id: OrchestrationRunId | None = None,
        observed_at: datetime | None = None,
    ) -> OrchestrationObservation:
        prior_id = prior_agent_run_ids[-1] if prior_agent_run_ids else None
        snapshot = self._readiness.build(
            goal.opportunity_id,
            owner_approvals_present=owner_approvals_present,
            provider_available=provider_available,
            prior_agent_run_id=prior_id,
            prior_agent_run_incomplete=False,
            observed_at=observed_at or datetime.now(tz=UTC),
        )
        return observation_from_snapshot(
            snapshot,
            goal,
            prior_agent_run_ids=prior_agent_run_ids,
            prior_orchestration_run_id=prior_orchestration_run_id,
        )


class StaticObservationBuilder:
    """Queue of observations for offline corpus / tests."""

    def __init__(self, observations: list[OrchestrationObservation] | None = None) -> None:
        self._queue: list[OrchestrationObservation] = list(observations or [])
        self._last: OrchestrationObservation | None = None

    def enqueue(self, *observations: OrchestrationObservation) -> None:
        self._queue.extend(observations)

    def build(
        self,
        goal: OrchestrationGoal,
        *,
        owner_approvals_present: bool,
        provider_available: bool = True,
        prior_agent_run_ids: tuple[AgentRunId, ...] = (),
        prior_orchestration_run_id: OrchestrationRunId | None = None,
        observed_at: datetime | None = None,
    ) -> OrchestrationObservation:
        _ = (owner_approvals_present, provider_available, observed_at)
        if self._queue:
            obs = self._queue.pop(0)
        elif self._last is not None:
            obs = self._last
        else:
            raise RuntimeError("StaticObservationBuilder has no observations")
        obs = obs.model_copy(
            update={
                "opportunity_id": goal.opportunity_id,
                "prior_agent_run_ids": prior_agent_run_ids or obs.prior_agent_run_ids,
                "prior_orchestration_run_id": prior_orchestration_run_id
                or obs.prior_orchestration_run_id,
                "owner_approvals_present": owner_approvals_present,
            }
        )
        needs = classify_briefing_needs(obs, goal)
        obs = obs.model_copy(update={"briefing_need_classes": needs})
        obs = obs.model_copy(update={"observation_hash": compute_observation_hash(obs)})
        self._last = obs
        return obs
