"""Unit tests for FR-008 M3 runner retry / exhaustion / resume behaviour."""

from __future__ import annotations

from career_intelligence.orchestration import (
    FailureInjection,
    InMemoryCheckpointStore,
    JsonDirectoryCheckpointStore,
    RetryPolicy,
    WorkflowResumeError,
)
from tests.unit.orchestration.m1_helpers import (
    fixture_job_input,
    json_runner,
    offline_dependencies,
    offline_runner,
)


def _event_types(state) -> list[str]:
    return [event.event_type for event in state.execution.events]


def _analyse_attempts(state) -> list[int]:
    return [
        event.attempt
        for event in state.execution.events
        if event.event_type == "node_started" and event.node_id == "analyse"
    ]


def test_same_process_recoverable_analyse_then_success() -> None:
    runner = offline_runner(
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="recoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=3),
    )
    state = runner.start(fixture_job_input())
    assert state.status == "awaiting_owner"
    assert state.retry is None
    assert "analyse" in {n.node_id for n in state.execution.completed_nodes}
    assert _analyse_attempts(state) == [1, 2]
    types = _event_types(state)
    assert types.count("node_failed") >= 1
    assert "retry_scheduled" in types
    assert types.index("node_failed") < types.index("retry_scheduled")
    assert "acquire" in {n.node_id for n in state.execution.completed_nodes}
    # Prior nodes completed once.
    assert sum(1 for n in state.execution.completed_nodes if n.node_id == "acquire") == 1


def test_retry_exhaustion_fails_closed_no_opportunity(tmp_path) -> None:
    runner = offline_runner(
        store=InMemoryCheckpointStore(),
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=5, kind="recoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=3),
    )
    state = runner.start(fixture_job_input())
    assert state.status == "failed"
    assert state.retry is not None
    assert state.retry.exhausted
    assert state.retry.attempts_used == 3
    assert "retry_exhausted" in _event_types(state)
    assert "owner_review" not in {n.node_id for n in state.execution.completed_nodes}
    assert state.artefacts.opportunity_id is None
    assert list(runner.opportunities.list_opportunities()) == []
    # Downstream nodes did not run.
    assert state.artefacts.job_analysis is None
    assert _analyse_attempts(state) == [1, 2, 3]


def test_unrecoverable_injected_failure_no_retry() -> None:
    runner = offline_runner(
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="unrecoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=3),
    )
    state = runner.start(fixture_job_input())
    assert state.status == "failed"
    assert "retry_scheduled" not in _event_types(state)
    assert "retry_exhausted" not in _event_types(state)
    assert _analyse_attempts(state) == [1]
    assert state.artefacts.job_analysis is None


def test_validation_failure_not_retried() -> None:
    runner = offline_runner()
    state = runner.start(fixture_job_input(raw_text="   "))
    assert state.status == "failed"
    assert "retry_scheduled" not in _event_types(state)
    assert state.control.last_error is not None
    assert state.control.last_error.recoverable is False


def test_cross_process_assess_retry_preserves_budget(tmp_path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    policy = RetryPolicy(max_attempts=3, yield_after_retry_schedule=True)
    first = offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="assess", fail_count=1, kind="recoverable"
        ),
        retry_policy=policy,
    )
    paused = first.start(fixture_job_input())
    assert paused.status == "running"
    assert paused.retry is not None
    assert paused.retry.node_id == "assess"
    assert paused.retry.attempts_used == 1
    assert not paused.retry.exhausted
    assert "retry_scheduled" in _event_types(paused)
    assert "assess" not in {n.node_id for n in paused.execution.completed_nodes}
    assert paused.artefacts.job_analysis is not None
    run_id = paused.run_id

    # New process: no injection; remaining budget continues from checkpoint.
    second = offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opps",
        retry_policy=RetryPolicy(max_attempts=3),
    )
    resumed = second.continue_run(run_id)
    assert resumed.run_id == run_id
    assert resumed.status == "awaiting_owner"
    assert resumed.retry is None
    assess_starts = [
        e
        for e in resumed.execution.events
        if e.event_type == "node_started" and e.node_id == "assess"
    ]
    assert [e.attempt for e in assess_starts] == [1, 2]
    # Analysis completed only once.
    assert sum(1 for n in resumed.execution.completed_nodes if n.node_id == "analyse") == 1
    assert "run_resumed" in _event_types(resumed)


