#!/usr/bin/env python3
"""FR-016 M4 manual validation + final corpus (learning-proof freeze).

Live Opportunity SoT is currently empty (index only). Journeys A-H use the same
deterministic fixtures as M2/M3 offline DOS + CLI surface. Corpus is the
authoritative 20/20 acceptance suite.
"""

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
    evaluate_delegation_policy,
    format_orchestration_history,
    format_orchestration_report,
    goal_from_owner_name,
    go_no_go_assessment,
    observation_from_snapshot,
    run_corpus,
    SpecialistDelegationProposal,
)

OPP = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"
runner = CliRunner()


def _now() -> datetime:
    return datetime(2026, 8, 6, 20, 0, tzinfo=timezone.utc)


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


def _section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    failures = 0

    _section("Final corpus (20 cases)")
    report = run_corpus()
    for case in report.results:
        mark = "PASS" if case.passed else "FAIL"
        print(f"  [{mark}] {case.case_id}: stop={case.stop_reason} {case.detail}")
        if not case.passed:
            failures += 1
    print(f"Corpus: {report.passed}/{report.total} all_passed={report.all_passed}")
    print("Assessment:", go_no_go_assessment(report))

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

    _section("A. brief-only")
    goal = goal_from_owner_name("brief", OPP)
    store = InMemoryOrchestrationStore()
    dos = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [observation_from_snapshot(_snap(), goal)]
        ),
        store=store,
    )
    run_a = dos.start(goal, owner_approvals_present=True)
    print(format_orchestration_report(run_a, store))
    if run_a.stop_reason != "briefing_complete":
        failures += 1

    _section("B. prepare")
    goal_b = goal_from_owner_name("prepare", OPP)
    agent = AgentRuntime(
        readiness=StaticReadinessBuilder([miss, ready, ready]),
        executor=ScriptedActionExecutor(
            {
                "run_preparation": [
                    AdapterResult(
                        summary="prepared",
                        result_ref="apr_01ARZ3NDEKTSV4RRFFQ69G5FAA",
                        mutates_domain=True,
                    )
                ]
            }
        ),
        proposer=DeterministicActionProposer(),
        store=InMemoryAgentRunStore(),
    )
    store_b = InMemoryOrchestrationStore()
    dos_b = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [observation_from_snapshot(miss, goal_b)]
        ),
        bopa_adapter=BopaSpecialistAdapter(agent),
        store=store_b,
    )
    run_b = dos_b.start(goal_b, owner_approvals_present=True)
    print(format_orchestration_report(run_b, store_b))
    if "bopa" not in {v.specialist_id for v in run_b.specialist_visits}:
        failures += 1

    _section("C. prepare_then_brief")
    goal_c = goal_from_owner_name("prepare_then_brief", OPP)
    agent_c = AgentRuntime(
        readiness=StaticReadinessBuilder([miss, ready, ready, ready]),
        executor=ScriptedActionExecutor(
            {
                "run_preparation": [
                    AdapterResult(
                        summary="prepared",
                        result_ref="apr_01ARZ3NDEKTSV4RRFFQ69G5FAA",
                        mutates_domain=True,
                    )
                ]
            }
        ),
        proposer=DeterministicActionProposer(),
        store=InMemoryAgentRunStore(),
    )
    store_c = InMemoryOrchestrationStore()
    dos_c = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [
                observation_from_snapshot(miss, goal_c),
                observation_from_snapshot(ready, goal_c),
                observation_from_snapshot(ready, goal_c),
            ]
        ),
        bopa_adapter=BopaSpecialistAdapter(agent_c),
        store=store_c,
    )
    run_c = dos_c.start(goal_c, owner_approvals_present=True)
    print(format_orchestration_report(run_c, store_c))
    specs = [v.specialist_id for v in run_c.specialist_visits]
    if specs[:2] != ["bopa", "obs"]:
        failures += 1

    _section("D. truth blocked")
    goal_d = goal_from_owner_name("brief", OPP)
    store_d = InMemoryOrchestrationStore()
    dos_d = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [
                observation_from_snapshot(
                    _snap(
                        package=PackageReadiness(
                            status="present",
                            cv_present=True,
                            cover_letter_present=True,
                            manifest_ref="pkg/x",
                        ),
                        truth=TruthReadiness(
                            status="fail",
                            report_ref="trp_01ARZ3NDEKTSV4RRFFQ69G5FAA",
                            blocking_finding_codes=("Unsupported certification",),
                        ),
                    ),
                    goal_d,
                )
            ]
        ),
        store=store_d,
    )
    run_d = dos_d.start(goal_d, owner_approvals_present=True)
    print(format_orchestration_report(run_d, store_d))
    brief = store_d.load_brief(run_d.last_brief_id) if run_d.last_brief_id else None
    if brief is None or "Unsupported certification" not in brief.truth_blocker_labels:
        failures += 1

    _section("E. interviewing")
    goal_e = goal_from_owner_name("prepare", OPP)
    store_e = InMemoryOrchestrationStore()
    dos_e = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [observation_from_snapshot(_snap(pipeline_status="interviewing"), goal_e)]
        ),
        store=store_e,
    )
    run_e = dos_e.start(goal_e, owner_approvals_present=True)
    print(format_orchestration_report(run_e, store_e))
    if [v.specialist_id for v in run_e.specialist_visits] != ["obs"]:
        failures += 1

    _section("F. illegal delegation")
    decision = evaluate_delegation_policy(
        goal_from_owner_name("brief", OPP),
        observation_from_snapshot(_snap(pipeline_status="interviewing"), goal_d),
        SpecialistDelegationProposal(
            target_specialist="bopa",
            rationale="illegal",
            requested_goal_kind="prepare_for_owner_review",
        ),
        owner_approvals_present=True,
    )
    print(f"decision={decision.decision} reason={decision.deny_reason}")
    if decision.decision != "deny":
        failures += 1

    _section("G. resume (no duplicate)")
    children_before = list(run_c.child_agent_run_ids)
    brief_before = run_c.last_brief_id
    if run_c.status == "awaiting_owner":
        run_g = dos_c.resume(run_c.orchestration_run_id, owner_approvals_present=True)
        print(format_orchestration_report(run_g, store_c))
        if run_g.child_agent_run_ids != tuple(children_before):
            failures += 1
        if run_g.last_brief_id != brief_before:
            failures += 1

    _section("H. audit reconstruction")
    print(format_orchestration_history(run_c, verbose=True))
    print(format_orchestration_report(run_c, store_c, verbose=True))

    _section("CLI approve gate + live interviewing brief")
    tmp = Path(".tmp_fr016_m4_manual")
    orch = tmp / "orch"
    orch.mkdir(parents=True, exist_ok=True)
    refuse = runner.invoke(
        app,
        [
            "agent",
            "orchestrate",
            "run",
            OPP,
            "--goal",
            "brief",
            "--orchestration-runs-dir",
            str(orch),
        ],
    )
    print(refuse.output)
    if refuse.exit_code != 1:
        failures += 1

    live_opp = "opp_01KY8RFAH81M9V30ZVH9TM09T5"
    from career_intelligence.multi_agent.factory import build_orchestration_supervisor

    live_dir = tmp / "live_orch"
    live_dir.mkdir(parents=True, exist_ok=True)
    try:
        dos_live, store_live = build_orchestration_supervisor(
            orchestration_runs_dir=live_dir
        )
        run_live = dos_live.start(
            goal_from_owner_name("brief", live_opp),
            owner_approvals_present=True,
        )
        print(format_orchestration_report(run_live, store_live))
        if (
            run_live.stop_reason != "briefing_complete"
            or [v.specialist_id for v in run_live.specialist_visits] != ["obs"]
        ):
            failures += 1
        print(
            "Live SoT note: brief-only on interviewing opportunity is safe "
            "(OBS read-only). Mutating prepare journeys remain offline fixtures "
            "to avoid package/truth side effects during freeze."
        )
    except Exception as error:  # noqa: BLE001
        print(f"Live brief skipped/failed: {error}")
        failures += 1

    _section("RESULT")
    print(f"failures={failures}")
    return 0 if failures == 0 and report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
