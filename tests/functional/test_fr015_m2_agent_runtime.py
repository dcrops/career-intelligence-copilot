"""Functional tests for FR-015 M2 bounded agent runtime."""

from __future__ import annotations

from career_intelligence.agent import (
    AgentGoal,
    AgentRuntime,
    DeterministicActionProposer,
    InMemoryAgentRunStore,
    ScriptedActionExecutor,
    StaticReadinessBuilder,
    AdapterResult,
)
from tests.unit.agent.helpers import (
    OPP,
    make_artefacts,
    make_package,
    make_snapshot,
    make_truth,
)


def test_fr015_m2_end_to_end_coordination_and_audit() -> None:
    missing = make_snapshot(package=make_package(status="absent"))
    need_truth = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref=f"package:{OPP}",
        ),
        truth=make_truth(status="absent"),
    )
    ready = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref=f"package:{OPP}",
        ),
        truth=make_truth(status="pass", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
    )
    executor = ScriptedActionExecutor(
        {
            "run_preparation": [
                AdapterResult(summary="ok", result_ref="apr_x", mutates_domain=True)
            ],
            "validate_truth_package": [
                AdapterResult(summary="pass", result_ref="trp_x", mutates_domain=True)
            ],
        }
    )
    runtime = AgentRuntime(
        readiness=StaticReadinessBuilder([missing, need_truth, ready]),
        executor=executor,
        proposer=DeterministicActionProposer(),
        store=InMemoryAgentRunStore(),
    )
    run = runtime.start(AgentGoal(opportunity_id=OPP), owner_approvals_present=True)
    assert run.stop_reason == "completed_for_owner_review"
    kinds = [e.kind for e in run.events]
    assert "run_started" in kinds
    assert "snapshot_observed" in kinds
    assert "action_proposed" in kinds
    assert "policy_evaluated" in kinds
    assert "action_executed" in kinds
    assert "stop_recorded" in kinds


def test_fr015_m2_missing_strategy_never_calls_fr008() -> None:
    snap = make_snapshot(artefacts=make_artefacts(strategy=False))
    executor = ScriptedActionExecutor()
    runtime = AgentRuntime(
        readiness=StaticReadinessBuilder([snap]),
        executor=executor,
        store=InMemoryAgentRunStore(),
    )
    run = runtime.start(AgentGoal(opportunity_id=OPP), owner_approvals_present=True)
    assert run.stop_reason == "invalid_state"
    assert executor.calls == []
