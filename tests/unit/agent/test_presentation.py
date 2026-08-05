"""Tests for FR-015 M3 agent owner presentation."""

from __future__ import annotations

from career_intelligence.agent import (
    format_agent_history,
    format_agent_list_line,
    format_agent_run_report,
    owner_action_required,
)
from career_intelligence.agent import (
    AgentRuntime,
    DeterministicActionProposer,
    InMemoryAgentRunStore,
    ScriptedActionExecutor,
    StaticReadinessBuilder,
    AgentGoal,
)
from tests.unit.agent.helpers import OPP, make_artefacts, make_package, make_snapshot


def test_owner_action_for_invalid_state() -> None:
    text = owner_action_required("invalid_state")
    assert "FR-008" in text
    assert "BOPA will not invoke" in text


def test_format_run_report_includes_required_sections() -> None:
    snap = make_snapshot(artefacts=make_artefacts(job_analysis=False))
    run = AgentRuntime(
        readiness=StaticReadinessBuilder([snap]),
        executor=ScriptedActionExecutor(),
        proposer=DeterministicActionProposer(),
        store=InMemoryAgentRunStore(),
    ).start(AgentGoal(opportunity_id=OPP), owner_approvals_present=True)
    report = format_agent_run_report(run, verbose=True)
    assert "Observed readiness" in report
    assert "primary_state:" in report
    assert "Steps" in report
    assert "proposed:" in report
    assert "policy:" in report
    assert "Owner action required" in report
    assert "stop_reason:" in report
    assert run.agent_run_id in report
    assert "pipeline" in report.lower()


def test_format_history_and_list() -> None:
    snap = make_snapshot(package=make_package(status="absent"))
    # Without approvals -> owner_approval_required immediate-ish via classify
    snap = make_snapshot(
        package=make_package(status="absent"),
        owner_approvals_present=False,
    )
    run = AgentRuntime(
        readiness=StaticReadinessBuilder([snap]),
        executor=ScriptedActionExecutor(),
        store=InMemoryAgentRunStore(),
    ).start(AgentGoal(opportunity_id=OPP), owner_approvals_present=False)
    hist = format_agent_history(run)
    assert run.agent_run_id in hist
    assert "snapshot_observed" in hist or "stop_recorded" in hist
    line = format_agent_list_line(run)
    assert run.agent_run_id in line
    assert OPP in line
