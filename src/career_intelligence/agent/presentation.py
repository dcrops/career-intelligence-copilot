"""Owner-facing presentation for AgentRun audit (FR-015 M3)."""

from __future__ import annotations

from .models import AgentAuditEvent, AgentRun, AgentStep
from .types import AgentStopReason

_OWNER_ACTIONS: dict[AgentStopReason, str] = {
    "completed_for_owner_review": (
        "Review package Markdown and TruthReports. Owner review remains "
        "mandatory before external use or submission. Edit Markdown if needed, "
        "then revalidate truth before submit."
    ),
    "truth_validation_blocked": (
        "Edit CV/cover-letter Markdown to remediate blocking findings, run "
        "`cic truth validate-package`, then `cic agent resume <run_id>`."
    ),
    "owner_approval_required": (
        "Re-run with `--approve` to set FR-006/FR-007 owner-approval gates "
        "explicitly (never silently defaulted)."
    ),
    "clarification_required": (
        "Provide the requested clarification, then resume or start a new run."
    ),
    "invalid_state": (
        "Complete missing FR-002–FR-005 artefacts via existing FR-008 / services. "
        "BOPA will not invoke FR-008 or invent analysis."
    ),
    "unsupported_state": (
        "Opportunity is not eligible for prepare_for_owner_review (e.g. decision "
        "is not apply, or contradictory package/artefact state)."
    ),
    "provider_unavailable": (
        "Retry when the proposer provider is available, or use the deterministic "
        "proposer (`--deterministic`, default)."
    ),
    "policy_blocked": (
        "Inspect `cic agent history <run_id>` for the denied proposal. Fix "
        "readiness state; do not attempt to bypass ToolPolicy."
    ),
    "max_steps_reached": (
        "Inspect history; start a new run after fixing blockers if needed."
    ),
    "retry_exhausted": "Inspect history and resolve the underlying service error.",
    "unexpected_failure": "Inspect history and service errors; fix SoT then resume or re-run.",
}


def owner_action_required(stop_reason: AgentStopReason | None) -> str:
    if stop_reason is None:
        return "None (run still active)."
    return _OWNER_ACTIONS.get(stop_reason, f"Inspect run history for stop reason {stop_reason!r}.")


def format_agent_run_report(run: AgentRun, *, verbose: bool = False) -> str:
    """Human-readable owner report covering readiness, policy, execution, stop."""
    lines: list[str] = [
        "=== Agent run ===",
        f"run_id:        {run.agent_run_id}",
        f"opportunity:   {run.goal.opportunity_id}",
        f"goal:          {run.goal.goal_kind}",
        f"status:        {run.status}",
        f"stop_reason:   {run.stop_reason or '(none)'}",
        f"checkpoint:    {run.checkpoint_ref or '(none)'}",
        f"steps:         {run.step_count}/{run.max_steps}",
        f"approvals:     {run.owner_approvals_present}",
    ]
    if run.provider is not None:
        lines.append(
            f"proposer:      {run.provider.provider or '?'} / {run.provider.model or '?'}"
        )
    lines.append("")
    lines.append("--- Observed readiness ---")
    lines.extend(_format_snapshot_block(run))
    lines.append("")
    lines.append("--- Steps ---")
    if not run.steps:
        lines.append("(no steps)")
    else:
        for step in run.steps:
            lines.extend(_format_step(step, verbose=verbose))
            lines.append("")
    lines.append("--- Owner action required ---")
    lines.append(owner_action_required(run.stop_reason))
    lines.append("")
    lines.append(
        "Note: Agent status is separate from Opportunity pipeline status. "
        "This run does not submit or advance pipeline."
    )
    return "\n".join(lines).rstrip() + "\n"


def format_agent_history(run: AgentRun, *, verbose: bool = False) -> str:
    lines = [
        f"=== Audit history: {run.agent_run_id} ===",
        f"opportunity: {run.goal.opportunity_id}",
        f"status: {run.status}  stop: {run.stop_reason or '(none)'}",
        "",
    ]
    if not run.events:
        lines.append("(no events)")
    else:
        for event in run.events:
            lines.append(_format_event(event, verbose=verbose))
    return "\n".join(lines).rstrip() + "\n"


def format_agent_list_line(run: AgentRun) -> str:
    stop = run.stop_reason or "-"
    return (
        f"{run.agent_run_id}  opp={run.goal.opportunity_id}  "
        f"status={run.status}  stop={stop}  steps={run.step_count}"
    )


def _format_snapshot_block(run: AgentRun) -> list[str]:
    snap = run.last_snapshot
    if snap is None:
        return ["(no snapshot)"]
    return [
        f"primary_state: {run.primary_state_class or '(unknown)'}",
        f"decision:      {snap.decision}",
        (
            "artefacts:     "
            f"analysis={snap.artefacts.job_analysis} "
            f"assessment={snap.artefacts.assessment} "
            f"match={snap.artefacts.portfolio_match} "
            f"strategy={snap.artefacts.strategy}"
        ),
        (
            "package:       "
            f"{snap.package.status} "
            f"cv={snap.package.cv_present} "
            f"cover_letter={snap.package.cover_letter_present}"
        ),
        (
            "truth:         "
            f"{snap.truth.status} "
            f"owner_edited={snap.truth.owner_edited_markdown_since_validation}"
        ),
        f"snapshot_hash: {snap.snapshot_hash or '(none)'}",
    ]


def _format_step(step: AgentStep, *, verbose: bool) -> list[str]:
    proposed = step.proposal.action if step.proposal else "(none)"
    rationale = ""
    if verbose and step.proposal is not None:
        rationale = f"\n    rationale: {step.proposal.rationale}"
    policy = (
        f"{step.policy.decision}"
        + (f" ({step.policy.deny_reason})" if step.policy.deny_reason else "")
    )
    executed = "yes" if step.executed else "no"
    if step.skipped_as_idempotent:
        executed += " (idempotent skip)"
    result = step.service_result_summary or step.error_summary or "-"
    return [
        f"[{step.index}] state={step.primary_state_class}",
        f"    proposed:  {proposed}{rationale}",
        f"    policy:    {policy}",
        f"    executed:  {executed}",
        f"    result:    {result}",
    ]


def _format_event(event: AgentAuditEvent, *, verbose: bool) -> str:
    parts = [f"{event.at.isoformat()}  {event.kind}"]
    if event.action:
        parts.append(f"action={event.action}")
    if event.policy_decision:
        parts.append(f"policy={event.policy_decision}")
    if event.state_class:
        parts.append(f"state={event.state_class}")
    if event.stop_reason:
        parts.append(f"stop={event.stop_reason}")
    if event.message and (verbose or event.kind in {"action_blocked", "error_recorded", "stop_recorded"}):
        msg = event.message if verbose else event.message[:120]
        parts.append(f"msg={msg}")
    if event.refs and verbose:
        parts.append(f"refs={list(event.refs)}")
    return "  ".join(parts)
