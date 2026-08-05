"""CLI tests for FR-015 M3 ``cic agent`` owner commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from career_intelligence.agent import (
    AgentGoal,
    AgentRun,
    AgentRuntime,
    DeterministicActionProposer,
    InMemoryAgentRunStore,
    JsonDirectoryAgentRunStore,
    ScriptedActionExecutor,
    StaticReadinessBuilder,
    AdapterResult,
    new_agent_run_id,
)
from career_intelligence.cli.main import app
from tests.unit.agent.helpers import (
    OPP,
    make_artefacts,
    make_package,
    make_snapshot,
    make_truth,
)

runner = CliRunner()


def _seed_run(tmp_path: Path, **snapshot_kwargs: object) -> AgentRun:
    snap = make_snapshot(**snapshot_kwargs)
    store = JsonDirectoryAgentRunStore(tmp_path / "agent_runs")
    runtime = AgentRuntime(
        readiness=StaticReadinessBuilder([snap]),
        executor=ScriptedActionExecutor(),
        proposer=DeterministicActionProposer(),
        store=store,
    )
    return runtime.start(AgentGoal(opportunity_id=OPP), owner_approvals_present=True)


def test_agent_run_requires_approve(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "run",
            OPP,
            "--dir",
            str(tmp_path),
            "--agent-runs-dir",
            str(tmp_path / "agent_runs"),
        ],
    )
    assert result.exit_code == 1
    assert "--approve" in result.output
    assert "Refusing agent run" in result.output


def test_agent_resume_requires_approve(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "resume",
            "agr_01ARZ3NDEKTSV4RRFFQ69G5FAA",
            "--agent-runs-dir",
            str(tmp_path / "agent_runs"),
        ],
    )
    assert result.exit_code == 1
    assert "Refusing agent resume" in result.output


def test_agent_show_history_list(tmp_path: Path) -> None:
    run = _seed_run(tmp_path, artefacts=make_artefacts(job_analysis=False))
    runs_dir = str(tmp_path / "agent_runs")

    shown = runner.invoke(
        app,
        ["agent", "show", run.agent_run_id, "--agent-runs-dir", runs_dir],
    )
    assert shown.exit_code == 0, shown.output
    assert run.agent_run_id in shown.output
    assert "Observed readiness" in shown.output
    assert "stop_reason:" in shown.output
    assert "Owner action required" in shown.output
    assert "invalid_state" in shown.output

    hist = runner.invoke(
        app,
        ["agent", "history", run.agent_run_id, "--agent-runs-dir", runs_dir],
    )
    assert hist.exit_code == 0, hist.output
    assert "Audit history" in hist.output
    assert "stop_recorded" in hist.output

    listed = runner.invoke(app, ["agent", "list", "--agent-runs-dir", runs_dir])
    assert listed.exit_code == 0, listed.output
    assert run.agent_run_id in listed.output
    assert OPP in listed.output


def test_agent_show_missing(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "show",
            "agr_01ARZ3NDEKTSV4RRFFQ69G5FAA",
            "--agent-runs-dir",
            str(tmp_path / "empty_runs"),
        ],
    )
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_agent_run_with_injected_runtime(tmp_path: Path, monkeypatch) -> None:
    """CLI run path via monkeypatched factory (offline readiness world)."""
    missing = make_snapshot(package=make_package(status="absent"))
    need_truth = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="package:x",
        ),
        truth=make_truth(status="absent"),
    )
    ready = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="package:x",
        ),
        truth=make_truth(status="pass", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
    )
    store = JsonDirectoryAgentRunStore(tmp_path / "agent_runs")
    runtime = AgentRuntime(
        readiness=StaticReadinessBuilder([missing, need_truth, ready]),
        executor=ScriptedActionExecutor(
            {
                "run_preparation": [
                    AdapterResult(summary="prepared", result_ref="apr_x", mutates_domain=True)
                ],
                "validate_truth_package": [
                    AdapterResult(summary="pass", result_ref="trp_x", mutates_domain=True)
                ],
            }
        ),
        proposer=DeterministicActionProposer(),
        store=store,
    )

    def _fake_build(**kwargs):
        return runtime

    monkeypatch.setattr("career_intelligence.cli.main.build_agent_runtime", _fake_build)
    result = runner.invoke(
        app,
        [
            "agent",
            "run",
            OPP,
            "--approve",
            "--agent-runs-dir",
            str(tmp_path / "agent_runs"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "completed_for_owner_review" in result.output
    assert "Observed readiness" in result.output
    assert "proposed:" in result.output
    assert "policy:" in result.output


def test_agent_list_filter_opportunity(tmp_path: Path) -> None:
    run = _seed_run(tmp_path, artefacts=make_artefacts(strategy=False))
    # Write a decoy run with different opportunity via direct save.
    store = JsonDirectoryAgentRunStore(tmp_path / "agent_runs")
    decoy = AgentRun(
        agent_run_id=new_agent_run_id(),
        goal=AgentGoal(opportunity_id="opp_01ARZ3NDEKTSV4RRFFQ69G5FAB"),
        status="failed",
        stop_reason="unexpected_failure",
        step_count=0,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    store.save(decoy)
    listed = runner.invoke(
        app,
        [
            "agent",
            "list",
            "--agent-runs-dir",
            str(tmp_path / "agent_runs"),
            "--opportunity",
            OPP,
        ],
    )
    assert listed.exit_code == 0
    assert run.agent_run_id in listed.output
    assert decoy.agent_run_id not in listed.output
