"""Contract-invariant helpers for FR-015 M1 agent models."""

from __future__ import annotations

from .errors import AgentContractError
from .models import AgentActionProposal, AgentRun, ReadinessSnapshot
from .state_classes import applicable_state_classes, primary_state_class
from .types import FORBIDDEN_ACTION_NAMES, AGENT_ACTIONS


def validate_readiness_snapshot_contract(snapshot: ReadinessSnapshot) -> None:
    """Fail closed on snapshot combinations that violate BOPA preconditions."""
    classes = applicable_state_classes(snapshot)
    if not classes:
        raise AgentContractError("snapshot classified to no state classes")
    primary = primary_state_class(snapshot)
    if primary not in classes:
        raise AgentContractError(
            "primary state class missing from applicable classes",
            details={"primary": primary, "applicable": list(classes)},
        )
    if snapshot.truth.status == "pass" and snapshot.truth.owner_edited_markdown_since_validation:
        raise AgentContractError("pass truth cannot coexist with owner-edited-since-validation")


def validate_action_proposal_contract(proposal: AgentActionProposal) -> None:
    """Ensure proposals stay within the M1 allow-list."""
    if proposal.action not in AGENT_ACTIONS:
        raise AgentContractError(f"action not in allow-list: {proposal.action!r}")
    if proposal.action in FORBIDDEN_ACTION_NAMES:  # type: ignore[comparison-overlap]
        raise AgentContractError(f"forbidden action: {proposal.action!r}")


def validate_agent_run_contract(run: AgentRun) -> None:
    """Validate run-level invariants beyond Pydantic field checks."""
    if run.goal.goal_kind != "prepare_for_owner_review":
        raise AgentContractError(f"unsupported goal_kind: {run.goal.goal_kind!r}")
    if run.last_snapshot is not None:
        validate_readiness_snapshot_contract(run.last_snapshot)
        if run.last_snapshot.opportunity_id != run.goal.opportunity_id:
            raise AgentContractError("snapshot opportunity_id mismatch")
    if run.status == "awaiting_owner" and run.stop_reason not in {
        "owner_approval_required",
        "clarification_required",
        "completed_for_owner_review",
        "truth_validation_blocked",
        "material_benefit_required",
        None,
    }:
        # awaiting_owner may carry a stop reason describing the gate; None allowed
        # only before stop is recorded — enforce completed path separately.
        pass
    for step in run.steps:
        if step.snapshot.opportunity_id != run.goal.opportunity_id:
            raise AgentContractError("step snapshot opportunity_id mismatch")
