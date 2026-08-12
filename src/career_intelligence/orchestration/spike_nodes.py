"""FR-008 workflow nodes — acquisition, validation, and FR-002–005 service wrappers."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from career_intelligence.application_strategy import (
    ApplicationStrategyService,
    SearchOperatingContext,
)
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.opportunity_assessment import (
    OpportunityAssessmentService,
    OpportunityAssessmentValidationError,
    assessment_validation_is_retryable,
)
from career_intelligence.portfolio_matching import PortfolioMatchingService

from .acquisition import AcquisitionAdapter, AcquisitionError, AcquisitionResult
from .models import AcquisitionEnvelope, WorkflowState
from .nodes import NodeFailure, NodeOutcome, NodeSpec, NodeSuccess
from .retry import classify_exception
from .routing import assert_node_is_next
from .state_helpers import (
    mark_node_completed,
    replace_acquisition,
    replace_artefacts,
    replace_control,
    utc_now,
)


@dataclass(frozen=True)
class PasteJobInput:
    """Caller-supplied paste/manual job text (also accepted by ``runner.start``)."""

    raw_text: str
    title: str | None = None
    company: str | None = None
    source_url: str | None = None


def _success(state: WorkflowState) -> NodeOutcome:
    return NodeOutcome(success=NodeSuccess(state=state))


def _failure(message: str, *, recoverable: bool = False, detail: str | None = None) -> NodeOutcome:
    return NodeOutcome(
        failure=NodeFailure(message=message, recoverable=recoverable, detail=detail)
    )


def _mechanical_normalise(text: str) -> str:
    """Collapse trailing spaces and normalise newlines without semantic edits."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    # Strip leading/trailing blank lines only.
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


class AcquireNode:
    """Deterministic acquire node — applies any ``AcquisitionAdapter`` result.

    The runner does not branch on source kind; provenance lives on the envelope.
    """

    def __init__(self, adapter: AcquisitionAdapter) -> None:
        self._adapter = adapter
        self._spec = NodeSpec(
            node_id="acquire",
            display_name="Job acquisition",
            kind="deterministic",
            description="Acquire a job via a source adapter and record provenance",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))

        try:
            result: AcquisitionResult = self._adapter.acquire()
        except AcquisitionError as error:
            return _failure(str(error), detail=error.detail)
        except Exception as error:  # noqa: BLE001 — fail closed at trust boundary
            return _failure(
                f"Acquisition adapter failed: {error}",
                detail=type(error).__name__,
            )

        acquired_at = result.acquired_at or utc_now()
        envelope = AcquisitionEnvelope(
            source_kind=result.source_kind,
            source_identifier=result.source_identifier,
            source_url=result.source_url,
            acquired_at=acquired_at,
            raw_content=result.raw_content,
            normalised_content=None,
            warnings=list(result.warnings),
            title=result.title,
            company=result.company,
        )

        updated = replace_acquisition(state, envelope)
        updated = replace_artefacts(updated, posting=result.posting)
        updated = replace_control(
            updated,
            current_node=self.spec.node_id,
            updated_at=acquired_at,
        )
        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=acquired_at
        )
        return _success(updated)


# Backward-compatible wrapper: accepts PasteJobInput, delegates to paste adapter.
class PasteAcquireNode(AcquireNode):
    """Deprecated entry point — prefer ``AcquireNode(PasteAcquisitionAdapter(...))``."""

    def __init__(self, job: PasteJobInput) -> None:
        from .adapters import PasteAcquisitionAdapter

        super().__init__(PasteAcquisitionAdapter(job))


