"""Owner-facing orchestration presentation (FR-016 M3 learning proof).

Presentation only — does not change DelegationPolicy or specialist ToolPolicies.
Not a product replacement for direct ``cic agent`` preparation.
"""

from __future__ import annotations

from .goals import owner_goal_label
from .json_store import JsonDirectoryOrchestrationStore
from .memory_store import InMemoryOrchestrationStore
from .models import Handoff, OrchestrationRun
from .specialist_registry import BOPA_SPECIALIST, OBS_SPECIALIST, get_specialist
from .types import SpecialistId

OrchestrationStore = InMemoryOrchestrationStore | JsonDirectoryOrchestrationStore

_AUTHORITY: dict[SpecialistId, tuple[str, ...]] = {
    "bopa": (
        "May coordinate approved preparation / package verify / truth validation "
        "under BOPA ToolPolicy.",
        "May request owner review or stop.",
        "Must not submit, advance pipeline, discover jobs, waive truth, or "
        "re-enter FR-008.",
    ),
    "obs": (
        "Read-only: inspect readiness / pipeline / truth blockers / agent history.",
        "May compose an OperationalBrief and recommend (not execute) delegation.",
        "Must not prepare, validate truth, submit, mutate pipeline, or repair data.",
    ),
}


def specialist_authority_lines(specialist_id: SpecialistId) -> tuple[str, ...]:
    return _AUTHORITY[specialist_id]


def _elapsed(run: OrchestrationRun) -> str:
    delta = run.updated_at - run.created_at
    seconds = max(0.0, delta.total_seconds())
    return f"{seconds:.3f}s (created_at -> updated_at; provider/cost deferred to FR-017)"


def owner_action_for_orchestration(run: OrchestrationRun) -> str:
    """Map status + stop reason to a legal next owner step."""
    if run.owner_action_required:
        base = run.owner_action_required
    elif run.stop_reason:
        base = f"Orchestration stopped: {run.stop_reason}"
    else:
        base = "Inspect orchestration status."

    if run.status == "awaiting_owner":
        return (
            f"{base} Next: cic agent orchestrate resume "
            f"{run.orchestration_run_id} --approve"
        )
    if run.status == "failed":
        return (
            f"{base} Resume is not available. Start a new "
            f"cic agent orchestrate run {run.goal.opportunity_id} "
            f"--goal {owner_goal_label(run.goal)} --approve"
        )
    if run.status == "completed":
        return f"{base} Orchestration completed."
    if run.status == "cancelled":
        return f"{base} Orchestration cancelled."
    return base


def format_orchestration_list_line(run: OrchestrationRun) -> str:
    goal = owner_goal_label(run.goal)
    return (
        f"{run.orchestration_run_id}  {run.status:15}  "
        f"stop={run.stop_reason or '-':28}  "
        f"goal={goal:18}  opp={run.goal.opportunity_id}  "
        f"steps={run.step_count}"
    )


def format_orchestration_history(
    run: OrchestrationRun,
    *,
    verbose: bool = False,
) -> str:
    lines = [
        f"Orchestration history {run.orchestration_run_id}",
        f"  parent status={run.status} stop={run.stop_reason}",
        "  events (append-only):",
    ]
    for event in run.events:
        detail = event.message if verbose and event.message else (event.message or "")
        piece = f"    - {event.kind}"
        if event.specialist_id:
            piece += f" specialist={event.specialist_id}"
        if event.handoff_id:
            piece += f" handoff={event.handoff_id}"
        if event.policy_decision:
            piece += f" policy={event.policy_decision}"
        if event.stop_reason:
            piece += f" stop={event.stop_reason}"
        if detail:
            piece += f" | {detail}"
        if verbose and event.refs:
            piece += f" refs={','.join(event.refs)}"
        lines.append(piece)
    return "\n".join(lines) + "\n"


