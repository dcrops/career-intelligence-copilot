"""CLI and presentation tests for FR-016 M3 learning-proof owner workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.agent.adapters import AdapterResult, ScriptedActionExecutor
from career_intelligence.agent.memory_store import InMemoryAgentRunStore
from career_intelligence.agent.models import (
    ArtefactPresence,
    PackageReadiness,
    ReadinessSnapshot,
    TruthReadiness,
)
from career_intelligence.agent.proposer import DeterministicActionProposer
from career_intelligence.agent.readiness import StaticReadinessBuilder
from career_intelligence.agent.runtime import AgentRuntime
from career_intelligence.cli.main import app
from career_intelligence.multi_agent import (
    BopaSpecialistAdapter,
    DeterministicOrchestrationSupervisor,
    InMemoryOrchestrationStore,
    StaticObservationBuilder,
    format_orchestration_history,
    format_orchestration_list_line,
    format_orchestration_report,
    goal_from_owner_name,
    observation_from_snapshot,
    owner_action_for_orchestration,
    owner_goal_label,
    specialist_authority_lines,
)

runner = CliRunner()
OPP = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"


def _now() -> datetime:
    return datetime(2026, 8, 6, 17, 0, tzinfo=timezone.utc)


def _snap(**overrides: object) -> ReadinessSnapshot:
    base: dict[str, object] = {
        "opportunity_id": OPP,
        "decision": "apply",
        "artefacts": ArtefactPresence(
            job_analysis=True,
            assessment=True,
            portfolio_match=True,
            strategy=True,
        ),
        "package": PackageReadiness(status="absent"),
        "truth": TruthReadiness(status="absent"),
        "owner_approvals_present": True,
        "provider_available": True,
        "pipeline_status": "assessed",
        "observed_at": _now(),
    }
    base.update(overrides)
    return ReadinessSnapshot.model_validate(base)


def test_goal_mapping() -> None:
    brief = goal_from_owner_name("brief", OPP)
    assert owner_goal_label(brief) == "brief"
    prep = goal_from_owner_name("prepare", OPP)
    assert owner_goal_label(prep) == "prepare"
    both = goal_from_owner_name("prepare_then_brief", OPP)
    assert owner_goal_label(both) == "prepare_then_brief"
    assert both.synthesize_after_prepare is True


def test_authority_display() -> None:
    bopa = specialist_authority_lines("bopa")
    obs = specialist_authority_lines("obs")
    assert any("Must not submit" in line for line in bopa)
    assert any("Read-only" in line for line in obs)
    assert any("Must not prepare" in line for line in obs)


def test_presentation_shows_handoff_and_authority() -> None:
    goal = goal_from_owner_name("brief", OPP)
    obs = observation_from_snapshot(_snap(pipeline_status="interviewing"), goal)
    store = InMemoryOrchestrationStore()
    dos = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder([obs]),
        store=store,
    )
    run = dos.start(goal, owner_approvals_present=True)
    report = format_orchestration_report(run, store, verbose=True)
    assert "learning proof" in report.lower()
    assert "Owner goal:" in report
    assert "Handoff" in report
    assert "ToolPolicy / authority boundary" in report
    assert "Read-only" in report
    assert run.orchestration_run_id in report
    assert "cic agent run" in report.lower() or "Prefer" in report
    history = format_orchestration_history(run)
    assert "orchestration_started" in history
    assert format_orchestration_list_line(run).startswith(run.orchestration_run_id)
    assert "resume" in owner_action_for_orchestration(run)


def test_prepare_then_brief_parent_child_trace() -> None:
    goal = goal_from_owner_name("prepare_then_brief", OPP)
    miss = _snap()
    ready = _snap(
        package=PackageReadiness(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="pkg/x",
        ),
        truth=TruthReadiness(status="pass", report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA"),
    )
    agent = AgentRuntime(
        readiness=StaticReadinessBuilder([miss, ready, ready, ready]),
        executor=ScriptedActionExecutor(
            {
                "run_preparation": [
                    AdapterResult(
                        summary="ok",
                        result_ref="apr_01ARZ3NDEKTSV4RRFFQ69G5FAA",
                        mutates_domain=True,
                    )
                ]
            }
        ),
        proposer=DeterministicActionProposer(),
        store=InMemoryAgentRunStore(),
    )
    store = InMemoryOrchestrationStore()
    dos = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [
                observation_from_snapshot(miss, goal),
                observation_from_snapshot(ready, goal),
                observation_from_snapshot(ready, goal),
            ]
        ),
        bopa_adapter=BopaSpecialistAdapter(agent),
        store=store,
    )
    run = dos.start(goal, owner_approvals_present=True)
    specs = [v.specialist_id for v in run.specialist_visits]
    assert specs == ["bopa", "obs"]
    assert run.child_agent_run_ids
    assert run.last_brief_id
    report = format_orchestration_report(run, store)
    assert run.child_agent_run_ids[0] in report
    assert "BOPA AgentRun" in report
    assert "OBS brief" in report


def test_orchestrate_run_requires_approve(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "orchestrate",
            "run",
            OPP,
            "--goal",
            "brief",
            "--orchestration-runs-dir",
            str(tmp_path / "orch"),
        ],
    )
    assert result.exit_code == 1
    assert "--approve" in result.output


def test_orchestrate_show_history_list(tmp_path: Path) -> None:
    goal = goal_from_owner_name("brief", OPP)
    obs = observation_from_snapshot(_snap(), goal)
    from career_intelligence.multi_agent import JsonDirectoryOrchestrationStore

    store = JsonDirectoryOrchestrationStore(tmp_path / "orch")
    dos = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder([obs]),
        store=store,
    )
    run = dos.start(goal, owner_approvals_present=True)

    show = runner.invoke(
        app,
        [
            "agent",
            "orchestrate",
            "show",
            run.orchestration_run_id,
            "--orchestration-runs-dir",
            str(tmp_path / "orch"),
        ],
    )
    assert show.exit_code == 0
    assert run.orchestration_run_id in show.output
    assert "authority boundary" in show.output

    history = runner.invoke(
        app,
        [
            "agent",
            "orchestrate",
            "history",
            run.orchestration_run_id,
            "--orchestration-runs-dir",
            str(tmp_path / "orch"),
        ],
    )
    assert history.exit_code == 0
    assert "orchestration_started" in history.output

    listed = runner.invoke(
        app,
        [
            "agent",
            "orchestrate",
            "list",
            "--orchestration-runs-dir",
            str(tmp_path / "orch"),
        ],
    )
    assert listed.exit_code == 0
    assert run.orchestration_run_id in listed.output


def test_check_delegation_illegal(tmp_path: Path, monkeypatch) -> None:
    """check-delegation shows deny without executing (uses live builder — mock it)."""
    from career_intelligence.multi_agent.models import (
        DelegationDecision,
        OrchestrationObservation,
    )

    class FakeObs:
        def build(self, goal, **kwargs):
            return OrchestrationObservation(
                opportunity_id=goal.opportunity_id,
                decision="apply",
                package_status="absent",
                truth_status="absent",
                pipeline_status="interviewing",
                owner_approvals_present=True,
                briefing_need_classes=("pipeline_advises_against_preparation",),
                observation_hash="abc",
                observed_at=_now(),
            )

    class FakeDos:
        def __init__(self):
            self._observation = FakeObs()

    def fake_build(**kwargs):
        return FakeDos(), None

    monkeypatch.setattr(
        "career_intelligence.cli.main.build_orchestration_supervisor",
        fake_build,
    )
    result = runner.invoke(
        app,
        [
            "agent",
            "orchestrate",
            "check-delegation",
            OPP,
            "--goal",
            "brief",
            "--target",
            "bopa",
        ],
    )
    assert result.exit_code == 1
    assert "decision=deny" in result.output
