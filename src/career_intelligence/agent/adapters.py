"""Thin service adapters for BOPA actions (FR-015 M2).

Adapters call existing public CIC services only. No filesystem/shell/submit/
pipeline/discovery/truth-waiver authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.application_preparation import ApplicationPreparationOrchestrator
from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterPlanOptions,
)
from career_intelligence.cv_generation import CvGenerationOptions, TailoringOptions
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation.gates import evaluate_package_truth
from career_intelligence.truth_validation.store import JsonDirectoryTruthReportStore

from .errors import AdapterExecutionError
from .models import ReadinessSnapshot
from .types import AgentAction


@dataclass(frozen=True)
class AdapterResult:
    summary: str
    result_ref: str | None = None
    skipped_as_idempotent: bool = False
    mutates_domain: bool = False


class AgentActionExecutor(Protocol):
    def execute(
        self,
        action: AgentAction,
        snapshot: ReadinessSnapshot,
        *,
        completed_actions: frozenset[AgentAction],
    ) -> AdapterResult: ...


class ServiceActionExecutor:
    """Default executor over preparation / package / truth public APIs."""

    def __init__(
        self,
        *,
        preparation: ApplicationPreparationOrchestrator | None = None,
        packages: ApplicationPackageService | None = None,
        profile: CareerProfile | None = None,
        truth_store: JsonDirectoryTruthReportStore | None = None,
        tailoring_options: TailoringOptions | None = None,
        cv_options: CvGenerationOptions | None = None,
        cover_letter_plan_options: CoverLetterPlanOptions | None = None,
        cover_letter_options: CoverLetterGenerationOptions | None = None,
    ) -> None:
        self._preparation = preparation
        self._packages = packages
        self._profile = profile
        self._truth_store = truth_store
        self._tailoring_options = tailoring_options
        self._cv_options = cv_options
        self._cover_letter_plan_options = cover_letter_plan_options
        self._cover_letter_options = cover_letter_options

    def execute(
        self,
        action: AgentAction,
        snapshot: ReadinessSnapshot,
        *,
        completed_actions: frozenset[AgentAction],
    ) -> AdapterResult:
        if action == "inspect_readiness":
            return AdapterResult(
                summary=(
                    f"inspected readiness primary hints: decision={snapshot.decision} "
                    f"package={snapshot.package.status} truth={snapshot.truth.status}"
                ),
                mutates_domain=False,
            )
        if action == "request_owner_review":
            return AdapterResult(
                summary="owner review requested; agent will stop",
                mutates_domain=False,
            )
        if action == "stop":
            return AdapterResult(summary="stop acknowledged", mutates_domain=False)
        if action == "verify_package":
            return self._verify(snapshot)
        if action == "run_preparation":
            return self._prepare(snapshot, completed_actions=completed_actions)
        if action == "validate_truth_package":
            return self._validate_truth(snapshot, completed_actions=completed_actions)
        raise AdapterExecutionError(f"unsupported action for executor: {action!r}")

    def _verify(self, snapshot: ReadinessSnapshot) -> AdapterResult:
        if self._packages is None:
            raise AdapterExecutionError("package service not configured")
        try:
            manifest = self._packages.get(snapshot.opportunity_id, verify=True)
        except Exception as error:  # noqa: BLE001
            raise AdapterExecutionError(f"verify_package failed: {error}") from error
        return AdapterResult(
            summary="package artefacts verified",
            result_ref=f"package:{manifest.opportunity_id}",
            mutates_domain=False,
        )

    def _prepare(
        self,
        snapshot: ReadinessSnapshot,
        *,
        completed_actions: frozenset[AgentAction],
    ) -> AdapterResult:
        # Idempotency: do not re-prepare when package already present and current.
        if snapshot.package.status == "present" and "run_preparation" in completed_actions:
            return AdapterResult(
                summary="run_preparation skipped — package already present in this run",
                result_ref=snapshot.package.manifest_ref,
                skipped_as_idempotent=True,
                mutates_domain=False,
            )
        if snapshot.package.status == "present":
            return AdapterResult(
                summary="run_preparation skipped — package already present on SoT",
                result_ref=snapshot.package.manifest_ref,
                skipped_as_idempotent=True,
                mutates_domain=False,
            )
        if self._preparation is None:
            raise AdapterExecutionError("preparation orchestrator not configured")
        if not snapshot.owner_approvals_present:
            raise AdapterExecutionError("owner approvals required for preparation")
        try:
            state = self._preparation.run(
                snapshot.opportunity_id,
                tailoring_options=self._tailoring_options
                or TailoringOptions(owner_approved_to_tailor=True),
                cv_options=self._cv_options
                or CvGenerationOptions(tailoring_plan_approved=True),
                cover_letter_plan_options=self._cover_letter_plan_options
                or CoverLetterPlanOptions(owner_approved_to_plan=True),
                cover_letter_options=self._cover_letter_options
                or CoverLetterGenerationOptions(cover_letter_plan_approved=True),
                prepared_at=datetime.now(tz=UTC),
            )
        except Exception as error:  # noqa: BLE001
            raise AdapterExecutionError(f"run_preparation failed: {error}") from error
        if state.status != "completed":
            raise AdapterExecutionError(
                f"preparation run {state.run_id} ended as {state.status}: "
                f"{getattr(state.error, 'message', state.error)}"
            )
        return AdapterResult(
            summary=f"preparation completed ({state.run_id})",
            result_ref=state.run_id,
            mutates_domain=True,
        )

    def _validate_truth(
        self,
        snapshot: ReadinessSnapshot,
        *,
        completed_actions: frozenset[AgentAction],
    ) -> AdapterResult:
        if (
            snapshot.truth.status == "pass"
            and not snapshot.truth.owner_edited_markdown_since_validation
            and "validate_truth_package" in completed_actions
        ):
            return AdapterResult(
                summary="validate_truth_package skipped — already PASS in this run",
                result_ref=snapshot.truth.report_ref,
                skipped_as_idempotent=True,
                mutates_domain=False,
            )
        if self._packages is None or self._profile is None:
            raise AdapterExecutionError("package service and profile required for truth")
        try:
            manifest = self._packages.get(snapshot.opportunity_id, verify=True)
            status = evaluate_package_truth(
                manifest=manifest,
                profile=self._profile,
                store=self._truth_store,
                revalidate=True,
            )
        except Exception as error:  # noqa: BLE001
            raise AdapterExecutionError(f"validate_truth_package failed: {error}") from error
        refs = ",".join(
            doc.report_id for doc in status.documents if doc.report_id is not None
        )
        allowed = "ALLOWED" if status.external_use_allowed else "BLOCKED"
        return AdapterResult(
            summary=f"truth package evaluation {allowed}",
            result_ref=refs or None,
            mutates_domain=True,  # may persist new TruthReports
        )


class ScriptedActionExecutor:
    """Test double: returns scripted results per action call count."""

    def __init__(self, results: dict[AgentAction, list[AdapterResult]] | None = None) -> None:
        self._results = results or {}
        self._calls: dict[AgentAction, int] = {}
        self.calls: list[tuple[AgentAction, bool]] = []

    def execute(
        self,
        action: AgentAction,
        snapshot: ReadinessSnapshot,
        *,
        completed_actions: frozenset[AgentAction],
    ) -> AdapterResult:
        # Honour idempotency the same way as production for prep/truth.
        if action == "run_preparation" and (
            snapshot.package.status == "present" or action in completed_actions
        ):
            result = AdapterResult(
                summary="scripted skip prepare",
                skipped_as_idempotent=True,
                mutates_domain=False,
            )
            self.calls.append((action, True))
            return result
        if action == "validate_truth_package" and (
            snapshot.truth.status == "pass"
            and not snapshot.truth.owner_edited_markdown_since_validation
            and action in completed_actions
        ):
            result = AdapterResult(
                summary="scripted skip truth",
                skipped_as_idempotent=True,
                mutates_domain=False,
            )
            self.calls.append((action, True))
            return result

        idx = self._calls.get(action, 0)
        self._calls[action] = idx + 1
        scripted = self._results.get(action, [])
        if idx < len(scripted):
            result = scripted[idx]
        else:
            result = AdapterResult(summary=f"scripted {action}", mutates_domain=False)
        self.calls.append((action, result.skipped_as_idempotent))
        return result
