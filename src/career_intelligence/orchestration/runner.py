"""Thin in-repo workflow runner for FR-008 (M1–M3)."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from career_intelligence.application_strategy import (
    ApplicationStrategyService,
    SearchOperatingContext,
)
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunity_assessment import OpportunityAssessmentService
from career_intelligence.portfolio_matching import PortfolioMatchingService
from career_intelligence.profile.models import CareerProfile

from .errors import WorkflowNodeError, WorkflowResumeError
from .ids import new_workflow_run_id
from .models import DomainArtefacts, RetryState, WorkflowControl, WorkflowState
from .nodes import NodeFailure, NodeOutcome, WorkflowNode
from .retry import (
    DEFAULT_RETRY_ELIGIBLE_NODES,
    FailureInjection,
    InjectingNode,
    RetryPolicy,
    classification_from_flag,
    is_recoverable_failure,
)
from .routing import (
    POST_DECISION_SEQUENCE,
    PRE_APPROVAL_SEQUENCE,
    SIDE_EFFECT_NODE_IDS,
    SPIKE_NODE_SEQUENCE,
    next_spike_node,
    post_decision_complete,
)
from .side_effect_nodes import (
    PersistOpportunityNode,
    RecordDecisionNode,
    allocate_opportunity_id,
)
from .adapters import coerce_acquisition_adapter
from .acquisition import AcquisitionAdapter
from .spike_nodes import (
    AcquireNode,
    AnalyseNode,
    AssessNode,
    MatchNode,
    OwnerReviewNode,
    PasteJobInput,
    StrategyNode,
    ValidateNormaliseNode,
)
from .state_helpers import (
    append_event,
    clear_retry,
    completed_node_ids,
    make_event,
    replace_artefacts,
    replace_control,
    replace_retry,
    set_last_error,
    utc_now,
)
from .store import CheckpointStore
from .types import OWNER_DECISION_KINDS, TERMINAL_WORKFLOW_STATUSES, OwnerDecisionKind


@dataclass(frozen=True)
class WorkflowDependencies:
    """Injected public services + profile + stores for one runner."""

    profile: CareerProfile
    job_analysis: JobAnalysisService
    assessment: OpportunityAssessmentService
    portfolio_matching: PortfolioMatchingService
    application_strategy: ApplicationStrategyService
    store: CheckpointStore
    opportunities: OpportunityService
    operating_context: SearchOperatingContext | None = None


class ApplicationWorkflowRunner:
    """Execute the application workflow with persist, owner-review, and retry.

    Owner-review completion semantics (unchanged from FR-008 M1): ``owner_review``
    is marked completed when the interrupt is *requested* (status→awaiting_owner),
    not when the decision is later received.

    Since FR-009 M1 the Opportunity is persisted *before* the interrupt, and the
    owner decision (apply, skip, or defer) is recorded against that same record.
    """

    def __init__(
        self,
        dependencies: WorkflowDependencies,
        *,
        retry_policy: RetryPolicy | None = None,
        failure_injection: FailureInjection | None = None,
    ) -> None:
        self._deps = dependencies
        self._retry_policy = retry_policy or RetryPolicy()
        self._failure_injection = failure_injection
        self._service_nodes: dict[str, WorkflowNode] = {
            "validate_normalise": ValidateNormaliseNode(),
            "analyse": AnalyseNode(dependencies.job_analysis),
            "assess": AssessNode(dependencies.assessment),
            "match": MatchNode(dependencies.portfolio_matching),
            "strategy": StrategyNode(
                dependencies.application_strategy,
                operating_context=dependencies.operating_context,
            ),
            "owner_review": OwnerReviewNode(),
            "persist": PersistOpportunityNode(dependencies.opportunities),
            "record_decision": RecordDecisionNode(dependencies.opportunities),
        }
        self._service_nodes = self._apply_injection(self._service_nodes)

    def _apply_injection(
        self, nodes: dict[str, WorkflowNode]
    ) -> dict[str, WorkflowNode]:
        injection = self._failure_injection
        if injection is None or injection.fail_count <= 0:
            return nodes
        if injection.node_id not in nodes:
            raise ValueError(
                f"Failure injection targets unknown node '{injection.node_id}'"
            )
        wrapped = dict(nodes)
        wrapped[injection.node_id] = InjectingNode(nodes[injection.node_id], injection)
        return wrapped

    @property
    def store(self) -> CheckpointStore:
        return self._deps.store

    @property
    def opportunities(self) -> OpportunityService:
        return self._deps.opportunities

    @property
    def retry_policy(self) -> RetryPolicy:
        return self._retry_policy

    def start(self, source: AcquisitionAdapter | PasteJobInput) -> WorkflowState:
        """Run from acquisition until owner-review interrupt, retry yield, or failure.

        ``source`` may be any ``AcquisitionAdapter`` or legacy ``PasteJobInput``
        (coerced to the paste adapter). The runner does not branch on source kind.
        """
        adapter = coerce_acquisition_adapter(source)
        stamp = utc_now()
        state = WorkflowState(
            control=WorkflowControl(
                run_id=new_workflow_run_id(),
                status="running",
                current_node="acquire",
                created_at=stamp,
                updated_at=stamp,
            ),
            artefacts=DomainArtefacts(profile=self._deps.profile),
        )
        state = append_event(state, make_event(state, "run_started", timestamp=stamp))
        state = self._checkpoint(state, reason="milestone")

        nodes: dict[str, WorkflowNode] = {
            "acquire": AcquireNode(adapter),
            **self._service_nodes,
        }
        return self._run_loop(state, nodes, post_approval=False)

    def continue_run(self, run_id: str) -> WorkflowState:
        """Continue a non-terminal running checkpoint (retry recovery or mid-apply).

        Does not accept a new owner decision. Use ``resume`` for awaiting_owner.
        """
        state = self._deps.store.load(run_id)

        if state.status in TERMINAL_WORKFLOW_STATUSES:
            raise WorkflowResumeError(
                f"Cannot continue terminal workflow '{run_id}' (status={state.status})"
            )

        if state.status == "awaiting_owner":
            raise WorkflowResumeError(
                f"Run '{run_id}' is awaiting_owner; use resume(..., decision=...)"
            )

        if state.status != "running":
            raise WorkflowResumeError(
                f"Cannot continue run '{run_id}' (status={state.status})"
            )

        stamp = utc_now()
        state = append_event(
            state,
            make_event(
                state,
                "run_resumed",
                timestamp=stamp,
                message="continue_run",
            ),
        )
        state = self._checkpoint(state, reason="milestone")

        if state.approval.owner_decision is not None:
            return self._continue_after_decision(state)

        return self._run_loop(state, self._service_nodes, post_approval=False)

    def retry_failed(self, run_id: str) -> WorkflowState:
        """Owner-initiated reopen of a terminal failed pre-approval LLM node.

        FR-019 M1.1: resume from the next incomplete spike node using the existing
        checkpoint (typically ``assess`` after successful ``analyse``). Does not
        touch the mailbox ledger or allocate a new run id.

        Eligible only when ``status=failed`` and the failed node is ``analyse`` or
        ``assess`` with required upstream artefacts present.
        """
        state = self._deps.store.load(run_id)

        if state.status != "failed":
            raise WorkflowResumeError(
                f"retry_failed requires status 'failed' "
                f"(run '{run_id}' has status={state.status})"
            )

        failed_node = (
            state.control.last_error.node_id
            if state.control.last_error is not None
            else state.control.current_node
        )
        if failed_node not in DEFAULT_RETRY_ELIGIBLE_NODES:
            raise WorkflowResumeError(
                f"retry_failed supports only analyse/assess failures "
                f"(run '{run_id}' failed_node={failed_node!r})"
            )

        if failed_node == "assess":
            if state.artefacts.job_analysis is None or state.artefacts.profile is None:
                raise WorkflowResumeError(
                    f"retry_failed assess requires job_analysis and profile "
                    f"on checkpoint '{run_id}'"
                )
        if failed_node == "analyse" and state.artefacts.posting is None:
            raise WorkflowResumeError(
                f"retry_failed analyse requires posting on checkpoint '{run_id}'"
            )

        stamp = utc_now()
        prior_message = (
            state.control.last_error.message
            if state.control.last_error is not None
            else "unknown failure"
        )
        state = clear_retry(state)
        state = replace_control(
            state,
            status="running",
            completed_at=None,
            last_error=None,
            updated_at=stamp,
            current_node=failed_node,
        )
        state = append_event(
            state,
            make_event(
                state,
                "run_resumed",
                timestamp=stamp,
                message=f"retry_failed from {failed_node}: {prior_message[:200]}",
            ),
        )
        state = self._checkpoint(state, reason="milestone")
        return self._run_loop(state, self._service_nodes, post_approval=False)

    def resume(self, run_id: str, decision: OwnerDecisionKind) -> WorkflowState:
        """Resume awaiting-owner or in-progress apply recovery with an owner decision."""
        state = self._deps.store.load(run_id)

        if state.status in TERMINAL_WORKFLOW_STATUSES:
            if state.approval.owner_decision == decision:
                return state
            raise WorkflowResumeError(
                f"Cannot resume terminal workflow '{run_id}' "
                f"(status={state.status}, decision={state.approval.owner_decision})"
            )

        # Mid-apply recovery: decision already accepted, side effects incomplete.
        if (
            state.status == "running"
            and state.approval.owner_decision is not None
            and state.approval.pending_kind is None
        ):
            if decision != state.approval.owner_decision:
                raise WorkflowResumeError(
                    f"Cannot change accepted owner decision "
                    f"({state.approval.owner_decision!r} → {decision!r})"
                )
            return self._continue_after_decision(state)

        # Pre-approval recoverable pause: do not accept apply/skip/defer here.
        if state.status == "running":
            raise WorkflowResumeError(
                f"Run '{run_id}' is running (e.g. retry recovery). "
                "Use continue_run(run_id) instead of resume with a decision."
            )

        if state.status != "awaiting_owner":
            raise WorkflowResumeError(
                f"Cannot resume run '{run_id}' unless status is awaiting_owner "
                f"or an in-progress apply recovery (status={state.status})"
            )

        if decision not in OWNER_DECISION_KINDS:
            raise WorkflowResumeError(
                f"Unsupported owner decision '{decision}'. "
                f"Allowed: {', '.join(OWNER_DECISION_KINDS)}"
            )

        if (
            state.approval.pending_kind is None
            or decision not in state.approval.pending_options
        ):
            raise WorkflowResumeError(
                f"Decision '{decision}' is not allowed for pending approval "
                f"(options={list(state.approval.pending_options)})"
            )

        stamp = utc_now()
        state = append_event(
            state,
            make_event(
                state,
                "approval_received",
                timestamp=stamp,
                decision=decision,
                approval_kind=state.approval.pending_kind,
            ),
        )
        state = append_event(
            state,
            make_event(state, "run_resumed", timestamp=stamp),
        )
        # Accept decision; remain running for skip/defer complete or apply side effects.
        state = WorkflowState.model_validate(
            state.model_copy(
                update={
                    "approval": state.approval.model_copy(
                        update={
                            "pending_kind": None,
                            "pending_options": [],
                            "pending_message": None,
                            "pending_requested_at": None,
                            "owner_decision": decision,
                            "decided_at": stamp,
                        }
                    ),
                    "control": state.control.model_copy(
                        update={
                            "status": "running",
                            "current_node": None,
                            "updated_at": stamp,
                            "last_error": None,
                        }
                    ),
                    "retry": None,
                }
            ).model_dump(mode="python")
        )
        state = self._checkpoint(state, reason="milestone")
        return self._continue_after_decision(state)

    def cancel(self, run_id: str) -> WorkflowState:
        """Cancel a non-terminal run."""
        state = self._deps.store.load(run_id)
        if state.status in TERMINAL_WORKFLOW_STATUSES:
            raise WorkflowResumeError(f"Cannot cancel terminal workflow '{run_id}'")
        stamp = utc_now()
        state = WorkflowState.model_validate(
            state.model_copy(
                update={
                    "approval": state.approval.model_copy(
                        update={
                            "pending_kind": None,
                            "pending_options": [],
                            "pending_message": None,
                            "pending_requested_at": None,
                        }
                    ),
                    "control": state.control.model_copy(
                        update={
                            "status": "cancelled",
                            "completed_at": stamp,
                            "updated_at": stamp,
                            "last_error": None,
                            "current_node": None,
                        }
                    ),
                }
            ).model_dump(mode="python")
        )
        state = append_event(state, make_event(state, "run_cancelled", timestamp=stamp))
        return self._checkpoint(state, reason="terminal")

    def _continue_after_decision(self, state: WorkflowState) -> WorkflowState:
        decision = state.approval.owner_decision
        if decision is None:
            raise WorkflowResumeError("Cannot continue without owner_decision")

        if decision not in OWNER_DECISION_KINDS:
            raise WorkflowResumeError(f"Unsupported post-approval decision: {decision}")

        # All three decisions are recorded against the pre-review Opportunity.
        state = self._run_loop(state, self._service_nodes, post_approval=True)
        if state.status == "running" and post_decision_complete(state):
            return self._complete(state, message=f"completed_with_decision:{decision}")
        return state

    def _complete(self, state: WorkflowState, *, message: str) -> WorkflowState:
        stamp = utc_now()
        state = clear_retry(state)
        state = replace_control(
            state,
            status="completed",
            completed_at=stamp,
            updated_at=stamp,
            current_node=None,
            last_error=None,
        )
        state = append_event(
            state,
            make_event(state, "run_completed", timestamp=stamp, message=message),
        )
        return self._checkpoint(state, reason="terminal")

    def _attempt_number(self, state: WorkflowState, node_id: str) -> int:
        if (
            state.retry is not None
            and state.retry.node_id == node_id
            and not state.retry.exhausted
        ):
            return state.retry.attempts_used + 1
        return 1

    def _run_loop(
        self,
        state: WorkflowState,
        nodes: dict[str, WorkflowNode],
        *,
        post_approval: bool,
    ) -> WorkflowState:
        while True:
            if state.status == "awaiting_owner":
                return state
            if state.status in TERMINAL_WORKFLOW_STATUSES:
                return state

            node_id = next_spike_node(state)
            if node_id is None:
                return state
            if node_id not in nodes:
                return self._fail(
                    state,
                    message=f"No node implementation registered for '{node_id}'",
                    node_id=node_id,
                )

            # Pre-allocate the opportunity id and checkpoint it before ``persist``
            # creates the record, so a crash cannot orphan an unknown Opportunity.
            if node_id == "persist" and state.artefacts.opportunity_id is None:
                state = replace_artefacts(
                    state, opportunity_id=allocate_opportunity_id()
                )
                state = self._checkpoint(state, reason="milestone")

            # Exhausted retry left on checkpoint — fail closed without re-executing.
            if (
                state.retry is not None
                and state.retry.exhausted
                and state.retry.node_id == node_id
            ):
                return self._fail(
                    state,
                    message=state.retry.last_message,
                    node_id=node_id,
                    recoverable=False,
                )

            node = nodes[node_id]
            started = utc_now()
            attempt = self._attempt_number(state, node_id)
            state = replace_control(
                state,
                current_node=node_id,
                updated_at=started,
                status="running",
                last_error=None,
            )
            state = append_event(
                state,
                make_event(
                    state,
                    "node_started",
                    timestamp=started,
                    node_id=node_id,
                    node_kind=node.spec.kind,
                    attempt=attempt,
                ),
            )
            # Durable cursor before side effects; checkpoint_written only after save.
            state = self._checkpoint(state, reason="milestone")

            t0 = perf_counter()
            try:
                outcome = node.execute(state)
            except WorkflowNodeError as error:
                duration_ms = int((perf_counter() - t0) * 1000)
                synthetic = NodeOutcome(
                    failure=NodeFailure(
                        message=str(error),
                        recoverable=error.recoverable,
                        detail=error.node_id,
                    )
                )
                state = self._apply_outcome(
                    state,
                    synthetic,
                    node_id=node_id,
                    node_kind=node.spec.kind,
                    duration_ms=duration_ms,
                    post_approval=post_approval,
                    attempt=attempt,
                )
            except Exception as error:  # noqa: BLE001 — unknown → fail closed
                duration_ms = int((perf_counter() - t0) * 1000)
                state = self._apply_outcome(
                    state,
                    NodeOutcome(
                        failure=NodeFailure(
                            message=f"Unexpected node exception: {error}",
                            recoverable=False,
                            detail=type(error).__name__,
                        )
                    ),
                    node_id=node_id,
                    node_kind=node.spec.kind,
                    duration_ms=duration_ms,
                    post_approval=post_approval,
                    attempt=attempt,
                )
            else:
                duration_ms = int((perf_counter() - t0) * 1000)
                state = self._apply_outcome(
                    state,
                    outcome,
                    node_id=node_id,
                    node_kind=node.spec.kind,
                    duration_ms=duration_ms,
                    post_approval=post_approval,
                    attempt=attempt,
                )

            if state.status == "failed":
                return state
            if state.status == "awaiting_owner":
                return state
            # Scheduled retry with yield (cross-process) or post-approval pause.
            if (
                state.status == "running"
                and state.control.last_error is not None
            ):
                return state

    def _apply_outcome(
        self,
        prior: WorkflowState,
        outcome: NodeOutcome,
        *,
        node_id: str,
        node_kind: str,
        duration_ms: int,
        post_approval: bool,
        attempt: int,
    ) -> WorkflowState:
        if outcome.failure is not None:
            failure = outcome.failure
            state = append_event(
                prior,
                make_event(
                    prior,
                    "node_failed",
                    node_id=node_id,
                    node_kind=node_kind,  # type: ignore[arg-type]
                    duration_ms=duration_ms,
                    recoverable=failure.recoverable,
                    message=failure.message,
                    attempt=attempt,
                ),
            )
            return self._handle_failure(
                state,
                failure=failure,
                node_id=node_id,
                node_kind=node_kind,
                attempt=attempt,
                post_approval=post_approval,
            )

        assert outcome.success is not None
        state = outcome.success.state
        if state.run_id != prior.run_id:
            return self._fail(
                prior,
                message="Node returned a different run_id",
                node_id=node_id,
            )

        finished = utc_now()
        # Successful execution clears active retry for this node.
        if prior.retry is not None and prior.retry.node_id == node_id:
            state = clear_retry(state)
        elif state.retry is not None and state.retry.node_id == node_id:
            state = clear_retry(state)

        state = append_event(
            state,
            make_event(
                state,
                "node_succeeded",
                timestamp=finished,
                node_id=node_id,
                node_kind=node_kind,  # type: ignore[arg-type]
                duration_ms=duration_ms,
                attempt=attempt,
            ),
        )

        if state.status == "awaiting_owner":
            state = append_event(
                state,
                make_event(
                    state,
                    "approval_requested",
                    timestamp=finished,
                    approval_kind=state.approval.pending_kind or "owner_review",
                    message=state.approval.pending_message,
                ),
            )
            return self._checkpoint(state, reason="approval")

        return self._checkpoint(state, reason="milestone")

    def _handle_failure(
        self,
        state: WorkflowState,
        *,
        failure: NodeFailure,
        node_id: str,
        node_kind: str | None,
        attempt: int,
        post_approval: bool,
    ) -> WorkflowState:
        recoverable = is_recoverable_failure(failure)
        classification = classification_from_flag(recoverable)
        policy = self._retry_policy

        # Side-effect nodes keep the FR-008 M2 resumable pause (no auto-retry
        # policy) so a storage failure never discards completed analysis work.
        if post_approval or node_id in SIDE_EFFECT_NODE_IDS:
            return self._fail(
                state,
                message=failure.message,
                node_id=node_id,
                node_kind=node_kind,
                detail=failure.detail,
                recoverable=recoverable,
                already_failed_event=True,
            )

        eligible = policy.is_eligible(node_id) and recoverable
        if eligible and attempt < policy.max_attempts:
            next_attempt = attempt + 1
            retry = RetryState(
                node_id=node_id,
                attempts_used=attempt,
                max_attempts=policy.max_attempts,
                last_classification=classification,
                last_message=failure.message,
                exhausted=False,
                next_action="retry_node",
            )
            state = replace_retry(state, retry)
            state = set_last_error(
                state,
                message=failure.message,
                recoverable=True,
                node_id=node_id,
                detail=failure.detail,
            )
            delay_note = (
                f"delay_ms={policy.delay_ms}" if policy.delay_ms else "delay_ms=0"
            )
            state = append_event(
                state,
                make_event(
                    state,
                    "retry_scheduled",
                    node_id=node_id,
                    node_kind=node_kind,  # type: ignore[arg-type]
                    attempt=next_attempt,
                    recoverable=True,
                    message=(
                        f"Retry scheduled for attempt {next_attempt}/"
                        f"{policy.max_attempts} ({delay_note})"
                    ),
                ),
            )
            state = replace_control(
                state,
                status="running",
                updated_at=utc_now(),
                current_node=node_id,
            )
            state = self._checkpoint(state, reason="failure")
            if policy.yield_after_retry_schedule:
                return state
            # Same-process: clear last_error so the loop continues the retry.
            return replace_control(state, last_error=None, updated_at=utc_now())

        if eligible and attempt >= policy.max_attempts:
            retry = RetryState(
                node_id=node_id,
                attempts_used=attempt,
                max_attempts=policy.max_attempts,
                last_classification=classification,
                last_message=failure.message,
                exhausted=True,
                next_action="fail_closed",
            )
            state = replace_retry(state, retry)
            state = append_event(
                state,
                make_event(
                    state,
                    "retry_exhausted",
                    node_id=node_id,
                    node_kind=node_kind,  # type: ignore[arg-type]
                    attempt=attempt,
                    recoverable=True,
                    message=(
                        f"Retry budget exhausted after {attempt}/"
                        f"{policy.max_attempts} attempts"
                    ),
                ),
            )
            return self._fail(
                state,
                message=failure.message,
                node_id=node_id,
                node_kind=node_kind,
                detail=failure.detail,
                recoverable=False,
                already_failed_event=True,
            )

        # Unrecoverable or ineligible node — fail closed, no retry.
        return self._fail(
            state,
            message=failure.message,
            node_id=node_id,
            node_kind=node_kind,
            detail=failure.detail,
            recoverable=False,
            already_failed_event=True,
        )

    def _fail(
        self,
        state: WorkflowState,
        *,
        message: str,
        node_id: str | None = None,
        node_kind: str | None = None,
        duration_ms: int | None = None,
        detail: str | None = None,
        recoverable: bool = False,
        already_failed_event: bool = False,
    ) -> WorkflowState:
        stamp = utc_now()
        if not already_failed_event and node_id is not None and duration_ms is not None:
            state = append_event(
                state,
                make_event(
                    state,
                    "node_failed",
                    timestamp=stamp,
                    node_id=node_id,
                    node_kind=node_kind,  # type: ignore[arg-type]
                    duration_ms=duration_ms,
                    recoverable=recoverable,
                    message=message,
                ),
            )
        state = set_last_error(
            state,
            message=message,
            recoverable=recoverable,
            node_id=node_id,
            detail=detail,
        )

        # Side-effect failures stay resumable (keep any decision + planned id).
        if node_id in SIDE_EFFECT_NODE_IDS:
            state = replace_control(
                state,
                status="running",
                updated_at=stamp,
                current_node=node_id,
            )
            return self._checkpoint(state, reason="failure")

        stamp = utc_now()
        state = WorkflowState.model_validate(
            state.model_copy(
                update={
                    "approval": state.approval.model_copy(
                        update={
                            "pending_kind": None,
                            "pending_options": [],
                            "pending_message": None,
                            "pending_requested_at": None,
                        }
                    ),
                    "control": state.control.model_copy(
                        update={
                            "status": "failed",
                            "completed_at": stamp,
                            "updated_at": stamp,
                            "current_node": node_id,
                        }
                    ),
                }
            ).model_dump(mode="python")
        )
        return self._checkpoint(state, reason="failure")

    def _checkpoint(
        self,
        state: WorkflowState,
        *,
        reason: str,
    ) -> WorkflowState:
        """Persist state; ``checkpoint_written`` is appended only for successful saves.

        Event is included in the payload that is saved, so a raised save error never
        leaves a durable ``checkpoint_written`` claim.
        """
        stamp = utc_now()
        with_event = append_event(
            state,
            make_event(
                state,
                "checkpoint_written",
                timestamp=stamp,
                checkpoint_reason=reason,  # type: ignore[arg-type]
            ),
        )
        return self._deps.store.save(with_event)


def describe_spike_graph() -> tuple[str, ...]:
    """Public inspectable full workflow sequence including post-decision nodes."""
    return SPIKE_NODE_SEQUENCE


def describe_pre_approval_graph() -> tuple[str, ...]:
    return PRE_APPROVAL_SEQUENCE


def describe_post_decision_graph() -> tuple[str, ...]:
    return POST_DECISION_SEQUENCE


def completed_spike_nodes(state: WorkflowState) -> list[str]:
    """Ordered completed workflow nodes present in state (public name retained)."""
    done = completed_node_ids(state)
    return [node_id for node_id in SPIKE_NODE_SEQUENCE if node_id in done]
