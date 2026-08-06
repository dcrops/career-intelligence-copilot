"""Contract-invariant helpers for FR-016 M1 multi-agent models."""

from __future__ import annotations

from .errors import MultiAgentContractError
from .models import (
    Handoff,
    OperationalBrief,
    OrchestrationRun,
    SpecialistDelegationProposal,
)
from .specialist_registry import is_future_placeholder
from .types import OBS_ACTIONS, OBS_FORBIDDEN_ACTION_NAMES, ORCHESTRATION_GOAL_KINDS


def validate_orchestration_run_contract(run: OrchestrationRun) -> None:
    """Fail closed on parent-run combinations that violate DOS preconditions."""
    if run.goal.goal_kind not in ORCHESTRATION_GOAL_KINDS:
        raise MultiAgentContractError(f"unsupported goal_kind: {run.goal.goal_kind!r}")
    if run.last_observation is not None:
        if run.last_observation.opportunity_id != run.goal.opportunity_id:
            raise MultiAgentContractError("observation opportunity_id mismatch")
    for visit in run.specialist_visits:
        if visit.visit_count > run.max_visits_per_specialist:
            raise MultiAgentContractError(
                "specialist visit_count exceeds max_visits_per_specialist",
                details={
                    "specialist_id": visit.specialist_id,
                    "visit_count": visit.visit_count,
                    "max": run.max_visits_per_specialist,
                },
            )


def validate_handoff_contract(handoff: Handoff) -> None:
    """Ensure handoffs stay within FR-016 authority rules."""
    if handoff.source != "supervisor":
        raise MultiAgentContractError("handoff source must be supervisor")
    if is_future_placeholder(handoff.target_specialist):
        raise MultiAgentContractError("handoff target is future placeholder")
    if handoff.policy_decision == "allow" and handoff.acceptance in {
        "accepted",
        "executing",
        "completed",
        "stopped",
    }:
        if handoff.target_specialist == "bopa" and handoff.expected_output_kind not in {
            "agent_run_result",
            "bopa_agent_run",
        }:
            raise MultiAgentContractError(
                "bopa handoff expected_output_kind must be agent_run_result shape",
                details={"expected_output_kind": handoff.expected_output_kind},
            )
        if handoff.target_specialist == "obs" and handoff.expected_output_kind not in {
            "operational_brief",
            "obs_brief",
        }:
            raise MultiAgentContractError(
                "obs handoff expected_output_kind must be operational_brief shape",
                details={"expected_output_kind": handoff.expected_output_kind},
            )


def validate_delegation_proposal_contract(proposal: SpecialistDelegationProposal) -> None:
    if is_future_placeholder(proposal.target_specialist):
        raise MultiAgentContractError(
            f"future placeholder specialist not delegable: {proposal.target_specialist!r}"
        )
    if proposal.target_specialist not in {"obs", "bopa"}:
        raise MultiAgentContractError(f"unknown specialist: {proposal.target_specialist!r}")


def validate_operational_brief_contract(brief: OperationalBrief) -> None:
    if not brief.briefing_need_classes:
        raise MultiAgentContractError("OperationalBrief requires briefing_need_classes")
    if not brief.owner_action_summary.strip():
        raise MultiAgentContractError("OperationalBrief requires owner_action_summary")


def assert_obs_cannot_mutate() -> None:
    """Invariant helper for tests/docs: OBS allow-list ∩ mutating names is empty."""
    mutating = {
        "run_preparation",
        "verify_package",
        "validate_truth_package",
        "submit",
        "advance_pipeline",
    }
    overlap = mutating.intersection(OBS_ACTIONS)
    if overlap:
        raise MultiAgentContractError(
            "OBS allow-list must not include mutating actions",
            details={"overlap": sorted(overlap)},
        )
    for name in mutating:
        if name not in OBS_FORBIDDEN_ACTION_NAMES:
            raise MultiAgentContractError(
                f"mutating action {name!r} missing from OBS_FORBIDDEN_ACTION_NAMES"
            )
