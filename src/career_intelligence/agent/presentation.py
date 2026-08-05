"""Owner-facing presentation for AgentRun audit (FR-015 M3 / OAT-001 Phase 4)."""

from __future__ import annotations

from .models import AgentAuditEvent, AgentRun, AgentStep, ReadinessSnapshot
from .types import AgentRunStatus, AgentStopReason

_PIPELINE_PREPARE_USUALLY_UNNECESSARY: frozenset[str] = frozenset(
    {
        "submitted",
        "interviewing",
        "offer",
        "accepted",
        "rejected",
        "withdrawn",
    }
)

_OWNER_ACTIONS: dict[AgentStopReason, str] = {
    "completed_for_owner_review": (
        "Review package Markdown and TruthReports. Owner review remains "
        "mandatory before external use or submission. Edit Markdown if needed, "
        "then revalidate truth before submit. Resume is available on this run "
        "after remediation (`cic agent resume <run_id> --approve`)."
    ),
    "truth_validation_blocked": (
        "Edit CV/cover-letter Markdown to remediate blocking findings, run "
        "`cic truth validate-package`, then `cic agent resume <run_id> --approve`."
    ),
    "material_benefit_required": (
        "Preparation blocked: material-benefit approval required (tier does not "
        "include consider_cv_tailoring). If appropriate, resume or start a new "
        "run with `--override-material-benefit` (and `--approve`) to record an "
        "explicit override. Example: `cic agent resume <run_id> --approve "
        "--override-material-benefit`."
    ),
    "owner_approval_required": (
        "Start a new run with `--approve` to set FR-006/FR-007 owner-approval "
        "gates explicitly (never silently defaulted)."
    ),
    "clarification_required": (
        "Provide the requested clarification, then `cic agent resume <run_id> "
        "--approve` (or start a new run)."
    ),
    "invalid_state": (
        "Complete missing FR-002-FR-005 artefacts via existing FR-008 / services, "
        "then start a new `cic agent run <opportunity_id> --approve`. BOPA will "
        "not invoke FR-008 or invent analysis. Resume is not available on failed runs."
    ),
    "unsupported_state": (
        "Opportunity is not eligible for prepare_for_owner_review (e.g. decision "
        "is not apply, or contradictory package/artefact state). Start a new run "
        "only after the Opportunity decision/state is eligible. Resume is not "
        "available on failed runs."
    ),
    "provider_unavailable": (
        "Retry with a new run when the proposer provider is available, or use "
        "the deterministic proposer (default). Resume is not available on failed runs."
    ),
    "policy_blocked": (
        "Inspect `cic agent history <run_id>` for the denied proposal. Fix "
        "readiness state, then start a new run. Do not attempt to bypass "
        "ToolPolicy. Resume is not available on failed runs."
    ),
    "max_steps_reached": (
        "Inspect history; start a new run after fixing blockers if needed. "
        "Resume is not available on failed runs."
    ),
    "retry_exhausted": (
        "Inspect history and resolve the underlying service error, then start a "
        "new run. Resume is not available on failed runs."
    ),
    "unexpected_failure": (
        "Inspect history and service errors; fix SoT, then start a new "
        "`cic agent run <opportunity_id> --approve`. Resume is not available on "
        "failed runs."
    ),
}

_AWAITING_OWNER_STOPS: frozenset[AgentStopReason] = frozenset(
    {
        "completed_for_owner_review",
        "owner_approval_required",
        "clarification_required",
        "truth_validation_blocked",
        "material_benefit_required",
    }
)


def owner_action_required(
    stop_reason: AgentStopReason | None,
    *,
    status: AgentRunStatus | None = None,
) -> str:
    if stop_reason is None:
        return "None (run still active)."
    base = _OWNER_ACTIONS.get(
        stop_reason, f"Inspect run history for stop reason {stop_reason!r}."
    )
    if status == "failed":
        # Enforce legal next action even if a stop reason is mis-classified.
        if "Resume is not available" not in base and "start a new" not in base.lower():
            return (
                f"{base} Next legal action: start a new "
                "`cic agent run <opportunity_id> --approve` "
                "(resume is not available when status is failed)."
            )
    if status == "awaiting_owner" and stop_reason in _AWAITING_OWNER_STOPS:
        if "resume" not in base.lower():
            return (
                f"{base} Resume is available: "
                "`cic agent resume <run_id> --approve`."
            )
    return base


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
    lines.append("--- Initial inspection ---")
    lines.extend(_format_initial_inspection(run))
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
    if run.stop_reason == "truth_validation_blocked" or (
        run.last_snapshot is not None and run.last_snapshot.truth.blocking_finding_codes
    ):
        lines.append("--- Truth blockers (owner-relevant) ---")
        lines.extend(_format_truth_blockers(run.last_snapshot))
        lines.append("")
    lines.append("--- Owner action required ---")
    lines.append(owner_action_required(run.stop_reason, status=run.status))
    lines.append("")
    lines.append(
        "Note: Agent status is separate from Opportunity pipeline status. "
        "This run does not submit or advance pipeline. "
        "Legal next-step rule: status=failed -> start a new run; "
        "status=awaiting_owner -> resume available."
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


def pipeline_owner_note(pipeline_status: str | None) -> str | None:
    """Informational pipeline messaging - not ToolPolicy authority."""
    if not pipeline_status:
        return None
    if pipeline_status in _PIPELINE_PREPARE_USUALLY_UNNECESSARY:
        return (
            f"Current pipeline stage: {pipeline_status}. "
            "Preparation is usually unnecessary at this stage. "
            "Pipeline remains owner-controlled; this agent does not advance it."
        )
    return (
        f"Current pipeline stage: {pipeline_status}. "
        "Pipeline remains owner-controlled; this agent does not advance it."
    )


def _format_initial_inspection(run: AgentRun) -> list[str]:
    snap = run.steps[0].snapshot if run.steps else run.last_snapshot
    if snap is None:
        return ["(no readiness observation yet)"]
    primary = run.steps[0].primary_state_class if run.steps else run.primary_state_class
    lines = [
        "Readiness was observed from the Opportunity system of record before "
        "coordination actions.",
        f"Observed primary state: {primary or '(unknown)'}",
        f"Decision: {snap.decision}",
        (
            f"Package={snap.package.status}; truth={snap.truth.status}; "
            f"approvals={snap.owner_approvals_present}"
        ),
    ]
    note = pipeline_owner_note(snap.pipeline_status)
    if note:
        lines.append(note)
    if run.steps and (run.steps[0].proposal is None or run.steps[0].proposal.action != "inspect_readiness"):
        lines.append(
            "Note: step 0 may be a coordination action; inspection still occurred "
            "and is summarised here and under Observed readiness."
        )
    return lines


def _format_snapshot_block(run: AgentRun) -> list[str]:
    snap = run.last_snapshot
    if snap is None:
        return ["(no snapshot)"]
    lines = [
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
        f"pipeline:      {snap.pipeline_status or '(unknown)'}",
        f"snapshot_hash: {snap.snapshot_hash or '(none)'}",
    ]
    note = pipeline_owner_note(snap.pipeline_status)
    if note:
        lines.append(f"pipeline_note: {note}")
    return lines


def _format_truth_blockers(snap: ReadinessSnapshot | None) -> list[str]:
    if snap is None or not snap.truth.blocking_finding_codes:
        return ["(no owner-facing blockers recorded on snapshot)"]
    return [f"- {item}" for item in snap.truth.blocking_finding_codes]


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
