#!/usr/bin/env python3
"""FR-016 M2 manual validation runner (not product CLI).

Demonstrates brief-only, prepare+brief, pipeline-advises, truth-blocked,
illegal delegation, resume, and audit reconstruction.
"""

from __future__ import annotations

from datetime import datetime, timezone

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
from career_intelligence.multi_agent import (
    BopaSpecialistAdapter,
    DeterministicOrchestrationSupervisor,
    InMemoryOrchestrationStore,
    OrchestrationGoal,
    SpecialistDelegationProposal,
    StaticObservationBuilder,
    evaluate_delegation_policy,
    format_orchestration_report,
    observation_from_snapshot,
    run_corpus,
)

OPP = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"


def _now() -> datetime:
    return datetime(2026, 8, 6, 16, 0, tzinfo=timezone.utc)


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
    _section("1. Brief-only owner goal")
    goal = OrchestrationGoal(goal_kind="brief_opportunity_readiness", opportunity_id=OPP)
    store = InMemoryOrchestrationStore()
    dos = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [observation_from_snapshot(_snap(pipeline_status="assessed"), goal)]
        ),
        store=store,
    )
    run = dos.start(goal, owner_approvals_present=True)
    print(format_orchestration_report(run, store))

    _section("2. Prepare-and-brief goal")
    goal2 = OrchestrationGoal(
        goal_kind="coordinate_opportunity_readiness",
        opportunity_id=OPP,
        synthesize_after_prepare=True,
    )
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
    store2 = InMemoryOrchestrationStore()
    dos2 = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [
                observation_from_snapshot(miss, goal2),
                observation_from_snapshot(ready, goal2),
                observation_from_snapshot(ready, goal2),
            ]
        ),
        bopa_adapter=BopaSpecialistAdapter(agent),
        store=store2,
    )
    run2 = dos2.start(goal2, owner_approvals_present=True)
    print(format_orchestration_report(run2, store2))

    _section("3. Pipeline advises against preparation")
    goal3 = OrchestrationGoal(goal_kind="coordinate_opportunity_readiness", opportunity_id=OPP)
    store3 = InMemoryOrchestrationStore()
    dos3 = DeterministicOrchestrationSupervisor(
        observation_builder=StaticObservationBuilder(
            [
                observation_from_snapshot(
                    _snap(pipeline_status="interviewing"),
                    goal3,
                )
            ]
        ),
        store=store3,
    )
    run3 = dos3.start(goal3, owner_approvals_present=True)
    print(format_orchestration_report(run3, store3))

    _section("4. Truth-blocked case")
    goal4 = OrchestrationGoal(goal_kind="brief_opportunity_readiness", opportunity_id=OPP)
    store4 = InMemoryOrchestrationStore()
    dos4 = DeterministicOrchestrationSupervisor(
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
                    goal4,
                )
            ]
        ),
        store=store4,
    )
    run4 = dos4.start(goal4, owner_approvals_present=True)
    print(format_orchestration_report(run4, store4))

    _section("5. Illegal delegation")
    decision = evaluate_delegation_policy(
        goal4,
        observation_from_snapshot(_snap(pipeline_status="interviewing"), goal4),
        SpecialistDelegationProposal(
            target_specialist="bopa",
            rationale="illegal",
            requested_goal_kind="prepare_for_owner_review",
        ),
        owner_approvals_present=True,
    )
    print(f"decision={decision.decision} reason={decision.deny_reason}")

    _section("6. Resume without duplicate work")
    print(
        f"prepare-and-brief child runs: {run2.child_agent_run_ids}; "
        f"resume status would require awaiting_owner (status={run2.status})"
    )
    if run2.status == "awaiting_owner":
        run2b = dos2.resume(run2.orchestration_run_id, owner_approvals_present=True)
        print(format_orchestration_report(run2b, store2))

    _section("7. Full audit reconstruction (case 1)")
    print(format_orchestration_report(run, store))

    _section("Corpus A–O")
    report = run_corpus()
    print(f"corpus {report.passed}/{report.total} all_passed={report.all_passed}")
    for row in report.results:
        mark = "PASS" if row.passed else "FAIL"
        print(f"  [{mark}] {row.case_id}: {row.detail}")

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
