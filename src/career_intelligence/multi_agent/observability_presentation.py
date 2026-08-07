"""FR-017 M3 — read-only owner presentation for orchestration observability.

Presentation only. Does not mutate DOS, BOPA, OBS, stores, or domain SoTs.
"""

from __future__ import annotations

from career_intelligence.agent.observability import AgentRunMetrics, extract_run_metrics
from career_intelligence.agent.json_store import JsonDirectoryAgentRunStore
from career_intelligence.agent.errors import AgentRunNotFoundError, AgentStorageError
from career_intelligence.agent.memory_store import InMemoryAgentRunStore

from .json_store import JsonDirectoryOrchestrationStore
from .memory_store import InMemoryOrchestrationStore
from .models import Handoff, OrchestrationRun
from .observability import (
    OrchestrationCorpusMetrics,
    OrchestrationRunMetrics,
    ReconstructabilityReport,
    aggregate_orchestration_metrics,
    evaluate_reconstructability,
    extract_orchestration_run_metrics,
)
from .observability_corpus import (
    ObservabilityCorpusReport,
    ObservabilityFixture,
    run_observability_corpus,
)
from .presentation import owner_action_for_orchestration

OrchestrationStore = InMemoryOrchestrationStore | JsonDirectoryOrchestrationStore
AgentStore = InMemoryAgentRunStore | JsonDirectoryAgentRunStore


def _fmt_optional_num(value: int | float | None, *, kind: str = "int") -> str:
    """Render optional numeric metadata: missing vs measured zero."""
    if value is None:
        return "missing"
    if kind == "float":
        return f"{value:.6f}" if isinstance(value, float) else str(value)
    return str(value)


def load_handoffs_for_run(
    run: OrchestrationRun,
    store: OrchestrationStore,
) -> tuple[Handoff, ...]:
    """Load handoffs for a run; skip missing files with empty result slots omitted."""
    loaded: list[Handoff] = []
    for hid in run.handoff_ids:
        try:
            loaded.append(store.load_handoff(hid))
        except Exception:  # noqa: BLE001 — read-only best-effort
            continue
    return tuple(loaded)


def load_child_agent_metrics(
    run: OrchestrationRun,
    agent_store: AgentStore | None,
) -> tuple[AgentRunMetrics, ...]:
    """Derive FR-015 child metrics when AgentRun files exist; else omit (missing)."""
    if agent_store is None:
        return ()
    out: list[AgentRunMetrics] = []
    for aid in run.child_agent_run_ids:
        try:
            child = agent_store.load(aid)
        except (AgentRunNotFoundError, AgentStorageError, Exception):  # noqa: BLE001
            continue
        out.append(extract_run_metrics(child))
    return tuple(out)


def evaluate_run_observability(
    run: OrchestrationRun,
    handoffs: tuple[Handoff, ...] = (),
    *,
    child_metrics: tuple[AgentRunMetrics, ...] = (),
    prior_observation_hash: str | None = None,
) -> tuple[OrchestrationRunMetrics, ReconstructabilityReport]:
    """Pure derive of metrics + R1-R12 for one run."""
    metrics = extract_orchestration_run_metrics(
        run,
        handoffs,
        child_agent_metrics=child_metrics,
    )
    report = evaluate_reconstructability(
        run,
        handoffs,
        child_agent_metrics=child_metrics,
        prior_observation_hash=prior_observation_hash,
    )
    return metrics, report


