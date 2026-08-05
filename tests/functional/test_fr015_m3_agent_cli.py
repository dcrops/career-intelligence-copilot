"""Functional smoke for FR-015 M3 agent CLI presentation surface."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.agent import (
    AgentGoal,
    AgentRuntime,
    DeterministicActionProposer,
    JsonDirectoryAgentRunStore,
    ScriptedActionExecutor,
    StaticReadinessBuilder,
)
from career_intelligence.cli.main import app
from tests.unit.agent.helpers import OPP, make_artefacts, make_snapshot

runner = CliRunner()


def test_fr015_m3_cli_show_history_list_roundtrip(tmp_path: Path) -> None:
    store = JsonDirectoryAgentRunStore(tmp_path / "agent_runs")
    run = AgentRuntime(
        readiness=StaticReadinessBuilder(
            [make_snapshot(artefacts=make_artefacts(assessment=False))]
        ),
        executor=ScriptedActionExecutor(),
        proposer=DeterministicActionProposer(),
        store=store,
    ).start(AgentGoal(opportunity_id=OPP), owner_approvals_present=True)

    shown = runner.invoke(
        app,
        ["agent", "show", run.agent_run_id, "--agent-runs-dir", str(tmp_path / "agent_runs")],
    )
    assert shown.exit_code == 0
    for needle in (
        "run_id:",
        "Observed readiness",
        "proposed:",
        "policy:",
        "stop_reason:",
        "Owner action required",
        "invalid_state",
    ):
        assert needle in shown.output

    hist = runner.invoke(
        app,
        [
            "agent",
            "history",
            run.agent_run_id,
            "--agent-runs-dir",
            str(tmp_path / "agent_runs"),
        ],
    )
    assert hist.exit_code == 0
    assert "stop_recorded" in hist.output

    listed = runner.invoke(
        app,
        ["agent", "list", "--agent-runs-dir", str(tmp_path / "agent_runs")],
    )
    assert listed.exit_code == 0
    assert run.agent_run_id in listed.output
