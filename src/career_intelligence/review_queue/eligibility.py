"""Deterministic queue eligibility policy (FR-009 M1).

The policy is a pure function of a persisted Opportunity plus an explicit
reference date. It never reads the clock, so "currently deferred" is decidable
and testable without freezing time.
"""

from __future__ import annotations

from datetime import date

from career_intelligence.opportunities.models import TERMINAL_STATUSES, Opportunity

from .models import ExclusionReason, QueueEligibility, QueueScope


def evaluate_eligibility(
    opportunity: Opportunity,
    *,
    reference_date: date,
    scope: QueueScope = "active",
) -> QueueEligibility:
    """Explain whether one Opportunity belongs in the requested queue scope.

    Reasons are evaluated in a fixed order so identical inputs always produce an
    identical explanation. ``scope='awaiting_review'`` additionally excludes
    records that already carry an owner decision.
    """
    reasons: list[ExclusionReason] = []

    if opportunity.review.archived_at is not None:
        reasons.append("archived")
    if opportunity.duplicate is not None:
        reasons.append("confirmed_duplicate")

    decision = opportunity.decision.decision if opportunity.decision else None
    if decision == "skip":
        reasons.append("skipped")
    if _is_deferred(opportunity, decision=decision, reference_date=reference_date):
        reasons.append("deferred")
    if opportunity.status in TERMINAL_STATUSES:
        reasons.append("closed")

    # Applied-for records stay active but are no longer awaiting a first decision.
    if not reasons and scope == "awaiting_review" and decision is not None:
        reasons.append("decided")

    return QueueEligibility(
        opportunity_id=opportunity.opportunity_id,
        eligible=not reasons,
        exclusion_reasons=tuple(reasons),
    )


def _is_deferred(
    opportunity: Opportunity,
    *,
    decision: str | None,
    reference_date: date,
) -> bool:
    """Whether a defer currently excludes the record from the queue.

    Policy (FR-009 M1/M2):

    - ``defer_until`` set and ``> reference_date`` → currently deferred
    - ``defer_until`` set and ``<= reference_date`` → expired; eligible to return
    - ``defer_until`` is None and ``decision == "defer"`` → indefinitely deferred
    """
    defer_until = opportunity.review.defer_until
    if defer_until is not None:
        return defer_until > reference_date
    return decision == "defer"
