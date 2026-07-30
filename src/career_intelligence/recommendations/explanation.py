"""Deterministic explanation helpers for opportunity recommendations (FR-009 M4).

Uses only fields already present on the Opportunity aggregate (and derived duplicate
group size). Never invents salary, closing dates, or preference matches that are not
on the record.
"""

from __future__ import annotations

from datetime import date, timedelta

from career_intelligence.opportunities.models import Opportunity
from career_intelligence.opportunity_comparison.models import RankedOpportunity

from .models import (
    OpportunityRecommendation,
    PriorityBand,
    RecommendedNextAction,
    UrgencyKind,
)

_STRONG_POSTURES = frozenset({"prioritise", "pursue"})
_WEAK_POSTURES = frozenset({"do_not_prioritise", "insufficient_information"})
_WEAK_FITS = frozenset({"weak", "misaligned", "unknown"})
_STRONG_FITS = frozenset({"strong"})


def priority_band(
    opportunity: Opportunity,
    *,
    fit_strength: int,
) -> PriorityBand:
    """Map ranking signals to a coarse band for quick owner scanning."""
    summary = opportunity.strategy_summary
    if summary is None:
        return "low"
    posture = summary.pursuit_posture
    value = summary.practical_value
    if posture == "prioritise" and value == "career_priority" and fit_strength >= 12:
        return "immediate"
    if posture in _STRONG_POSTURES and value in {
        "career_priority",
        "acceptable_opportunity",
    }:
        return "high"
    if posture in {"consider", "low_effort_submit"}:
        return "standard"
    return "low"


def urgency_kind(
    opportunity: Opportunity,
    *,
    reference_date: date,
) -> UrgencyKind:
    """Urgency from available timestamps only — never invents application deadlines.

    Closing dates are not extracted anywhere in the product today, so they cannot
    contribute. Process urgency (interview/offer) and recorded follow-up dates can.
    """
    if opportunity.status in {"interviewing", "offer"}:
        return "process"
    follow_up = (
        opportunity.outcome.follow_up_date if opportunity.outcome is not None else None
    )
    if follow_up is not None:
        if follow_up <= reference_date:
            return "due"
        if follow_up <= reference_date + timedelta(days=7):
            return "upcoming"
    return "none"


def recommended_next_action(
    opportunity: Opportunity,
    *,
    reference_date: date,
) -> RecommendedNextAction:
    """Deterministic next step from decision, review, and pipeline status."""
    decision = opportunity.decision.decision if opportunity.decision else None
    status = opportunity.status

    if status == "offer":
        return "decide_on_offer"
    if status == "interviewing":
        return "prepare_for_interview"
    if status in {"submitted"}:
        return "track_application_pipeline"
    if status == "preparing":
        return "continue_package_preparation"

    if decision is None:
        return "record_owner_decision"
    if decision == "defer":
        defer_until = opportunity.review.defer_until
        if defer_until is None:
            return "wait_until_defer_date"
        if defer_until <= reference_date:
            return "re_review_expired_defer"
        return "wait_until_defer_date"
    if decision == "apply":
        return "prepare_application_package"
    return "review_opportunity"


def build_recommendation(
    ranked: RankedOpportunity,
    opportunity: Opportunity,
    *,
    reference_date: date,
    group_size: int | None,
) -> OpportunityRecommendation:
    """Compose one recommendation from a ranked item and its source record."""
    summary = opportunity.strategy_summary
    strength = ranked.fit_strength
    positives, negatives, missing, trade_offs = _explain(opportunity, strength)
    return OpportunityRecommendation(
        rank=ranked.rank,
        opportunity_id=opportunity.opportunity_id,
        company=opportunity.identity.company,
        title=opportunity.identity.title,
        priority_band=priority_band(opportunity, fit_strength=strength),
        urgency=urgency_kind(opportunity, reference_date=reference_date),
        recommended_next_action=recommended_next_action(
            opportunity, reference_date=reference_date
        ),
        pursuit_posture=summary.pursuit_posture if summary else None,
        practical_value=summary.practical_value if summary else None,
        application_tier=summary.application_tier if summary else None,
        fit_strength=strength,
        pinned=opportunity.review.pinned,
        duplicate_group_size=group_size,
        positives=positives,
        negatives=negatives,
        missing=missing,
        ranking_reasons=tuple(ranked.reasons),
        trade_offs=trade_offs,
    )


def _explain(
    opportunity: Opportunity,
    strength: int,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    positives: list[str] = []
    negatives: list[str] = []
    missing: list[str] = []
    trade_offs: list[str] = []
    summary = opportunity.strategy_summary
    identity = opportunity.identity

    if summary is None:
        missing.append("Strategy summary absent (legacy or partial record)")
        missing.append("Fit judgments unavailable without FR-003–FR-005 summary")
        return tuple(positives), tuple(negatives), tuple(missing), tuple(trade_offs)

    if summary.pursuit_posture in _STRONG_POSTURES:
        positives.append(f"Strong pursuit posture ({summary.pursuit_posture})")
    elif summary.pursuit_posture in _WEAK_POSTURES:
        negatives.append(f"Weak pursuit posture ({summary.pursuit_posture})")

    if summary.practical_value == "career_priority":
        positives.append("Marked as a career-priority opportunity")
    elif summary.practical_value == "acceptable_opportunity":
        positives.append("Acceptable opportunity value")
    elif summary.practical_value == "volume_obligation":
        negatives.append("Volume obligation — lower owner value than career priorities")
    elif summary.practical_value == "deferred_pending_information":
        negatives.append("Practical value deferred pending more information")

    if strength >= 12:
        positives.append(f"Strong combined fit ({strength}/15)")
    elif strength <= 3:
        negatives.append(f"Weak combined fit ({strength}/15)")

    for label, judgment in (
        ("technical", summary.technical_fit),
        ("commercial", summary.commercial_fit),
        ("portfolio", summary.portfolio_fit),
    ):
        if judgment in _STRONG_FITS:
            positives.append(f"{label.capitalize()} fit is strong")
        elif judgment in _WEAK_FITS:
            if judgment == "unknown":
                missing.append(f"{label.capitalize()} fit is unknown")
            else:
                negatives.append(f"{label.capitalize()} fit is {judgment}")

    if identity.company is None:
        missing.append("Company missing from Opportunity identity")
    if identity.title is None:
        missing.append("Title missing from Opportunity identity")
    if identity.location_text is None:
        missing.append("Location text missing from Opportunity identity")
    # Closing dates and salary are not fields on Opportunity identity today — they
    # are never invented here. Prefer identity/summary gaps that are actionable.

    if summary.application_tier in {"platinum", "gold"} and summary.practical_value in {
        "volume_obligation",
        "deferred_pending_information",
    }:
        trade_offs.append(
            f"Effort band is {summary.application_tier} but practical value is "
            f"{summary.practical_value} — effort does not raise priority"
        )
    if summary.pursuit_posture in _STRONG_POSTURES and strength <= 6:
        trade_offs.append(
            "Pursuit posture is strong while combined fit is modest — "
            "review gaps before investing"
        )
    if opportunity.review.pinned:
        positives.append("Pinned by owner for presentation prominence")

    return (
        tuple(positives),
        tuple(negatives),
        tuple(missing),
        tuple(trade_offs),
    )
