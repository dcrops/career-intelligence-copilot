"""Application Preparation Orchestrator (FR-011 M0).

Coordinates existing services for package preparation. Does not extend the
FR-008 workflow runner, does not re-run analysis/assessment/strategy, and does
not move business rules out of ``ApplicationPackageService``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.application_package import (
    ApplicationPackageService,
)
from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterPlanOptions,
)
from career_intelligence.cv_generation import CvGenerationOptions, TailoringOptions
from career_intelligence.opportunities import (
    OpportunityNotFoundError,
    OpportunityService,
    OpportunityStorageError,
)

from .errors import PreparationRunNotFoundError
from .ids import new_preparation_run_id
from .json_store import JsonDirectoryPreparationRunStore
from .models import (
    CompletedStepRecord,
    PackageResultRef,
    PreparationErrorInfo,
    PreparationRunState,
    PreparationStepId,
)
from .store import PreparationRunStore

DEFAULT_PREPARATION_RUNS_ROOT = (
    Path(__file__).resolve().parents[3] / "data" / "preparation_runs"
)


class ApplicationPreparationOrchestrator:
    """Deterministic coordinator: validate preconditions → prepare package."""

    def __init__(
        self,
        opportunities: OpportunityService,
        packages: ApplicationPackageService,
        *,
        store: PreparationRunStore | None = None,
        runs_root: Path | None = None,
    ) -> None:
        self._opportunities = opportunities
        self._packages = packages
        if store is not None:
            self._store = store
        else:
            root = runs_root if runs_root is not None else DEFAULT_PREPARATION_RUNS_ROOT
            self._store = JsonDirectoryPreparationRunStore(root)

    def get(self, run_id: str) -> PreparationRunState:
        """Reload a preparation run by id."""
        return self._store.load(run_id)

    def exists(self, run_id: str) -> bool:
        return self._store.exists(run_id)

    def run(
        self,
        opportunity_id: str,
        *,
        tailoring_options: TailoringOptions | None = None,
        cv_options: CvGenerationOptions | None = None,
        cover_letter_plan_options: CoverLetterPlanOptions | None = None,
        cover_letter_options: CoverLetterGenerationOptions | None = None,
        prepared_at: datetime | None = None,
    ) -> PreparationRunState:
        """Execute the M0 preparation sequence for one Opportunity.

        Step order is fixed inline (no separate routing module):
        1. ``validate_preconditions`` — apply decision + load artefacts
        2. ``prepare_package`` — ``ApplicationPackageService.prepare``
        """
        now = datetime.now(UTC)
        state = PreparationRunState(
            run_id=new_preparation_run_id(),
            opportunity_id=opportunity_id,  # type: ignore[arg-type]
            status="running",
            created_at=now,
            updated_at=now,
        )
        self._store.save(state)

        try:
            self._validate_preconditions(opportunity_id)
        except (OpportunityNotFoundError, OpportunityStorageError, ValueError) as error:
            return self._fail(state, "validate_preconditions", error)

        state = self._complete_step(state, "validate_preconditions")

        try:
            manifest = self._packages.prepare(
                opportunity_id,
                tailoring_options=tailoring_options,
                cv_options=cv_options,
                cover_letter_plan_options=cover_letter_plan_options,
                cover_letter_options=cover_letter_options,
                prepared_at=prepared_at,
            )
        except Exception as error:
            # Package / FR-006 / FR-007 failures stay in those services; the
            # orchestrator records them and fails closed without inventing success.
            return self._fail(state, "prepare_package", error)

        stamp = datetime.now(UTC)
        state = state.model_copy(
            update={
                "status": "completed",
                "updated_at": stamp,
                "completed_steps": [
                    *state.completed_steps,
                    CompletedStepRecord(step_id="prepare_package", completed_at=stamp),
                ],
                "package": PackageResultRef(
                    opportunity_id=manifest.opportunity_id,
                    prepared_at=manifest.prepared_at,
                ),
                "error": None,
            }
        )
        return self._store.save(state)

    def _validate_preconditions(self, opportunity_id: str) -> None:
        opportunity = self._opportunities.get(opportunity_id)
        decision = opportunity.decision.decision if opportunity.decision else None
        if decision != "apply":
            raise ValueError(
                f"Opportunity {opportunity_id} is not eligible for preparation "
                f"(decision={decision!r}; require 'apply')"
            )
        # Confirms FR-002–FR-005 snapshots exist; does not re-run those services.
        self._opportunities.load_artifacts(opportunity_id)

    def _complete_step(
        self,
        state: PreparationRunState,
        step_id: PreparationStepId,
    ) -> PreparationRunState:
        stamp = datetime.now(UTC)
        updated = state.model_copy(
            update={
                "updated_at": stamp,
                "completed_steps": [
                    *state.completed_steps,
                    CompletedStepRecord(step_id=step_id, completed_at=stamp),
                ],
            }
        )
        return self._store.save(updated)

    def _fail(
        self,
        state: PreparationRunState,
        step_id: PreparationStepId,
        error: BaseException,
    ) -> PreparationRunState:
        stamp = datetime.now(UTC)
        failed = state.model_copy(
            update={
                "status": "failed",
                "updated_at": stamp,
                "error": PreparationErrorInfo(
                    step_id=step_id,
                    message=str(error),
                    error_type=type(error).__name__,
                ),
            }
        )
        return self._store.save(failed)


# Re-export for callers that only need the not-found type from this module.
__all__ = [
    "DEFAULT_PREPARATION_RUNS_ROOT",
    "ApplicationPreparationOrchestrator",
    "PreparationRunNotFoundError",
]
