"""PipelineTrackingService — coordinated lifecycle writes (FR-013 M2).

Architecture (event-first dual write):

1. Validate completely before any persistence.
2. Append ``PipelineEvent`` first (immutable audit).
3. Project onto ``Opportunity`` current-state fields second.
4. On Opportunity failure after append: raise ``PipelinePartialWriteError``;
   retry with the same ``event_id`` is idempotent (skip append, re-project).
5. ``note`` / ``evidence_added`` are event-only (no Opportunity write).

SubmissionAttempt success never calls this service automatically (ADR-005).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from career_intelligence.opportunities import (
    Opportunity,
    OpportunityService,
    OpportunityStorageError,
    OpportunityTransitionError,
    OpportunityValidationError,
)
from career_intelligence.opportunities.models import (
    InterviewStage,
    OutcomeKind,
    PipelineStatus,
)

from .constants import ACTIVE_PIPELINE_STATUSES
from .errors import (
    PipelineConsistencyError,
    PipelineDivergenceError,
    PipelinePartialWriteError,
    PipelineValidationError,
    ErrorDetail,
)
from .ids import new_pipeline_event_id
from .json_store import JsonDirectoryPipelineEventStore
from .models import (
    PackageEvidenceRef,
    PipelineEvent,
    PipelineEvidence,
)
from .projection import fold_lifecycle_state, projection_from_event
from .reporting import (
    DEFAULT_PIPELINE_EXPORT_PATH,
    FollowUpItem,
    PipelineSummaryReport,
    build_summary_report,
    export_pipeline_csv,
)
from .store import PipelineEventStore
from .transitions import validate_event_contract

DEFAULT_PIPELINE_EVENTS_ROOT = (
    Path(__file__).resolve().parents[3] / "data" / "pipeline_events"
)

_STATUS_KINDS = frozenset({"status_transition", "correction"})


@dataclass(frozen=True)
class PipelineApplyResult:
    """Result of a coordinated apply (event ± Opportunity projection)."""

    event: PipelineEvent
    opportunity: Opportunity
    appended: bool
    opportunity_updated: bool


@dataclass(frozen=True)
class PipelineDivergenceReport:
    """Structured divergence between Opportunity and folded event history."""

    opportunity_id: str
    divergent: bool
    expected_status: PipelineStatus | None
    actual_status: PipelineStatus
    expected_outcome: OutcomeKind | None
    actual_outcome: OutcomeKind | None
    expected_interview_stage: InterviewStage | None
    actual_interview_stage: InterviewStage | None
    reasons: tuple[str, ...]


class PipelineTrackingService:
    """Sole coordinated writer for PipelineEvent + Opportunity lifecycle fields."""

    def __init__(
        self,
        *,
        opportunities: OpportunityService,
        events: PipelineEventStore,
    ) -> None:
        self._opportunities = opportunities
        self._events = events

    @classmethod
    def from_paths(
        cls,
        *,
        opportunities_root: Path,
        events_root: Path | None = None,
    ) -> PipelineTrackingService:
        return cls(
            opportunities=OpportunityService.from_path(opportunities_root),
            events=JsonDirectoryPipelineEventStore(
                events_root or (opportunities_root.parent / "pipeline_events")
            ),
        )

    # --- reads --------------------------------------------------------------

    def list_events(self, opportunity_id: str) -> list[PipelineEvent]:
        self._opportunities.get(opportunity_id)
        return self._events.list(opportunity_id=opportunity_id)

    def get_opportunity(self, opportunity_id: str) -> Opportunity:
        return self._opportunities.get(opportunity_id)

    def list_pipeline(
        self,
        *,
        active_only: bool = True,
        status: PipelineStatus | None = None,
    ) -> list[Opportunity]:
        """List opportunities for owner pipeline review.

        Default ``active_only`` shows preparing / submitted / interviewing / offer.
        Pass ``status`` to filter exactly, or ``active_only=False`` for all records.
        """
        items = self._opportunities.list_opportunities()
        if status is not None:
            return [item for item in items if item.status == status]
        if active_only:
            return [item for item in items if item.status in ACTIVE_PIPELINE_STATUSES]
        return list(items)

    def summary_report(
        self,
        *,
        as_of: datetime | None = None,
        reference_date: date | None = None,
    ) -> PipelineSummaryReport:
        """Derived owner report from Opportunities + append-only event history."""
        opportunities = self._opportunities.list_opportunities()
        events_by_opportunity = {
            item.opportunity_id: self._events.list(opportunity_id=item.opportunity_id)
            for item in opportunities
        }
        return build_summary_report(
            opportunities,
            events_by_opportunity=events_by_opportunity,
            as_of=as_of,
            reference_date=reference_date,
        )

    def follow_ups_due(
        self,
        *,
        reference_date: date | None = None,
    ) -> list[FollowUpItem]:
        """Follow-up reminders due on or before ``reference_date`` (tracking only)."""
        report = self.summary_report(reference_date=reference_date)
        return list(report.follow_ups_due)

    def export_csv(
        self,
        output_path: Path | None = None,
        *,
        active_only: bool = False,
    ) -> Path:
        """Owner-controlled CSV export for operational continuity."""
        opportunities = self.list_pipeline(active_only=active_only)
        events_by_opportunity = {
            item.opportunity_id: self._events.list(opportunity_id=item.opportunity_id)
            for item in opportunities
        }
        target = Path(output_path) if output_path is not None else DEFAULT_PIPELINE_EXPORT_PATH
        return export_pipeline_csv(
            opportunities,
            target,
            events_by_opportunity=events_by_opportunity,
        )

    def record_acknowledgement(
        self,
        opportunity_id: str,
        *,
        note: str | None = None,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        """Record employer acknowledgement without changing PipelineStatus."""
        opportunity = self._opportunities.get(opportunity_id)
        if opportunity.status not in {"submitted", "interviewing", "offer"}:
            raise PipelineConsistencyError(
                "Acknowledgement is recorded after the application is submitted "
                f"(current status: {opportunity.status})"
            )
        return self.add_evidence(
            opportunity_id,
            PipelineEvidence(note=note or "Acknowledgement received"),
            occurred_at=occurred_at,
            event_id=event_id,
            actor=actor,
        )

    def record_interview(
        self,
        opportunity_id: str,
        interview_stage: InterviewStage,
        *,
        note: str | None = None,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        """Move into interviewing or update interview stage (owner-natural)."""
        if event_id is not None and self._events.exists(event_id):
            return self.apply_stored_event(event_id)
        opportunity = self._opportunities.get(opportunity_id)
        evidence = PipelineEvidence(
            note=note or f"Interview stage: {interview_stage}"
        )
        if opportunity.status == "submitted":
            return self.advance_status(
                opportunity_id,
                "interviewing",
                evidence=evidence,
                occurred_at=occurred_at,
                interview_stage=interview_stage,
                event_id=event_id,
                actor=actor,
            )
        if opportunity.status == "interviewing":
            return self.change_interview_stage(
                opportunity_id,
                interview_stage,
                evidence=evidence,
                occurred_at=occurred_at,
                event_id=event_id,
                actor=actor,
            )
        raise PipelineConsistencyError(
            "Record submission before interviewing "
            f"(current status: {opportunity.status})"
        )

    def detect_divergence(self, opportunity_id: str) -> PipelineDivergenceReport:
        opportunity = self._opportunities.get(opportunity_id)
        folded = fold_lifecycle_state(self._events.list(opportunity_id=opportunity_id))
        reasons: list[str] = []

        actual_outcome = (
            opportunity.outcome.outcome if opportunity.outcome is not None else None
        )
        actual_stage = (
            opportunity.outcome.interview_stage
            if opportunity.outcome is not None
            else None
        )

        if folded.has_status_events and folded.status != opportunity.status:
            reasons.append(
                f"status: events imply {folded.status!r}, "
                f"opportunity has {opportunity.status!r}"
            )
        if folded.has_outcome_events and folded.outcome != actual_outcome:
            reasons.append(
                f"outcome: events imply {folded.outcome!r}, "
                f"opportunity has {actual_outcome!r}"
            )
        if folded.has_interview_events and folded.interview_stage != actual_stage:
            reasons.append(
                f"interview_stage: events imply {folded.interview_stage!r}, "
                f"opportunity has {actual_stage!r}"
            )

        return PipelineDivergenceReport(
            opportunity_id=opportunity_id,
            divergent=bool(reasons),
            expected_status=folded.status if folded.has_status_events else None,
            actual_status=opportunity.status,
            expected_outcome=folded.outcome if folded.has_outcome_events else None,
            actual_outcome=actual_outcome,
            expected_interview_stage=(
                folded.interview_stage if folded.has_interview_events else None
            ),
            actual_interview_stage=actual_stage,
            reasons=tuple(reasons),
        )

    def reconcile(self, opportunity_id: str) -> Opportunity:
        """Re-project Opportunity from durable event history (recovery)."""
        opportunity = self._opportunities.get(opportunity_id)
        events = self._events.list(opportunity_id=opportunity_id)
        folded = fold_lifecycle_state(events)
        if not any(
            (
                folded.has_status_events,
                folded.has_outcome_events,
                folded.has_interview_events,
                folded.has_follow_up_events,
            )
        ):
            return opportunity

        return self._opportunities.apply_pipeline_projection(
            opportunity_id,
            status=folded.status if folded.has_status_events else None,
            outcome=folded.outcome if folded.has_outcome_events else None,
            interview_stage=(
                folded.interview_stage if folded.has_interview_events else None
            ),
            follow_up_date=(
                folded.follow_up_date if folded.has_follow_up_events else None
            ),
            clear_follow_up_date=(
                folded.follow_up_cleared if folded.has_follow_up_events else False
            ),
            allow_terminal_reopen=True,
        )

    # --- coordinated write --------------------------------------------------

    def apply_stored_event(self, event_id: str) -> PipelineApplyResult:
        """Re-project a durable event onto Opportunity (idempotent recovery)."""
        durable = self._events.load(event_id)
        opportunity = self._opportunities.get(durable.opportunity_id)
        return self._project_after_event(
            durable,
            opportunity=opportunity,
            appended=False,
        )

    def apply_event(self, event: PipelineEvent) -> PipelineApplyResult:
        """Validate → append (if new) → project Opportunity.

        Idempotent recovery for a known ``event_id`` should prefer
        ``apply_stored_event`` (or owner helpers that detect an existing id).
        """
        opportunity = self._opportunities.get(event.opportunity_id)

        existing = self._events.exists(event.event_id)
        if existing:
            stored = self._events.load(event.event_id)
            if _event_business_payload(stored) != _event_business_payload(event):
                raise PipelineConsistencyError(
                    f"Pipeline event {event.event_id} already exists with different "
                    "payload; refusing to overwrite (append-only)"
                )
            return self._project_after_event(
                stored,
                opportunity=opportunity,
                appended=False,
            )

        validate_event_contract(event)
        self._assert_status_precondition(opportunity, event)
        durable = self._events.append(event)
        return self._project_after_event(
            durable,
            opportunity=opportunity,
            appended=True,
        )

    def _project_after_event(
        self,
        durable: PipelineEvent,
        *,
        opportunity: Opportunity,
        appended: bool,
    ) -> PipelineApplyResult:
        projection = projection_from_event(durable)
        if not projection.touches_opportunity:
            return PipelineApplyResult(
                event=durable,
                opportunity=opportunity,
                appended=appended,
                opportunity_updated=False,
            )

        try:
            updated = self._opportunities.apply_pipeline_projection(
                durable.opportunity_id,
                status=projection.status,
                outcome=projection.outcome,
                interview_stage=projection.interview_stage,
                follow_up_date=projection.follow_up_date,
                clear_follow_up_date=projection.clear_follow_up_date,
                notes=projection.notes,
                allow_terminal_reopen=projection.allow_terminal_reopen,
            )
        except (
            OpportunityStorageError,
            OpportunityValidationError,
            OpportunityTransitionError,
            OSError,
        ) as error:
            raise PipelinePartialWriteError(
                f"Pipeline event {durable.event_id} was appended but Opportunity "
                f"projection failed: {error}",
                event_id=durable.event_id,
                opportunity_id=durable.opportunity_id,
                phase="opportunity",
            ) from error

        return PipelineApplyResult(
            event=durable,
            opportunity=updated,
            appended=appended,
            opportunity_updated=True,
        )

    # --- owner operations ---------------------------------------------------

    def advance_status(
        self,
        opportunity_id: str,
        to_status: PipelineStatus,
        *,
        evidence: PipelineEvidence | None = None,
        occurred_at: datetime | None = None,
        outcome: OutcomeKind | None = None,
        interview_stage: InterviewStage | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        if event_id is not None and self._events.exists(event_id):
            return self.apply_stored_event(event_id)
        opportunity = self._opportunities.get(opportunity_id)
        now = datetime.now(UTC)
        event = PipelineEvent(
            event_id=event_id or new_pipeline_event_id(),
            opportunity_id=opportunity_id,
            occurred_at=occurred_at or now,
            recorded_at=now,
            kind="status_transition",
            from_status=opportunity.status,
            to_status=to_status,
            outcome=outcome,
            interview_stage=interview_stage,
            evidence=evidence or PipelineEvidence(),
            actor=actor,
        )
        return self.apply_event(event)

    def record_submitted(
        self,
        opportunity_id: str,
        *,
        evidence: PipelineEvidence,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        """Explicit owner action to mark submitted (never called by FR-012)."""
        return self.advance_status(
            opportunity_id,
            "submitted",
            evidence=evidence,
            occurred_at=occurred_at,
            outcome="pending",
            event_id=event_id,
            actor=actor,
        )

    def change_interview_stage(
        self,
        opportunity_id: str,
        interview_stage: InterviewStage,
        *,
        evidence: PipelineEvidence | None = None,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        if event_id is not None and self._events.exists(event_id):
            return self.apply_stored_event(event_id)
        now = datetime.now(UTC)
        event = PipelineEvent(
            event_id=event_id or new_pipeline_event_id(),
            opportunity_id=opportunity_id,
            occurred_at=occurred_at or now,
            recorded_at=now,
            kind="interview_stage_change",
            interview_stage=interview_stage,
            evidence=evidence or PipelineEvidence(note="interview stage update"),
            actor=actor,
        )
        return self.apply_event(event)

    def change_outcome(
        self,
        opportunity_id: str,
        outcome: OutcomeKind,
        *,
        evidence: PipelineEvidence | None = None,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        if event_id is not None and self._events.exists(event_id):
            return self.apply_stored_event(event_id)
        now = datetime.now(UTC)
        event = PipelineEvent(
            event_id=event_id or new_pipeline_event_id(),
            opportunity_id=opportunity_id,
            occurred_at=occurred_at or now,
            recorded_at=now,
            kind="outcome_change",
            outcome=outcome,
            evidence=evidence or PipelineEvidence(note="outcome update"),
            actor=actor,
        )
        return self.apply_event(event)

    def set_follow_up(
        self,
        opportunity_id: str,
        follow_up_date: date | None,
        *,
        clear: bool = False,
        evidence: PipelineEvidence | None = None,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        if event_id is not None and self._events.exists(event_id):
            return self.apply_stored_event(event_id)
        now = datetime.now(UTC)
        event = PipelineEvent(
            event_id=event_id or new_pipeline_event_id(),
            opportunity_id=opportunity_id,
            occurred_at=occurred_at or now,
            recorded_at=now,
            kind="follow_up_set",
            follow_up_date=None if clear else follow_up_date,
            clear_follow_up_date=clear,
            evidence=evidence or PipelineEvidence(),
            actor=actor,
        )
        return self.apply_event(event)

    def add_note(
        self,
        opportunity_id: str,
        note: str,
        *,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        if event_id is not None and self._events.exists(event_id):
            return self.apply_stored_event(event_id)
        now = datetime.now(UTC)
        event = PipelineEvent(
            event_id=event_id or new_pipeline_event_id(),
            opportunity_id=opportunity_id,
            occurred_at=occurred_at or now,
            recorded_at=now,
            kind="note",
            evidence=PipelineEvidence(note=note),
            actor=actor,
        )
        return self.apply_event(event)

    def add_evidence(
        self,
        opportunity_id: str,
        evidence: PipelineEvidence,
        *,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        if event_id is not None and self._events.exists(event_id):
            return self.apply_stored_event(event_id)
        now = datetime.now(UTC)
        event = PipelineEvent(
            event_id=event_id or new_pipeline_event_id(),
            opportunity_id=opportunity_id,
            occurred_at=occurred_at or now,
            recorded_at=now,
            kind="evidence_added",
            evidence=evidence,
            actor=actor,
        )
        return self.apply_event(event)

    def correct_status(
        self,
        opportunity_id: str,
        to_status: PipelineStatus,
        *,
        note: str,
        supersedes_event_id: str | None = None,
        outcome: OutcomeKind | None = None,
        interview_stage: InterviewStage | None = None,
        occurred_at: datetime | None = None,
        event_id: str | None = None,
        actor: str = "owner",
    ) -> PipelineApplyResult:
        if event_id is not None and self._events.exists(event_id):
            return self.apply_stored_event(event_id)
        opportunity = self._opportunities.get(opportunity_id)
        now = datetime.now(UTC)
        event = PipelineEvent(
            event_id=event_id or new_pipeline_event_id(),
            opportunity_id=opportunity_id,
            occurred_at=occurred_at or now,
            recorded_at=now,
            kind="correction",
            from_status=opportunity.status,
            to_status=to_status,
            outcome=outcome,
            interview_stage=interview_stage,
            evidence=PipelineEvidence(note=note),
            actor=actor,
            supersedes_event_id=supersedes_event_id,  # type: ignore[arg-type]
        )
        return self.apply_event(event)

    def require_consistent(self, opportunity_id: str) -> PipelineDivergenceReport:
        report = self.detect_divergence(opportunity_id)
        if report.divergent:
            raise PipelineDivergenceError(
                "Opportunity lifecycle diverges from pipeline event history: "
                + "; ".join(report.reasons),
                report=report,
            )
        return report

    def _assert_status_precondition(
        self,
        opportunity: Opportunity,
        event: PipelineEvent,
    ) -> None:
        if event.kind not in _STATUS_KINDS:
            return
        if event.from_status is None:
            raise PipelineValidationError(
                [
                    ErrorDetail(
                        loc=("from_status",),
                        msg="status-affecting events require from_status",
                        type="value_error",
                    )
                ]
            )
        if event.from_status != opportunity.status:
            raise PipelineConsistencyError(
                f"Event from_status {event.from_status!r} does not match "
                f"Opportunity.status {opportunity.status!r}; refusing write "
                "(validate before write / stale state)"
            )


# Re-export for callers that build submit evidence with package refs.
__all__ = [
    "DEFAULT_PIPELINE_EVENTS_ROOT",
    "PackageEvidenceRef",
    "PipelineApplyResult",
    "PipelineDivergenceReport",
    "PipelineTrackingService",
]


def _event_business_payload(event: PipelineEvent) -> dict[str, object]:
    """Compare events without ``recorded_at`` (system write clock on retries)."""
    payload = event.model_dump(mode="json")
    payload.pop("recorded_at", None)
    return payload
