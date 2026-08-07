"""FR-017 M1 — orchestration observability contracts (derive-only).

Pure functions over existing OrchestrationRun / Handoff audits (+ optional child
AgentRunMetrics from FR-015). Does not mutate domain SoTs, DOS, BOPA, OBS,
Handoff, AgentRun, or orchestration runtime behaviour.

Missing vs zero (normative):
- Count fields use ``0`` when the audit contains no matching items.
- Optional provider / token / cost / latency fields use ``None`` when absent;
  never coerce missing to ``0`` (``0`` means measured zero).
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from career_intelligence.agent.observability import AgentRunMetrics

from .goals import owner_goal_label
from .models import Handoff, OrchestrationRun
from .types import (
    DelegationDecisionKind,
    HandoffAcceptance,
    OrchestrationStopReason,
    SpecialistId,
)

ReconstructabilityId = Literal[
    "R1",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
    "R7",
    "R8",
    "R9",
    "R10",
    "R11",
    "R12",
]

RECONSTRUCTABILITY_IDS: tuple[ReconstructabilityId, ...] = (
    "R1",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
    "R7",
    "R8",
    "R9",
    "R10",
    "R11",
    "R12",
)

RECONSTRUCTABILITY_QUESTIONS: dict[ReconstructabilityId, str] = {
    "R1": "What owner goal started the run?",
    "R2": "What authoritative state was observed?",
    "R3": "Which specialists were selected, and why?",
    "R4": "Did DelegationPolicy allow or deny, and why?",
    "R5": "Which specialist authority boundary applied?",
    "R6": "What was the handoff lifecycle?",
    "R7": "What child AgentRun or OperationalBrief resulted?",
    "R8": "Why did orchestration stop?",
    "R9": "What must the owner do next?",
    "R10": "Were global step / visit limits approached or hit?",
    "R11": "Can parent -> handoff -> child be walked without gaps?",
    "R12": "On resume paths, can SoT re-inspect / idempotency be evidenced?",
}


class HandoffMetrics(BaseModel):
    """Derived summary for one typed handoff."""

    model_config = ConfigDict(extra="forbid")

    handoff_id: str
    target_specialist: SpecialistId
    requested_goal_kind: str
    selection_reason: str
    policy_decision: DelegationDecisionKind
    policy_deny_reason: str | None = None
    acceptance: HandoffAcceptance
    acceptance_reason: str | None = None
    observed_state_hash: str | None = None
    idempotency_key: str | None = None
    expected_output_kind: str
    child_agent_run_id: str | None = None
    child_brief_id: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    handoff_elapsed_ms: int | None = None


class SpecialistVisitMetrics(BaseModel):
    """Derived visit accounting for one specialist."""

    model_config = ConfigDict(extra="forbid")

    specialist_id: SpecialistId
    visit_count: int = Field(..., ge=0)
    last_handoff_id: str | None = None
    last_observation_hash: str | None = None


class ParentChildCorrelation(BaseModel):
    """Parent OrchestrationRun ↔ handoff ↔ child result linkage."""

    model_config = ConfigDict(extra="forbid")

    parent_orchestration_run_id: str
    parent_child_agent_run_ids: tuple[str, ...] = ()
    parent_last_brief_id: str | None = None
    handoff_child_agent_run_ids: tuple[str, ...] = ()
    handoff_child_brief_ids: tuple[str, ...] = ()
    orphan_parent_child_agent_run_ids: tuple[str, ...] = ()
    orphan_handoff_child_agent_run_ids: tuple[str, ...] = ()
    orphan_handoff_brief_ids: tuple[str, ...] = ()
    correlation_complete: bool = False


class OrchestrationRunMetrics(BaseModel):
    """Per-run orchestration observability summary (derived; not a SoT)."""

    model_config = ConfigDict(extra="forbid")

    orchestration_run_id: str
    opportunity_id: str
    owner_goal_label: str
    goal_kind: str
    brief_only: bool
    synthesize_after_prepare: bool
    status: str
    stop_reason: OrchestrationStopReason | None = None
    owner_action_required: str | None = None
    step_count: int = Field(..., ge=0)
    max_steps: int = Field(..., ge=1)
    max_visits_per_specialist: int = Field(..., ge=1)
    events_count: int = Field(..., ge=0)
    handoff_count: int = Field(..., ge=0)
    handoffs_allowed: int = Field(..., ge=0)
    handoffs_denied: int = Field(..., ge=0)
    specialist_visits: tuple[SpecialistVisitMetrics, ...] = ()
    handoffs: tuple[HandoffMetrics, ...] = ()
    specialists_selected: tuple[SpecialistId, ...] = ()
    last_observation_hash: str | None = None
    last_package_status: str | None = None
    last_truth_status: str | None = None
    last_pipeline_status: str | None = None
    last_readiness_class: str | None = None
    last_brief_id: str | None = None
    child_agent_run_ids: tuple[str, ...] = ()
    child_agent_metrics: tuple[AgentRunMetrics, ...] = ()
    parent_child: ParentChildCorrelation
    owner_approvals_present: bool
    provider_available: bool
    # Optional provider roll-up from children — None means absent, not zero.
    provider: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    elapsed_ms: int | None = None
    created_at: datetime
    updated_at: datetime
    step_limit_reached: bool = False
    visit_limit_reached: bool = False


class OrchestrationCorpusMetrics(BaseModel):
    """Aggregate metrics across many orchestration runs."""

    model_config = ConfigDict(extra="forbid")

    run_count: int = Field(..., ge=0)
    total_steps: int = Field(..., ge=0)
    mean_steps: float = 0.0
    total_handoffs: int = Field(..., ge=0)
    handoffs_allowed: int = Field(..., ge=0)
    handoffs_denied: int = Field(..., ge=0)
    stop_reason_counts: dict[str, int] = Field(default_factory=dict)
    specialist_visit_counts: dict[str, int] = Field(default_factory=dict)
    provider_unavailable_count: int = Field(..., ge=0)
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_estimated_cost_usd: float | None = None
    total_elapsed_ms: int | None = None


class ReconstructabilityCheck(BaseModel):
    """One R1–R12 reconstructability result."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: ReconstructabilityId
    question: str
    satisfied: bool
    detail: str = ""