def format_orchestration_report(
    run: OrchestrationRun,
    store: OrchestrationStore,
    *,
    verbose: bool = False,
) -> str:
    """Owner report distinguishing orchestration / handoff / specialist / domain."""
    goal_label = owner_goal_label(run.goal)
    lines: list[str] = [
        "=" * 72,
        "FR-016 orchestration (learning proof - not default daily workflow)",
        "Prefer `cic agent run` for ordinary preparation.",
        "=" * 72,
        f"Orchestration run: {run.orchestration_run_id}",
        f"Owner goal:        {goal_label} ({run.goal.goal_kind})",
        f"Opportunity:       {run.goal.opportunity_id}",
        f"Status:            {run.status}",
        f"Stop reason:       {run.stop_reason or '-'}",
        f"Global steps:      {run.step_count}/{run.max_steps}  "
        f"(max visits/specialist={run.max_visits_per_specialist})",
        f"Elapsed:           {_elapsed(run)}",
        f"Parent/child IDs:  orchestration={run.orchestration_run_id}",
    ]
    if run.child_agent_run_ids:
        lines.append(f"                   BOPA children={', '.join(run.child_agent_run_ids)}")
    if run.last_brief_id:
        lines.append(f"                   OBS brief={run.last_brief_id}")
    if run.checkpoint_ref:
        lines.append(f"Checkpoint:        {run.checkpoint_ref}")

    lines.append("")
    lines.append("--- Authoritative state observed (derived) ---")
    if run.last_observation is None:
        lines.append("  (none yet)")
    else:
        obs = run.last_observation
        lines.extend(
            [
                f"  decision={obs.decision}  package={obs.package_status}  "
                f"truth={obs.truth_status}  pipeline={obs.pipeline_status}",
                f"  readiness_class={obs.readiness_primary_state_class}",
                f"  briefing_needs={', '.join(obs.briefing_need_classes) or '-'}",
                f"  observation_hash={obs.observation_hash}",
            ]
        )
        if obs.truth_blocking_labels:
            lines.append(f"  truth_blockers={', '.join(obs.truth_blocking_labels)}")
        if obs.contradictory_flags:
            lines.append(f"  contradictory={', '.join(obs.contradictory_flags)}")

    lines.append("")
    lines.append("--- Specialist visits ---")
    if not run.specialist_visits:
        lines.append("  (none)")
    for visit in run.specialist_visits:
        lines.append(
            f"  {visit.specialist_id}: visits={visit.visit_count} "
            f"last_handoff={visit.last_handoff_id}"
        )

    lines.append("")
    lines.append("--- Handoffs (typed; supervisor-sourced) ---")
    if not run.handoff_ids:
        lines.append("  (none)")
    for hid in run.handoff_ids:
        try:
            handoff = store.load_handoff(hid)
        except Exception as error:  # noqa: BLE001
            lines.append(f"  {hid}: (load failed: {error})")
            continue
        lines.extend(_format_handoff_block(handoff, store, verbose=verbose))

    lines.append("")
    lines.append("--- Owner action required ---")
    lines.append(f"  {owner_action_for_orchestration(run)}")
    lines.append("")
    lines.append(
        "Safety: no submission, no pipeline mutation, no truth waiver, "
        "no job discovery from orchestration."
    )
    lines.append(
        "Learning note: FR-016 is a substrate/learning proof; "
        "direct BOPA (`cic agent`) remains preferred for ordinary prep."
    )
    return "\n".join(lines) + "\n"


def _format_handoff_block(
    handoff: Handoff,
    store: OrchestrationStore,
    *,
    verbose: bool,
) -> list[str]:
    specialist = get_specialist(handoff.target_specialist)
    lines = [
        f"  Handoff {handoff.handoff_id}",
        f"    source -> target:  {handoff.source} -> {handoff.target_specialist} "
        f"({specialist.display_name})",
        f"    requested goal:   {handoff.requested_goal_kind}",
        f"    selection reason: {handoff.reason}",
        f"    delegation policy: {handoff.policy_decision}"
        + (
            f" ({handoff.policy_deny_reason})"
            if handoff.policy_deny_reason
            else ""
        ),
        f"    lifecycle:        {handoff.acceptance}"
        + (
            f" ({handoff.acceptance_reason})"
            if handoff.acceptance_reason
            else ""
        ),
        f"    state hash:       {handoff.observed_state_hash or '-'}",
        f"    expected output:  {handoff.expected_output_kind}",
    ]
    lines.append("    ToolPolicy / authority boundary:")
    for line in specialist_authority_lines(handoff.target_specialist):
        lines.append(f"      - {line}")
    if handoff.target_specialist == "bopa":
        lines.append(
            f"      - allow-list: {', '.join(BOPA_SPECIALIST.allowed_actions)}"
        )
    else:
        lines.append(
            f"      - allow-list: {', '.join(OBS_SPECIALIST.allowed_actions)}"
        )

    if handoff.child_agent_run_id:
        lines.append(f"    specialist result: BOPA AgentRun {handoff.child_agent_run_id}")
        lines.append(
            "      (inspect with: cic agent show "
            f"{handoff.child_agent_run_id})"
        )
    if handoff.child_brief_id:
        lines.append(f"    specialist result: OBS brief {handoff.child_brief_id}")
        try:
            brief = store.load_brief(handoff.child_brief_id)
            lines.append(f"      needs: {', '.join(brief.briefing_need_classes)}")
            lines.append(f"      recommended next: {brief.recommended_next_step}")
            if brief.recommended_specialist:
                lines.append(
                    f"      recommended specialist: {brief.recommended_specialist} "
                    "(suggestion only - not authority)"
                )
            lines.append(f"      summary: {brief.owner_action_summary}")
            if brief.pipeline_note:
                lines.append(f"      pipeline note: {brief.pipeline_note}")
            if brief.truth_blocker_labels:
                lines.append(
                    f"      truth blockers: {', '.join(brief.truth_blocker_labels)}"
                )
            if verbose and brief.evidence_refs:
                lines.append(f"      evidence: {', '.join(brief.evidence_refs)}")
        except Exception as error:  # noqa: BLE001
            lines.append(f"      (brief load failed: {error})")

    if verbose and handoff.idempotency_key:
        lines.append(f"    idempotency_key: {handoff.idempotency_key}")
    return lines
