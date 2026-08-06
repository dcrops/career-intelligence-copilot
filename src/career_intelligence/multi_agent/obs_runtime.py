"""Operational Briefing Specialist runtime (FR-016 M2).

Strictly read-only. Produces OperationalBrief from OrchestrationObservation.
Never prepares, validates truth, mutates packages/pipeline, or submits.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .briefing import (
    classify_briefing_needs,
    recommended_next_step_from_observation,
)
from .ids import new_operational_brief_id
from .models import (
    Handoff,
    ObsActionProposal,
    OperationalBrief,
    OrchestrationGoal,
    OrchestrationObservation,
)
from .obs_policy import evaluate_obs_action_policy, require_obs_action_allowed
from .types import ObsAction


_PIPELINE_NOTES: dict[str, str] = {
    "submitted": "Preparation is usually unnecessary after submission.",
    "interviewing": "Preparation is usually unnecessary while interviewing.",
    "offer": "Preparation is usually unnecessary after an offer.",
    "accepted": "Opportunity already accepted - preparation is not appropriate.",
    "rejected": "Opportunity rejected - preparation is not appropriate.",
    "withdrawn": "Opportunity withdrawn - preparation is not appropriate.",
}


class ObsRuntime:
    """Read-only OBS: policy-gated inspect → compose_brief → stop."""

    def execute(
        self,
        handoff: Handoff,
        goal: OrchestrationGoal,
        observation: OrchestrationObservation,
        *,
        force_regenerate: bool = False,
    ) -> OperationalBrief:
        _ = force_regenerate
        if handoff.target_specialist != "obs":
            raise ValueError("ObsRuntime only accepts obs handoffs")
        if handoff.source != "supervisor":
            raise ValueError("OBS rejects non-supervisor handoffs")

        # Policy-gated read-only actions (no domain mutation).
        step = 0
        recent: list[ObsAction] = []
        hashes: list[str] = []
        for action in (
            "inspect_readiness",
            "inspect_pipeline_context",
            "inspect_truth_blockers",
            "inspect_agent_history",
            "compose_brief",
        ):
            proposal = ObsActionProposal(
                action=action,
                rationale=f"OBS read-only step: {action}",
                evidence_refs=(f"opp:{observation.opportunity_id}",),
            )
            decision = evaluate_obs_action_policy(
                observation,
                proposal,
                recent_actions=tuple(recent),
                recent_observation_hashes=tuple(hashes),
                step_count=step,
            )
            if decision.decision == "deny":
                require_obs_action_allowed(
                    observation,
                    proposal,
                    recent_actions=tuple(recent),
                    recent_observation_hashes=tuple(hashes),
                    step_count=step,
                )
            recent.append(action)
            if observation.observation_hash:
                hashes.append(observation.observation_hash)
            step += 1

        return self._compose_brief(handoff, goal, observation)

    def _compose_brief(
        self,
        handoff: Handoff,
        goal: OrchestrationGoal,
        observation: OrchestrationObservation,
    ) -> OperationalBrief:
        needs = classify_briefing_needs(observation, goal)
        next_step, specialist = recommended_next_step_from_observation(observation, goal)
        pipeline = observation.pipeline_status
        pipeline_note = _PIPELINE_NOTES.get(pipeline) if pipeline else None

        if "pipeline_advises_against_preparation" in needs:
            owner_action = (
                "Review pipeline stage before any preparation. "
                "Do not run preparation unless you explicitly intend to."
            )
        elif "truth_blockers_need_synthesis" in needs:
            blockers = ", ".join(observation.truth_blocking_labels) or "see TruthReport"
            owner_action = (
                f"Remediate truth blockers ({blockers}), then revalidate. "
                "Do not waive findings."
            )
        elif "cross_surface_ambiguity" in needs:
            owner_action = (
                "Resolve contradictory or incomplete decision state before preparation."
            )
        elif next_step == "invoke_bopa":
            owner_action = (
                "Preparation appears appropriate if you approve. "
                "Orchestration may delegate to BOPA when allowed."
            )
        elif next_step == "owner_run_fr008":
            owner_action = (
                "Upstream FR-002–FR-005 artefacts are missing. "
                "Complete analysis via FR-008/services - not via agents."
            )
        else:
            owner_action = "Review the opportunity readiness brief and decide next steps."

        # Owner notes never grant authority — surface injection attempts as evidence only.
        evidence = list(observation.truth_blocking_labels)
        if goal.owner_notes:
            evidence.append("owner_notes:present_ignored_for_authority")
        evidence.append(f"handoff:{handoff.handoff_id}")
        if observation.observation_hash:
            evidence.append(f"obs_hash:{observation.observation_hash}")

        return OperationalBrief(
            brief_id=new_operational_brief_id(),
            opportunity_id=observation.opportunity_id,
            orchestration_run_id=handoff.orchestration_run_id,
            briefing_need_classes=needs,
            readiness_primary_state_class=observation.readiness_primary_state_class,
            pipeline_status=observation.pipeline_status,
            pipeline_note=pipeline_note,
            truth_blocker_labels=observation.truth_blocking_labels,
            package_status=observation.package_status,
            prior_agent_run_ids=observation.prior_agent_run_ids,
            recommended_next_step=next_step,
            recommended_specialist=specialist,
            owner_action_summary=owner_action,
            evidence_refs=tuple(evidence),
            observation_hash=observation.observation_hash,
            created_at=datetime.now(tz=UTC),
        )
