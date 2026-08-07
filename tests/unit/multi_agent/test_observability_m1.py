"""FR-017 M1 — derive-only orchestration observability contracts."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from career_intelligence.agent.observability import AgentRunMetrics
from career_intelligence.multi_agent import (
    OrchestrationAuditEvent,
    SpecialistVisitRecord,
    new_orchestration_audit_event_id,
)
from career_intelligence.multi_agent.observability import (
    RECONSTRUCTABILITY_IDS,
    OrchestrationRunMetrics,
    aggregate_orchestration_metrics,
    correlate_parent_child,
    evaluate_reconstructability,
    extract_handoff_metrics,
    extract_orchestration_run_metrics,
)
from tests.unit.multi_agent.helpers import (
    OPP,
    _now,
    make_handoff,
    make_observation,
    make_run,
)

AGR_1 = "agr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
AGR_2 = "agr_01ARZ3NDEKTSV4RRFFQ69G5FAB"
AGR_3 = "agr_01ARZ3NDEKTSV4RRFFQ69G5FAC"
OBR_1 = "obr_01ARZ3NDEKTSV4RRFFQ69G5FAA"


def _event(**overrides: object) -> OrchestrationAuditEvent:
    base: dict[str, object] = {
        "event_id": new_orchestration_audit_event_id(),
        "kind": "specialist_selected",
        "at": _now(),
        "specialist_id": "obs",
        "message": "selected obs",
    }
    base.update(overrides)
    return OrchestrationAuditEvent.model_validate(base)


def _child_metrics(**overrides: object) -> AgentRunMetrics:
    base: dict[str, object] = {
        "agent_run_id": AGR_1,
        "opportunity_id": OPP,
        "status": "completed",
        "step_count": 2,
        "max_steps": 8,
        "events_count": 4,
        "provider": None,
        "model": None,
        "input_tokens": None,
        "output_tokens": None,
        "estimated_cost_usd": None,
        "elapsed_ms": None,
        "created_at": _now(),
        "updated_at": _now() + timedelta(seconds=1),
    }
    base.update(overrides)
    return AgentRunMetrics.model_validate(base)


def test_extract_empty_run_counts_are_zero_optional_fields_none() -> None:
    run = make_run(status="running", step_count=0)
    metrics = extract_orchestration_run_metrics(run, ())
    assert metrics.handoff_count == 0
    assert metrics.handoffs_allowed == 0
    assert metrics.handoffs_denied == 0
    assert metrics.events_count == 0
    assert metrics.input_tokens is None
    assert metrics.output_tokens is None
    assert metrics.estimated_cost_usd is None
    assert metrics.provider is None
    assert metrics.model is None
    assert metrics.elapsed_ms == 0  # same created/updated


def test_missing_provider_metadata_not_coerced_to_zero() -> None:
    run = make_run(
        status="completed",
        stop_reason="completed_for_owner_review",
        last_observation=make_observation(),
        child_agent_run_ids=(AGR_1,),
    )
    handoff = make_handoff(
        orchestration_run_id=run.orchestration_run_id,
        target_specialist="bopa",
        requested_goal_kind="prepare_opportunity",
        expected_output_kind="agent_run",
        policy_decision="allow",
        acceptance="completed",
        child_agent_run_id=AGR_1,
        observed_state_hash="hash_a",
        idempotency_key="idem_1",
        resolved_at=_now() + timedelta(seconds=2),
    )
    child = _child_metrics()  # all optional token fields None
    metrics = extract_orchestration_run_metrics(run, (handoff,), child_agent_metrics=(child,))
    assert metrics.input_tokens is None
    assert metrics.output_tokens is None
    assert metrics.estimated_cost_usd is None
    assert metrics.provider is None
    # measured zero remains distinguishable when provided
    child_zero = _child_metrics(input_tokens=0, output_tokens=0, estimated_cost_usd=0.0)
    metrics_zero = extract_orchestration_run_metrics(
        run, (handoff,), child_agent_metrics=(child_zero,)
    )
    assert metrics_zero.input_tokens == 0
    assert metrics_zero.output_tokens == 0
    assert metrics_zero.estimated_cost_usd == 0.0


def test_child_token_cost_rollup() -> None:
    run = make_run(
        status="completed",
        stop_reason="completed_for_owner_review",
        last_observation=make_observation(),
        child_agent_run_ids=(AGR_1, AGR_2),
    )
    children = (
        _child_metrics(
            agent_run_id=AGR_1,
            provider="openai",
            model="gpt-test",
            input_tokens=10,
            output_tokens=5,
            estimated_cost_usd=0.01,
        ),
        _child_metrics(
            agent_run_id=AGR_2,
            provider="openai",
            model="gpt-test",
            input_tokens=20,
            output_tokens=None,
            estimated_cost_usd=0.02,
        ),
    )
    metrics = extract_orchestration_run_metrics(run, (), child_agent_metrics=children)
    assert metrics.provider == "openai"
    assert metrics.model == "gpt-test"
    assert metrics.input_tokens == 30
    assert metrics.output_tokens == 5
    assert metrics.estimated_cost_usd == pytest.approx(0.03)


def test_handoff_metrics_and_allow_deny_counts() -> None:
    run = make_run(status="running", last_observation=make_observation())
    allow = make_handoff(
        orchestration_run_id=run.orchestration_run_id,
        policy_decision="allow",
        acceptance="pending",
        observed_state_hash="hash_a",
    )
    deny = make_handoff(
        orchestration_run_id=run.orchestration_run_id,
        policy_decision="deny",
        policy_deny_reason="not approved for goal",
        acceptance="policy_blocked",
        acceptance_reason="delegation denied",
        observed_state_hash="hash_a",
    )
    metrics = extract_orchestration_run_metrics(run, (allow, deny))
    assert metrics.handoff_count == 2
    assert metrics.handoffs_allowed == 1
    assert metrics.handoffs_denied == 1
    assert metrics.specialists_selected == ("obs",)
    hm = extract_handoff_metrics(deny)
    assert hm.policy_decision == "deny"
    assert hm.policy_deny_reason == "not approved for goal"
    assert hm.handoff_elapsed_ms is None


def test_parent_child_correlation_complete_and_orphan() -> None:
    run = make_run(
        status="completed",
        stop_reason="completed_for_owner_review",
        last_brief_id=OBR_1,
        child_agent_run_ids=(AGR_1,),
        last_observation=make_observation(),
    )
    handoff_ok = make_handoff(
        orchestration_run_id=run.orchestration_run_id,
        target_specialist="bopa",
        expected_output_kind="agent_run",
        policy_decision="allow",
        acceptance="completed",
        child_agent_run_id=AGR_1,
        observed_state_hash="hash_a",
        idempotency_key="k1",
    )
    # brief orphan: last_brief set but no handoff cites it
    corr = correlate_parent_child(run, (handoff_ok,))
    assert corr.orphan_handoff_brief_ids == (OBR_1,)
    assert corr.correlation_complete is False

    obs_handoff = make_handoff(
        orchestration_run_id=run.orchestration_run_id,
        target_specialist="obs",
        expected_output_kind="operational_brief",
        policy_decision="allow",
        acceptance="completed",
        child_brief_id=OBR_1,
        observed_state_hash="hash_a",
        idempotency_key="k2",
    )
    corr2 = correlate_parent_child(run, (handoff_ok, obs_handoff))
    assert corr2.correlation_complete is True
    assert corr2.orphan_parent_child_agent_run_ids == ()
    assert corr2.orphan_handoff_child_agent_run_ids == ()
    assert corr2.orphan_handoff_brief_ids == ()


def test_aggregate_corpus_preserves_none_totals() -> None:
    run = make_run(status="running")
    m = extract_orchestration_run_metrics(run, ())
    corpus = aggregate_orchestration_metrics((m,))
    assert corpus.run_count == 1
    assert corpus.total_input_tokens is None
    assert corpus.total_output_tokens is None
    assert corpus.total_estimated_cost_usd is None
    empty = aggregate_orchestration_metrics(())
    assert empty.run_count == 0
    assert empty.total_handoffs == 0


def test_reconstructability_r1_r12_on_complete_obs_run() -> None:
    run = make_run(
        status="completed",
        stop_reason="completed_for_owner_review",
        step_count=1,
        last_observation=make_observation(),
        last_brief_id=OBR_1,
        events=(_event(),),
        specialist_visits=(
            SpecialistVisitRecord(
                specialist_id="obs",
                visit_count=1,
                last_observation_hash="hash_a",
            ),
        ),
        owner_action_required=None,
    )
    handoff = make_handoff(
        orchestration_run_id=run.orchestration_run_id,
        target_specialist="obs",
        expected_output_kind="operational_brief",
        policy_decision="allow",
        acceptance="completed",
        child_brief_id=OBR_1,
        observed_state_hash="hash_a",
        idempotency_key="idem_obs",
        resolved_at=_now() + timedelta(milliseconds=500),
    )
    report = evaluate_reconstructability(run, (handoff,))
    assert report.total_count == 12
    assert tuple(c.criterion_id for c in report.checks) == RECONSTRUCTABILITY_IDS
    assert report.all_satisfied is True
    assert report.satisfied_count == 12


def test_reconstructability_detects_r11_orphan() -> None:
    run = make_run(
        status="completed",
        stop_reason="completed_for_owner_review",
        last_observation=make_observation(),
        child_agent_run_ids=(AGR_3,),
        events=(_event(specialist_id="bopa"),),
    )
    handoff = make_handoff(
        orchestration_run_id=run.orchestration_run_id,
        target_specialist="bopa",
        expected_output_kind="agent_run",
        policy_decision="allow",
        acceptance="completed",
        child_agent_run_id=AGR_2,
        observed_state_hash="hash_a",
        idempotency_key="idem_b",
    )
    report = evaluate_reconstructability(run, (handoff,))
    r11 = next(c for c in report.checks if c.criterion_id == "R11")
    assert r11.satisfied is False


def test_reconstructability_r9_awaiting_owner_requires_action() -> None:
    run = make_run(
        status="awaiting_owner",
        stop_reason="owner_approval_required",
        owner_action_required=None,
        last_observation=make_observation(),
        events=(_event(),),
    )
    report = evaluate_reconstructability(run, ())
    r9 = next(c for c in report.checks if c.criterion_id == "R9")
    assert r9.satisfied is False


def test_metrics_models_forbid_extra() -> None:
    run = make_run(status="running")
    metrics = extract_orchestration_run_metrics(run, ())
    raw = metrics.model_dump(mode="python")
    raw["mystery"] = True
    with pytest.raises(ValidationError):
        OrchestrationRunMetrics.model_validate(raw)


def test_visit_and_step_limit_flags() -> None:
    run = make_run(
        status="failed",
        stop_reason="specialist_visit_limit",
        step_count=3,
        max_steps=8,
        max_visits_per_specialist=1,
        last_observation=make_observation(),
        specialist_visits=(
            SpecialistVisitRecord(specialist_id="obs", visit_count=1),
        ),
        events=(_event(),),
        updated_at=_now() + timedelta(seconds=3),
    )
    metrics = extract_orchestration_run_metrics(run, ())
    assert metrics.visit_limit_reached is True
    assert metrics.elapsed_ms == 3000
