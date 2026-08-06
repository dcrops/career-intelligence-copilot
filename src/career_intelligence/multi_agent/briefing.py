"""Classify when OBS briefing adds value beyond BOPA (FR-016 M1/M2).

Pure functions only — no I/O, no LLM, no service calls.
"""

from __future__ import annotations

from career_intelligence.pipeline.constants import ACTIVE_PIPELINE_STATUSES

from .models import OrchestrationGoal, OrchestrationObservation
from .types import BriefingNeedClass, RecommendedNextStep, SpecialistId

# Pipeline statuses where preparing via BOPA is usually the wrong first move.
_BRIEF_FIRST_PIPELINE: frozenset[str] = frozenset(ACTIVE_PIPELINE_STATUSES) | frozenset(
    {"rejected", "withdrawn", "accepted"}
)


def classify_briefing_needs(
    observation: OrchestrationObservation,
    goal: OrchestrationGoal,
) -> tuple[BriefingNeedClass, ...]:
    """Return briefing-need classes that justify OBS over broadening BOPA."""
    found: list[BriefingNeedClass] = []

    if goal.goal_kind == "brief_opportunity_readiness" or goal.brief_only:
        found.append("owner_requested_brief_only")

    pipeline = observation.pipeline_status
    if pipeline is not None and pipeline in _BRIEF_FIRST_PIPELINE:
        if pipeline != "preparing":
            found.append("pipeline_advises_against_preparation")

    if observation.contradictory_flags:
        found.append("cross_surface_ambiguity")
    elif observation.decision is None and (
        observation.package_status not in {None, "absent"}
        or observation.truth_status not in {None, "absent"}
    ):
        found.append("cross_surface_ambiguity")

    if observation.truth_blocking_labels:
        found.append("truth_blockers_need_synthesis")

    if observation.prior_agent_run_ids:
        found.append("prior_agent_history_material")
        if (
            goal.goal_kind == "coordinate_opportunity_readiness"
            and getattr(goal, "synthesize_after_prepare", False)
        ):
            found.append("post_specialist_synthesis")

    if not found:
        found.append("no_briefing_delta")

    seen: set[BriefingNeedClass] = set()
    ordered: list[BriefingNeedClass] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return tuple(ordered)


def primary_briefing_need(
    observation: OrchestrationObservation,
    goal: OrchestrationGoal,
) -> BriefingNeedClass:
    needs = classify_briefing_needs(observation, goal)
    return needs[0]


def obs_adds_value_beyond_bopa(
    observation: OrchestrationObservation,
    goal: OrchestrationGoal,
) -> bool:
    """True when OBS provides a briefing delta BOPA should not absorb."""
    needs = classify_briefing_needs(observation, goal)
    return needs != ("no_briefing_delta",)


def recommended_next_step_from_observation(
    observation: OrchestrationObservation,
    goal: OrchestrationGoal,
) -> tuple[RecommendedNextStep, SpecialistId | None]:
    """Deterministic recommendation used by briefs and delegation matrix tests."""
    needs = classify_briefing_needs(observation, goal)

    if "truth_blockers_need_synthesis" in needs:
        return "owner_remediate_truth", None

    if "owner_requested_brief_only" in needs and goal.goal_kind == "brief_opportunity_readiness":
        return "owner_review", None

    if "pipeline_advises_against_preparation" in needs:
        return "owner_review", None

    if "cross_surface_ambiguity" in needs:
        return "owner_review", None

    if goal.goal_kind == "coordinate_opportunity_readiness" and not goal.brief_only:
        if (
            observation.decision == "apply"
            and observation.package_status in {None, "absent", "stale", "incomplete"}
            and "pipeline_advises_against_preparation" not in needs
            and "cross_surface_ambiguity" not in needs
        ):
            return "invoke_bopa", "bopa"

    if observation.readiness_primary_state_class in {
        "missing_analysis",
        "missing_assessment",
        "missing_portfolio_match",
        "missing_strategy",
    }:
        return "owner_run_fr008", None

    return "owner_review", None


def approved_specialists_for(
    observation: OrchestrationObservation,
    goal: OrchestrationGoal,
) -> tuple[SpecialistId, ...]:
    """Specialists DelegationPolicy may admit for this goal/observation."""
    if goal.goal_kind == "brief_opportunity_readiness" or goal.brief_only:
        return ("obs",)

    approved: list[SpecialistId] = []
    if obs_adds_value_beyond_bopa(observation, goal):
        approved.append("obs")

    next_step, specialist = recommended_next_step_from_observation(observation, goal)
    if next_step == "invoke_bopa" and specialist == "bopa":
        approved.append("bopa")
    elif not approved:
        approved.append("obs")

    seen: set[SpecialistId] = set()
    out: list[SpecialistId] = []
    for s in approved:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return tuple(out)


def select_next_specialist(
    observation: OrchestrationObservation,
    goal: OrchestrationGoal,
    *,
    specialist_visit_counts: dict[SpecialistId, int] | None = None,
    obs_completed_for_hash: bool = False,
    bopa_completed: bool = False,
) -> SpecialistId | None:
    """Deterministic specialist selection for DOS (no LLM)."""
    _ = specialist_visit_counts
    approved = approved_specialists_for(observation, goal)
    if not approved:
        return None

    needs_obs = obs_adds_value_beyond_bopa(observation, goal)
    wants_bopa = "bopa" in approved

    if goal.goal_kind == "brief_opportunity_readiness" or goal.brief_only:
        if obs_completed_for_hash:
            return None
        return "obs" if "obs" in approved else None

    if needs_obs and "obs" in approved and not obs_completed_for_hash:
        needs = classify_briefing_needs(observation, goal)
        brief_first = any(
            n in needs
            for n in (
                "pipeline_advises_against_preparation",
                "cross_surface_ambiguity",
                "truth_blockers_need_synthesis",
                "owner_requested_brief_only",
                "batch_triage",
                "brief_before_mutate",
            )
        )
        post_synth = "post_specialist_synthesis" in needs and bopa_completed
        if brief_first or post_synth:
            return "obs"
        if wants_bopa and not bopa_completed:
            return "bopa"
        return "obs"

    if wants_bopa and not bopa_completed:
        return "bopa"

    if "obs" in approved and not obs_completed_for_hash:
        return "obs"

    return None
