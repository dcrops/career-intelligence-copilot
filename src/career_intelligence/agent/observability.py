"""Observability metrics derived from AgentRun audit (FR-015 M4).

Read-only aggregation over AgentRun records. Does not mutate domain SoTs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .models import AgentRun
from .types import AgentAction, AgentStopReason


class AgentRunMetrics(BaseModel):
    """Per-run observability summary."""

    model_config = ConfigDict(extra="forbid")

    agent_run_id: str
    opportunity_id: str
    status: str
    stop_reason: AgentStopReason | None = None
    step_count: int = 0
    max_steps: int = 0
    events_count: int = 0
    actions_proposed: tuple[AgentAction, ...] = ()
    actions_allowed: tuple[AgentAction, ...] = ()
    actions_blocked: tuple[AgentAction, ...] = ()
    services_executed: tuple[AgentAction, ...] = ()
    idempotent_skips: int = 0
    policy_blocks: int = 0
    repeated_action_blocks: int = 0
    retries_recorded: int = 0
    provider: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    elapsed_ms: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentCorpusMetrics(BaseModel):
    """Aggregate metrics across a corpus of runs."""

    model_config = ConfigDict(extra="forbid")

    run_count: int = 0
    total_steps: int = 0
    mean_steps: float = 0.0
    stop_reason_counts: dict[str, int] = Field(default_factory=dict)
    actions_proposed_counts: dict[str, int] = Field(default_factory=dict)
    actions_allowed_counts: dict[str, int] = Field(default_factory=dict)
    actions_blocked_counts: dict[str, int] = Field(default_factory=dict)
    services_executed_counts: dict[str, int] = Field(default_factory=dict)
    policy_blocks: int = 0
    repeated_action_blocks: int = 0
    idempotent_skips: int = 0
    provider_unavailable_count: int = 0
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_estimated_cost_usd: float | None = None
    total_elapsed_ms: int | None = None


def extract_run_metrics(run: AgentRun) -> AgentRunMetrics:
    """Derive observability fields from a completed or in-progress AgentRun."""
    proposed: list[AgentAction] = []
    allowed: list[AgentAction] = []
    blocked: list[AgentAction] = []
    executed: list[AgentAction] = []
    idempotent = 0
    policy_blocks = 0
    repeated_blocks = 0

    for step in run.steps:
        if step.proposal is not None:
            proposed.append(step.proposal.action)
        if step.policy.decision == "allow" and step.policy.action is not None:
            allowed.append(step.policy.action)
        if step.policy.decision == "deny":
            policy_blocks += 1
            if step.proposal is not None:
                blocked.append(step.proposal.action)
            if step.policy.deny_reason and "repeated no-op" in step.policy.deny_reason:
                repeated_blocks += 1
        if step.executed and step.proposal is not None:
            executed.append(step.proposal.action)
        if step.skipped_as_idempotent:
            idempotent += 1

    for event in run.events:
        if event.kind == "action_blocked" and event.action:
            if event.action not in blocked:
                blocked.append(event.action)

    retries = sum(1 for e in run.events if e.kind == "error_recorded")
    elapsed_ms: int | None = None
    if run.created_at is not None and run.updated_at is not None:
        elapsed_ms = int((run.updated_at - run.created_at).total_seconds() * 1000)

    provider = run.provider
    return AgentRunMetrics(
        agent_run_id=run.agent_run_id,
        opportunity_id=run.goal.opportunity_id,
        status=run.status,
        stop_reason=run.stop_reason,
        step_count=run.step_count,
        max_steps=run.max_steps,
        events_count=len(run.events),
        actions_proposed=tuple(proposed),
        actions_allowed=tuple(allowed),
        actions_blocked=tuple(blocked),
        services_executed=tuple(executed),
        idempotent_skips=idempotent,
        policy_blocks=policy_blocks,
        repeated_action_blocks=repeated_blocks,
        retries_recorded=retries,
        provider=provider.provider if provider else None,
        model=provider.model if provider else None,
        input_tokens=provider.input_tokens if provider else None,
        output_tokens=provider.output_tokens if provider else None,
        estimated_cost_usd=provider.estimated_cost_usd if provider else None,
        elapsed_ms=elapsed_ms,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def aggregate_metrics(runs: Iterable[AgentRun]) -> AgentCorpusMetrics:
    """Aggregate metrics across many runs."""
    metrics = [extract_run_metrics(run) for run in runs]
    if not metrics:
        return AgentCorpusMetrics()

    def _count(values: Iterable[str]) -> dict[str, int]:
        out: dict[str, int] = {}
        for value in values:
            out[value] = out.get(value, 0) + 1
        return out

    stop_reasons = _count(m.stop_reason or "none" for m in metrics)
    proposed = _count(a for m in metrics for a in m.actions_proposed)
    allowed = _count(a for m in metrics for a in m.actions_allowed)
    blocked = _count(a for m in metrics for a in m.actions_blocked)
    executed = _count(a for m in metrics for a in m.services_executed)

    input_tokens = [m.input_tokens for m in metrics if m.input_tokens is not None]
    output_tokens = [m.output_tokens for m in metrics if m.output_tokens is not None]
    costs = [m.estimated_cost_usd for m in metrics if m.estimated_cost_usd is not None]
    elapsed = [m.elapsed_ms for m in metrics if m.elapsed_ms is not None]

    total_steps = sum(m.step_count for m in metrics)
    return AgentCorpusMetrics(
        run_count=len(metrics),
        total_steps=total_steps,
        mean_steps=total_steps / len(metrics),
        stop_reason_counts=stop_reasons,
        actions_proposed_counts=proposed,
        actions_allowed_counts=allowed,
        actions_blocked_counts=blocked,
        services_executed_counts=executed,
        policy_blocks=sum(m.policy_blocks for m in metrics),
        repeated_action_blocks=sum(m.repeated_action_blocks for m in metrics),
        idempotent_skips=sum(m.idempotent_skips for m in metrics),
        provider_unavailable_count=stop_reasons.get("provider_unavailable", 0),
        total_input_tokens=sum(input_tokens) if input_tokens else None,
        total_output_tokens=sum(output_tokens) if output_tokens else None,
        total_estimated_cost_usd=sum(costs) if costs else None,
        total_elapsed_ms=sum(elapsed) if elapsed else None,
    )
