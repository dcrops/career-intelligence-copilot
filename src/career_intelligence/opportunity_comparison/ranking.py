"""Deterministic ranking of open Opportunity records (M4).

Sort key (ascending = higher priority):
1. Pursuit posture (FR-005 primary attention signal)
2. Fit strength sum from strategy summary (FR-003 judgments)
3. Application tier (effort band)
4. opportunity_id (stable tie-break)

Does not call OpenAI, re-assess, or mutate Opportunity records.
"""

from __future__ import annotations

from career_intelligence.application_strategy.models import ApplicationTier, PursuitPosture
from career_intelligence.opportunity_assessment.models import FitJudgment
from career_intelligence.opportunities.models import Opportunity, PipelineStatus, TERMINAL_STATUSES

from .models import RankedOpportunity

OPEN_STATUSES: frozenset[PipelineStatus] = frozenset(
    {
        "assessed",
        "deferred",
        "preparing",
        "submitted",
        "interviewing",
        "offer",
    }
)

_POSTURE_RANK: dict[PursuitPosture | None, int] = {
    "prioritise": 0,
    "pursue": 1,
    "consider": 2,
    "low_effort_submit": 3,
    "do_not_prioritise": 4,
    "insufficient_information": 5,
    None: 6,
}

_TIER_RANK: dict[ApplicationTier | None, int] = {
    "platinum": 0,
    "gold": 1,
    "silver": 2,
    "bronze": 3,
    None: 4,
}

_FIT_SCORE: dict[FitJudgment, int] = {
    "strong": 5,
    "moderate": 4,
    "mixed": 3,
    "unknown": 2,
    "weak": 1,
    "misaligned": 0,
}


def is_open_opportunity(opportunity: Opportunity) -> bool:
    """Return True when the opportunity is eligible for open ranking."""
    if opportunity.status in TERMINAL_STATUSES:
        return False
    if opportunity.status not in OPEN_STATUSES:
        return False
    if opportunity.decision is not None and opportunity.decision.decision == "skip":
        return False
    return True


def fit_strength(opportunity: Opportunity) -> int:
    """Sum of technical + commercial + portfolio fit scores (0–15)."""
    summary = opportunity.strategy_summary
    if summary is None:
        return 0
    return (
        _FIT_SCORE[summary.technical_fit]
        + _FIT_SCORE[summary.commercial_fit]
        + _FIT_SCORE[summary.portfolio_fit]
    )


def sort_key(opportunity: Opportunity) -> tuple[int, int, int, str]:
    """Lower tuple sorts earlier (higher priority)."""
    summary = opportunity.strategy_summary
    posture = summary.pursuit_posture if summary else None
    tier = summary.application_tier if summary else None
    return (
        _POSTURE_RANK[posture],
        -fit_strength(opportunity),  # higher fit first within same posture
        _TIER_RANK[tier],
        opportunity.opportunity_id,
    )


def rank_open_opportunities(opportunities: list[Opportunity]) -> list[RankedOpportunity]:
    """Filter to open opportunities and return ranked items with reasons."""
    open_items = [item for item in opportunities if is_open_opportunity(item)]
    ordered = sorted(open_items, key=sort_key)
    ranked: list[RankedOpportunity] = []
    for index, opportunity in enumerate(ordered, start=1):
        ranked.append(_to_ranked(index, opportunity, predecessor=ordered[index - 2] if index > 1 else None))
    return ranked


def _to_ranked(
    rank: int,
    opportunity: Opportunity,
    *,
    predecessor: Opportunity | None,
) -> RankedOpportunity:
    summary = opportunity.strategy_summary
    strength = fit_strength(opportunity)
    return RankedOpportunity(
        rank=rank,
        opportunity_id=opportunity.opportunity_id,
        company=opportunity.identity.company,
        title=opportunity.identity.title,
        status=opportunity.status,
        pursuit_posture=summary.pursuit_posture if summary else None,
        application_tier=summary.application_tier if summary else None,
        fit_strength=strength,
        technical_fit=summary.technical_fit if summary else None,
        commercial_fit=summary.commercial_fit if summary else None,
        portfolio_fit=summary.portfolio_fit if summary else None,
        reasons=_build_reasons(opportunity, strength, predecessor=predecessor),
    )


def _build_reasons(
    opportunity: Opportunity,
    strength: int,
    *,
    predecessor: Opportunity | None,
) -> list[str]:
    reasons: list[str] = []
    summary = opportunity.strategy_summary

    if summary is None:
        reasons.append(
            "Incomplete strategy summary (legacy or partial record); "
            "ranked after opportunities with full FR-003–FR-005 summaries"
        )
    else:
        reasons.append(f"Pursuit posture: {summary.pursuit_posture}")
        reasons.append(
            "Fit strength "
            f"{strength}/15 "
            f"(technical={summary.technical_fit}, "
            f"commercial={summary.commercial_fit}, "
            f"portfolio={summary.portfolio_fit})"
        )
        reasons.append(f"Application tier (effort): {summary.application_tier}")
        if predecessor is not None:
            reasons.append(_relative_reason(opportunity, predecessor))

    if opportunity.decision is None:
        reasons.append("Owner has not yet recorded apply/skip/defer")
    elif opportunity.decision.decision == "defer":
        reasons.append("Owner deferred this opportunity")
    elif opportunity.decision.decision == "apply":
        reasons.append("Owner decided to apply")

    if opportunity.status == "deferred":
        reasons.append("Pipeline status is deferred")
    elif opportunity.status == "assessed":
        reasons.append("Recently assessed; awaiting owner action")
    elif opportunity.status in {"preparing", "submitted"}:
        reasons.append(f"Application in progress ({opportunity.status})")
    elif opportunity.status == "interviewing":
        reasons.append("Interview stage — prioritise preparation effort")
    elif opportunity.status == "offer":
        reasons.append("Offer received — prioritise decision effort")

    if opportunity.outcome is not None and opportunity.outcome.follow_up_date is not None:
        reasons.append(
            f"Follow-up dated {opportunity.outcome.follow_up_date.isoformat()}"
        )

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            unique.append(reason)
    return unique


def _relative_reason(current: Opportunity, previous: Opportunity) -> str:
    """Explain why current sorts after previous (same or weaker primary key)."""
    cur = sort_key(current)
    prev = sort_key(previous)
    if cur[0] > prev[0]:
        return "Lower pursuit posture than the opportunity ranked above"
    if cur[1] > prev[1]:  # negated fit: larger means weaker
        return "Weaker combined fit than the opportunity ranked above"
    if cur[2] > prev[2]:
        return "Lower application tier (effort) than the opportunity ranked above"
    return "Equal ranking signals; ordered by stable opportunity_id"
