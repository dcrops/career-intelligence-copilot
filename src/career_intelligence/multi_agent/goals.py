"""Owner goals for FR-016 M3 learning-proof CLI."""

from __future__ import annotations

from typing import Literal

from career_intelligence.opportunities.models import OpportunityId

from .models import OrchestrationGoal

OwnerOrchestrationGoalName = Literal["brief", "prepare", "prepare_then_brief"]
OWNER_ORCHESTRATION_GOALS: tuple[OwnerOrchestrationGoalName, ...] = (
    "brief",
    "prepare",
    "prepare_then_brief",
)


def goal_from_owner_name(
    name: OwnerOrchestrationGoalName,
    opportunity_id: OpportunityId,
    *,
    owner_notes: str | None = None,
) -> OrchestrationGoal:
    """Map owner-facing goal names to typed OrchestrationGoal."""
    if name == "brief":
        return OrchestrationGoal(
            goal_kind="brief_opportunity_readiness",
            opportunity_id=opportunity_id,
            owner_notes=owner_notes,
            brief_only=True,
            synthesize_after_prepare=False,
        )
    if name == "prepare":
        return OrchestrationGoal(
            goal_kind="coordinate_opportunity_readiness",
            opportunity_id=opportunity_id,
            owner_notes=owner_notes,
            brief_only=False,
            synthesize_after_prepare=False,
        )
    if name == "prepare_then_brief":
        return OrchestrationGoal(
            goal_kind="coordinate_opportunity_readiness",
            opportunity_id=opportunity_id,
            owner_notes=owner_notes,
            brief_only=False,
            synthesize_after_prepare=True,
        )
    raise ValueError(f"unsupported owner goal: {name!r}")


def owner_goal_label(goal: OrchestrationGoal) -> OwnerOrchestrationGoalName:
    """Inverse label for presentation."""
    if goal.goal_kind == "brief_opportunity_readiness" or goal.brief_only:
        return "brief"
    if goal.synthesize_after_prepare:
        return "prepare_then_brief"
    return "prepare"
