#!/usr/bin/env python3
"""FR-016 M3 manual validation (learning-proof CLI journeys).

Demonstrates A–I journeys via the ``cic agent orchestrate`` surface where
practical, and offline DOS for deterministic fixtures.
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
    format_orchestration_report,
    goal_from_owner_name,
    observation_from_snapshot,
    SpecialistDelegationProposal,
)

OPP = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"
runner = CliRunner()


def _now() -> datetime:
    return datetime(2026, 8, 6, 18, 0, tzinfo=timezone.utc)


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
    tmp = Path(".tmp_fr016_m3_manual")
    orch = tmp / "orch"
    orch.mkdir(parents=True, exist_ok=True)

    _section("A. brief-only (offline DOS presentation)")
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

    _section("B. prepare (DOS -> BOPA)")
    goal_b = goal_from_owner_name("prepare", OPP)
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

    _section("D. truth blocked (OBS)")
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

    _section("E. pipeline advises against preparation")
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

    _section("F. illegal delegation (CLI check-delegation)")
    # Offline policy deny (same rule as CLI).
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
    cli = runner.invoke(
        app,
        ["agent", "orchestrate", "run", OPP, "--goal", "brief"],
    )
    print("CLI without --approve exit=", cli.exit_code, "snippet=", cli.output[:120])

    _section("G. resume (no duplicate)")
    if run_c.status == "awaiting_owner":
        run_g = dos_c.resume(run_c.orchestration_run_id, owner_approvals_present=True)
        print(format_orchestration_report(run_g, store_c))
        print(f"child runs unchanged: {run_g.child_agent_run_ids == run_c.child_agent_run_ids}")

    _section("H. audit reconstruction")
    print(format_orchestration_report(run_c, store_c, verbose=True))

    _section("I. pipeline/submission safety note")
    print("DOS has no advance_pipeline / submit APIs; reports state this explicitly.")

    _section("CLI approve gate")
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
    return 0 if decision.decision == "deny" and refuse.exit_code == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