class ValidateNormaliseNode:
    """Narrow deterministic validation / mechanical normalisation."""

    def __init__(self) -> None:
        self._spec = NodeSpec(
            node_id="validate_normalise",
            display_name="Validate and normalise",
            kind="deterministic",
            description="Mechanical validation of acquisition + JobPosting",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))

        if state.acquisition is None:
            return _failure("validate_normalise requires acquisition envelope")
        if state.artefacts.posting is None:
            return _failure("validate_normalise requires JobPosting")

        warnings = list(state.acquisition.warnings)
        normalised = _mechanical_normalise(state.acquisition.raw_content)
        if not normalised:
            return _failure("Job content is empty after normalisation")

        if normalised != state.acquisition.raw_content:
            warnings.append("Applied mechanical whitespace/newline normalisation")

        if state.acquisition.title and state.artefacts.posting.title != state.acquisition.title:
            return _failure("JobPosting.title does not match acquisition provenance title")
        if (
            state.acquisition.company
            and state.artefacts.posting.company != state.acquisition.company
        ):
            return _failure("JobPosting.company does not match acquisition provenance company")

        try:
            posting = state.artefacts.posting.model_copy(update={"raw_text": normalised})
            envelope = state.acquisition.model_copy(
                update={
                    "normalised_content": normalised,
                    "warnings": warnings,
                }
            )
        except ValidationError as error:
            return _failure("Normalisation produced invalid acquisition/posting", detail=str(error))

        stamp = utc_now()
        updated = replace_acquisition(state, envelope)
        updated = replace_artefacts(updated, posting=posting)
        updated = replace_control(updated, current_node=self.spec.node_id, updated_at=stamp)
        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=stamp
        )
        return _success(updated)


class AnalyseNode:
    def __init__(self, service: JobAnalysisService) -> None:
        self._service = service
        self._spec = NodeSpec(
            node_id="analyse",
            display_name="Job Analysis",
            kind="llm_backed",
            description="FR-002 JobAnalysisService",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))
        if state.artefacts.posting is None:
            return _failure("analyse requires JobPosting")
        try:
            analysis = self._service.analyse(state.artefacts.posting)
        except Exception as error:  # noqa: BLE001 — map to node failure; runner fail-closes
            classification = classify_exception(error)
            return _failure(
                f"Job analysis failed: {error}",
                recoverable=classification == "recoverable",
                detail=type(error).__name__,
            )
        stamp = utc_now()
        updated = replace_artefacts(
            state,
            posting=analysis.posting,
            job_analysis=analysis,
        )
        updated = replace_control(updated, current_node=self.spec.node_id, updated_at=stamp)
        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=stamp
        )
        return _success(updated)


class AssessNode:
    def __init__(self, service: OpportunityAssessmentService) -> None:
        self._service = service
        self._spec = NodeSpec(
            node_id="assess",
            display_name="Opportunity Assessment",
            kind="llm_backed",
            description="FR-003 OpportunityAssessmentService",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))
        if state.artefacts.job_analysis is None or state.artefacts.profile is None:
            return _failure("assess requires JobAnalysis and CareerProfile")
        try:
            assessment = self._service.assess(
                state.artefacts.job_analysis,
                state.artefacts.profile,
            )
        except OpportunityAssessmentValidationError as error:
            # FR-019 M1.1: only approved stochastic generated-output codes retry.
            recoverable = assessment_validation_is_retryable(error)
            return _failure(
                f"Opportunity assessment failed: {error}",
                recoverable=recoverable,
                detail=type(error).__name__,
            )
        except Exception as error:  # noqa: BLE001
            classification = classify_exception(error)
            return _failure(
                f"Opportunity assessment failed: {error}",
                recoverable=classification == "recoverable",
                detail=type(error).__name__,
            )
        stamp = utc_now()
        updated = replace_artefacts(state, assessment=assessment)
        updated = replace_control(updated, current_node=self.spec.node_id, updated_at=stamp)
        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=stamp
        )
        return _success(updated)