def test_resume_exhausted_budget_fails_without_rerun(tmp_path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    policy = RetryPolicy(max_attempts=2, yield_after_retry_schedule=True)
    first = offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=2, kind="recoverable"
        ),
        retry_policy=policy,
    )
    # Attempt 1 fails → yield with budget remaining.
    paused = first.start(fixture_job_input())
    assert paused.status == "running"
    assert paused.retry is not None
    assert paused.retry.attempts_used == 1

    # Same injection process would fail attempt 2 and exhaust; use continue with
    # a runner that still injects once more then would succeed — but max=2 so
    # second failure exhausts.
    second = offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="recoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=2),
    )
    failed = second.continue_run(paused.run_id)
    assert failed.status == "failed"
    assert failed.retry is not None
    assert failed.retry.exhausted
    assert failed.retry.attempts_used == 2
    assert "retry_exhausted" in _event_types(failed)
    assert failed.artefacts.job_analysis is None


def test_m2_opportunity_id_stable_after_retry_path(tmp_path) -> None:
    runner = json_runner(
        tmp_path,
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="recoverable"
        ),
    )
    awaiting = runner.start(fixture_job_input())
    assert awaiting.status == "awaiting_owner"
    completed = runner.resume(awaiting.run_id, "apply")
    assert completed.status == "completed"
    opp_id = completed.artefacts.opportunity_id
    assert opp_id is not None
    again = runner.resume(awaiting.run_id, "apply")
    assert again.status == "completed"
    assert again.artefacts.opportunity_id == opp_id
    assert len(list(runner.opportunities.list_opportunities())) == 1


def test_cancel_while_retry_paused(tmp_path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    runner = offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="recoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=3, yield_after_retry_schedule=True),
    )
    paused = runner.start(fixture_job_input())
    assert paused.status == "running"
    cancelled = runner.cancel(paused.run_id)
    assert cancelled.status == "cancelled"
    assert "run_cancelled" in _event_types(cancelled)
    assert list(runner.opportunities.list_opportunities()) == []


def test_resume_decision_rejected_while_retry_running(tmp_path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    runner = offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opps",
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="recoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=3, yield_after_retry_schedule=True),
    )
    paused = runner.start(fixture_job_input())
    try:
        runner.resume(paused.run_id, "apply")
        raise AssertionError("expected WorkflowResumeError")
    except WorkflowResumeError as error:
        assert "continue_run" in str(error)


def test_prior_completed_nodes_not_reexecuted_on_continue(tmp_path) -> None:
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
    acquire_events = sum(
        1
        for e in paused.execution.events
        if e.event_type == "node_started" and e.node_id == "acquire"
    )
    assert acquire_events == 1

    second = offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opps",
    )
    done = second.continue_run(paused.run_id)
    acquire_events_after = sum(
        1
        for e in done.execution.events
        if e.event_type == "node_started" and e.node_id == "acquire"
    )
    assert acquire_events_after == 1
    assert done.status == "awaiting_owner"


def test_checkpoint_survives_retry_state(tmp_path) -> None:
    runner = json_runner(
        tmp_path,
        failure_injection=FailureInjection(
            node_id="analyse", fail_count=1, kind="recoverable"
        ),
        retry_policy=RetryPolicy(max_attempts=3, yield_after_retry_schedule=True),
    )
    paused = runner.start(fixture_job_input())
    loaded = runner.store.load(paused.run_id)
    assert loaded.retry is not None
    assert loaded.retry.attempts_used == 1
    assert loaded.retry.last_classification == "recoverable"
