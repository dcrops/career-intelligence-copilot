"""Deterministic DelegationPolicy for FR-016 DOS (M1).

Validates specialist delegation proposals. Does not execute specialists, call
providers, or mutate domain state. Supervisor authority is delegation admission
only — never domain super-user.
"""

from __future__ import annotations

from .briefing import approved_specialists_for
from .errors import DelegationPolicyError
from .models import (
    DelegationDecision,
    OrchestrationGoal,
    OrchestrationObservation,
    SpecialistDelegationProposal,
)
from .specialist_registry import is_future_placeholder
from .types import (
    DEFAULT_MAX_ORCHESTRATION_STEPS,
    DEFAULT_MAX_VISITS_PER_SPECIALIST,
    SpecialistId,
)


def evaluate_delegation_policy(
    goal: OrchestrationGoal,
    observation: OrchestrationObservation,
    proposal: SpecialistDelegationProposal,
    *,
    step_count: int = 0,
    max_steps: int | None = None,
    specialist_visit_counts: dict[SpecialistId, int] | None = None,
    max_visits_per_specialist: int | None = None,
    recent_delegation_keys: tuple[str, ...] = (),
    delegation_path: tuple[SpecialistId, ...] = (),
    owner_approvals_present: bool = False,
) -> DelegationDecision:
    """Return allow/deny for a proposed specialist delegation."""
    approved = approved_specialists_for(observation, goal)
    visits = specialist_visit_counts or {}
    visit_limit = (
        max_visits_per_specialist
        if max_visits_per_specialist is not None
        else DEFAULT_MAX_VISITS_PER_SPECIALIST
    )
    step_limit = max_steps if max_steps is not None else DEFAULT_MAX_ORCHESTRATION_STEPS

    if is_future_placeholder(proposal.target_specialist):
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason=f"specialist {proposal.target_specialist!r} is a future placeholder",
            stop_reason="delegation_blocked",
        )

    if proposal.target_specialist not in {"obs", "bopa"}:
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason=f"unknown specialist {proposal.target_specialist!r}",
            stop_reason="delegation_blocked",
        )

    if step_count >= step_limit:
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason=f"orchestration max_steps {step_limit} reached",
            stop_reason="orchestration_max_steps",
        )

    if visits.get(proposal.target_specialist, 0) >= visit_limit:
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason=(
                f"specialist {proposal.target_specialist!r} visit limit "
                f"{visit_limit} reached"
            ),
            stop_reason="specialist_visit_limit",
        )

    # Circular / ping-pong: obs→bopa→obs→bopa with no hash progress is runtime;
    # M1 detects simple immediate cycle in delegation_path.
    if _is_circular(delegation_path, proposal.target_specialist):
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason="circular delegation detected",
            stop_reason="circular_delegation",
        )

    idem_key = _idempotency_key(
        observation,
        proposal.target_specialist,
        proposal.requested_goal_kind,
    )
    if idem_key in recent_delegation_keys:
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason="repeated delegation for unchanged observation hash",
            stop_reason="repeated_delegation",
        )

    if proposal.target_specialist not in approved:
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason=(
                f"specialist {proposal.target_specialist!r} not approved for "
                f"goal={goal.goal_kind!r}"
            ),
            stop_reason="delegation_blocked",
        )

    # BOPA mutate path requires owner approvals when coordination intends preparation.
    if proposal.target_specialist == "bopa" and not owner_approvals_present:
        if goal.goal_kind == "coordinate_opportunity_readiness" and not goal.brief_only:
            return DelegationDecision(
                decision="deny",
                approved_specialists=approved,
                deny_reason="bopa delegation requires owner_approvals_present",
                stop_reason="owner_approval_required",
            )

    # Goal-kind mismatch hard rules.
    if goal.goal_kind == "brief_opportunity_readiness" and proposal.target_specialist == "bopa":
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason="brief_opportunity_readiness cannot delegate to bopa",
            stop_reason="delegation_blocked",
        )

    if goal.brief_only and proposal.target_specialist == "bopa":
        return DelegationDecision(
            decision="deny",
            approved_specialists=approved,
            deny_reason="brief_only orchestration cannot delegate to bopa",
            stop_reason="delegation_blocked",
        )

    return DelegationDecision(
        decision="allow",
        target_specialist=proposal.target_specialist,
        approved_specialists=approved,
    )


def require_delegation_allowed(
    goal: OrchestrationGoal,
    observation: OrchestrationObservation,
    proposal: SpecialistDelegationProposal,
    **kwargs: object,
) -> DelegationDecision:
    """Like evaluate_delegation_policy but raise on deny."""
    decision = evaluate_delegation_policy(goal, observation, proposal, **kwargs)  # type: ignore[arg-type]
    if decision.decision == "deny":
        raise DelegationPolicyError(
            decision.deny_reason or "delegation denied",
            details={"stop_reason": decision.stop_reason},
        )
    return decision


def handoff_idempotency_key(
    orchestration_run_id: str,
    target_specialist: SpecialistId,
    requested_goal_kind: str,
    observed_state_hash: str | None,
) -> str:
    """Stable key for duplicate-handoff prevention."""
    return "|".join(
        [
            orchestration_run_id,
            target_specialist,
            requested_goal_kind,
            observed_state_hash or "",
        ]
    )


def _idempotency_key(
    observation: OrchestrationObservation,
    target: SpecialistId,
    goal_kind: str,
) -> str:
    return "|".join([target, goal_kind, observation.observation_hash or ""])


def _is_circular(path: tuple[SpecialistId, ...], nxt: SpecialistId) -> bool:
    if len(path) < 2:
        return False
    # A→B→A when proposing A again after B (simple oscillation).
    if len(path) >= 2 and path[-1] != nxt and path[-2] == nxt:
        return True
    # Direct repeat without progress handled by idempotency keys.
    return False