class ReconstructabilityReport(BaseModel):
    """Full R1–R12 report for one orchestration run (+ handoffs/children)."""

    model_config = ConfigDict(extra="forbid")

    orchestration_run_id: str
    checks: tuple[ReconstructabilityCheck, ...]
    all_satisfied: bool
    satisfied_count: int = Field(..., ge=0)
    total_count: int = Field(..., ge=0)


def extract_handoff_metrics(handoff: Handoff) -> HandoffMetrics:
    """Derive metrics for a single handoff."""
    elapsed: int | None = None
    if handoff.resolved_at is not None:
        elapsed = int(
            (handoff.resolved_at - handoff.created_at).total_seconds() * 1000
        )
    return HandoffMetrics(
        handoff_id=handoff.handoff_id,
        target_specialist=handoff.target_specialist,
        requested_goal_kind=handoff.requested_goal_kind,
        selection_reason=handoff.reason,
        policy_decision=handoff.policy_decision,
        policy_deny_reason=handoff.policy_deny_reason,
        acceptance=handoff.acceptance,
        acceptance_reason=handoff.acceptance_reason,
        observed_state_hash=handoff.observed_state_hash,
        idempotency_key=handoff.idempotency_key,
        expected_output_kind=handoff.expected_output_kind,
        child_agent_run_id=handoff.child_agent_run_id,
        child_brief_id=handoff.child_brief_id,
        created_at=handoff.created_at,
        resolved_at=handoff.resolved_at,
        handoff_elapsed_ms=elapsed,
    )


