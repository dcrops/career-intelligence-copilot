"""Specialist registry for FR-016 (M1 contracts only).

Documents allow-lists and authority without implementing runtimes.
BOPA mutating tools are imported from ``career_intelligence.agent`` and must not
be redefined or widened here.
"""

from __future__ import annotations

from dataclasses import dataclass

from career_intelligence.agent.types import AGENT_ACTIONS, FORBIDDEN_ACTION_NAMES

from .types import (
    FUTURE_SPECIALIST_IDS,
    OBS_ACTIONS,
    OBS_FORBIDDEN_ACTION_NAMES,
    SpecialistId,
)


@dataclass(frozen=True, slots=True)
class SpecialistContract:
    """Static specialist boundary (not a runtime)."""

    specialist_id: SpecialistId
    display_name: str
    mutates_domain: bool
    goal_kinds_served: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    forbidden_action_names: frozenset[str]
    notes: str


BOPA_SPECIALIST = SpecialistContract(
    specialist_id="bopa",
    display_name="Bounded Opportunity Preparation Agent",
    mutates_domain=True,
    goal_kinds_served=("prepare_for_owner_review",),
    allowed_actions=tuple(AGENT_ACTIONS),
    forbidden_action_names=FORBIDDEN_ACTION_NAMES,
    notes=(
        "FR-015 frozen specialist. Mutating allow-list unchanged. "
        "Invoked only as a child run under DOS; ToolPolicy remains "
        "career_intelligence.agent.evaluate_action_policy."
    ),
)

OBS_SPECIALIST = SpecialistContract(
    specialist_id="obs",
    display_name="Operational Briefing Specialist",
    mutates_domain=False,
    goal_kinds_served=("brief_opportunity_readiness",),
    allowed_actions=tuple(OBS_ACTIONS),
    forbidden_action_names=OBS_FORBIDDEN_ACTION_NAMES,
    notes=(
        "Strictly read-only. Produces OperationalBrief and may recommend "
        "delegation; cannot prepare, verify, validate truth, submit, or "
        "mutate pipeline. Exists because BOPA's prepare_for_owner_review "
        "goal and mutating allow-list must not be broadened into a "
        "brief-only / batch-triage authority."
    ),
)

SPECIALIST_REGISTRY: dict[SpecialistId, SpecialistContract] = {
    "bopa": BOPA_SPECIALIST,
    "obs": OBS_SPECIALIST,
}


def get_specialist(specialist_id: SpecialistId) -> SpecialistContract:
    return SPECIALIST_REGISTRY[specialist_id]


def is_future_placeholder(specialist_id: str) -> bool:
    return specialist_id in FUTURE_SPECIALIST_IDS


def specialist_may_mutate(specialist_id: SpecialistId) -> bool:
    return SPECIALIST_REGISTRY[specialist_id].mutates_domain
