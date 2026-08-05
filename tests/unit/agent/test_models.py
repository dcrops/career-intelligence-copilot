"""Unit tests for FR-015 M1 agent contracts, state classes, and ToolPolicy."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.agent import (
    FORBIDDEN_ACTION_NAMES,
    AgentActionProposal,
    AgentPolicyError,
    evaluate_action_policy,
    expected_owner_stop_reason,
    new_agent_run_id,
    new_agent_step_id,
    primary_state_class,
    require_action_allowed,
    validate_action_proposal_contract,
    validate_agent_run_contract,
    validate_readiness_snapshot_contract,
)
from tests.unit.agent.helpers import (
    make_artefacts,
    make_package,
    make_proposal,
    make_run,
    make_snapshot,
    make_truth,
)


def test_id_generators() -> None:
    assert new_agent_run_id().startswith("agr_")
    assert new_agent_step_id().startswith("ags_")


def test_rejects_bad_run_id() -> None:
    with pytest.raises(ValidationError):
        make_run(agent_run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FAA")


def test_extra_fields_forbidden_on_snapshot() -> None:
    with pytest.raises(ValidationError):
        ReadinessSnapshot = make_snapshot().model_dump(mode="python")
        from career_intelligence.agent import ReadinessSnapshot as RS

        RS.model_validate({**ReadinessSnapshot, "surprise": True})


def test_truth_pass_cannot_coexist_with_owner_edit_flag() -> None:
    with pytest.raises(ValidationError):
        make_truth(
            status="pass",
            report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA",
            owner_edited_markdown_since_validation=True,
        )


def test_present_package_requires_both_drafts() -> None:
    with pytest.raises(ValidationError):
        make_package(status="present", cv_present=True, cover_letter_present=False)


# --- State classification ---


def test_missing_analysis_primary() -> None:
    snap = make_snapshot(artefacts=make_artefacts(job_analysis=False))
    assert primary_state_class(snap) == "missing_analysis"
    assert expected_owner_stop_reason(snap) == "invalid_state"


def test_missing_assessment_primary() -> None:
    snap = make_snapshot(artefacts=make_artefacts(assessment=False))
    assert primary_state_class(snap) == "missing_assessment"


def test_missing_strategy_primary() -> None:
    snap = make_snapshot(artefacts=make_artefacts(strategy=False))
    assert primary_state_class(snap) == "missing_strategy"


def test_missing_package_when_apply_ready_upstream() -> None:
    snap = make_snapshot(package=make_package(status="absent"))
    assert primary_state_class(snap) == "missing_package"


def test_stale_package() -> None:
    snap = make_snapshot(
        package=make_package(
            status="stale",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        )
    )
    assert primary_state_class(snap) == "stale_package"


def test_missing_cv() -> None:
    snap = make_snapshot(
        package=make_package(
            status="incomplete",
            cv_present=False,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        )
    )
    assert primary_state_class(snap) == "missing_cv"


def test_missing_cover_letter() -> None:
    snap = make_snapshot(
        package=make_package(
            status="incomplete",
            cv_present=True,
            cover_letter_present=False,
            manifest_ref="pkg/opp",
        )
    )
    assert primary_state_class(snap) == "missing_cover_letter"


def test_package_integrity_failure() -> None:
    snap = make_snapshot(
        package=make_package(
            status="integrity_failed",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        )
    )
    assert primary_state_class(snap) == "package_integrity_failure"


def test_stale_truth_report() -> None:
    snap = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        ),
        truth=make_truth(status="stale", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
    )
    assert primary_state_class(snap) == "stale_truth_report"


def test_owner_markdown_revalidation_required() -> None:
    snap = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        ),
        truth=make_truth(
            status="stale",
            report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA",
            owner_edited_markdown_since_validation=True,
        ),
    )
    assert primary_state_class(snap) == "owner_markdown_revalidation_required"


def test_truth_blocked() -> None:
    snap = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        ),
        truth=make_truth(
            status="fail",
            report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA",
            blocking_finding_codes=("tech_unsupported",),
        ),
    )
    assert primary_state_class(snap) == "truth_blocked"
    assert expected_owner_stop_reason(snap) == "truth_validation_blocked"


def test_clarification_required() -> None:
    snap = make_snapshot(
        clarification_required=True,
        clarification_message="Which approval flags should apply?",
    )
    assert primary_state_class(snap) == "clarification_required"


def test_provider_unavailable() -> None:
    snap = make_snapshot(provider_available=False)
    assert primary_state_class(snap) == "provider_unavailable"


def test_unsupported_non_apply_decision() -> None:
    snap = make_snapshot(decision="skip")
    assert primary_state_class(snap) == "unsupported_or_contradictory"


def test_contradictory_package_without_artefacts() -> None:
    snap = make_snapshot(
        artefacts=make_artefacts(job_analysis=False),
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        ),
    )
    assert primary_state_class(snap) == "unsupported_or_contradictory"


def test_partial_agent_run_when_otherwise_clear() -> None:
    snap = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        ),
        truth=make_truth(status="pass", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
        prior_agent_run_id=new_agent_run_id(),
        prior_agent_run_incomplete=True,
    )
    assert primary_state_class(snap) == "partial_agent_run"


def test_ready_for_owner_review() -> None:
    snap = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        ),
        truth=make_truth(status="pass", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
    )
    assert primary_state_class(snap) == "ready_for_owner_review"
    assert expected_owner_stop_reason(snap) == "completed_for_owner_review"


def test_owner_approval_required_before_prep() -> None:
    snap = make_snapshot(owner_approvals_present=False, package=make_package(status="absent"))
    assert primary_state_class(snap) == "owner_approval_required"


# --- ToolPolicy ---


def test_policy_blocks_prep_when_missing_analysis() -> None:
    snap = make_snapshot(artefacts=make_artefacts(job_analysis=False))
    decision = evaluate_action_policy(snap, make_proposal("run_preparation"))
    assert decision.decision == "deny"
    assert decision.stop_reason == "invalid_state"


def test_policy_allows_prep_for_missing_package_with_approvals() -> None:
    snap = make_snapshot(package=make_package(status="absent"), owner_approvals_present=True)
    decision = evaluate_action_policy(snap, make_proposal("run_preparation"))
    assert decision.decision == "allow"


def test_policy_blocks_prep_without_approvals() -> None:
    snap = make_snapshot(package=make_package(status="absent"), owner_approvals_present=False)
    decision = evaluate_action_policy(snap, make_proposal("run_preparation"))
    assert decision.decision == "deny"


def test_policy_allows_revalidate_when_stale_truth() -> None:
    snap = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        ),
        truth=make_truth(status="stale", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
    )
    decision = evaluate_action_policy(snap, make_proposal("validate_truth_package"))
    assert decision.decision == "allow"


def test_policy_blocks_validate_when_integrity_failed() -> None:
    snap = make_snapshot(
        package=make_package(
            status="integrity_failed",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        )
    )
    decision = evaluate_action_policy(snap, make_proposal("validate_truth_package"))
    assert decision.decision == "deny"


def test_policy_blocks_repeated_noop() -> None:
    snap = make_snapshot(package=make_package(status="absent"))
    decision = evaluate_action_policy(
        snap,
        make_proposal("inspect_readiness"),
        recent_actions=("inspect_readiness",),
        recent_snapshot_hashes=("hash_a",),
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "policy_blocked"


def test_policy_max_steps() -> None:
    snap = make_snapshot(package=make_package(status="absent"))
    decision = evaluate_action_policy(
        snap,
        make_proposal("run_preparation"),
        step_count=8,
        max_steps=8,
    )
    assert decision.decision == "deny"
    assert decision.stop_reason == "max_steps_reached"


def test_policy_allows_stop_at_max_steps() -> None:
    snap = make_snapshot(package=make_package(status="absent"))
    decision = evaluate_action_policy(
        snap,
        make_proposal("stop"),
        step_count=8,
        max_steps=8,
    )
    assert decision.decision == "allow"


def test_policy_provider_unavailable_only_inspect_or_stop() -> None:
    snap = make_snapshot(provider_available=False, package=make_package(status="absent"))
    assert evaluate_action_policy(snap, make_proposal("run_preparation")).decision == "deny"
    assert evaluate_action_policy(snap, make_proposal("inspect_readiness")).decision == "allow"
    assert evaluate_action_policy(snap, make_proposal("stop")).decision == "allow"


def test_require_action_allowed_raises() -> None:
    snap = make_snapshot(artefacts=make_artefacts(strategy=False))
    with pytest.raises(AgentPolicyError):
        require_action_allowed(snap, make_proposal("run_preparation"))


def test_forbidden_action_names_documented() -> None:
    assert "submit" in FORBIDDEN_ACTION_NAMES
    assert "advance_pipeline" in FORBIDDEN_ACTION_NAMES
    assert "waive_truth" in FORBIDDEN_ACTION_NAMES
    assert "run_analyse" in FORBIDDEN_ACTION_NAMES


def test_proposal_contract() -> None:
    validate_action_proposal_contract(make_proposal())
    with pytest.raises(ValidationError):
        AgentActionProposal.model_validate(
            {"action": "submit", "rationale": "hack", "evidence_refs": []}
        )


def test_agent_run_terminal_requires_stop_reason() -> None:
    with pytest.raises(ValidationError):
        make_run(status="completed")


def test_agent_run_contract_ok() -> None:
    run = make_run(
        status="completed",
        stop_reason="completed_for_owner_review",
        last_snapshot=make_snapshot(
            package=make_package(
                status="present",
                cv_present=True,
                cover_letter_present=True,
                manifest_ref="pkg/opp",
            ),
            truth=make_truth(status="pass", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
        ),
    )
    validate_agent_run_contract(run)
    validate_readiness_snapshot_contract(run.last_snapshot)  # type: ignore[arg-type]


def test_snapshot_opportunity_must_match_goal() -> None:
    with pytest.raises(ValidationError):
        make_run(
            last_snapshot=make_snapshot(opportunity_id="opp_01BZ3NDEKTSV4RRFFQ69G5FAB"),
        )


def test_ready_stop_records_completed_reason() -> None:
    snap = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/opp",
        ),
        truth=make_truth(status="pass", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
    )
    decision = evaluate_action_policy(snap, make_proposal("stop"))
    assert decision.decision == "allow"
    assert decision.stop_reason == "completed_for_owner_review"