def correlate_parent_child(
    run: OrchestrationRun,
    handoffs: Iterable[Handoff],
) -> ParentChildCorrelation:
    """Correlate parent child refs with handoff child refs (gap detection)."""
    handoff_list = tuple(handoffs)
    handoff_agents = tuple(
        h.child_agent_run_id for h in handoff_list if h.child_agent_run_id is not None
    )
    handoff_briefs = tuple(
        h.child_brief_id for h in handoff_list if h.child_brief_id is not None
    )
    parent_agents = tuple(run.child_agent_run_ids)
    parent_set = set(parent_agents)
    handoff_agent_set = set(handoff_agents)
    orphan_parent = tuple(sorted(parent_set - handoff_agent_set))
    orphan_handoff_agents = tuple(sorted(handoff_agent_set - parent_set))
    # Orphan brief = last_brief_id set but no handoff cites it
    if run.last_brief_id is not None and run.last_brief_id not in handoff_briefs:
        orphan_briefs: tuple[str, ...] = (run.last_brief_id,)
    else:
        orphan_briefs = ()

    correlation_complete = (
        not orphan_parent
        and not orphan_handoff_agents
        and not orphan_briefs
        and all(h.orchestration_run_id == run.orchestration_run_id for h in handoff_list)
    )
    return ParentChildCorrelation(
        parent_orchestration_run_id=run.orchestration_run_id,
        parent_child_agent_run_ids=parent_agents,
        parent_last_brief_id=run.last_brief_id,
        handoff_child_agent_run_ids=handoff_agents,
        handoff_child_brief_ids=handoff_briefs,
        orphan_parent_child_agent_run_ids=orphan_parent,
        orphan_handoff_child_agent_run_ids=orphan_handoff_agents,
        orphan_handoff_brief_ids=orphan_briefs,
        correlation_complete=correlation_complete,
    )


def extract_orchestration_run_metrics(
    run: OrchestrationRun,
    handoffs: Iterable[Handoff] = (),
    *,
    child_agent_metrics: Iterable[AgentRunMetrics] = (),
) -> OrchestrationRunMetrics:
    """Derive orchestration metrics from existing audit records only."""
    handoff_list = tuple(handoffs)
    handoff_metrics = tuple(extract_handoff_metrics(h) for h in handoff_list)
    allowed = sum(1 for h in handoff_list if h.policy_decision == "allow")
    denied = sum(1 for h in handoff_list if h.policy_decision == "deny")
    visits = tuple(
        SpecialistVisitMetrics(
            specialist_id=v.specialist_id,
            visit_count=v.visit_count,
            last_handoff_id=v.last_handoff_id,
            last_observation_hash=v.last_observation_hash,
        )
        for v in run.specialist_visits
    )
    selected: list[SpecialistId] = []
    for h in handoff_list:
        if h.policy_decision == "allow" and h.target_specialist not in selected:
            selected.append(h.target_specialist)

    child_metrics = tuple(child_agent_metrics)
    # Provider roll-up: first non-null wins for provider/model; sum tokens/cost.
    provider: str | None = None
    model: str | None = None
    input_tokens_vals: list[int] = []
    output_tokens_vals: list[int] = []
    cost_vals: list[float] = []
    for child in child_metrics:
        if provider is None and child.provider is not None:
            provider = child.provider
        if model is None and child.model is not None:
            model = child.model
        if child.input_tokens is not None:
            input_tokens_vals.append(child.input_tokens)
        if child.output_tokens is not None:
            output_tokens_vals.append(child.output_tokens)
        if child.estimated_cost_usd is not None:
            cost_vals.append(child.estimated_cost_usd)

    elapsed_ms: int | None = None
    if run.created_at is not None and run.updated_at is not None:
        elapsed_ms = int((run.updated_at - run.created_at).total_seconds() * 1000)

    obs = run.last_observation
    visit_limit = any(
        v.visit_count >= run.max_visits_per_specialist for v in run.specialist_visits
    )
    return OrchestrationRunMetrics(
        orchestration_run_id=run.orchestration_run_id,
        opportunity_id=run.goal.opportunity_id,
        owner_goal_label=owner_goal_label(run.goal),
        goal_kind=run.goal.goal_kind,
        brief_only=run.goal.brief_only,
        synthesize_after_prepare=run.goal.synthesize_after_prepare,
        status=run.status,
        stop_reason=run.stop_reason,
        owner_action_required=run.owner_action_required,
        step_count=run.step_count,
        max_steps=run.max_steps,
        max_visits_per_specialist=run.max_visits_per_specialist,
        events_count=len(run.events),
        handoff_count=len(handoff_list),
        handoffs_allowed=allowed,
        handoffs_denied=denied,
        specialist_visits=visits,
        handoffs=handoff_metrics,
        specialists_selected=tuple(selected),
        last_observation_hash=obs.observation_hash if obs else None,
        last_package_status=obs.package_status if obs else None,
        last_truth_status=obs.truth_status if obs else None,
        last_pipeline_status=obs.pipeline_status if obs else None,
        last_readiness_class=obs.readiness_primary_state_class if obs else None,
        last_brief_id=run.last_brief_id,
        child_agent_run_ids=tuple(run.child_agent_run_ids),
        child_agent_metrics=child_metrics,
        parent_child=correlate_parent_child(run, handoff_list),
        owner_approvals_present=run.owner_approvals_present,
        provider_available=run.provider_available,
        provider=provider,
        model=model,
        input_tokens=sum(input_tokens_vals) if input_tokens_vals else None,
        output_tokens=sum(output_tokens_vals) if output_tokens_vals else None,
        estimated_cost_usd=sum(cost_vals) if cost_vals else None,
        elapsed_ms=elapsed_ms,
        created_at=run.created_at,
        updated_at=run.updated_at,
        step_limit_reached=run.step_count >= run.max_steps
        or run.stop_reason == "orchestration_max_steps",
        visit_limit_reached=visit_limit
        or run.stop_reason == "specialist_visit_limit",
    )


