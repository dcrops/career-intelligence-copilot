"""Deterministic ToolPolicy for BOPA (FR-015 M1).

Validates proposed actions against readiness snapshots. Does not execute tools,
call providers, or mutate domain state.
"""

from __future__ import annotations

from .errors import AgentPolicyError
from .models import AgentActionProposal, PolicyDecision, ReadinessSnapshot
from .state_classes import (
    applicable_state_classes,
    approved_actions_for,
    expected_owner_stop_reason,
    primary_state_class,
)
from .types import (
    FORBIDDEN_ACTION_NAMES,
    AgentAction,
    AGENT_ACTIONS,
)


def evaluate_action_policy(
    snapshot: ReadinessSnapshot,
    proposal: AgentActionProposal,
    *,
    recent_actions: tuple[AgentAction, ...] = (),
    recent_snapshot_hashes: tuple[str, ...] = (),
    step_count: int = 0,
    max_steps: int | None = None,
) -> PolicyDecision:
    """Return allow/deny for a proposed action against the current snapshot."""
    primary = primary_state_class(snapshot)
    applicable = applicable_state_classes(snapshot)
    approved = tuple(sorted(approved_actions_for(snapshot, state_class=primary)))

    # Forbidden names should never appear as AgentAction; defend anyway.
    if proposal.action in FORBIDDEN_ACTION_NAMES:  # type: ignore[comparison-overlap]
        return PolicyDecision(
            decision="deny",
            primary_state_class=primary,
            applicable_state_classes=applicable,
            approved_actions=approved,
            deny_reason=f"forbidden action {proposal.action!r}",
            stop_reason="policy_blocked",
        )

    if proposal.action not in AGENT_ACTIONS:
        return PolicyDecision(
            decision="deny",
            primary_state_class=primary,
            applicable_state_classes=applicable,
            approved_actions=approved,
            deny_reason=f"action {proposal.action!r} not in allow-list",
            stop_reason="policy_blocked",
        )

    limit = max_steps if max_steps is not None else snapshot_max_steps_default()
    if step_count >= limit and proposal.action != "stop":
        return PolicyDecision(
            decision="deny",
            primary_state_class=primary,
            applicable_state_classes=applicable,
            approved_actions=approved,
            deny_reason=f"max_steps {limit} reached",
            stop_reason="max_steps_reached",
        )

    if proposal.action not in approved_actions_for(snapshot, state_class=primary):
        stop = expected_owner_stop_reason(snapshot, state_class=primary)
        return PolicyDecision(
            decision="deny",
            primary_state_class=primary,
            applicable_state_classes=applicable,
            approved_actions=approved,
            deny_reason=(
                f"action {proposal.action!r} illegal for primary state "
                f"{primary!r}"
            ),
            stop_reason=stop or "policy_blocked",
        )

    # Extra hard rules independent of class tables.
    extra_deny = _hard_rule_deny(snapshot, proposal.action)
    if extra_deny is not None:
        return PolicyDecision(
            decision="deny",
            primary_state_class=primary,
            applicable_state_classes=applicable,
            approved_actions=approved,
            deny_reason=extra_deny,
            stop_reason="policy_blocked",
        )

    if _is_noop_repeat(proposal.action, recent_actions, snapshot, recent_snapshot_hashes):
        return PolicyDecision(
            decision="deny",
            primary_state_class=primary,
            applicable_state_classes=applicable,
            approved_actions=approved,
            deny_reason="repeated no-op action for unchanged snapshot",
            stop_reason="policy_blocked",
        )

    return PolicyDecision(
        decision="allow",
        action=proposal.action,
        primary_state_class=primary,
        applicable_state_classes=applicable,
        approved_actions=approved,
        stop_reason=expected_owner_stop_reason(snapshot, state_class=primary)
        if proposal.action in {"stop", "request_owner_review"}
        else None,
    )


def require_action_allowed(
    snapshot: ReadinessSnapshot,
    proposal: AgentActionProposal,
    **kwargs: object,
) -> PolicyDecision:
    """Like evaluate_action_policy but raise AgentPolicyError on deny."""
    decision = evaluate_action_policy(snapshot, proposal, **kwargs)  # type: ignore[arg-type]
    if decision.decision == "deny":
        raise AgentPolicyError(
            decision.deny_reason or "action denied",
            details={
                "primary_state_class": decision.primary_state_class,
                "stop_reason": decision.stop_reason,
            },
        )
    return decision


def snapshot_max_steps_default() -> int:
    from .types import DEFAULT_MAX_STEPS

    return DEFAULT_MAX_STEPS


def _hard_rule_deny(snapshot: ReadinessSnapshot, action: AgentAction) -> str | None:
    if action == "run_preparation":
        if snapshot.decision != "apply":
            return "run_preparation requires decision=apply"
        if not snapshot.artefacts.all_present:
            return "run_preparation requires FR-002–FR-005 artefacts"
        if not snapshot.owner_approvals_present:
            return "run_preparation requires explicit owner approvals"
    if action == "verify_package":
        if snapshot.package.status == "absent":
            return "verify_package requires a package manifest"
    if action == "validate_truth_package":
        if snapshot.package.status not in {"present", "stale", "incomplete", "integrity_failed"}:
            # Allow validate only when something package-shaped exists to validate.
            if snapshot.package.status == "absent":
                return "validate_truth_package requires a package"
        if snapshot.package.status in {"incomplete", "integrity_failed"}:
            return "validate_truth_package blocked until package integrity/completeness restored"
        if snapshot.decision != "apply":
            return "validate_truth_package requires decision=apply"
    return None


def _is_noop_repeat(
    action: AgentAction,
    recent_actions: tuple[AgentAction, ...],
    snapshot: ReadinessSnapshot,
    recent_snapshot_hashes: tuple[str, ...],
) -> bool:
    if action in {"stop", "request_owner_review"}:
        return False
    if not recent_actions or recent_actions[-1] != action:
        return False
    if snapshot.snapshot_hash is None:
        # Without hashes, identical consecutive non-stop actions are treated as loops.
        return True
    if not recent_snapshot_hashes:
        return True
    return recent_snapshot_hashes[-1] == snapshot.snapshot_hash