def format_observability_report(
    metrics: OrchestrationRunMetrics,
    report: ReconstructabilityReport,
    *,
    source_label: str = "store",
) -> str:
    """Owner-facing reconstructability + metrics report (ASCII; read-only)."""
    corr = metrics.parent_child
    lines: list[str] = [
        "=" * 72,
        "FR-017 orchestration metrics (derive-only; read-only)",
        "Prefer `cic agent run` for ordinary preparation.",
        f"Source: {source_label}",
        "=" * 72,
        f"Orchestration run: {metrics.orchestration_run_id}",
        f"Owner goal:        {metrics.owner_goal_label} ({metrics.goal_kind})",
        f"Opportunity:       {metrics.opportunity_id}",
        f"Status:            {metrics.status}",
        f"Stop reason:       {metrics.stop_reason or '-'}",
        f"Owner next action: {metrics.owner_action_required or '-'}",
        (
            f"Steps / visits:    {metrics.step_count}/{metrics.max_steps} steps; "
            f"max_visits/specialist={metrics.max_visits_per_specialist}; "
            f"step_limit={metrics.step_limit_reached} "
            f"visit_limit={metrics.visit_limit_reached}"
        ),
        f"Elapsed:           {_fmt_optional_num(metrics.elapsed_ms)} ms",
        "",
        "--- Observed state ---",
    ]
    if metrics.last_observation_hash is None and metrics.last_package_status is None:
        lines.append("  (none)")
    else:
        lines.extend(
            [
                f"  package={metrics.last_package_status}  "
                f"truth={metrics.last_truth_status}  "
                f"pipeline={metrics.last_pipeline_status}",
                f"  readiness_class={metrics.last_readiness_class}",
                f"  observation_hash={metrics.last_observation_hash}",
            ]
        )

    lines.append("")
    lines.append("--- Selection / specialists ---")
    if metrics.specialists_selected:
        lines.append(f"  selected={', '.join(metrics.specialists_selected)}")
    else:
        lines.append("  selected=(none)")
    for visit in metrics.specialist_visits:
        lines.append(
            f"  visit {visit.specialist_id}: count={visit.visit_count} "
            f"last_handoff={visit.last_handoff_id or '-'} "
            f"last_hash={visit.last_observation_hash or '-'}"
        )

    lines.append("")
    lines.append("--- Handoffs ---")
    lines.append(
        f"  count={metrics.handoff_count} "
        f"allowed={metrics.handoffs_allowed} denied={metrics.handoffs_denied}"
    )
    if not metrics.handoffs:
        lines.append("  (none)")
    for hm in metrics.handoffs:
        lines.extend(
            [
                f"  Handoff {hm.handoff_id}",
                f"    target={hm.target_specialist} goal={hm.requested_goal_kind}",
                f"    selection_reason={hm.selection_reason}",
                f"    delegation={hm.policy_decision}"
                + (
                    f" ({hm.policy_deny_reason})"
                    if hm.policy_deny_reason
                    else ""
                ),
                f"    lifecycle={hm.acceptance}"
                + (
                    f" ({hm.acceptance_reason})"
                    if hm.acceptance_reason
                    else ""
                ),
                f"    expected_output={hm.expected_output_kind}",
                f"    state_hash={hm.observed_state_hash or '-'}",
                f"    idempotency_key={hm.idempotency_key or 'missing'}",
                f"    child_agent_run={hm.child_agent_run_id or '-'}",
                f"    child_brief={hm.child_brief_id or '-'}",
                f"    handoff_elapsed_ms={_fmt_optional_num(hm.handoff_elapsed_ms)}",
            ]
        )

    lines.append("")
    lines.append("--- Parent / child correlation ---")
    lines.append(f"  correlation_complete={corr.correlation_complete}")
    lines.append(
        f"  parent_children={', '.join(corr.parent_child_agent_run_ids) or '-'}"
    )
    lines.append(f"  parent_brief={corr.parent_last_brief_id or '-'}")
    lines.append(
        f"  handoff_children={', '.join(corr.handoff_child_agent_run_ids) or '-'}"
    )
    lines.append(
        f"  handoff_briefs={', '.join(corr.handoff_child_brief_ids) or '-'}"
    )
    if corr.orphan_parent_child_agent_run_ids:
        lines.append(
            "  ORPHAN parent child ids: "
            + ", ".join(corr.orphan_parent_child_agent_run_ids)
        )
    if corr.orphan_handoff_child_agent_run_ids:
        lines.append(
            "  ORPHAN handoff child ids: "
            + ", ".join(corr.orphan_handoff_child_agent_run_ids)
        )
    if corr.orphan_handoff_brief_ids:
        lines.append(
            "  ORPHAN brief ids: " + ", ".join(corr.orphan_handoff_brief_ids)
        )
    if corr.correlation_complete:
        lines.append("  (no orphans)")

    lines.append("")
    lines.append("--- Optional provider / token / cost (missing != zero) ---")
    lines.append(f"  provider={metrics.provider if metrics.provider is not None else 'missing'}")
    lines.append(f"  model={metrics.model if metrics.model is not None else 'missing'}")
    lines.append(f"  input_tokens={_fmt_optional_num(metrics.input_tokens)}")
    lines.append(f"  output_tokens={_fmt_optional_num(metrics.output_tokens)}")
    lines.append(
        f"  estimated_cost_usd={_fmt_optional_num(metrics.estimated_cost_usd, kind='float')}"
    )
    if metrics.input_tokens is None and metrics.child_agent_run_ids:
        lines.append(
            "  WARNING: child AgentRun id(s) present but token/cost metadata missing "
            "(join absent or provider fields unset)."
        )
    if (
        metrics.input_tokens == 0
        or metrics.output_tokens == 0
        or metrics.estimated_cost_usd == 0.0
    ):
        lines.append(
            "  NOTE: measured zero present (distinct from missing)."
        )

    lines.append("")
    lines.append("--- Resume / idempotency evidence ---")
    hashes = [h.observed_state_hash for h in metrics.handoffs if h.observed_state_hash]
    keys = [h.idempotency_key for h in metrics.handoffs if h.idempotency_key]
    lines.append(f"  observation_hashes_on_handoffs={', '.join(hashes) or 'missing'}")
    lines.append(f"  idempotency_keys={', '.join(keys) or 'missing'}")

    lines.append("")
    lines.append("--- R1-R12 reconstructability ---")
    lines.append(
        f"  satisfied={report.satisfied_count}/{report.total_count} "
        f"all_satisfied={report.all_satisfied}"
    )
    for check in report.checks:
        mark = "PASS" if check.satisfied else "FAIL"
        lines.append(f"  {check.criterion_id} {mark}: {check.question}")
        if check.detail:
            lines.append(f"       {check.detail}")

    lines.append("")
    lines.append(
        "Safety: read-only derive; no DOS/BOPA/OBS mutation; no new SoT; "
        "Horizon 1B not gated on FR-017."
    )
    return "\n".join(lines) + "\n"


