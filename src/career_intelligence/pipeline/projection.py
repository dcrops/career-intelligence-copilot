"""Project PipelineEvents onto Opportunity lifecycle fields (FR-013 M2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from career_intelligence.opportunities.models import (
    InterviewStage,
    OutcomeKind,
    PipelineStatus,
)

from .models import PipelineEvent


@dataclass(frozen=True)
class LifecycleProjection:
    """Field deltas to apply to Opportunity after an event is durable."""

    status: PipelineStatus | None = None
    outcome: OutcomeKind | None = None
    interview_stage: InterviewStage | None = None
    follow_up_date: date | None = None
    clear_follow_up_date: bool = False
    notes: str | None = None
    allow_terminal_reopen: bool = False

    @property
    def touches_opportunity(self) -> bool:
        return any(
            (
                self.status is not None,
                self.outcome is not None,
                self.interview_stage is not None,
                self.follow_up_date is not None,
                self.clear_follow_up_date,
                self.notes is not None,
            )
        )


def projection_from_event(event: PipelineEvent) -> LifecycleProjection:
    """Derive Opportunity field updates for one event."""
    if event.kind in {"note", "evidence_added"}:
        return LifecycleProjection()

    if event.kind == "status_transition":
        return LifecycleProjection(
            status=event.to_status,
            outcome=event.outcome,
            interview_stage=event.interview_stage,
            follow_up_date=event.follow_up_date,
            clear_follow_up_date=event.clear_follow_up_date,
            notes=event.evidence.note,
            allow_terminal_reopen=False,
        )

    if event.kind == "correction":
        return LifecycleProjection(
            status=event.to_status,
            outcome=event.outcome,
            interview_stage=event.interview_stage,
            follow_up_date=event.follow_up_date,
            clear_follow_up_date=event.clear_follow_up_date,
            notes=event.evidence.note,
            allow_terminal_reopen=True,
        )

    if event.kind == "interview_stage_change":
        return LifecycleProjection(
            interview_stage=event.interview_stage,
            notes=event.evidence.note,
        )

    if event.kind == "outcome_change":
        return LifecycleProjection(
            outcome=event.outcome,
            notes=event.evidence.note,
        )

    if event.kind == "follow_up_set":
        return LifecycleProjection(
            follow_up_date=event.follow_up_date,
            clear_follow_up_date=event.clear_follow_up_date,
            notes=event.evidence.note,
        )

    return LifecycleProjection()


@dataclass(frozen=True)
class FoldedLifecycleState:
    """Expected Opportunity lifecycle fields after folding event history."""

    status: PipelineStatus | None
    outcome: OutcomeKind | None
    interview_stage: InterviewStage | None
    follow_up_date: date | None
    follow_up_cleared: bool
    has_status_events: bool
    has_outcome_events: bool
    has_interview_events: bool
    has_follow_up_events: bool


def fold_lifecycle_state(events: list[PipelineEvent]) -> FoldedLifecycleState:
    """Last-write-wins fold of status / outcome / interview / follow-up events."""
    status: PipelineStatus | None = None
    outcome: OutcomeKind | None = None
    interview_stage: InterviewStage | None = None
    follow_up_date: date | None = None
    follow_up_cleared = False
    has_status = False
    has_outcome = False
    has_interview = False
    has_follow_up = False

    for event in sorted(events, key=lambda item: (item.occurred_at, item.event_id)):
        if event.kind in {"status_transition", "correction"} and event.to_status:
            status = event.to_status
            has_status = True
            if event.outcome is not None:
                outcome = event.outcome
                has_outcome = True
            if event.interview_stage is not None:
                interview_stage = event.interview_stage
                has_interview = True
        elif event.kind == "outcome_change" and event.outcome is not None:
            outcome = event.outcome
            has_outcome = True
        elif event.kind == "interview_stage_change" and event.interview_stage is not None:
            interview_stage = event.interview_stage
            has_interview = True
        elif event.kind == "follow_up_set":
            has_follow_up = True
            if event.clear_follow_up_date:
                follow_up_date = None
                follow_up_cleared = True
            else:
                follow_up_date = event.follow_up_date
                follow_up_cleared = False

    return FoldedLifecycleState(
        status=status,
        outcome=outcome,
        interview_stage=interview_stage,
        follow_up_date=follow_up_date,
        follow_up_cleared=follow_up_cleared,
        has_status_events=has_status,
        has_outcome_events=has_outcome,
        has_interview_events=has_interview,
        has_follow_up_events=has_follow_up,
    )
