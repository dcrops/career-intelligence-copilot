"""Deterministic OBS ToolPolicy (FR-016 M1).

Read-only allow-list only. Does not execute tools or mutate domain state.
"""

from __future__ import annotations

from .errors import ObsPolicyError
from .models import ObsActionProposal, ObsPolicyDecision, OrchestrationObservation
from .types import (
    DEFAULT_MAX_OBS_STEPS,
    OBS_ACTIONS,
    OBS_FORBIDDEN_ACTION_NAMES,
    ObsAction,
)

_ALWAYS: frozenset[ObsAction] = frozenset(OBS_ACTIONS)


def approved_obs_actions_for(_observation: OrchestrationObservation) -> frozenset[ObsAction]:
    """OBS actions are state-light: all read-only actions remain potentially legal.

    Hard rules in evaluate_obs_action_policy still block forbidden names, loops,
    and max steps. Runtime (M2) may narrow further; M1 keeps the closed set.
    """
    return _ALWAYS


def evaluate_obs_action_policy(
    observation: OrchestrationObservation,
    proposal: ObsActionProposal,
    *,
    recent_actions: tuple[ObsAction, ...] = (),
    recent_observation_hashes: tuple[str, ...] = (),
    step_count: int = 0,
    max_steps: int | None = None,
) -> ObsPolicyDecision:
    """Return allow/deny for a proposed OBS action."""
    approved = tuple(sorted(approved_obs_actions_for(observation)))

    if proposal.action in OBS_FORBIDDEN_ACTION_NAMES:  # type: ignore[comparison-overlap]
        return ObsPolicyDecision(
            decision="deny",
            approved_actions=approved,  # type: ignore[arg-type]
            deny_reason=f"forbidden OBS action {proposal.action!r}",
            stop_reason="policy_blocked",
        )

    if proposal.action not in OBS_ACTIONS:
        return ObsPolicyDecision(
            decision="deny",
            approved_actions=approved,  # type: ignore[arg-type]
            deny_reason=f"action {proposal.action!r} not in OBS allow-list",
            stop_reason="policy_blocked",
        )

    limit = max_steps if max_steps is not None else DEFAULT_MAX_OBS_STEPS
    if step_count >= limit and proposal.action != "stop":
        return ObsPolicyDecision(
            decision="deny",
            approved_actions=approved,  # type: ignore[arg-type]
            deny_reason=f"OBS max_steps {limit} reached",
            stop_reason="orchestration_max_steps",
        )

    if _is_noop_repeat(proposal.action, recent_actions, observation, recent_observation_hashes):
        return ObsPolicyDecision(
            decision="deny",
            approved_actions=approved,  # type: ignore[arg-type]
            deny_reason="repeated no-op OBS action for unchanged observation",
            stop_reason="no_progress",
        )

    # recommend_delegation never grants authority — it only records a suggestion.
    return ObsPolicyDecision(
        decision="allow",
        action=proposal.action,
        approved_actions=approved,  # type: ignore[arg-type]
        stop_reason="briefing_complete" if proposal.action == "stop" else None,
    )


def require_obs_action_allowed(
    observation: OrchestrationObservation,
    proposal: ObsActionProposal,
    **kwargs: object,
) -> ObsPolicyDecision:
    decision = evaluate_obs_action_policy(observation, proposal, **kwargs)  # type: ignore[arg-type]
    if decision.decision == "deny":
        raise ObsPolicyError(
            decision.deny_reason or "OBS action denied",
            details={"stop_reason": decision.stop_reason},
        )
    return decision


def _is_noop_repeat(
    action: ObsAction,
    recent_actions: tuple[ObsAction, ...],
    observation: OrchestrationObservation,
    recent_hashes: tuple[str, ...],
) -> bool:
    if action in {"stop", "request_owner_review", "compose_brief", "recommend_delegation"}:
        return False
    if not recent_actions or recent_actions[-1] != action:
        return False
    if observation.observation_hash is None:
        return True
    if not recent_hashes:
        return True
    return recent_hashes[-1] == observation.observation_hash
