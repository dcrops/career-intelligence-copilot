"""Unit tests for FR-008 M2 side-effect nodes and decision boundary."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.orchestration import WorkflowState, to_opportunity_decision
from career_intelligence.orchestration.side_effect_nodes import PersistOpportunityNode
from tests.unit.orchestration.m1_helpers import fixture_job_input, offline_runner


def test_to_opportunity_decision_maps_literals() -> None:
    assert to_opportunity_decision("apply") == "apply"
    assert to_opportunity_decision("skip") == "skip"
    assert to_opportunity_decision("defer") == "defer"


def test_create_from_strategy_idempotent_with_planned_id(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    done = runner.resume(paused.run_id, "apply")
    oid = done.artefacts.opportunity_id
    assert oid is not None
    again = runner.opportunities.create_from_strategy(
        posting=done.artefacts.posting,
        job_analysis=done.artefacts.job_analysis,
        assessment=done.artefacts.assessment,
        portfolio_match=done.artefacts.portfolio_match,
        strategy=done.artefacts.strategy,
        opportunity_id=oid,
    )
    assert again.opportunity_id == oid
    assert len(runner.opportunities.list_opportunities()) == 1


def test_persist_node_requires_planned_id(tmp_path: Path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())
    outcome = PersistOpportunityNode(runner.opportunities).execute(
        _state_ready_for_persist(paused)
    )
    assert outcome.failure is not None
    assert "pre-allocated" in outcome.failure.message


def _state_ready_for_persist(paused: WorkflowState) -> WorkflowState:
    """Rewind an awaiting-owner state to the point just before ``persist`` ran."""
    pre_persist = [
        record
        for record in paused.execution.completed_nodes
        if record.node_id not in {"persist", "owner_review"}
    ]
    return WorkflowState.model_validate(
        paused.model_copy(
            update={
                "artefacts": paused.artefacts.model_copy(
                    update={"opportunity_id": None}
                ),
                "execution": paused.execution.model_copy(
                    update={"completed_nodes": pre_persist}
                ),
                "approval": paused.approval.model_copy(
                    update={
                        "pending_kind": None,
                        "pending_options": [],
                        "pending_message": None,
                        "pending_requested_at": None,
                    }
                ),
                "control": paused.control.model_copy(
                    update={"status": "running", "last_error": None}
                ),
            }
        ).model_dump(mode="python")
    )


def test_partial_failure_after_create_recovers_without_duplicate(tmp_path: Path) -> None:
    from career_intelligence.orchestration import InMemoryCheckpointStore, completed_spike_nodes

    store = InMemoryCheckpointStore()
    runner = offline_runner(store=store, opportunities_dir=tmp_path / "opps")
    paused = runner.start(fixture_job_input())

    real_record = runner.opportunities.record_decision
    calls = {"n": 0}

    def flaky(opportunity_id, decision, *, notes=None):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated decision write failure")
        return real_record(opportunity_id, decision, notes=notes)

    runner.opportunities.record_decision = flaky  # type: ignore[method-assign]

    paused_after = runner.resume(paused.run_id, "apply")
    assert paused_after.status == "running"
    assert paused_after.artefacts.opportunity_id is not None
    assert paused_after.control.last_error is not None
    assert len(runner.opportunities.list_opportunities()) == 1
    assert "persist" in completed_spike_nodes(paused_after)
    assert "record_decision" not in completed_spike_nodes(paused_after)

    runner.opportunities.record_decision = real_record  # type: ignore[method-assign]
    done = runner.resume(paused_after.run_id, "apply")
    assert done.status == "completed"
    assert len(runner.opportunities.list_opportunities()) == 1
    opp = runner.opportunities.get(done.artefacts.opportunity_id)  # type: ignore[arg-type]
    assert opp.decision is not None
    assert opp.decision.decision == "apply"