class MatchNode:
    def __init__(self, service: PortfolioMatchingService) -> None:
        self._service = service
        self._spec = NodeSpec(
            node_id="match",
            display_name="Portfolio Matching",
            kind="deterministic",
            description="FR-004 PortfolioMatchingService",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))
        if state.artefacts.job_analysis is None or state.artefacts.profile is None:
            return _failure("match requires JobAnalysis and CareerProfile")
        try:
            portfolio_match = self._service.match(
                state.artefacts.job_analysis,
                state.artefacts.profile,
            )
        except Exception as error:  # noqa: BLE001
            return _failure(
                f"Portfolio matching failed: {error}",
                recoverable=False,
                detail=type(error).__name__,
            )
        stamp = utc_now()
        updated = replace_artefacts(state, portfolio_match=portfolio_match)
        updated = replace_control(updated, current_node=self.spec.node_id, updated_at=stamp)
        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=stamp
        )
        return _success(updated)


class StrategyNode:
    def __init__(
        self,
        service: ApplicationStrategyService,
        *,
        operating_context: SearchOperatingContext | None = None,
    ) -> None:
        self._service = service
        self._context = operating_context or SearchOperatingContext()
        self._spec = NodeSpec(
            node_id="strategy",
            display_name="Application Strategy",
            kind="deterministic",
            description="FR-005 ApplicationStrategyService",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))
        assessment = state.artefacts.assessment
        portfolio_match = state.artefacts.portfolio_match
        profile = state.artefacts.profile
        if assessment is None or portfolio_match is None or profile is None:
            return _failure("strategy requires assessment, portfolio_match, and profile")
        try:
            strategy = self._service.plan(
                assessment,
                portfolio_match,
                profile,
                operating_context=self._context,
            )
        except Exception as error:  # noqa: BLE001
            return _failure(
                f"Application strategy failed: {error}",
                recoverable=False,
                detail=type(error).__name__,
            )
        stamp = utc_now()
        updated = replace_artefacts(state, strategy=strategy)
        updated = replace_control(updated, current_node=self.spec.node_id, updated_at=stamp)
        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=stamp
        )
        return _success(updated)


class OwnerReviewNode:
    """Interrupt node — sets awaiting_owner; does not choose a decision."""

    def __init__(self) -> None:
        self._spec = NodeSpec(
            node_id="owner_review",
            display_name="Owner review interrupt",
            kind="deterministic",
            description="Mandatory owner decision on the persisted Opportunity",
        )

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    def execute(self, state: WorkflowState) -> NodeOutcome:
        try:
            assert_node_is_next(state, self.spec.node_id)
        except ValueError as error:
            return _failure(str(error))
        if state.artefacts.strategy is None:
            return _failure("owner_review requires ApplicationStrategy")
        if state.artefacts.opportunity_id is None:
            return _failure(
                "owner_review requires a persisted Opportunity (FR-009 M1): "
                "the interrupt must not be reached before the durable record exists"
            )

        stamp = utc_now()
        try:
            updated = WorkflowState.model_validate(
                state.model_copy(
                    update={
                        "approval": state.approval.model_copy(
                            update={
                                "pending_kind": "owner_review",
                                "pending_options": ["apply", "skip", "defer"],
                                "pending_message": (
                                    "Review application strategy before continuing. "
                                    "The Opportunity is already persisted; apply, skip, "
                                    "and defer each record the decision against that "
                                    "same durable record."
                                ),
                                "pending_requested_at": stamp,
                                "owner_decision": None,
                                "decided_at": None,
                            }
                        ),
                        "control": state.control.model_copy(
                            update={
                                "status": "awaiting_owner",
                                "current_node": self.spec.node_id,
                                "updated_at": stamp,
                                "last_error": None,
                            }
                        ),
                    }
                ).model_dump(mode="python")
            )
        except Exception as error:  # noqa: BLE001
            return _failure(f"Failed to enter owner-review interrupt: {error}")

        updated = mark_node_completed(
            updated, node_id=self.spec.node_id, kind=self.spec.kind, completed_at=stamp
        )
        return _success(updated)


# Transient classification lives in retry.classify_exception (M3).
