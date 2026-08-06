"""Test helpers for FR-016 M1 multi-agent contracts."""

from __future__ import annotations

from datetime import datetime, timezone

from career_intelligence.multi_agent import (
    Handoff,
    ObsActionProposal,
    OperationalBrief,
    OrchestrationGoal,
    OrchestrationObservation,
    OrchestrationRun,
    SpecialistDelegationProposal,
    new_handoff_id,
    new_operational_brief_id,
    new_orchestration_run_id,
)

OPP = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"


def _now() -> datetime:
    return datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)


def make_goal(**overrides: object) -> OrchestrationGoal:
    base: dict[str, object] = {
        "goal_kind": "coordinate_opportunity_readiness",
        "opportunity_id": OPP,
        "brief_only": False,
    }
    base.update(overrides)
    return OrchestrationGoal.model_validate(base)


def make_observation(**overrides: object) -> OrchestrationObservation:
    base: dict[str, object] = {
        "opportunity_id": OPP,
        "decision": "apply",
        "readiness_primary_state_class": "missing_package",
        "package_status": "absent",
        "truth_status": "absent",
        "pipeline_status": "assessed",
        "owner_approvals_present": True,
        "prior_agent_run_ids": (),
        "truth_blocking_labels": (),
        "contradictory_flags": (),
        "briefing_need_classes": (),
        "observation_hash": "hash_a",
        "observed_at": _now(),
    }
    base.update(overrides)
    return OrchestrationObservation.model_validate(base)


def make_delegation_proposal(**overrides: object) -> SpecialistDelegationProposal:
    base: dict[str, object] = {
        "target_specialist": "obs",
        "rationale": "brief first",
        "requested_goal_kind": "brief_opportunity_readiness",
    }
    base.update(overrides)
    return SpecialistDelegationProposal.model_validate(base)


def make_obs_proposal(**overrides: object) -> ObsActionProposal:
    base: dict[str, object] = {
        "action": "compose_brief",
        "rationale": "synthesise readiness",
    }
    base.update(overrides)
    return ObsActionProposal.model_validate(base)


def make_brief(**overrides: object) -> OperationalBrief:
    base: dict[str, object] = {
        "brief_id": new_operational_brief_id(),
        "opportunity_id": OPP,
        "briefing_need_classes": ("pipeline_advises_against_preparation",),
        "pipeline_status": "interviewing",
        "pipeline_note": "Preparation usually unnecessary while interviewing.",
        "recommended_next_step": "owner_review",
        "owner_action_summary": "Review pipeline stage before any preparation.",
        "created_at": _now(),
    }
    base.update(overrides)
    return OperationalBrief.model_validate(base)


def make_handoff(**overrides: object) -> Handoff:
    run_id = new_orchestration_run_id()
    base: dict[str, object] = {
        "handoff_id": new_handoff_id(),
        "orchestration_run_id": run_id,
        "source": "supervisor",
        "target_specialist": "obs",
        "opportunity_id": OPP,
        "requested_goal_kind": "brief_opportunity_readiness",
        "observed_state_hash": "hash_a",
        "expected_output_kind": "operational_brief",
        "owner_approval_status": "present",
        "policy_decision": "allow",
        "reason": "briefing delta present",
        "acceptance": "pending",
        "created_at": _now(),
    }
    base.update(overrides)
    return Handoff.model_validate(base)


def make_run(**overrides: object) -> OrchestrationRun:
    base: dict[str, object] = {
        "orchestration_run_id": new_orchestration_run_id(),
        "goal": make_goal(),
        "status": "running",
        "step_count": 0,
        "owner_approvals_present": True,
        "created_at": _now(),
        "updated_at": _now(),
    }
    base.update(overrides)
    return OrchestrationRun.model_validate(base)
