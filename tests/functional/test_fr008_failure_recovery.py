"""Functional FR-008 M3 failure-recovery scenarios."""

from __future__ import annotations

from career_intelligence.orchestration import (
    FailureInjection,
    JsonDirectoryCheckpointStore,
    RetryPolicy,
)
from tests.unit.orchestration.m1_helpers import fixture_job_input, offline_runner


def test_functional_recoverable_analyse_reaches_owner_review(tmp_path) -> None:
    runner = offline_runner(
        store=JsonDirectoryCheckpointStore(tmp_path / "runs"),
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="recoverable"
        ),
    )
    state = runner.start(fixture_job_input())
    assert state.status == "awaiting_owner"
    assert state.artefacts.job_analysis is not None
    assert state.artefacts.strategy is not None
    types = [e.event_type for e in state.execution.events]
    assert "node_failed" in types
    assert "retry_scheduled" in types
    assert types.count("node_succeeded") >= 7  # pre-approval graph


def test_functional_assess_cross_process_recovery(tmp_path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    first = offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="assess", fail_count=1, kind="recoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=3, yield_after_retry_schedule=True),
    )
    paused = first.start(fixture_job_input())
    run_id = paused.run_id
    assert paused.status == "running"
    assert paused.retry is not None

    second = offline_runner(store=store, opportunities_dir=tmp_path / "opps")
    resumed = second.continue_run(run_id)
    assert resumed.run_id == run_id
    assert resumed.status == "awaiting_owner"
    assert resumed.retry is None
    assert resumed.artefacts.assessment is not None
    analyse_starts = [
        e
        for e in resumed.execution.events
        if e.event_type == "node_started" and e.node_id == "analyse"
    ]
    assert len(analyse_starts) == 1


def test_functional_retry_exhaustion_no_downstream(tmp_path) -> None:
    runner = offline_runner(
        store=JsonDirectoryCheckpointStore(tmp_path / "runs"),
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="assess", fail_count=10, kind="recoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=3),
    )
    state = runner.start(fixture_job_input())
    assert state.status == "failed"
    assert state.retry is not None and state.retry.exhausted
    loaded = runner.store.load(state.run_id)
    assert loaded.status == "failed"
    assert loaded.artefacts.assessment is None
    assert loaded.artefacts.portfolio_match is None
    assert loaded.artefacts.opportunity_id is None
    assert list(runner.opportunities.list_opportunities()) == []
    assert "match" not in {n.node_id for n in loaded.execution.completed_nodes}


def test_functional_unrecoverable_validation(tmp_path) -> None:
    runner = offline_runner(
        store=JsonDirectoryCheckpointStore(tmp_path / "runs"),
        opportunities_dir=tmp_path / "opps",
    )
    state = runner.start(fixture_job_input(raw_text=""))
    assert state.status == "failed"
    assert all(e.event_type != "retry_scheduled" for e in state.execution.events)
    assert state.artefacts.posting is None


def test_functional_m2_regression_after_retry(tmp_path) -> None:
    runner = offline_runner(
        store=JsonDirectoryCheckpointStore(tmp_path / "runs"),
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="recoverable"
        ),
    )
    awaiting = runner.start(fixture_job_input())
    completed = runner.resume(awaiting.run_id, "apply")
    assert completed.status == "completed"
    opp_id = completed.artefacts.opportunity_id
    assert opp_id is not None
    reloaded = runner.resume(awaiting.run_id, "apply")
    assert reloaded.artefacts.opportunity_id == opp_id
    assert len(list(runner.opportunities.list_opportunities())) == 1
    record = runner.opportunities.get(opp_id)
    assert record.decision is not None
    assert record.decision.decision == "apply"
