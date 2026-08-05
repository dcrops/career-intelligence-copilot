"""Derived pipeline reporting projections (FR-013 M4).

Reports only what Opportunity current state and PipelineEvents already record.
No new lifecycle concepts and no Opportunity schema changes.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from career_intelligence.opportunities.models import Opportunity, PipelineStatus

from .constants import ACTIVE_PIPELINE_STATUSES
from .models import PipelineEvent

DEFAULT_PIPELINE_EXPORT_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "exports" / "pipeline.csv"
)

PIPELINE_EXPORT_COLUMNS: tuple[str, ...] = (
    "opportunity_id",
    "company",
    "title",
    "status",
    "outcome",
    "interview_stage",
    "follow_up_date",
    "owner_decision",
    "days_in_current_status",
    "updated_at",
    "source_url",
)

# Statuses that imply an application was submitted (current snapshot).
_POST_SUBMIT_STATUSES: frozenset[PipelineStatus] = frozenset(
    {
        "submitted",
        "interviewing",
        "offer",
        "accepted",
        "rejected",
        "withdrawn",
    }
)


@dataclass(frozen=True)
class FollowUpItem:
    opportunity_id: str
    company: str | None
    title: str | None
    status: PipelineStatus
    follow_up_date: date
    days_until_due: int


@dataclass(frozen=True)
class AgeingItem:
    opportunity_id: str
    company: str | None
    title: str | None
    status: PipelineStatus
    entered_at: datetime | None
    days_in_status: float | None


@dataclass(frozen=True)
class PipelineSummaryReport:
    """Owner-facing snapshot derived from Opportunities (+ optional events)."""

    as_of: datetime
    total_opportunities: int
    by_status: dict[str, int]
    by_outcome: dict[str, int]
    active_count: int
    submitted_count: int
    awaiting_response_count: int
    interviewing_count: int
    offer_count: int
    accepted_count: int
    rejected_count: int
    withdrawn_count: int
    follow_ups_due_count: int
    follow_ups_overdue_count: int
    offer_rate: float | None
    acceptance_rate: float | None
    interview_rate: float | None
    ageing: tuple[AgeingItem, ...] = ()
    follow_ups_due: tuple[FollowUpItem, ...] = ()
    historical_event_count: int = 0


def entered_current_status_at(
    events: list[PipelineEvent],
    current_status: PipelineStatus,
) -> datetime | None:
    """Latest time history moved into ``current_status`` (append-only events)."""
    entered: datetime | None = None
    for event in sorted(events, key=lambda item: (item.occurred_at, item.event_id)):
        if (
            event.kind in {"status_transition", "correction"}
            and event.to_status == current_status
        ):
            entered = event.occurred_at
    return entered


def days_in_current_status(
    events: list[PipelineEvent],
    current_status: PipelineStatus,
    *,
    as_of: datetime,
) -> float | None:
    entered = entered_current_status_at(events, current_status)
    if entered is None:
        return None
    delta = as_of - entered
    return round(delta.total_seconds() / 86400.0, 2)


def build_summary_report(
    opportunities: list[Opportunity],
    *,
    events_by_opportunity: dict[str, list[PipelineEvent]] | None = None,
    as_of: datetime | None = None,
    reference_date: date | None = None,
) -> PipelineSummaryReport:
    """Build a deterministic summary from current Opportunity rows (+ events)."""
    now = as_of or datetime.now(UTC)
    today = reference_date or now.date()
    events_by_opportunity = events_by_opportunity or {}

    by_status: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    active = 0
    submitted = 0
    awaiting = 0
    interviewing = 0
    offers = 0
    accepted = 0
    rejected = 0
    withdrawn = 0
    due: list[FollowUpItem] = []
    overdue = 0
    ageing: list[AgeingItem] = []
    event_total = 0

    for opportunity in opportunities:
        by_status[opportunity.status] = by_status.get(opportunity.status, 0) + 1
        outcome_kind = (
            opportunity.outcome.outcome if opportunity.outcome is not None else None
        )
        if outcome_kind is not None:
            by_outcome[outcome_kind] = by_outcome.get(outcome_kind, 0) + 1

        if opportunity.status in ACTIVE_PIPELINE_STATUSES:
            active += 1
        if opportunity.status in _POST_SUBMIT_STATUSES:
            submitted += 1
        if opportunity.status == "submitted":
            awaiting += 1
        if opportunity.status == "interviewing":
            interviewing += 1
        if opportunity.status == "offer":
            offers += 1
        if opportunity.status == "accepted":
            accepted += 1
        if opportunity.status == "rejected":
            rejected += 1
        if opportunity.status == "withdrawn":
            withdrawn += 1

        follow_up = (
            opportunity.outcome.follow_up_date
            if opportunity.outcome is not None
            else None
        )
        if follow_up is not None and follow_up <= today:
            days = (follow_up - today).days
            due.append(
                FollowUpItem(
                    opportunity_id=opportunity.opportunity_id,
                    company=opportunity.identity.company,
                    title=opportunity.identity.title,
                    status=opportunity.status,
                    follow_up_date=follow_up,
                    days_until_due=days,
                )
            )
            if follow_up < today:
                overdue += 1

        events = events_by_opportunity.get(opportunity.opportunity_id, [])
        event_total += len(events)
        if opportunity.status in ACTIVE_PIPELINE_STATUSES:
            entered = entered_current_status_at(events, opportunity.status)
            ageing.append(
                AgeingItem(
                    opportunity_id=opportunity.opportunity_id,
                    company=opportunity.identity.company,
                    title=opportunity.identity.title,
                    status=opportunity.status,
                    entered_at=entered,
                    days_in_status=days_in_current_status(
                        events, opportunity.status, as_of=now
                    ),
                )
            )

    # Rates among the post-submit cohort (current snapshot).
    offer_like = offers + accepted
    terminal = accepted + rejected + withdrawn
    offer_rate = (offer_like / submitted) if submitted else None
    acceptance_rate = (accepted / terminal) if terminal else None
    interview_reached = interviewing + offers + accepted + rejected + withdrawn
    # interview_rate among submitted: those who left pure "submitted" or are interviewing+
    interviewed = sum(
        1
        for item in opportunities
        if item.status in {"interviewing", "offer", "accepted", "rejected", "withdrawn"}
        or (
            item.outcome is not None
            and item.outcome.interview_stage not in {None, "none"}
        )
    )
    # Prefer status-based interview progress for rate clarity.
    interviewed_status = sum(
        1
        for item in opportunities
        if item.status in {"interviewing", "offer", "accepted"}
        or (
            item.status in {"rejected", "withdrawn"}
            and item.outcome is not None
            and item.outcome.interview_stage not in {None, "none"}
        )
    )
    interview_rate = (interviewed_status / submitted) if submitted else None
    _ = interview_reached, interviewed  # kept for clarity; rate uses interviewed_status

    due_sorted = tuple(
        sorted(due, key=lambda item: (item.follow_up_date, item.opportunity_id))
    )
    ageing_sorted = tuple(
        sorted(
            ageing,
            key=lambda item: (
                -(item.days_in_status or -1.0),
                item.opportunity_id,
            ),
        )
    )

    return PipelineSummaryReport(
        as_of=now,
        total_opportunities=len(opportunities),
        by_status=dict(sorted(by_status.items())),
        by_outcome=dict(sorted(by_outcome.items())),
        active_count=active,
        submitted_count=submitted,
        awaiting_response_count=awaiting,
        interviewing_count=interviewing,
        offer_count=offers,
        accepted_count=accepted,
        rejected_count=rejected,
        withdrawn_count=withdrawn,
        follow_ups_due_count=len(due_sorted),
        follow_ups_overdue_count=overdue,
        offer_rate=round(offer_rate, 4) if offer_rate is not None else None,
        acceptance_rate=(
            round(acceptance_rate, 4) if acceptance_rate is not None else None
        ),
        interview_rate=round(interview_rate, 4) if interview_rate is not None else None,
        ageing=ageing_sorted,
        follow_ups_due=due_sorted,
        historical_event_count=event_total,
    )


def export_pipeline_csv(
    opportunities: list[Opportunity],
    output_path: Path,
    *,
    events_by_opportunity: dict[str, list[PipelineEvent]] | None = None,
    as_of: datetime | None = None,
) -> Path:
    """Deterministic UTF-8-SIG CSV for operational continuity (owner-controlled)."""
    now = as_of or datetime.now(UTC)
    events_by_opportunity = events_by_opportunity or {}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(opportunities, key=lambda item: item.opportunity_id)

    rows: list[dict[str, str]] = []
    for opportunity in ordered:
        events = events_by_opportunity.get(opportunity.opportunity_id, [])
        days = days_in_current_status(events, opportunity.status, as_of=now)
        outcome = opportunity.outcome
        identity = opportunity.identity
        rows.append(
            {
                "opportunity_id": opportunity.opportunity_id,
                "company": identity.company or "",
                "title": identity.title or "",
                "status": opportunity.status,
                "outcome": outcome.outcome if outcome is not None else "",
                "interview_stage": (
                    outcome.interview_stage if outcome is not None else ""
                ),
                "follow_up_date": (
                    outcome.follow_up_date.isoformat()
                    if outcome is not None and outcome.follow_up_date is not None
                    else ""
                ),
                "owner_decision": (
                    opportunity.decision.decision
                    if opportunity.decision is not None
                    else ""
                ),
                "days_in_current_status": "" if days is None else f"{days:.2f}",
                "updated_at": opportunity.updated_at.isoformat().replace("+00:00", "Z"),
                "source_url": (
                    str(identity.source_url) if identity.source_url is not None else ""
                ),
            }
        )

    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=list(PIPELINE_EXPORT_COLUMNS),
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(output_path)
    except OSError:
        if temporary.exists():
            temporary.unlink(missing_ok=True)
        raise
    return output_path