def aggregate_orchestration_metrics(
    metrics: Iterable[OrchestrationRunMetrics],
) -> OrchestrationCorpusMetrics:
    """Aggregate derived orchestration metrics (no I/O)."""
    items = tuple(metrics)
    if not items:
        return OrchestrationCorpusMetrics(
            run_count=0,
            total_steps=0,
            mean_steps=0.0,
            total_handoffs=0,
            handoffs_allowed=0,
            handoffs_denied=0,
            provider_unavailable_count=0,
        )

    def _count(values: Iterable[str]) -> dict[str, int]:
        out: dict[str, int] = {}
        for value in values:
            out[value] = out.get(value, 0) + 1
        return out

    stop_reasons = _count(m.stop_reason or "none" for m in items)
    visit_counts: dict[str, int] = {}
    for m in items:
        for visit in m.specialist_visits:
            visit_counts[visit.specialist_id] = (
                visit_counts.get(visit.specialist_id, 0) + visit.visit_count
            )

    input_tokens = [m.input_tokens for m in items if m.input_tokens is not None]
    output_tokens = [m.output_tokens for m in items if m.output_tokens is not None]
    costs = [m.estimated_cost_usd for m in items if m.estimated_cost_usd is not None]
    elapsed = [m.elapsed_ms for m in items if m.elapsed_ms is not None]
    total_steps = sum(m.step_count for m in items)
    return OrchestrationCorpusMetrics(
        run_count=len(items),
        total_steps=total_steps,
        mean_steps=total_steps / len(items),
        total_handoffs=sum(m.handoff_count for m in items),
        handoffs_allowed=sum(m.handoffs_allowed for m in items),
        handoffs_denied=sum(m.handoffs_denied for m in items),
        stop_reason_counts=stop_reasons,
        specialist_visit_counts=visit_counts,
        provider_unavailable_count=stop_reasons.get("provider_unavailable", 0),
        total_input_tokens=sum(input_tokens) if input_tokens else None,
        total_output_tokens=sum(output_tokens) if output_tokens else None,
        total_estimated_cost_usd=sum(costs) if costs else None,
        total_elapsed_ms=sum(elapsed) if elapsed else None,
    )


