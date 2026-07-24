"""Public service boundary for durable Opportunity persistence (M1–M2)."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis, JobPosting
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch

from .errors import ErrorDetail, OpportunityTransitionError, OpportunityValidationError
from .identity import build_identity
from .models import (
    OUTCOME_KINDS,
    OWNER_DECISION_KINDS,
    PIPELINE_STATUSES,
    InterviewStage,
    Opportunity,
    OutcomeKind,
    OutcomeRecord,
    OwnerDecisionKind,
    OwnerDecisionRecord,
    PipelineStatus,
    StrategySummary,
)
from .store import OpportunityStore
from .transitions import validate_status_transition
from .yaml_store import YamlDirectoryOpportunityStore

DEFAULT_OPPORTUNITIES_ROOT = (
    Path(__file__).resolve().parents[3] / "data" / "opportunities"
)


class OpportunityService:
    """Stable interface for creating, deciding, and updating opportunities."""

    def __init__(self, store: OpportunityStore | None = None) -> None:
        self._store = store or YamlDirectoryOpportunityStore(_configured_root())

    @classmethod
    def from_path(cls, root: Path) -> OpportunityService:
        """Compose the service for an explicit opportunities directory."""
        return cls(store=YamlDirectoryOpportunityStore(root))

    def get(self, opportunity_id: str) -> Opportunity:
        return self._store.get(opportunity_id)

    def list_opportunities(self) -> list[Opportunity]:
        return self._store.list_opportunities()

    def legacy_import_fingerprints(self) -> set[str]:
        """Return import fingerprints already present (M3 duplicate safety)."""
        return {
            item.legacy_import.import_fingerprint
            for item in self._store.list_opportunities()
            if item.legacy_import is not None
        }

    def create_from_legacy(self, opportunity: Opportunity) -> Opportunity:
        """Persist a legacy-imported opportunity without fabricating artifacts.

        Requires ``legacy_import`` provenance and empty ``artifact_paths``.
        ``strategy_summary`` must be None (no FR-003–FR-005 evidence).
        """
        if opportunity.legacy_import is None:
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("legacy_import",),
                        msg="create_from_legacy requires legacy_import provenance",
                        type="value_error",
                    )
                ]
            )
        if opportunity.artifact_paths:
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("artifact_paths",),
                        msg="legacy imports must not claim artifact snapshots",
                        type="value_error",
                    )
                ]
            )
        if opportunity.strategy_summary is not None:
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("strategy_summary",),
                        msg=(
                            "legacy imports must leave strategy_summary empty "
                            "(no fabricated FR-003–FR-005 summary)"
                        ),
                        type="value_error",
                    )
                ]
            )
        fingerprint = opportunity.legacy_import.import_fingerprint
        if fingerprint in self.legacy_import_fingerprints():
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("legacy_import", "import_fingerprint"),
                        msg=f"Legacy fingerprint already imported: {fingerprint}",
                        type="value_error",
                    )
                ]
            )
        return self._store.create_index_only(opportunity)

    def create_from_strategy(
        self,
        *,
        posting: JobPosting,
        job_analysis: JobAnalysis,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        strategy: ApplicationStrategy,
    ) -> Opportunity:
        """Persist a new opportunity from trusted FR-002–FR-005 artifacts.

        Does not call OpenAI, re-assess, change strategy fields, record owner
        decisions, or enforce duplicate detection.
        """
        now = datetime.now(UTC)
        identity = build_identity(posting, job_analysis=job_analysis, created_at=now)
        summary = StrategySummary(
            pursuit_posture=strategy.pursuit_posture,
            application_tier=strategy.application_tier,
            practical_value=strategy.practical_value,
            technical_fit=assessment.technical_fit.judgment,
            commercial_fit=assessment.commercial_fit.judgment,
            portfolio_fit=assessment.portfolio_fit.judgment,
        )
        try:
            opportunity = Opportunity(
                identity=identity,
                status="assessed",
                decision=None,
                outcome=None,
                strategy_summary=summary,
                artifact_paths={},
                updated_at=now,
            )
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

        return self._store.create(
            opportunity,
            posting=posting,
            job_analysis=job_analysis,
            assessment=assessment,
            portfolio_match=portfolio_match,
            strategy=strategy,
        )

    def record_decision(
        self,
        opportunity_id: str,
        decision: OwnerDecisionKind,
        *,
        notes: str | None = None,
    ) -> Opportunity:
        """Record the owner's apply / skip / defer decision.

        Does not change pipeline status or artifact snapshots. Status remains an
        independent field updated via ``update_outcome``.
        """
        if decision not in OWNER_DECISION_KINDS:
            allowed = ", ".join(OWNER_DECISION_KINDS)
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("decision",),
                        msg=f"Invalid decision '{decision}'. Choose from: {allowed}.",
                        type="value_error",
                    )
                ]
            )

        current = self._store.get(opportunity_id)
        now = datetime.now(UTC)
        try:
            record = OwnerDecisionRecord(
                decision=decision,
                decided_at=now,
                notes=notes,
            )
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

        updated = current.model_copy(
            update={"decision": record, "updated_at": now},
            deep=True,
        )
        return self._store.save(updated)

    def update_outcome(
        self,
        opportunity_id: str,
        *,
        status: PipelineStatus | None = None,
        outcome: OutcomeKind | None = None,
        interview_stage: InterviewStage | None = None,
        follow_up_date: date | None = None,
        notes: str | None = None,
        clear_follow_up_date: bool = False,
    ) -> Opportunity:
        """Update pipeline status and/or outcome details.

        ``status`` is operational state on the Opportunity. ``outcome`` is the
        historical result on OutcomeRecord. They are validated independently.
        Artifact snapshots are never modified.
        """
        if status is None and outcome is None and interview_stage is None and (
            notes is None and follow_up_date is None and not clear_follow_up_date
        ):
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=(),
                        msg=(
                            "Provide at least one of: status, outcome, "
                            "interview_stage, follow_up_date, notes."
                        ),
                        type="value_error",
                    )
                ]
            )

        if status is not None and status not in PIPELINE_STATUSES:
            allowed = ", ".join(PIPELINE_STATUSES)
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("status",),
                        msg=f"Invalid status '{status}'. Choose from: {allowed}.",
                        type="value_error",
                    )
                ]
            )
        if outcome is not None and outcome not in OUTCOME_KINDS:
            allowed = ", ".join(OUTCOME_KINDS)
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("outcome",),
                        msg=f"Invalid outcome '{outcome}'. Choose from: {allowed}.",
                        type="value_error",
                    )
                ]
            )

        current = self._store.get(opportunity_id)
        now = datetime.now(UTC)

        new_status = current.status
        if status is not None:
            try:
                validate_status_transition(current.status, status)
            except OpportunityTransitionError:
                raise
            new_status = status

        existing = current.outcome
        outcome_payload: dict[str, object] = {
            "outcome": existing.outcome if existing is not None else "pending",
            "interview_stage": (
                existing.interview_stage if existing is not None else "none"
            ),
            "follow_up_date": (
                existing.follow_up_date if existing is not None else None
            ),
            "notes": existing.notes if existing is not None else None,
            "updated_at": now,
        }
        if outcome is not None:
            outcome_payload["outcome"] = outcome
        if interview_stage is not None:
            outcome_payload["interview_stage"] = interview_stage
        if clear_follow_up_date:
            outcome_payload["follow_up_date"] = None
        elif follow_up_date is not None:
            outcome_payload["follow_up_date"] = follow_up_date
        if notes is not None:
            outcome_payload["notes"] = notes

        try:
            outcome_record = OutcomeRecord.model_validate(outcome_payload)
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

        updated = current.model_copy(
            update={
                "status": new_status,
                "outcome": outcome_record,
                "updated_at": now,
            },
            deep=True,
        )
        return self._store.save(updated)

    def backfill_identity_from_posting_artifacts(self) -> list[dict[str, object]]:
        """Fill missing identity title/company from trusted posting.json snapshots.

        Deterministic only — does not call OpenAI or re-analyse. Skips rows without
        a posting artifact or without grounded title/company in that artifact.
        Never overwrites identity fields that are already set.
        """
        import json

        results: list[dict[str, object]] = []
        for opportunity in self._store.list_opportunities():
            identity = opportunity.identity
            needs_title = identity.title is None
            needs_company = identity.company is None
            if not needs_title and not needs_company:
                results.append(
                    {
                        "opportunity_id": opportunity.opportunity_id,
                        "result": "skipped",
                        "reason": "identity already complete",
                    }
                )
                continue

            relative = opportunity.artifact_paths.get("posting.json")
            if not relative:
                results.append(
                    {
                        "opportunity_id": opportunity.opportunity_id,
                        "result": "skipped",
                        "reason": "no posting.json artifact",
                    }
                )
                continue

            path = self._store.resolve_artifact_path(relative)
            if not path.is_file():
                results.append(
                    {
                        "opportunity_id": opportunity.opportunity_id,
                        "result": "skipped",
                        "reason": f"missing artifact file: {relative}",
                    }
                )
                continue

            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                posting = JobPosting.model_validate(raw)
            except (OSError, ValueError, ValidationError) as error:
                results.append(
                    {
                        "opportunity_id": opportunity.opportunity_id,
                        "result": "failed",
                        "reason": f"could not load posting.json: {error}",
                    }
                )
                continue

            updates: dict[str, object] = {}
            if needs_title and posting.title is not None:
                updates["title"] = posting.title
            if needs_company and posting.company is not None:
                updates["company"] = posting.company

            if not updates:
                results.append(
                    {
                        "opportunity_id": opportunity.opportunity_id,
                        "result": "skipped",
                        "reason": "posting.json also lacks title/company",
                    }
                )
                continue

            now = datetime.now(UTC)
            new_identity = identity.model_copy(update=updates)
            updated = opportunity.model_copy(
                update={"identity": new_identity, "updated_at": now},
                deep=True,
            )
            self._store.save(updated)
            results.append(
                {
                    "opportunity_id": opportunity.opportunity_id,
                    "result": "updated",
                    "reason": f"filled from posting.json: {', '.join(sorted(updates))}",
                    "title": new_identity.title,
                    "company": new_identity.company,
                }
            )
        return results


def _configured_root() -> Path:
    configured = os.getenv("CIC_OPPORTUNITIES_DIR")
    return Path(configured) if configured else DEFAULT_OPPORTUNITIES_ROOT