def format_corpus_observability_report(
    corpus: ObservabilityCorpusReport,
) -> str:
    """Format M2 acceptance corpus results for owner CLI."""
    lines: list[str] = [
        "=" * 72,
        "FR-017 observability corpus (deterministic; derive-only)",
        "=" * 72,
        f"passed={corpus.passed}/{corpus.total} all_passed={corpus.all_passed}",
        f"deterministic_repeat_ok={corpus.deterministic_repeat_ok}",
        f"derive_only={corpus.derive_only}",
        f"runtime_instrumentation_required={corpus.runtime_instrumentation_required}",
        f"go_no_go={corpus.go_no_go}",
        f"rationale={corpus.go_no_go_rationale}",
        "",
        "--- Cases ---",
    ]
    for result in corpus.results:
        mark = "PASS" if result.passed else "FAIL"
        lines.append(f"  {result.case_id}: {mark} | {result.detail}")
        if result.actual_r_failures:
            lines.append(f"    r_failures={', '.join(result.actual_r_failures)}")
        if result.missing_vs_zero_ok is not None:
            lines.append(f"    missing_vs_zero_ok={result.missing_vs_zero_ok}")

    # Aggregate metrics from all case metrics (mixed picture).
    all_metrics = tuple(m for r in corpus.results for m in r.metrics)
    if all_metrics:
        agg = aggregate_orchestration_metrics(all_metrics)
        lines.append("")
        lines.append("--- Aggregate metrics (all case fixtures) ---")
        lines.extend(_format_aggregate_lines(agg))
        if corpus.results[-1].corpus_aggregate is not None:
            lines.append("")
            lines.append("--- C15 mixed-corpus aggregate (dedicated) ---")
            lines.extend(_format_aggregate_lines(corpus.results[-1].corpus_aggregate))

    lines.append("")
    lines.append("Read-only: corpus uses static fixtures; no store writes.")
    return "\n".join(lines) + "\n"


def _format_aggregate_lines(agg: OrchestrationCorpusMetrics) -> list[str]:
    return [
        f"  run_count={agg.run_count}",
        f"  total_steps={agg.total_steps} mean_steps={agg.mean_steps:.3f}",
        f"  total_handoffs={agg.total_handoffs} "
        f"allowed={agg.handoffs_allowed} denied={agg.handoffs_denied}",
        f"  provider_unavailable_count={agg.provider_unavailable_count}",
        f"  stop_reason_counts={agg.stop_reason_counts}",
        f"  specialist_visit_counts={agg.specialist_visit_counts}",
        f"  total_input_tokens={_fmt_optional_num(agg.total_input_tokens)}",
        f"  total_output_tokens={_fmt_optional_num(agg.total_output_tokens)}",
        f"  total_estimated_cost_usd="
        f"{_fmt_optional_num(agg.total_estimated_cost_usd, kind='float')}",
        f"  total_elapsed_ms={_fmt_optional_num(agg.total_elapsed_ms)}",
    ]


def format_fixture_observability(fixture: ObservabilityFixture) -> str:
    """Evaluate and format a static demo fixture (no I/O)."""
    metrics, report = evaluate_run_observability(
        fixture.run,
        fixture.handoffs,
        child_metrics=fixture.child_metrics,
        prior_observation_hash=fixture.prior_observation_hash,
    )
    return format_observability_report(
        metrics,
        report,
        source_label=f"demo fixture ({fixture.label})",
    )


def format_store_observability(
    run: OrchestrationRun,
    orch_store: OrchestrationStore,
    *,
    agent_store: AgentStore | None = None,
    prior_observation_hash: str | None = None,
) -> str:
    """Load handoffs/children from stores (read-only) and format metrics."""
    handoffs = load_handoffs_for_run(run, orch_store)
    children = load_child_agent_metrics(run, agent_store)
    metrics, report = evaluate_run_observability(
        run,
        handoffs,
        child_metrics=children,
        prior_observation_hash=prior_observation_hash,
    )
    # Surface owner next action using existing FR-016 helper for consistency.
    if not metrics.owner_action_required:
        # report already has stop; append presentation hint via detail in footer
        pass
    text = format_observability_report(metrics, report, source_label="orchestration store")
    # Replace owner next action line with richer FR-016 mapping when blank.
    owner_line = owner_action_for_orchestration(run)
    return text.replace(
        f"Owner next action: {metrics.owner_action_required or '-'}",
        f"Owner next action: {owner_line}",
        1,
    )


def format_corpus_cli() -> str:
    """Run acceptance corpus and format (read-only / in-memory)."""
    return format_corpus_observability_report(run_observability_corpus())
