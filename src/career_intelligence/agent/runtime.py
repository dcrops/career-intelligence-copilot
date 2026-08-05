"""Bounded Opportunity Preparation Agent runtime (FR-015 M2).

Loop: observe → propose → ToolPolicy → execute thin adapter → audit → stop/continue.
Does not own FR-002–005 workflow execution (FR-008). Does not submit or advance pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .adapters import AgentActionExecutor
from .errors import AgentProviderError, AdapterExecutionError, AgentRuntimeError
from .hashing import compute_snapshot_hash
from .ids import (
    new_agent_audit_event_id,
    new_agent_run_id,
    new_agent_step_id,
)
from .memory_store import InMemoryAgentRunStore
from .models import (
    AgentActionProposal,
    AgentAuditEvent,
    AgentGoal,
    AgentRun,
    AgentStep,
    CompletedOperationRecord,
    PolicyDecision,
    ProviderMetadata,
    ReadinessSnapshot,
)
from .policy import evaluate_action_policy
from .proposer import ActionProposer, DeterministicActionProposer
from .readiness import ReadinessBuilder
from .state_classes import (
    approved_actions_for,
    expected_owner_stop_reason,
    primary_state_class,
)
from .store import AgentRunStore
from .types import (
    DEFAULT_MAX_STEPS,
    AgentAction,
    AgentStopReason,
)

# States that should stop without attempting mutating coordination.
_IMMEDIATE_STOP_REASONS: dict[str, AgentStopReason] = {
    "missing_analysis": "invalid_state",
    "missing_assessment": "invalid_state",
    "missing_portfolio_match": "invalid_state",
    "missing_strategy": "invalid_state",
    "unsupported_or_contradictory": "unsupported_state",
    "clarification_required": "clarification_required",
    "owner_approval_required": "owner_approval_required",
    "truth_blocked": "truth_validation_blocked",
    "provider_unavailable": "provider_unavailable",
    "ready_for_owner_review": "completed_for_owner_review",
}

_AWAITING_OWNER_STOPS: frozenset[AgentStopReason] = frozenset(
    {
        "completed_for_owner_review",
        "owner_approval_required",
        "clarification_required",
        "truth_validation_blocked",
    }
)


class AgentRuntime:
    """Bounded agent loop with checkpointed AgentRun persistence."""

    def __init__(
        self,
        *,
        readiness: ReadinessBuilder,
        executor: AgentActionExecutor,
        proposer: ActionProposer | None = None,
        store: AgentRunStore | None = None,
        max_steps: int = DEFAULT_MAX_STEPS,
        max_proposal_retries: int = 1,
    ) -> None:
        self._readiness = readiness
        self._executor = executor
        self._proposer = proposer or DeterministicActionProposer()
        self._store = store or InMemoryAgentRunStore()
        self._max_steps = max_steps
        self._max_proposal_retries = max_proposal_retries

    def get(self, agent_run_id: str) -> AgentRun:
        return self._store.load(agent_run_id)

    def start(
        self,
        goal: AgentGoal,
        *,
        owner_approvals_present: bool = False,
        provider_available: bool = True,
    ) -> AgentRun:
        now = _now()
        run = AgentRun(
            agent_run_id=new_agent_run_id(),
            goal=goal,
            status="running",
            step_count=0,
            max_steps=self._max_steps,
            owner_approvals_present=owner_approvals_present,
            checkpoint_ref=None,
            created_at=now,
            updated_at=now,
        )
        run = self._append_event(
            run,
            kind="run_started",
            message=f"goal={goal.goal_kind} opportunity={goal.opportunity_id}",
        )
        run = self._store.save(run)
        return self._loop(
            run,
            provider_available=provider_available,
            resume_incomplete=False,
        )

    def resume(
        self,
        agent_run_id: str,
        *,
        owner_approvals_present: bool | None = None,
        provider_available: bool = True,
    ) -> AgentRun:
        run = self._store.load(agent_run_id)
        if run.status not in {"awaiting_owner", "running"}:
            raise AgentRuntimeError(
                f"cannot resume agent run in status {run.status!r}"
            )
        # Clear terminal awaiting fields to continue.
        updates: dict[str, object] = {
            "status": "running",
            "stop_reason": None,
            "updated_at": _now(),
        }
        if owner_approvals_present is not None:
            updates["owner_approvals_present"] = owner_approvals_present
        run = run.model_copy(update=updates)
        run = self._append_event(
            run,
            kind="resume_observed",
            message=f"resuming {agent_run_id}",
            refs=(agent_run_id,),
        )
        run = self._store.save(run)
        return self._loop(
            run,
            provider_available=provider_available,
            resume_incomplete=True,
        )

    def _loop(
        self,
        run: AgentRun,
        *,
        provider_available: bool,
        resume_incomplete: bool,
    ) -> AgentRun:
        need_resume_inspect = resume_incomplete
        while run.status == "running":
            if run.step_count >= run.max_steps:
                return self._stop(run, "max_steps_reached", status="failed")

            snapshot = self._readiness.build(
                run.goal.opportunity_id,
                owner_approvals_present=run.owner_approvals_present,
                provider_available=provider_available,
                prior_agent_run_id=run.agent_run_id if need_resume_inspect else None,
                prior_agent_run_incomplete=need_resume_inspect,
            )
            if snapshot.snapshot_hash is None:
                snapshot = snapshot.model_copy(
                    update={"snapshot_hash": compute_snapshot_hash(snapshot)}
                )

            primary = primary_state_class(snapshot)
            run = run.model_copy(
                update={
                    "last_snapshot": snapshot,
                    "primary_state_class": primary,
                    "updated_at": _now(),
                }
            )
            run = self._append_event(
                run,
                kind="snapshot_observed",
                state_class=primary,
                message=f"hash={snapshot.snapshot_hash}",
                refs=(
                    f"package:{snapshot.package.status}",
                    f"truth:{snapshot.truth.status}",
                ),
            )

            if need_resume_inspect:
                need_resume_inspect = False
                proposal = AgentActionProposal(
                    action="inspect_readiness",
                    rationale="Resume requires inspect_readiness before further actions.",
                    evidence_refs=(f"run:{run.agent_run_id}",),
                    primary_state_class=primary,
                )
                run, should_continue = self._apply_step(
                    run, snapshot, proposal, provider_meta=None
                )
                if not should_continue:
                    return run
                continue

            if primary in _IMMEDIATE_STOP_REASONS:
                reason = _IMMEDIATE_STOP_REASONS[primary]
                return self._finalize_stop_from_state(run, snapshot, primary, reason)

            approved = approved_actions_for(snapshot, state_class=primary)
            proposal, provider_meta, provider_failed = self._propose(
                snapshot, approved=approved, primary=primary
            )
            if provider_failed:
                run = run.model_copy(update={"provider": provider_meta})
                return self._stop(run, "provider_unavailable", status="failed")

            run, should_continue = self._apply_step(
                run, snapshot, proposal, provider_meta=provider_meta
            )
            if not should_continue:
                return run

        return run

    def _propose(
        self,
        snapshot: ReadinessSnapshot,
        *,
        approved: frozenset[AgentAction],
        primary: str,
    ) -> tuple[AgentActionProposal, ProviderMetadata | None, bool]:
        attempts = 0
        last_error: Exception | None = None
        while attempts <= self._max_proposal_retries:
            attempts += 1
            try:
                proposal, meta = self._proposer.propose(
                    snapshot,
                    approved_actions=approved,
                    primary_state_class=primary,  # type: ignore[arg-type]
                )
                return proposal, meta, False
            except AgentProviderError as error:
                last_error = error
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                break
        meta = ProviderMetadata(provider="unavailable", model=None)
        # Return a stop proposal for audit if needed — runtime treats provider_failed.
        _ = last_error
        return (
            AgentActionProposal(
                action="stop",
                rationale=f"provider unavailable: {last_error}",
                evidence_refs=(f"state:{primary}",),
                primary_state_class=primary,  # type: ignore[arg-type]
            ),
            meta,
            True,
        )

    def _apply_step(
        self,
        run: AgentRun,
        snapshot: ReadinessSnapshot,
        proposal: AgentActionProposal,
        *,
        provider_meta: ProviderMetadata | None,
    ) -> tuple[AgentRun, bool]:
        """Returns (run, should_continue)."""
        # Prefer executed proposal actions for loop detection.
        recent_actions = tuple(
            s.proposal.action
            for s in run.steps
            if s.proposal is not None
        )
        recent_hashes = tuple(
            s.snapshot.snapshot_hash
            for s in run.steps
            if s.snapshot.snapshot_hash is not None
        )

        run = self._append_event(
            run,
            kind="action_proposed",
            action=proposal.action,
            state_class=primary_state_class(snapshot),
            message=proposal.rationale[:500],
            provider=provider_meta,
        )

        policy = evaluate_action_policy(
            snapshot,
            proposal,
            recent_actions=recent_actions,
            recent_snapshot_hashes=recent_hashes,
            step_count=run.step_count,
            max_steps=run.max_steps,
        )
        run = self._append_event(
            run,
            kind="policy_evaluated",
            action=proposal.action,
            state_class=policy.primary_state_class,
            policy_decision=policy.decision,
            stop_reason=policy.stop_reason,
            message=policy.deny_reason,
        )

        step_id = new_agent_step_id()
        if policy.decision == "deny":
            run = self._append_event(
                run,
                kind="action_blocked",
                step_id=step_id,
                action=proposal.action,
                state_class=policy.primary_state_class,
                policy_decision="deny",
                stop_reason=policy.stop_reason,
                message=policy.deny_reason,
            )
            step = AgentStep(
                step_id=step_id,
                index=run.step_count,
                snapshot=snapshot,
                primary_state_class=policy.primary_state_class,
                proposal=proposal,
                policy=policy,
                executed=False,
                error_summary=policy.deny_reason,
            )
            run = self._with_step(run, step, provider_meta=provider_meta)
            stop_reason = policy.stop_reason or "policy_blocked"
            status = "awaiting_owner" if stop_reason in _AWAITING_OWNER_STOPS else "failed"
            return self._stop(run, stop_reason, status=status), False

        # Execute through thin adapter.
        completed = frozenset(op.action for op in run.completed_operations)
        try:
            result = self._executor.execute(
                proposal.action,
                snapshot,
                completed_actions=completed,
            )
        except AdapterExecutionError as error:
            step = AgentStep(
                step_id=step_id,
                index=run.step_count,
                snapshot=snapshot,
                primary_state_class=policy.primary_state_class,
                proposal=proposal,
                policy=policy,
                executed=False,
                error_summary=str(error),
            )
            run = self._with_step(run, step, provider_meta=provider_meta)
            run = self._append_event(
                run,
                kind="error_recorded",
                step_id=step_id,
                action=proposal.action,
                message=str(error),
            )
            return self._stop(run, "unexpected_failure", status="failed"), False

        step = AgentStep(
            step_id=step_id,
            index=run.step_count,
            snapshot=snapshot,
            primary_state_class=policy.primary_state_class,
            proposal=proposal,
            policy=policy,
            executed=True,
            skipped_as_idempotent=result.skipped_as_idempotent,
            service_result_summary=result.summary,
        )
        run = self._with_step(run, step, provider_meta=provider_meta)
        run = self._append_event(
            run,
            kind="action_executed",
            step_id=step_id,
            action=proposal.action,
            state_class=policy.primary_state_class,
            policy_decision="allow",
            message=result.summary,
            refs=((result.result_ref,) if result.result_ref else ()),
        )
        run = self._append_event(
            run,
            kind="service_result",
            step_id=step_id,
            action=proposal.action,
            message=result.summary,
            refs=((result.result_ref,) if result.result_ref else ()),
        )

        if result.mutates_domain or (
            proposal.action in {"run_preparation", "validate_truth_package"}
            and not result.skipped_as_idempotent
        ):
            run = run.model_copy(
                update={
                    "completed_operations": run.completed_operations
                    + (
                        CompletedOperationRecord(
                            action=proposal.action,
                            at=_now(),
                            result_ref=result.result_ref,
                            skipped_as_idempotent=result.skipped_as_idempotent,
                        ),
                    )
                }
            )
        elif result.skipped_as_idempotent and proposal.action in {
            "run_preparation",
            "validate_truth_package",
        }:
            run = run.model_copy(
                update={
                    "completed_operations": run.completed_operations
                    + (
                        CompletedOperationRecord(
                            action=proposal.action,
                            at=_now(),
                            result_ref=result.result_ref,
                            skipped_as_idempotent=True,
                        ),
                    )
                }
            )

        if proposal.action in {"stop", "request_owner_review"}:
            reason = (
                policy.stop_reason
                or expected_owner_stop_reason(snapshot)
                or ("completed_for_owner_review" if proposal.action == "stop" else "owner_approval_required")
            )
            status = "awaiting_owner" if reason in _AWAITING_OWNER_STOPS else "completed"
            if reason in {
                "invalid_state",
                "unsupported_state",
                "provider_unavailable",
                "max_steps_reached",
                "unexpected_failure",
                "policy_blocked",
                "retry_exhausted",
            }:
                status = "failed"
            if reason == "completed_for_owner_review":
                status = "awaiting_owner"
            return self._stop(run, reason, status=status), False

        run = self._store.save(run)
        return run, True

    def _finalize_stop_from_state(
        self,
        run: AgentRun,
        snapshot: ReadinessSnapshot,
        primary: str,
        reason: AgentStopReason,
    ) -> AgentRun:
        proposal = AgentActionProposal(
            action="stop",
            rationale=f"Immediate stop for primary state {primary!r}.",
            evidence_refs=(f"state:{primary}", f"hash:{snapshot.snapshot_hash}"),
            primary_state_class=primary,  # type: ignore[arg-type]
        )
        policy = evaluate_action_policy(
            snapshot,
            proposal,
            step_count=run.step_count,
            max_steps=run.max_steps,
        )
        # Force allow stop even if somehow denied (should not happen).
        if policy.decision == "deny":
            policy = PolicyDecision(
                decision="allow",
                action="stop",
                primary_state_class=policy.primary_state_class,
                applicable_state_classes=policy.applicable_state_classes,
                approved_actions=policy.approved_actions,
                stop_reason=reason,
            )
        step = AgentStep(
            step_id=new_agent_step_id(),
            index=run.step_count,
            snapshot=snapshot,
            primary_state_class=policy.primary_state_class,
            proposal=proposal,
            policy=policy,
            executed=True,
            service_result_summary=f"stopped: {reason}",
        )
        run = self._append_event(
            run,
            kind="action_proposed",
            action="stop",
            state_class=policy.primary_state_class,
            message=proposal.rationale,
        )
        run = self._append_event(
            run,
            kind="policy_evaluated",
            action="stop",
            state_class=policy.primary_state_class,
            policy_decision="allow",
            stop_reason=reason,
        )
        run = self._with_step(run, step)
        status = "awaiting_owner" if reason in _AWAITING_OWNER_STOPS else "failed"
        if reason == "completed_for_owner_review":
            status = "awaiting_owner"
        return self._stop(run, reason, status=status)

    def _with_step(
        self,
        run: AgentRun,
        step: AgentStep,
        *,
        provider_meta: ProviderMetadata | None = None,
    ) -> AgentRun:
        updates: dict[str, object] = {
            "steps": run.steps + (step,),
            "step_count": run.step_count + 1,
            "updated_at": _now(),
            "checkpoint_ref": f"step:{step.step_id}",
        }
        if provider_meta is not None:
            updates["provider"] = provider_meta
        return run.model_copy(update=updates)

    def _stop(
        self,
        run: AgentRun,
        reason: AgentStopReason,
        *,
        status: str,
    ) -> AgentRun:
        run = run.model_copy(
            update={
                "status": status,
                "stop_reason": reason,
                "updated_at": _now(),
            }
        )
        run = self._append_event(
            run,
            kind="stop_recorded",
            stop_reason=reason,
            message=f"status={status}",
        )
        return self._store.save(run)

    def _append_event(
        self,
        run: AgentRun,
        *,
        kind: str,
        message: str | None = None,
        action: AgentAction | None = None,
        state_class: str | None = None,
        policy_decision: str | None = None,
        stop_reason: AgentStopReason | None = None,
        step_id: str | None = None,
        refs: tuple[str, ...] = (),
        provider: ProviderMetadata | None = None,
    ) -> AgentRun:
        event = AgentAuditEvent(
            event_id=new_agent_audit_event_id(),
            kind=kind,  # type: ignore[arg-type]
            at=_now(),
            step_id=step_id,  # type: ignore[arg-type]
            state_class=state_class,  # type: ignore[arg-type]
            action=action,
            policy_decision=policy_decision,  # type: ignore[arg-type]
            stop_reason=stop_reason,
            message=message,
            refs=refs,
            provider=provider,
        )
        return run.model_copy(
            update={"events": run.events + (event,), "updated_at": _now()}
        )


def _now() -> datetime:
    return datetime.now(tz=UTC)