def evaluate_reconstructability(
    run: OrchestrationRun,
    handoffs: Iterable[Handoff] = (),
    *,
    child_agent_metrics: Iterable[AgentRunMetrics] = (),
    prior_observation_hash: str | None = None,
) -> ReconstructabilityReport:
    """Evaluate R1–R12 against existing audit evidence (derive-only)."""
    handoff_list = tuple(handoffs)
    metrics = extract_orchestration_run_metrics(
        run,
        handoff_list,
        child_agent_metrics=child_agent_metrics,
    )
    checks: list[ReconstructabilityCheck] = []

    def add(cid: ReconstructabilityId, ok: bool, detail: str) -> None:
        checks.append(
            ReconstructabilityCheck(
                criterion_id=cid,
                question=RECONSTRUCTABILITY_QUESTIONS[cid],
                satisfied=ok,
                detail=detail,
            )
        )

    # R1 goal
    add(
        "R1",
        bool(run.goal.goal_kind and run.goal.opportunity_id),
        f"goal_label={metrics.owner_goal_label} kind={run.goal.goal_kind}",
    )
    # R2 observation
    obs = run.last_observation
    add(
        "R2",
        obs is not None and obs.observation_hash is not None,
        (
            f"hash={obs.observation_hash} package={obs.package_status} "
            f"truth={obs.truth_status} pipeline={obs.pipeline_status}"
            if obs
            else "no last_observation"
        ),
    )
    # R3 selection
    selected_events = [
        e for e in run.events if e.kind in {"specialist_selected", "specialist_considered"}
    ]
    add(
        "R3",
        bool(metrics.specialists_selected)
        or any(h.policy_decision == "deny" for h in handoff_list)
        or bool(selected_events),
        f"selected={metrics.specialists_selected} selection_events={len(selected_events)}",
    )
    # R4 policy
    add(
        "R4",
        all(
            (h.policy_decision == "allow" and h.policy_deny_reason is None)
            or (h.policy_decision == "deny" and h.policy_deny_reason is not None)
            for h in handoff_list
        )
        if handoff_list
        else True,  # no handoffs yet — vacuously OK for early running
        f"allowed={metrics.handoffs_allowed} denied={metrics.handoffs_denied}",
    )
    # R5 authority boundary cited by specialist id on allow handoffs
    add(
        "R5",
        all(h.target_specialist in {"obs", "bopa"} for h in handoff_list)
        if handoff_list
        else True,
        f"targets={[h.target_specialist for h in handoff_list]}",
    )
    # R6 lifecycle
    add(
        "R6",
        all(h.acceptance is not None for h in handoff_list) if handoff_list else True,
        f"acceptances={[h.acceptance for h in handoff_list]}",
    )
    # R7 child refs when completed allow handoffs expect output
    completed_allows = [
        h
        for h in handoff_list
        if h.policy_decision == "allow" and h.acceptance in {"completed", "stopped"}
    ]
    r7_ok = all(
        (h.target_specialist == "bopa" and h.child_agent_run_id is not None)
        or (h.target_specialist == "obs" and h.child_brief_id is not None)
        or h.acceptance == "stopped"  # may stop without child on specialist failure
        for h in completed_allows
    )
    add(
        "R7",
        r7_ok,
        f"completed_allows={len(completed_allows)} "
        f"children={metrics.child_agent_run_ids} brief={metrics.last_brief_id}",
    )
    # R8 stop reason when not running
    add(
        "R8",
        run.status == "running" or run.stop_reason is not None,
        f"status={run.status} stop={run.stop_reason}",
    )
    # R9 owner action when awaiting
    add(
        "R9",
        run.status != "awaiting_owner" or bool(run.owner_action_required),
        f"owner_action={run.owner_action_required!r}",
    )
    # R10 limits visible
    add(
        "R10",
        run.max_steps >= 1 and run.max_visits_per_specialist >= 1,
        (
            f"steps={run.step_count}/{run.max_steps} "
            f"visit_limit_reached={metrics.visit_limit_reached} "
            f"step_limit_reached={metrics.step_limit_reached}"
        ),
    )
    # R11 parent/child walk
    corr = metrics.parent_child
    add(
        "R11",
        corr.correlation_complete
        or (not handoff_list and not run.child_agent_run_ids and run.last_brief_id is None),
        (
            f"complete={corr.correlation_complete} "
            f"orphan_parent={corr.orphan_parent_child_agent_run_ids} "
            f"orphan_handoff={corr.orphan_handoff_child_agent_run_ids} "
            f"orphan_briefs={corr.orphan_handoff_brief_ids}"
        ),
    )
    # R12 resume / idempotency evidence
    has_hash = any(h.observed_state_hash for h in handoff_list)
    has_idem = any(h.idempotency_key for h in handoff_list)
    hash_changed = (
        prior_observation_hash is not None
        and obs is not None
        and obs.observation_hash != prior_observation_hash
    )
    r12_ok = (
        run.status == "running" and not handoff_list
    ) or has_hash or has_idem or hash_changed
    current_hash = obs.observation_hash if obs else None
    add(
        "R12",
        r12_ok,
        (
            f"hashes_present={has_hash} idempotency_keys={has_idem} "
            f"prior_hash={prior_observation_hash!r} "
            f"current_hash={current_hash!r}"
        ),
    )

    satisfied = sum(1 for c in checks if c.satisfied)
    return ReconstructabilityReport(
        orchestration_run_id=run.orchestration_run_id,
        checks=tuple(checks),
        all_satisfied=satisfied == len(checks),
        satisfied_count=satisfied,
        total_count=len(checks),
    )
