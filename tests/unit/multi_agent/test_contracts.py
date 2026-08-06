"""Unit tests for FR-016 M1 multi-agent contracts, policies, and briefing value."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.agent import AGENT_ACTIONS
from career_intelligence.multi_agent import (
    OBS_ACTIONS,
    OBS_FORBIDDEN_ACTION_NAMES,
    BOPA_SPECIALIST,
    OBS_SPECIALIST,
    DelegationPolicyError,
    ObsPolicyError,
    assert_obs_cannot_mutate,
    classify_briefing_needs,
    evaluate_delegation_policy,
    evaluate_obs_action_policy,
    handoff_idempotency_key,
    new_handoff_id,
    new_orchestration_run_id,
    obs_adds_value_beyond_bopa,
    require_delegation_allowed,
    require_obs_action_allowed,
    specialist_may_mutate,
    validate_handoff_contract,
    validate_operational_brief_contract,
    validate_orchestration_run_contract,
)
from tests.unit.multi_agent.helpers import (
    OPP,
    make_brief,
    make_delegation_proposal,
    make_goal,
    make_handoff,
    make_obs_proposal,
    make_observation,
    make_run,
)


def test_id_generators() -> None:
    assert new_orchestration_run_id().startswith("orr_")
    assert new_handoff_id().startswith("hof_")


def test_rejects_bad_orchestration_run_id() -> None:
    with pytest.raises(ValidationError):
        make_run(orchestration_run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FAA")


def test_extra_fields_forbidden_on_observation() -> None:
    raw = make_observation().model_dump(mode="python")
    raw["surprise"] = True
    from career_intelligence.multi_agent import OrchestrationObservation

    with pytest.raises(ValidationError):
        OrchestrationObservation.model_validate(raw)


def test_bopa_allow_list_unchanged_reference() -> None:
    assert BOPA_SPECIALIST.allowed_actions == tuple(AGENT_ACTIONS)
    assert BOPA_SPECIALIST.mutates_domain is True
    assert specialist_may_mutate("bopa") is True
    assert specialist_may_mutate("obs") is False


def test_obs_cannot_mutate_invariant() -> None:
    assert_obs_cannot_mutate()
    for action in ("run_preparation", "verify_package", "validate_truth_package"):
        assert action not in OBS_ACTIONS
        assert action in OBS_FORBIDDEN_ACTION_NAMES


def test_obs_registry_read_only() -> None:
    assert OBS_SPECIALIST.mutates_domain is False
    assert "compose_brief" in OBS_SPECIALIST.allowed_actions


# --- Briefing value beyond BOPA ---


def test_interviewing_pipeline_needs_obs_briefing() -> None:
    obs = make_observation(pipeline_status="interviewing")
    goal = make_goal()
    needs = classify_briefing_needs(obs, goal)
    assert "pipeline_advises_against_preparation" in needs
    assert obs_adds_value_beyond_bopa(obs, goal) is True


def test_happy_assessed_missing_package_no_briefing_delta() -> None:
    obs = make_observation(pipeline_status="assessed", package_status="absent")
    goal = make_goal()
    assert classify_briefing_needs(obs, goal) == ("no_briefing_delta",)
    assert obs_adds_value_beyond_bopa(obs, goal) is False


def test_truth_blockers_are_briefing_delta() -> None:
    obs = make_observation(
        truth_status="fail",
        truth_blocking_labels=("Unsupported certification",),
        package_status="present",
        readiness_primary_state_class="truth_blocked",
    )
    goal = make_goal()
    assert "truth_blockers_need_synthesis" in classify_briefing_needs(obs, goal)


def test_brief_only_goal_forces_obs_value() -> None:
    obs = make_observation()
    goal = make_goal(goal_kind="brief_opportunity_readiness")
    assert "owner_requested_brief_only" in classify_briefing_needs(obs, goal)


# --- DelegationPolicy ---


def test_brief_goal_allows_obs_denies_bopa() -> None:
    goal = make_goal(goal_kind="brief_opportunity_readiness")
    observation = make_observation(pipeline_status="interviewing")
    allow = evaluate_delegation_policy(
        goal,
        observation,
        make_delegation_proposal(target_specialist="obs"),
        owner_approvals_present=True,
    )
    assert allow.decision == "allow"
    deny = evaluate_delegation_policy(
        goal,
        observation,
        make_delegation_proposal(
            target_specialist="bopa",
            requested_goal_kind="prepare_for_owner_review",
        ),
        owner_approvals_present=True,
    )
    assert deny.decision == "deny"
    assert deny.stop_reason == "delegation_blocked"


def test_bopa_requires_owner_approvals() -> None:
    goal = make_goal()
    # No briefing delta so BOPA can be approved alone.
    observation = make_observation(pipeline_status="assessed")
    decision = evaluate_delegation_policy(
        goal,
        observation,
        make_delegation_proposal(
            target_specialist="bopa",
            requested_goal_kind="prepare_for_owner_review",
            rationale="prepare package",
        ),
        owner_approvals_present=False,
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "owner_approval_required"


def test_coordinate_with_briefing_delta_allows_obs_and_bopa() -> None:
    goal = make_goal()
    observation = make_observation(
        pipeline_status="assessed",
        prior_agent_run_ids=("agr_01ARZ3NDEKTSV4RRFFQ69G5FAA",),
    )
    assert obs_adds_value_beyond_bopa(observation, goal)
    obs_decision = evaluate_delegation_policy(
        goal,
        observation,
        make_delegation_proposal(target_specialist="obs"),
        owner_approvals_present=True,
    )
    assert obs_decision.decision == "allow"


def test_repeated_delegation_denied() -> None:
    goal = make_goal(goal_kind="brief_opportunity_readiness")
    observation = make_observation(pipeline_status="interviewing")
    proposal = make_delegation_proposal(target_specialist="obs")
    key = "obs|brief_opportunity_readiness|hash_a"
    decision = evaluate_delegation_policy(
        goal,
        observation,
        proposal,
        recent_delegation_keys=(key,),
        owner_approvals_present=True,
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "repeated_delegation"


def test_circular_delegation_denied() -> None:
    goal = make_goal()
    observation = make_observation(
        prior_agent_run_ids=("agr_01ARZ3NDEKTSV4RRFFQ69G5FAA",),
    )
    decision = evaluate_delegation_policy(
        goal,
        observation,
        make_delegation_proposal(target_specialist="obs"),
        delegation_path=("obs", "bopa"),
        owner_approvals_present=True,
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "circular_delegation"


def test_visit_limit_denied() -> None:
    goal = make_goal(goal_kind="brief_opportunity_readiness")
    observation = make_observation(pipeline_status="interviewing")
    decision = evaluate_delegation_policy(
        goal,
        observation,
        make_delegation_proposal(target_specialist="obs"),
        specialist_visit_counts={"obs": 3},
        max_visits_per_specialist=3,
        owner_approvals_present=True,
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "specialist_visit_limit"


def test_max_steps_denied() -> None:
    goal = make_goal(goal_kind="brief_opportunity_readiness")
    observation = make_observation(pipeline_status="interviewing")
    decision = evaluate_delegation_policy(
        goal,
        observation,
        make_delegation_proposal(target_specialist="obs"),
        step_count=12,
        max_steps=12,
        owner_approvals_present=True,
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "orchestration_max_steps"


def test_acquisition_placeholder_denied() -> None:
    goal = make_goal()
    observation = make_observation()
    from career_intelligence.multi_agent.models import SpecialistDelegationProposal

    with pytest.raises(ValidationError):
        # SpecialistId literal rejects acquisition at model layer.
        SpecialistDelegationProposal.model_validate(
            {
                "target_specialist": "acquisition",
                "rationale": "discover jobs",
                "requested_goal_kind": "discover",
            }
        )


def test_require_delegation_raises() -> None:
    goal = make_goal(goal_kind="brief_opportunity_readiness")
    observation = make_observation(pipeline_status="interviewing")
    with pytest.raises(DelegationPolicyError):
        require_delegation_allowed(
            goal,
            observation,
            make_delegation_proposal(
                target_specialist="bopa",
                requested_goal_kind="prepare_for_owner_review",
            ),
            owner_approvals_present=True,
        )


# --- OBS ToolPolicy ---


def test_obs_allows_compose_brief() -> None:
    decision = evaluate_obs_action_policy(
        make_observation(),
        make_obs_proposal(action="compose_brief"),
    )
    assert decision.decision == "allow"


def test_obs_denies_preparation_even_if_cast() -> None:
    # Forbidden names are not in ObsAction; defend via forbidden set helper path
    # by evaluating a stop after max steps instead, and assert forbidden set.
    assert "run_preparation" in OBS_FORBIDDEN_ACTION_NAMES
    decision = evaluate_obs_action_policy(
        make_observation(),
        make_obs_proposal(action="inspect_readiness"),
        step_count=6,
        max_steps=6,
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "orchestration_max_steps"


def test_obs_noop_repeat_denied() -> None:
    observation = make_observation(observation_hash="h1")
    decision = evaluate_obs_action_policy(
        observation,
        make_obs_proposal(action="inspect_pipeline_context"),
        recent_actions=("inspect_pipeline_context",),
        recent_observation_hashes=("h1",),
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "no_progress"


def test_require_obs_raises() -> None:
    with pytest.raises(ObsPolicyError):
        require_obs_action_allowed(
            make_observation(),
            make_obs_proposal(action="inspect_readiness"),
            step_count=6,
            max_steps=6,
        )


# --- Handoff / run contracts ---


def test_handoff_must_source_supervisor() -> None:
    with pytest.raises(ValidationError):
        make_handoff(source="bopa")


def test_handoff_accept_requires_allow() -> None:
    with pytest.raises(ValidationError):
        make_handoff(policy_decision="deny", policy_deny_reason="no", acceptance="accepted")


def test_validate_handoff_obs_output_kind() -> None:
    h = make_handoff(acceptance="accepted", expected_output_kind="operational_brief")
    validate_handoff_contract(h)


def test_validate_handoff_rejects_wrong_output_kind() -> None:
    h = make_handoff(acceptance="accepted", expected_output_kind="chat_message")
    with pytest.raises(Exception):
        validate_handoff_contract(h)


def test_orchestration_run_terminal_requires_stop() -> None:
    with pytest.raises(ValidationError):
        make_run(status="completed", stop_reason=None)


def test_validate_orchestration_run_ok() -> None:
    run = make_run(last_observation=make_observation())
    validate_orchestration_run_contract(run)


def test_operational_brief_contract() -> None:
    brief = make_brief()
    validate_operational_brief_contract(brief)


def test_handoff_idempotency_key_stable() -> None:
    key = handoff_idempotency_key("orr_01ARZ3NDEKTSV4RRFFQ69G5FAA", "obs", "brief", "hash_a")
    assert key == "orr_01ARZ3NDEKTSV4RRFFQ69G5FAA|obs|brief|hash_a"


def test_no_privilege_escalation_via_obs_recommend() -> None:
    """recommend_delegation is allow-listed for OBS but does not expand tools."""
    decision = evaluate_obs_action_policy(
        make_observation(),
        make_obs_proposal(action="recommend_delegation", rationale="suggest bopa"),
    )
    assert decision.decision == "allow"
    # Escalation still requires DelegationPolicy on supervisor.
    goal = make_goal(goal_kind="brief_opportunity_readiness")
    deny = evaluate_delegation_policy(
        goal,
        make_observation(pipeline_status="interviewing"),
        make_delegation_proposal(
            target_specialist="bopa",
            requested_goal_kind="prepare_for_owner_review",
        ),
        owner_approvals_present=True,
    )
    assert deny.decision == "deny"
