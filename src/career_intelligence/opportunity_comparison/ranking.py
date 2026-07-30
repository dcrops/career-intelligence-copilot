"""Deterministic ranking of open Opportunity records (FR-009 M4 calibration).

Sort key (ascending = higher priority) — quality and owner value, not effort:

1. Pursuit posture (FR-005 primary attention signal)
2. Fit strength sum from strategy summary (FR-003 judgments)
3. Practical value (career value of the opportunity)
4. opportunity_id (stable tie-break)

``application_tier`` remains on the ranked item and in explanations as effort
context, but it does not decide order: generation and submission are expected to
be largely automated, so effort band must not outrank opportunity quality.

``unknown`` fit judgments contribute 0 to fit strength — missing evidence must
not increase confidence.

Does not call OpenAI, re-assess, or mutate Opportunity records.
"""

from __future__ import annotations

from career_intelligence.application_strategy.models import (
    PracticalValue,
    PursuitPosture,
)
from career_intelligence.opportunities.models import (
    TERMINAL_STATUSES,
    Opportunity,
    PipelineStatus,
)
from career_intelligence.opportunity_assessment.models import FitJudgment

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

_VALUE_RANK: dict[PracticalValue | None, int] = {
    "career_priority": 0,
    "acceptable_opportunity": 1,
    "volume_obligation": 2,
    "deferred_pending_information": 3,
    None: 4,
}

_FIT_SCORE: dict[FitJudgment, int] = {
    "strong": 5,
    "moderate": 4,
    "mixed": 3,
    "weak": 1,
    "misaligned": 0,
    # Unknown evidence must not inflate confidence.
    "unknown": 0,
}


def is_open_opportunity(opportunity: Opportunity) -> bool:
    """Return True when the opportunity is eligible for open ranking."""
    if opportunity.status in TERMINAL_STATUSES:
        return False
    if opportunity.status not in OPEN_STATUSES:
        return False
    return not (
        opportunity.decision is not None and opportunity.decision.decision == "skip"
    )


def fit_strength(opportunity: Opportunity) -> int:
    """Sum of technical + commercial + portfolio fit scores (0–15).

    ``unknown`` contributes 0 so missing judgments cannot raise priority.
    """
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
    value = summary.practical_value if summary else None
    return (
        _POSTURE_RANK[posture],
        -fit_strength(opportunity),  # higher fit first within same posture
        _VALUE_RANK[value],
        opportunity.opportunity_id,
    )


def rank_open_opportunities(opportunities: list[Opportunity]) -> list[RankedOpportunity]:
    """Filter to open opportunities and return ranked items with reasons."""
    open_items = [item for item in opportunities if is_open_opportunity(item)]
    ordered = sorted(open_items, key=sort_key)
    ranked: list[RankedOpportunity] = []
    for index, opportunity in enumerate(ordered, start=1):
        ranked.append(
            _to_ranked(
                index,
                opportunity,
                predecessor=ordered[index - 2] if index > 1 else None,
            )
        )
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
        reasons.append(f"Practical value: {summary.practical_value}")
        # Effort band is context for the owner, not a ranking factor.
        reasons.append(f"Application tier (effort context): {summary.application_tier}")
        if predecessor is not None:
            reasons.append(_relative_reason(opportunity, predecessor))

    decision = opportunity.decision.decision if opportunity.decision else None
    if decision is None:
        reasons.append("Owner has not yet recorded apply/skip/defer")
    elif decision == "defer":
        reasons.append("Owner deferred this opportunity")
    elif decision == "apply":
        reasons.append("Owner decided to apply")

    if opportunity.status == "deferred":
        reasons.append("Pipeline status is deferred")
    elif opportunity.status == "assessed":
        # Decision-aware: FR-009 keeps status=assessed after apply/skip/defer.
        if decision is None:
            reasons.append("Assessed; awaiting owner decision")
        elif decision == "apply":
            reasons.append("Assessed; owner chose apply — ready for package preparation")
        elif decision == "defer":
            reasons.append("Assessed; owner deferred review")
        # skip is excluded by is_open_opportunity
    elif opportunity.status in {"preparing", "submitted"}:
        reasons.append(f"Application in progress ({opportunity.status})")
    elif opportunity.status == "interviewing":
        reasons.append("Interview stage — prioritise preparation")
    elif opportunity.status == "offer":
        reasons.append("Offer received — prioritise the offer decision")

    if opportunity.outcome is not None and opportunity.outcome.follow_up_date is not None:
        reasons.append(
            f"Follow-up dated {opportunity.outcome.follow_up_date.isoformat()}"
        )

    seen: set[str] = set()
    unique: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            unique.append(reason)
    return unique


def _relative_reason(current: Opportunity, previous: Opportunity) -> str:
    """Explain why current sorts after previous."""
    cur = sort_key(current)
    prev = sort_key(previous)
    if cur[0] > prev[0]:
        return "Lower pursuit posture than the opportunity ranked above"
    if cur[1] > prev[1]:  # negated fit: larger means weaker
        return "Weaker combined fit than the opportunity ranked above"
    if cur[2] > prev[2]:
        return "Lower practical value than the opportunity ranked above"
    return "Equal ranking signals; ordered by stable opportunity_id"
