"""FR-017 M2 — deterministic observability corpus (derive-only).

Builds static OrchestrationRun / Handoff / AgentRunMetrics fixtures and evaluates
them with M1 helpers. Does not invoke DOS, BOPA, OBS, or change runtime behaviour.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from career_intelligence.agent.observability import AgentRunMetrics

from .models import (
    Handoff,
    OrchestrationAuditEvent,
    OrchestrationGoal,
    OrchestrationObservation,
    OrchestrationRun,
    SpecialistVisitRecord,
)
from .observability import (
    OrchestrationCorpusMetrics,
    OrchestrationRunMetrics,
    ParentChildCorrelation,
    ReconstructabilityReport,
    aggregate_orchestration_metrics,
    evaluate_reconstructability,
    extract_orchestration_run_metrics,
)

OPP = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"

# Fixed ids for deterministic repeatability (ULID alphabet-safe).
ORR_1 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
ORR_2 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAB"
ORR_3 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAC"
ORR_4 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAD"
ORR_5 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAE"
ORR_6 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAF"
ORR_7 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAG"
ORR_8 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAH"
ORR_9 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAJ"
ORR_10 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAK"
ORR_11 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAM"
ORR_12A = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAN"
ORR_12B = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAP"
ORR_12C = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAQ"
ORR_13 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAR"
ORR_14 = "orr_01ARZ3NDEKTSV4RRFFQ69G5FAS"

HOF_1 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAA"
HOF_2 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAB"
HOF_3 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAC"
HOF_4 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAD"
HOF_5 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAE"
HOF_6 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAF"
HOF_7 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAG"
HOF_8 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAH"
HOF_9 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAJ"
HOF_10 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAK"
HOF_11 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAM"
HOF_12 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAN"
HOF_13 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAP"
HOF_14 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAQ"
HOF_15 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAR"
HOF_16 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAT"
HOF_17 = "hof_01ARZ3NDEKTSV4RRFFQ69G5FAV"

AGR_1 = "agr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
AGR_2 = "agr_01ARZ3NDEKTSV4RRFFQ69G5FAB"
AGR_3 = "agr_01ARZ3NDEKTSV4RRFFQ69G5FAC"
AGR_ORPHAN = "agr_01ARZ3NDEKTSV4RRFFQ69G5FAD"
AGR_MISSING = "agr_01ARZ3NDEKTSV4RRFFQ69G5FAE"

OBR_1 = "obr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
OBR_2 = "obr_01ARZ3NDEKTSV4RRFFQ69G5FAB"

OAE_1 = "oae_01ARZ3NDEKTSV4RRFFQ69G5FAA"
OAE_2 = "oae_01ARZ3NDEKTSV4RRFFQ69G5FAB"
OAE_3 = "oae_01ARZ3NDEKTSV4RRFFQ69G5FAC"
OAE_4 = "oae_01ARZ3NDEKTSV4RRFFQ69G5FAD"
OAE_5 = "oae_01ARZ3NDEKTSV4RRFFQ69G5FAE"

T0 = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)

CorpusCaseId = Literal[
    "C01_complete_successful",
    "C02_delegation_blocked",
    "C03_bopa_child",
    "C04_obs_brief",
    "C05_prepare_then_brief",
    "C06_missing_optional_metadata",
    "C07_measured_zero",
    "C08_orphaned_child_ref",
    "C09_missing_child_record",
    "C10_stale_incomplete_handoff",
    "C11_safe_resume",
    "C12_loop_stops",
    "C13_provider_unavailable",
    "C14_malformed_contradictory",
    "C15_mixed_corpus_aggregation",
]

CORPUS_CASE_IDS: tuple[CorpusCaseId, ...] = (
    "C01_complete_successful",
    "C02_delegation_blocked",
    "C03_bopa_child",
    "C04_obs_brief",
    "C05_prepare_then_brief",
    "C06_missing_optional_metadata",
    "C07_measured_zero",
    "C08_orphaned_child_ref",
    "C09_missing_child_record",
    "C10_stale_incomplete_handoff",
    "C11_safe_resume",
    "C12_loop_stops",
    "C13_provider_unavailable",
    "C14_malformed_contradictory",
    "C15_mixed_corpus_aggregation",
)


class ObservabilityFixture(BaseModel):
    """One static audit bundle for derive-only evaluation."""

    model_config = ConfigDict(extra="forbid")

    label: str
    run: OrchestrationRun
    handoffs: tuple[Handoff, ...] = ()
    child_metrics: tuple[AgentRunMetrics, ...] = ()
    prior_observation_hash: str | None = None


class ObservabilityCaseResult(BaseModel):
    """Per-case evaluation outcome."""

    model_config = ConfigDict(extra="forbid")

    case_id: CorpusCaseId
    passed: bool
    detail: str = ""
    fixture_labels: tuple[str, ...] = ()
    metrics: tuple[OrchestrationRunMetrics, ...] = ()
    reconstructability: tuple[ReconstructabilityReport, ...] = ()
    correlations: tuple[ParentChildCorrelation, ...] = ()
    expected_r_failures: tuple[str, ...] = ()
    actual_r_failures: tuple[str, ...] = ()
    missing_vs_zero_ok: bool | None = None
    corpus_aggregate: OrchestrationCorpusMetrics | None = None


class ObservabilityCorpusReport(BaseModel):
    """Full M2 corpus report."""

    model_config = ConfigDict(extra="forbid")

    results: tuple[ObservabilityCaseResult, ...] = ()
    passed: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    all_passed: bool = False
    derive_only: bool = True
    runtime_instrumentation_required: bool = False
    deterministic_repeat_ok: bool = False
    go_no_go: Literal["GO", "DEFER"] = "DEFER"
    go_no_go_rationale: str = ""


def _goal(**overrides: object) -> OrchestrationGoal:
    base: dict[str, object] = {
        "goal_kind": "coordinate_opportunity_readiness",
        "opportunity_id": OPP,
        "brief_only": False,
        "synthesize_after_prepare": False,
    }
    base.update(overrides)
    return OrchestrationGoal.model_validate(base)


def _obs(**overrides: object) -> OrchestrationObservation:
    base: dict[str, object] = {
        "opportunity_id": OPP,
        "decision": "apply",
        "readiness_primary_state_class": "missing_package",
        "package_status": "absent",
        "truth_status": "absent",
        "pipeline_status": "assessed",
        "owner_approvals_present": True,
        "observation_hash": "hash_a",
        "observed_at": T0,
    }
    base.update(overrides)
    return OrchestrationObservation.model_validate(base)


def _event(
    *,
    event_id: str,
    kind: str,
    specialist_id: str | None = None,
    handoff_id: str | None = None,
    message: str | None = None,
    at: datetime | None = None,
) -> OrchestrationAuditEvent:
    return OrchestrationAuditEvent.model_validate(
        {
            "event_id": event_id,
            "kind": kind,
            "at": at or T0,
            "specialist_id": specialist_id,
            "handoff_id": handoff_id,
            "message": message,
        }
    )


def _child(
    agent_run_id: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
    elapsed_ms: int | None = 100,
) -> AgentRunMetrics:
    return AgentRunMetrics.model_validate(
        {
            "agent_run_id": agent_run_id,
            "opportunity_id": OPP,
            "status": "completed",
            "stop_reason": "completed_for_owner_review",
            "step_count": 2,
            "max_steps": 8,
            "events_count": 4,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "elapsed_ms": elapsed_ms,
            "created_at": T0,
            "updated_at": T0 + timedelta(milliseconds=elapsed_ms or 0),
        }
    )


def _run(**overrides: object) -> OrchestrationRun:
    base: dict[str, object] = {
        "orchestration_run_id": ORR_1,
        "goal": _goal(),
        "status": "completed",
        "step_count": 1,
        "max_steps": 8,
        "max_visits_per_specialist": 2,
        "stop_reason": "briefing_complete",
        "owner_approvals_present": True,
        "provider_available": True,
        "created_at": T0,
        "updated_at": T0 + timedelta(seconds=2),
        "events": (),
        "specialist_visits": (),
        "child_agent_run_ids": (),
        "handoff_ids": (),
    }
    base.update(overrides)
    return OrchestrationRun.model_validate(base)


def _handoff(**overrides: object) -> Handoff:
    base: dict[str, object] = {
        "handoff_id": HOF_1,
        "orchestration_run_id": ORR_1,
        "source": "supervisor",
        "target_specialist": "obs",
        "opportunity_id": OPP,
        "requested_goal_kind": "brief_opportunity_readiness",
        "observed_state_hash": "hash_a",
        "expected_output_kind": "operational_brief",
        "owner_approval_status": "present",
        "policy_decision": "allow",
        "reason": "briefing delta present",
        "acceptance": "pending",
        "created_at": T0,
    }
    base.update(overrides)
    return Handoff.model_validate(base)


def _fixture_complete_successful() -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_1,
        last_observation=_obs(),
        last_brief_id=OBR_1,
        handoff_ids=(HOF_1,),
        events=(
            _event(
                event_id=OAE_1,
                kind="specialist_selected",
                specialist_id="obs",
                handoff_id=HOF_1,
                message="selected obs",
            ),
        ),
        specialist_visits=(
            SpecialistVisitRecord(
                specialist_id="obs",
                visit_count=1,
                last_handoff_id=HOF_1,
                last_observation_hash="hash_a",
            ),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_1,
        orchestration_run_id=ORR_1,
        acceptance="completed",
        child_brief_id=OBR_1,
        idempotency_key=f"{ORR_1}|obs|brief|hash_a",
        resolved_at=T0 + timedelta(milliseconds=400),
    )
    return ObservabilityFixture(label="complete_successful", run=run, handoffs=(handoff,))


def _fixture_delegation_blocked() -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_2,
        status="failed",
        stop_reason="delegation_blocked",
        step_count=1,
        last_observation=_obs(),
        handoff_ids=(HOF_2,),
        events=(
            _event(
                event_id=OAE_2,
                kind="specialist_considered",
                specialist_id="bopa",
                message="considered bopa",
            ),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_2,
        orchestration_run_id=ORR_2,
        target_specialist="bopa",
        requested_goal_kind="prepare_for_owner_review",
        expected_output_kind="agent_run",
        policy_decision="deny",
        policy_deny_reason="owner approvals absent for mutate path",
        acceptance="policy_blocked",
        acceptance_reason="delegation denied",
        reason="prepare attempted without approvals",
        resolved_at=T0 + timedelta(milliseconds=50),
    )
    return ObservabilityFixture(label="delegation_blocked", run=run, handoffs=(handoff,))


def _fixture_bopa_child(*, with_provider: bool) -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_3 if with_provider else ORR_6,
        stop_reason="completed_for_owner_review",
        last_observation=_obs(readiness_primary_state_class="ready_for_owner_review"),
        child_agent_run_ids=(AGR_1 if with_provider else AGR_2,),
        handoff_ids=(HOF_3 if with_provider else HOF_6,),
        events=(
            _event(
                event_id=OAE_1 if with_provider else OAE_3,
                kind="specialist_selected",
                specialist_id="bopa",
            ),
        ),
        specialist_visits=(
            SpecialistVisitRecord(
                specialist_id="bopa",
                visit_count=1,
                last_handoff_id=HOF_3 if with_provider else HOF_6,
                last_observation_hash="hash_a",
            ),
        ),
        goal=_goal(),
    )
    hid = HOF_3 if with_provider else HOF_6
    aid = AGR_1 if with_provider else AGR_2
    orr = ORR_3 if with_provider else ORR_6
    handoff = _handoff(
        handoff_id=hid,
        orchestration_run_id=orr,
        target_specialist="bopa",
        requested_goal_kind="prepare_for_owner_review",
        expected_output_kind="agent_run",
        acceptance="completed",
        child_agent_run_id=aid,
        idempotency_key=f"{orr}|bopa|prepare|hash_a",
        reason="package absent; prepare approved",
        resolved_at=T0 + timedelta(seconds=1),
    )
    if with_provider:
        child = _child(
            aid,
            provider="openai",
            model="gpt-test",
            input_tokens=12,
            output_tokens=4,
            estimated_cost_usd=0.02,
            elapsed_ms=250,
        )
    else:
        child = _child(aid)  # all optional metadata None
    return ObservabilityFixture(
        label="bopa_with_provider" if with_provider else "missing_optional_metadata",
        run=run,
        handoffs=(handoff,),
        child_metrics=(child,),
    )


def _fixture_obs_brief() -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_4,
        goal=_goal(goal_kind="brief_opportunity_readiness", brief_only=True),
        stop_reason="briefing_complete",
        last_observation=_obs(
            briefing_need_classes=("pipeline_advises_against_preparation",),
            pipeline_status="interviewing",
        ),
        last_brief_id=OBR_2,
        handoff_ids=(HOF_4,),
        events=(
            _event(
                event_id=OAE_2,
                kind="specialist_selected",
                specialist_id="obs",
            ),
        ),
        specialist_visits=(
            SpecialistVisitRecord(
                specialist_id="obs",
                visit_count=1,
                last_handoff_id=HOF_4,
                last_observation_hash="hash_a",
            ),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_4,
        orchestration_run_id=ORR_4,
        acceptance="completed",
        child_brief_id=OBR_2,
        idempotency_key=f"{ORR_4}|obs|brief|hash_a",
        reason="pipeline advises against preparation",
        resolved_at=T0 + timedelta(milliseconds=300),
    )
    return ObservabilityFixture(label="obs_brief", run=run, handoffs=(handoff,))


def _fixture_prepare_then_brief() -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_5,
        goal=_goal(synthesize_after_prepare=True),
        stop_reason="briefing_complete",
        step_count=2,
        last_observation=_obs(observation_hash="hash_b", package_status="complete"),
        last_brief_id=OBR_1,
        child_agent_run_ids=(AGR_1,),
        handoff_ids=(HOF_5, HOF_7),
        events=(
            _event(
                event_id=OAE_1,
                kind="specialist_selected",
                specialist_id="bopa",
                handoff_id=HOF_5,
            ),
            _event(
                event_id=OAE_2,
                kind="specialist_selected",
                specialist_id="obs",
                handoff_id=HOF_7,
                at=T0 + timedelta(seconds=1),
            ),
        ),
        specialist_visits=(
            SpecialistVisitRecord(
                specialist_id="bopa",
                visit_count=1,
                last_handoff_id=HOF_5,
                last_observation_hash="hash_a",
            ),
            SpecialistVisitRecord(
                specialist_id="obs",
                visit_count=1,
                last_handoff_id=HOF_7,
                last_observation_hash="hash_b",
            ),
        ),
        updated_at=T0 + timedelta(seconds=5),
    )
    bopa = _handoff(
        handoff_id=HOF_5,
        orchestration_run_id=ORR_5,
        target_specialist="bopa",
        requested_goal_kind="prepare_for_owner_review",
        expected_output_kind="agent_run",
        observed_state_hash="hash_a",
        acceptance="completed",
        child_agent_run_id=AGR_1,
        idempotency_key=f"{ORR_5}|bopa|prepare|hash_a",
        reason="prepare then brief",
        resolved_at=T0 + timedelta(seconds=2),
    )
    obs = _handoff(
        handoff_id=HOF_7,
        orchestration_run_id=ORR_5,
        target_specialist="obs",
        observed_state_hash="hash_b",
        acceptance="completed",
        child_brief_id=OBR_1,
        idempotency_key=f"{ORR_5}|obs|brief|hash_b",
        reason="synthesize after prepare",
        created_at=T0 + timedelta(seconds=2),
        resolved_at=T0 + timedelta(seconds=4),
    )
    return ObservabilityFixture(
        label="prepare_then_brief",
        run=run,
        handoffs=(bopa, obs),
        child_metrics=(
            _child(
                AGR_1,
                provider="openai",
                model="gpt-test",
                input_tokens=8,
                output_tokens=2,
                estimated_cost_usd=0.01,
            ),
        ),
    )


def _fixture_measured_zero() -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_7,
        stop_reason="completed_for_owner_review",
        last_observation=_obs(),
        child_agent_run_ids=(AGR_3,),
        handoff_ids=(HOF_8,),
        events=(
            _event(event_id=OAE_3, kind="specialist_selected", specialist_id="bopa"),
        ),
        specialist_visits=(
            SpecialistVisitRecord(
                specialist_id="bopa",
                visit_count=1,
                last_handoff_id=HOF_8,
                last_observation_hash="hash_a",
            ),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_8,
        orchestration_run_id=ORR_7,
        target_specialist="bopa",
        requested_goal_kind="prepare_for_owner_review",
        expected_output_kind="agent_run",
        acceptance="completed",
        child_agent_run_id=AGR_3,
        idempotency_key=f"{ORR_7}|bopa|prepare|hash_a",
        reason="measured zero tokens",
        resolved_at=T0 + timedelta(milliseconds=10),
    )
    child = _child(
        AGR_3,
        provider="openai",
        model="gpt-test",
        input_tokens=0,
        output_tokens=0,
        estimated_cost_usd=0.0,
        elapsed_ms=0,
    )
    return ObservabilityFixture(
        label="measured_zero",
        run=run,
        handoffs=(handoff,),
        child_metrics=(child,),
    )


def _fixture_orphaned_child() -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_8,
        stop_reason="completed_for_owner_review",
        last_observation=_obs(),
        child_agent_run_ids=(AGR_ORPHAN,),
        handoff_ids=(HOF_9,),
        events=(
            _event(event_id=OAE_1, kind="specialist_selected", specialist_id="bopa"),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_9,
        orchestration_run_id=ORR_8,
        target_specialist="bopa",
        requested_goal_kind="prepare_for_owner_review",
        expected_output_kind="agent_run",
        acceptance="completed",
        child_agent_run_id=AGR_1,  # disagrees with parent orphan
        idempotency_key=f"{ORR_8}|bopa|prepare|hash_a",
        reason="orphan parent child ref",
        resolved_at=T0 + timedelta(milliseconds=20),
    )
    return ObservabilityFixture(label="orphaned_child_ref", run=run, handoffs=(handoff,))


def _fixture_missing_child_record() -> ObservabilityFixture:
    """Handoff and parent cite child id, but AgentRunMetrics join is absent."""
    run = _run(
        orchestration_run_id=ORR_9,
        stop_reason="completed_for_owner_review",
        last_observation=_obs(),
        child_agent_run_ids=(AGR_MISSING,),
        handoff_ids=(HOF_10,),
        events=(
            _event(event_id=OAE_2, kind="specialist_selected", specialist_id="bopa"),
        ),
        specialist_visits=(
            SpecialistVisitRecord(
                specialist_id="bopa",
                visit_count=1,
                last_handoff_id=HOF_10,
                last_observation_hash="hash_a",
            ),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_10,
        orchestration_run_id=ORR_9,
        target_specialist="bopa",
        requested_goal_kind="prepare_for_owner_review",
        expected_output_kind="agent_run",
        acceptance="completed",
        child_agent_run_id=AGR_MISSING,
        idempotency_key=f"{ORR_9}|bopa|prepare|hash_a",
        reason="child id present; metrics record absent",
        resolved_at=T0 + timedelta(milliseconds=30),
    )
    return ObservabilityFixture(
        label="missing_child_record",
        run=run,
        handoffs=(handoff,),
        child_metrics=(),
    )


def _fixture_stale_incomplete() -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_10,
        status="failed",
        stop_reason="handoff_stale",
        last_observation=_obs(observation_hash="hash_new"),
        handoff_ids=(HOF_11,),
        events=(
            _event(event_id=OAE_3, kind="specialist_selected", specialist_id="obs"),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_11,
        orchestration_run_id=ORR_10,
        observed_state_hash="hash_a",
        acceptance="stale",
        acceptance_reason="observation hash changed before acceptance",
        reason="brief selected then state moved",
        resolved_at=T0 + timedelta(milliseconds=5),
    )
    return ObservabilityFixture(label="stale_incomplete_handoff", run=run, handoffs=(handoff,))


def _fixture_safe_resume() -> ObservabilityFixture:
    run = _run(
        orchestration_run_id=ORR_11,
        stop_reason="briefing_complete",
        last_observation=_obs(observation_hash="hash_resume"),
        last_brief_id=OBR_1,
        handoff_ids=(HOF_12,),
        events=(
            _event(event_id=OAE_4, kind="specialist_selected", specialist_id="obs"),
        ),
        specialist_visits=(
            SpecialistVisitRecord(
                specialist_id="obs",
                visit_count=1,
                last_handoff_id=HOF_12,
                last_observation_hash="hash_resume",
            ),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_12,
        orchestration_run_id=ORR_11,
        observed_state_hash="hash_resume",
        acceptance="completed",
        child_brief_id=OBR_1,
        idempotency_key=f"{ORR_11}|obs|brief|hash_resume",
        reason="resume after SoT re-inspect; single completion",
        resolved_at=T0 + timedelta(milliseconds=100),
    )
    return ObservabilityFixture(
        label="safe_resume",
        run=run,
        handoffs=(handoff,),
        prior_observation_hash="hash_prior",
    )


def _fixtures_loop_stops() -> tuple[ObservabilityFixture, ...]:
    repeated = ObservabilityFixture(
        label="repeated_delegation",
        run=_run(
            orchestration_run_id=ORR_12A,
            status="failed",
            stop_reason="repeated_delegation",
            step_count=3,
            last_observation=_obs(),
            events=(
                _event(event_id=OAE_1, kind="specialist_selected", specialist_id="obs"),
            ),
            specialist_visits=(
                SpecialistVisitRecord(specialist_id="obs", visit_count=2),
            ),
            handoff_ids=(HOF_13,),
        ),
        handoffs=(
            _handoff(
                handoff_id=HOF_13,
                orchestration_run_id=ORR_12A,
                policy_decision="deny",
                policy_deny_reason="repeated delegation without progress",
                acceptance="policy_blocked",
                acceptance_reason="repeated_delegation",
                reason="repeat obs without delta",
                resolved_at=T0 + timedelta(milliseconds=1),
            ),
        ),
    )
    circular = ObservabilityFixture(
        label="circular_delegation",
        run=_run(
            orchestration_run_id=ORR_12B,
            status="failed",
            stop_reason="circular_delegation",
            step_count=2,
            last_observation=_obs(),
            events=(
                _event(event_id=OAE_2, kind="specialist_considered", specialist_id="bopa"),
            ),
            handoff_ids=(HOF_14,),
        ),
        handoffs=(
            _handoff(
                handoff_id=HOF_14,
                orchestration_run_id=ORR_12B,
                target_specialist="bopa",
                requested_goal_kind="prepare_for_owner_review",
                expected_output_kind="agent_run",
                policy_decision="deny",
                policy_deny_reason="circular specialist cycle detected",
                acceptance="policy_blocked",
                acceptance_reason="circular_delegation",
                reason="cycle obs->bopa->obs",
                resolved_at=T0 + timedelta(milliseconds=1),
            ),
        ),
    )
    no_progress = ObservabilityFixture(
        label="no_progress",
        run=_run(
            orchestration_run_id=ORR_12C,
            status="failed",
            stop_reason="no_progress",
            step_count=4,
            last_observation=_obs(),
            events=(
                _event(event_id=OAE_3, kind="specialist_selected", specialist_id="obs"),
            ),
            specialist_visits=(
                SpecialistVisitRecord(specialist_id="obs", visit_count=2),
            ),
            handoff_ids=(HOF_15,),
        ),
        handoffs=(
            _handoff(
                handoff_id=HOF_15,
                orchestration_run_id=ORR_12C,
                policy_decision="deny",
                policy_deny_reason="no observation hash progress",
                acceptance="policy_blocked",
                acceptance_reason="no_progress",
                reason="identical observation after visit",
                resolved_at=T0 + timedelta(milliseconds=1),
            ),
        ),
    )
    return (repeated, circular, no_progress)


def _fixture_provider_unavailable() -> ObservabilityFixture:
    handoff = _handoff(
        handoff_id=HOF_16,
        orchestration_run_id=ORR_13,
        target_specialist="bopa",
        requested_goal_kind="prepare_for_owner_review",
        expected_output_kind="agent_run",
        acceptance="stopped",
        acceptance_reason="provider unavailable during specialist execution",
        reason="prepare selected then provider outage",
        child_agent_run_id=None,
        resolved_at=T0 + timedelta(milliseconds=15),
        idempotency_key=f"{ORR_13}|bopa|prepare|hash_a",
    )
    run = _run(
        orchestration_run_id=ORR_13,
        status="failed",
        stop_reason="provider_unavailable",
        provider_available=False,
        last_observation=_obs(),
        events=(
            _event(event_id=OAE_4, kind="specialist_selected", specialist_id="bopa"),
        ),
        handoff_ids=(HOF_16,),
    )
    return ObservabilityFixture(label="provider_unavailable", run=run, handoffs=(handoff,))


def _fixture_malformed_contradictory() -> ObservabilityFixture:
    """Valid models with contradictory child linkage (R11 must fail)."""
    run = _run(
        orchestration_run_id=ORR_14,
        stop_reason="completed_for_owner_review",
        last_observation=_obs(),
        last_brief_id=OBR_1,
        child_agent_run_ids=(AGR_1,),
        handoff_ids=(HOF_17,),
        events=(
            _event(
                event_id=OAE_5,
                kind="specialist_selected",
                specialist_id="obs",
            ),
        ),
    )
    handoff = _handoff(
        handoff_id=HOF_17,
        orchestration_run_id=ORR_14,
        acceptance="completed",
        child_brief_id=None,
        reason="contradictory completed handoff without child refs",
        idempotency_key=f"{ORR_14}|obs|brief|hash_a",
        resolved_at=T0 + timedelta(milliseconds=2),
    )
    return ObservabilityFixture(
        label="malformed_contradictory",
        run=run,
        handoffs=(handoff,),
    )


def _evaluate_fixture(fx: ObservabilityFixture) -> tuple[
    OrchestrationRunMetrics,
    ReconstructabilityReport,
    ParentChildCorrelation,
]:
    metrics = extract_orchestration_run_metrics(
        fx.run,
        fx.handoffs,
        child_agent_metrics=fx.child_metrics,
    )
    report = evaluate_reconstructability(
        fx.run,
        fx.handoffs,
        child_agent_metrics=fx.child_metrics,
        prior_observation_hash=fx.prior_observation_hash,
    )
    return metrics, report, metrics.parent_child


def _r_failures(report: ReconstructabilityReport) -> tuple[str, ...]:
    return tuple(c.criterion_id for c in report.checks if not c.satisfied)


def _assert_true(cond: bool, msg: str) -> str | None:
    return None if cond else msg


def _check_happy_path(fx: ObservabilityFixture) -> str:
    _metrics, report, corr = _evaluate_fixture(fx)
    failures = _r_failures(report)
    return (
        _assert_true(report.all_satisfied, f"expected all R ok; failed={failures}")
        or _assert_true(corr.correlation_complete, f"expected correlation; orphans={corr}")
        or ""
    )


CaseRunner = Callable[[], ObservabilityCaseResult]


def _result(
    case_id: CorpusCaseId,
    *,
    passed: bool,
    detail: str,
    fixtures: tuple[ObservabilityFixture, ...] = (),
    expected_r_failures: tuple[str, ...] = (),
    missing_vs_zero_ok: bool | None = None,
    corpus_aggregate: OrchestrationCorpusMetrics | None = None,
) -> ObservabilityCaseResult:
    metrics_list: list[OrchestrationRunMetrics] = []
    reports: list[ReconstructabilityReport] = []
    corrs: list[ParentChildCorrelation] = []
    actual_fail: list[str] = []
    for fx in fixtures:
        m, r, c = _evaluate_fixture(fx)
        metrics_list.append(m)
        reports.append(r)
        corrs.append(c)
        actual_fail.extend(_r_failures(r))
    return ObservabilityCaseResult(
        case_id=case_id,
        passed=passed,
        detail=detail,
        fixture_labels=tuple(fx.label for fx in fixtures),
        metrics=tuple(metrics_list),
        reconstructability=tuple(reports),
        correlations=tuple(corrs),
        expected_r_failures=expected_r_failures,
        actual_r_failures=tuple(dict.fromkeys(actual_fail)),
        missing_vs_zero_ok=missing_vs_zero_ok,
        corpus_aggregate=corpus_aggregate,
    )


def run_case_c01() -> ObservabilityCaseResult:
    fx = _fixture_complete_successful()
    err = _check_happy_path(fx)
    m, _, _ = _evaluate_fixture(fx)
    ok = not err
    detail = err or (
        f"status={m.status} stop={m.stop_reason} handoffs={m.handoff_count} "
        f"brief={m.last_brief_id}"
    )
    return _result("C01_complete_successful", passed=ok, detail=detail, fixtures=(fx,))


def run_case_c02() -> ObservabilityCaseResult:
    fx = _fixture_delegation_blocked()
    m, report, corr = _evaluate_fixture(fx)
    ok = (
        m.handoffs_denied == 1
        and m.handoffs_allowed == 0
        and m.stop_reason == "delegation_blocked"
        and report.all_satisfied
        and corr.correlation_complete
    )
    return _result(
        "C02_delegation_blocked",
        passed=ok,
        detail=f"denied={m.handoffs_denied} stop={m.stop_reason} r_ok={report.all_satisfied}",
        fixtures=(fx,),
    )


def run_case_c03() -> ObservabilityCaseResult:
    fx = _fixture_bopa_child(with_provider=True)
    m, report, corr = _evaluate_fixture(fx)
    ok = (
        report.all_satisfied
        and corr.correlation_complete
        and m.provider == "openai"
        and m.input_tokens == 12
        and AGR_1 in m.child_agent_run_ids
    )
    return _result(
        "C03_bopa_child",
        passed=ok,
        detail=f"provider={m.provider} tokens={m.input_tokens} r_ok={report.all_satisfied}",
        fixtures=(fx,),
    )


def run_case_c04() -> ObservabilityCaseResult:
    fx = _fixture_obs_brief()
    err = _check_happy_path(fx)
    m, _, _ = _evaluate_fixture(fx)
    ok = not err and m.owner_goal_label == "brief" and m.last_brief_id == OBR_2
    return _result(
        "C04_obs_brief",
        passed=ok,
        detail=err or f"goal={m.owner_goal_label} brief={m.last_brief_id}",
        fixtures=(fx,),
    )


def run_case_c05() -> ObservabilityCaseResult:
    fx = _fixture_prepare_then_brief()
    m, report, corr = _evaluate_fixture(fx)
    ok = (
        report.all_satisfied
        and corr.correlation_complete
        and set(m.specialists_selected) == {"bopa", "obs"}
        and m.handoff_count == 2
        and m.last_brief_id == OBR_1
        and AGR_1 in m.child_agent_run_ids
        and m.owner_goal_label == "prepare_then_brief"
    )
    return _result(
        "C05_prepare_then_brief",
        passed=ok,
        detail=(
            f"specialists={m.specialists_selected} handoffs={m.handoff_count} "
            f"r_ok={report.all_satisfied}"
        ),
        fixtures=(fx,),
    )


def run_case_c06() -> ObservabilityCaseResult:
    fx = _fixture_bopa_child(with_provider=False)
    m, report, corr = _evaluate_fixture(fx)
    missing_ok = (
        m.provider is None
        and m.model is None
        and m.input_tokens is None
        and m.output_tokens is None
        and m.estimated_cost_usd is None
    )
    ok = missing_ok and report.all_satisfied and corr.correlation_complete
    return _result(
        "C06_missing_optional_metadata",
        passed=ok,
        detail=f"missing_ok={missing_ok} r_ok={report.all_satisfied}",
        fixtures=(fx,),
        missing_vs_zero_ok=missing_ok,
    )


def run_case_c07() -> ObservabilityCaseResult:
    fx = _fixture_measured_zero()
    m, report, corr = _evaluate_fixture(fx)
    zero_ok = (
        m.input_tokens == 0
        and m.output_tokens == 0
        and m.estimated_cost_usd == 0.0
        and m.provider == "openai"
    )
    missing = _fixture_bopa_child(with_provider=False)
    m_miss, _, _ = _evaluate_fixture(missing)
    distinct = m_miss.input_tokens is None and m.input_tokens == 0
    ok = zero_ok and distinct and report.all_satisfied and corr.correlation_complete
    return _result(
        "C07_measured_zero",
        passed=ok,
        detail=f"zero_ok={zero_ok} distinct_from_missing={distinct}",
        fixtures=(fx,),
        missing_vs_zero_ok=ok,
    )


def run_case_c08() -> ObservabilityCaseResult:
    fx = _fixture_orphaned_child()
    _m, report, corr = _evaluate_fixture(fx)
    expected = ("R11",)
    actual = _r_failures(report)
    ok = (
        not corr.correlation_complete
        and bool(corr.orphan_parent_child_agent_run_ids)
        and bool(corr.orphan_handoff_child_agent_run_ids)
        and "R11" in actual
    )
    return _result(
        "C08_orphaned_child_ref",
        passed=ok,
        detail=f"orphans_parent={corr.orphan_parent_child_agent_run_ids} r={actual}",
        fixtures=(fx,),
        expected_r_failures=expected,
    )


def run_case_c09() -> ObservabilityCaseResult:
    fx = _fixture_missing_child_record()
    m, report, corr = _evaluate_fixture(fx)
    ok = (
        corr.correlation_complete
        and report.all_satisfied
        and m.input_tokens is None
        and m.child_agent_metrics == ()
        and AGR_MISSING in m.child_agent_run_ids
    )
    return _result(
        "C09_missing_child_record",
        passed=ok,
        detail=(
            f"correlation={corr.correlation_complete} tokens={m.input_tokens} "
            f"child_metrics={len(m.child_agent_metrics)}"
        ),
        fixtures=(fx,),
        missing_vs_zero_ok=m.input_tokens is None,
    )


def run_case_c10() -> ObservabilityCaseResult:
    fx = _fixture_stale_incomplete()
    m, report, corr = _evaluate_fixture(fx)
    hm = m.handoffs[0]
    ok = (
        m.stop_reason == "handoff_stale"
        and hm.acceptance == "stale"
        and hm.child_brief_id is None
        and hm.child_agent_run_id is None
        and report.all_satisfied
        and corr.correlation_complete
    )
    return _result(
        "C10_stale_incomplete_handoff",
        passed=ok,
        detail=f"acceptance={hm.acceptance} stop={m.stop_reason} r_ok={report.all_satisfied}",
        fixtures=(fx,),
    )


def run_case_c11() -> ObservabilityCaseResult:
    fx = _fixture_safe_resume()
    m, report, corr = _evaluate_fixture(fx)
    r12 = next(c for c in report.checks if c.criterion_id == "R12")
    ok = (
        report.all_satisfied
        and r12.satisfied
        and corr.correlation_complete
        and m.handoff_count == 1
        and m.specialist_visits[0].visit_count == 1
    )
    return _result(
        "C11_safe_resume",
        passed=ok,
        detail=f"r12={r12.satisfied} visits={m.specialist_visits[0].visit_count}",
        fixtures=(fx,),
    )


def run_case_c12() -> ObservabilityCaseResult:
    fixtures = _fixtures_loop_stops()
    details: list[str] = []
    all_ok = True
    for fx in fixtures:
        m, report, _corr = _evaluate_fixture(fx)
        ok = report.all_satisfied and m.stop_reason in {
            "repeated_delegation",
            "circular_delegation",
            "no_progress",
        }
        details.append(f"{fx.label}:{m.stop_reason}:r_ok={report.all_satisfied}")
        all_ok = all_ok and ok
    return _result(
        "C12_loop_stops",
        passed=all_ok,
        detail="; ".join(details),
        fixtures=fixtures,
    )


def run_case_c13() -> ObservabilityCaseResult:
    fx = _fixture_provider_unavailable()
    m, report, corr = _evaluate_fixture(fx)
    ok = (
        m.stop_reason == "provider_unavailable"
        and m.provider_available is False
        and report.all_satisfied
        and corr.correlation_complete
    )
    return _result(
        "C13_provider_unavailable",
        passed=ok,
        detail=f"stop={m.stop_reason} provider_available={m.provider_available}",
        fixtures=(fx,),
    )


def run_case_c14() -> ObservabilityCaseResult:
    fx = _fixture_malformed_contradictory()
    m, report, corr = _evaluate_fixture(fx)
    actual = _r_failures(report)
    ok = (
        not corr.correlation_complete
        and "R11" in actual
        and bool(corr.orphan_parent_child_agent_run_ids or corr.orphan_handoff_brief_ids)
        and m.stop_reason == "completed_for_owner_review"
    )
    return _result(
        "C14_malformed_contradictory",
        passed=ok,
        detail=f"correlation={corr.correlation_complete} r_failures={actual}",
        fixtures=(fx,),
        expected_r_failures=("R7", "R11"),
    )


def run_case_c15() -> ObservabilityCaseResult:
    fixtures = (
        _fixture_complete_successful(),
        _fixture_delegation_blocked(),
        _fixture_bopa_child(with_provider=True),
        _fixture_obs_brief(),
        _fixture_prepare_then_brief(),
        _fixture_bopa_child(with_provider=False),
        _fixture_measured_zero(),
        _fixture_provider_unavailable(),
    )
    metrics = tuple(_evaluate_fixture(fx)[0] for fx in fixtures)
    agg = aggregate_orchestration_metrics(metrics)
    has_tokens = any(m.input_tokens is not None for m in metrics)
    ok = (
        agg.run_count == len(fixtures)
        and agg.total_handoffs == sum(m.handoff_count for m in metrics)
        and agg.handoffs_denied >= 1
        and agg.provider_unavailable_count == 1
        and (agg.total_input_tokens is not None) == has_tokens
        and agg.mean_steps == agg.total_steps / agg.run_count
    )
    missing_only = aggregate_orchestration_metrics(
        (_evaluate_fixture(_fixture_bopa_child(with_provider=False))[0],)
    )
    ok = ok and missing_only.total_input_tokens is None
    return _result(
        "C15_mixed_corpus_aggregation",
        passed=ok,
        detail=(
            f"runs={agg.run_count} steps={agg.total_steps} "
            f"handoffs={agg.total_handoffs} denied={agg.handoffs_denied} "
            f"provider_unavail={agg.provider_unavailable_count} "
            f"tokens={agg.total_input_tokens}"
        ),
        fixtures=fixtures,
        corpus_aggregate=agg,
        missing_vs_zero_ok=missing_only.total_input_tokens is None,
    )


_CASE_RUNNERS: tuple[tuple[CorpusCaseId, CaseRunner], ...] = (
    ("C01_complete_successful", run_case_c01),
    ("C02_delegation_blocked", run_case_c02),
    ("C03_bopa_child", run_case_c03),
    ("C04_obs_brief", run_case_c04),
    ("C05_prepare_then_brief", run_case_c05),
    ("C06_missing_optional_metadata", run_case_c06),
    ("C07_measured_zero", run_case_c07),
    ("C08_orphaned_child_ref", run_case_c08),
    ("C09_missing_child_record", run_case_c09),
    ("C10_stale_incomplete_handoff", run_case_c10),
    ("C11_safe_resume", run_case_c11),
    ("C12_loop_stops", run_case_c12),
    ("C13_provider_unavailable", run_case_c13),
    ("C14_malformed_contradictory", run_case_c14),
    ("C15_mixed_corpus_aggregation", run_case_c15),
)


def get_demo_fixture(case_id: str) -> ObservabilityFixture:
    """Return a static demo fixture by case id (read-only; no I/O).

    Raises ``KeyError`` for unknown ids. C12 maps to three fixtures via
    ``C12_repeated_delegation``, ``C12_circular_delegation``, ``C12_no_progress``.
    """
    builders = _demo_fixture_builders()
    if case_id not in builders:
        known = ", ".join(builders)
        raise KeyError(f"Unknown demo fixture {case_id!r}. Known: {known}")
    return builders[case_id]()


def list_demo_fixture_ids() -> tuple[str, ...]:
    """Stable list of demo fixture ids for CLI help / manuals."""
    return tuple(_demo_fixture_builders())


def _demo_fixture_builders() -> dict[str, Callable[[], ObservabilityFixture]]:
    loop = None

    def _loop(index: int) -> Callable[[], ObservabilityFixture]:
        def _build() -> ObservabilityFixture:
            nonlocal loop
            if loop is None:
                loop = _fixtures_loop_stops()
            return loop[index]

        return _build

    return {
        "C01_complete_successful": _fixture_complete_successful,
        "C02_delegation_blocked": _fixture_delegation_blocked,
        "C03_bopa_child": lambda: _fixture_bopa_child(with_provider=True),
        "C04_obs_brief": _fixture_obs_brief,
        "C05_prepare_then_brief": _fixture_prepare_then_brief,
        "C06_missing_optional_metadata": lambda: _fixture_bopa_child(with_provider=False),
        "C07_measured_zero": _fixture_measured_zero,
        "C08_orphaned_child_ref": _fixture_orphaned_child,
        "C09_missing_child_record": _fixture_missing_child_record,
        "C10_stale_incomplete_handoff": _fixture_stale_incomplete,
        "C11_safe_resume": _fixture_safe_resume,
        "C12_repeated_delegation": _loop(0),
        "C12_circular_delegation": _loop(1),
        "C12_no_progress": _loop(2),
        "C13_provider_unavailable": _fixture_provider_unavailable,
        "C14_malformed_contradictory": _fixture_malformed_contradictory,
    }


def run_observability_corpus() -> ObservabilityCorpusReport:
    """Run the full FR-017 M2 derive-only corpus once."""
    results = tuple(runner() for _cid, runner in _CASE_RUNNERS)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    all_passed = passed == total

    results2 = tuple(runner() for _cid, runner in _CASE_RUNNERS)
    repeat_ok = True
    for a, b in zip(results, results2, strict=True):
        if a.passed != b.passed or a.case_id != b.case_id:
            repeat_ok = False
            break
        dump_a = tuple(m.model_dump(mode="json") for m in a.metrics)
        dump_b = tuple(m.model_dump(mode="json") for m in b.metrics)
        if dump_a != dump_b:
            repeat_ok = False
            break
        reports_a = tuple(r.model_dump(mode="json") for r in a.reconstructability)
        reports_b = tuple(r.model_dump(mode="json") for r in b.reconstructability)
        if reports_a != reports_b:
            repeat_ok = False
            break

    derive_only = True
    runtime_required = False
    if all_passed and repeat_ok and derive_only and not runtime_required:
        verdict: Literal["GO", "DEFER"] = "GO"
        rationale = (
            "Useful evaluation remains derive-only; R1-R12 and correlation/orphan "
            "detection are reliable from existing OrchestrationRun/Handoff/"
            "AgentRunMetrics records; deterministic repeatability confirmed; "
            "no runtime instrumentation, new events, dashboards, or FR-016 redesign required."
        )
    else:
        verdict = "DEFER"
        rationale = (
            f"Corpus incomplete or non-deterministic (passed={passed}/{total}, "
            f"repeat_ok={repeat_ok}). Useful outcomes appear to require further "
            "instrumentation or redesign — defer FR-017."
        )

    return ObservabilityCorpusReport(
        results=results,
        passed=passed,
        total=total,
        all_passed=all_passed,
        derive_only=derive_only,
        runtime_instrumentation_required=runtime_required,
        deterministic_repeat_ok=repeat_ok,
        go_no_go=verdict,
        go_no_go_rationale=rationale,
    )


def go_no_go_observability() -> tuple[Literal["GO", "DEFER"], str]:
    """Return M2 go/no-go from a fresh corpus run."""
    report = run_observability_corpus()
    return report.go_no_go, report.go_no_go_rationale
