"""FR-008 M2 side-effect nodes: persist Opportunity + record decision."""

from __future__ import annotations

from career_intelligence.opportunities import (
    OpportunityNotFoundError,
    OpportunityService,
    new_opportunity_id,
)

from .decision_boundary import to_opportunity_decision
from .nodes import NodeFailure, NodeOutcome, NodeSpec, NodeSuccess
from .routing import assert_node_is_next
from .state_helpers import (
    mark_node_completed,
    replace_artefacts,
    replace_control,
    utc_now,
)
from .models import WorkflowState


def _success(state: WorkflowState) -> NodeOutcome:
    return NodeOutcome(success=NodeSuccess(state=state))


def _failure(message: str, *, recoverable: bool = False, detail: str | None = None) -> NodeOutcome:
    return NodeOutcome(
        failure=NodeFailure(message=message, recoverable=recoverable, detail=detail)
    )


class PersistOpportunityNode:
    """Thin wrapper around ``OpportunityService.create_from_strategy``."""

    def __init__(self, service: OpportunityService) -> None:
        self._service = service
        self._spec = NodeSpec(
            node_id="persist",
            display_name="Persist Opportunity",
            kind="deterministic",
            description="ADR-002 OpportunityService.create_from_strategy",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))

        if state.approval.owner_decision != "apply":
            return _failure("persist requires owner_decision='apply'")

        artefacts = state.artefacts
        if (
            artefacts.posting is None
            or artefacts.job_analysis is None
            or artefacts.assessment is None
            or artefacts.portfolio_match is None
            or artefacts.strategy is None
        ):
            return _failure("persist requires posting + FR-002–FR-005 artefacts")

        planned_id = artefacts.opportunity_id
        if planned_id is None:
            return _failure(
                "persist requires a pre-allocated opportunity_id "
                "(runner must checkpoint the planned id before create)"
            )

        try:
            opportunity = self._service.create_from_strategy(
                posting=artefacts.posting,
                job_analysis=artefacts.job_analysis,
                assessment=artefacts.assessment,
                portfolio_match=artefacts.portfolio_match,
                strategy=artefacts.strategy,
                opportunity_id=planned_id,
            )
        except Exception as error:  # noqa: BLE001
            return _failure(
                f"Opportunity persistence failed: {error}",
                recoverable=True,
                detail=type(error).__name__,
            )

        if opportunity.opportunity_id != planned_id:
            return _failure(
                "create_from_strategy returned a different opportunity_id than planned"
            )

        stamp = utc_now()
        updated = replace_artefacts(state, opportunity_id=opportunity.opportunity_id)
        updated = replace_control(updated, current_node=self.spec.node_id, updated_at=stamp)
        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=stamp
        )
        return _success(updated)


class RecordDecisionNode:
    """Thin wrapper around ``OpportunityService.record_decision``."""

    def __init__(self, service: OpportunityService) -> None:
        self._service = service
        self._spec = NodeSpec(
            node_id="record_decision",
            display_name="Record owner decision",
            kind="deterministic",
            description="ADR-002 OpportunityService.record_decision",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))

        if state.approval.owner_decision is None:
            return _failure("record_decision requires approval.owner_decision")
        if state.artefacts.opportunity_id is None:
            return _failure("record_decision requires artefacts.opportunity_id")

        opportunity_id = state.artefacts.opportunity_id
        workflow_decision = state.approval.owner_decision
        opportunity_decision = to_opportunity_decision(workflow_decision)

        try:
            current = self._service.get(opportunity_id)
        except OpportunityNotFoundError as error:
            return _failure(
                f"Opportunity not found for decision recording: {opportunity_id}",
                recoverable=True,
                detail=type(error).__name__,
            )

        if current.decision is not None:
            if current.decision.decision == opportunity_decision:
                stamp = utc_now()
                updated = replace_control(
                    state, current_node=self.spec.node_id, updated_at=stamp
                )
                updated = mark_node_completed(
                    updated,
                    node_id=self.spec.node_id,
                    kind=self.spec.kind,
                    completed_at=stamp,
                )
                return _success(updated)
            return _failure(
                "Opportunity already has a conflicting owner decision "
                f"({current.decision.decision!r} != {opportunity_decision!r})"
            )

        try:
            self._service.record_decision(
                opportunity_id,
                opportunity_decision,
                notes=f"workflow_run_id={state.run_id}",
            )
        except Exception as error:  # noqa: BLE001
            return _failure(
                f"Opportunity decision recording failed: {error}",
                recoverable=True,
                detail=type(error).__name__,
            )

        stamp = utc_now()
        updated = replace_control(state, current_node=self.spec.node_id, updated_at=stamp)
        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=stamp
        )
        return _success(updated)


def allocate_opportunity_id() -> str:
    """Allocate a permanent opportunity id for pre-create checkpointing."""
    return new_opportunity_id()
