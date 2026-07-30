"""Unit tests for deterministic open-opportunity ranking (M4)."""

from __future__ import annotations

from datetime import date

from career_intelligence.opportunity_comparison import (
    OpportunityComparisonService,
    fit_strength,
    is_open_opportunity,
    sort_key,
)
from career_intelligence.opportunity_comparison.ranking import rank_open_opportunities

from .helpers import ID_A, ID_B, ID_C, ID_D, ID_E, ID_F, make_opportunity


def test_fit_strength_sums_judgments() -> None:
    # strong(5) + moderate(4) + strong(5) = 14
    opp = make_opportunity(ID_A, technical_fit="strong", commercial_fit="moderate", portfolio_fit="strong")
    assert fit_strength(opp) == 14


def test_incomplete_opportunity_has_zero_fit() -> None:
    assert fit_strength(make_opportunity(ID_A, incomplete=True)) == 0


def test_open_filter_excludes_terminal_and_skip() -> None:
    assert is_open_opportunity(make_opportunity(ID_A, status="assessed"))
    assert is_open_opportunity(make_opportunity(ID_B, status="interviewing", decision="apply"))
    assert not is_open_opportunity(make_opportunity(ID_C, status="accepted"))
    assert not is_open_opportunity(make_opportunity(ID_D, status="rejected"))
    assert not is_open_opportunity(make_opportunity(ID_E, status="withdrawn"))
    assert not is_open_opportunity(make_opportunity(ID_F, status="assessed", decision="skip"))


def test_posture_beats_fit_and_value() -> None:
    """Higher pursuit posture outranks stronger fit / higher practical value."""
    weaker_posture = make_opportunity(
        ID_A,
        pursuit_posture="consider",
        practical_value="career_priority",
        technical_fit="strong",
        commercial_fit="strong",
        portfolio_fit="strong",
        company="Weak Posture Co",
    )
    stronger_posture = make_opportunity(
        ID_B,
        pursuit_posture="prioritise",
        practical_value="volume_obligation",
        technical_fit="weak",
        commercial_fit="weak",
        portfolio_fit="weak",
        company="Strong Posture Co",
    )
    ranked = rank_open_opportunities([weaker_posture, stronger_posture])
    assert [item.opportunity_id for item in ranked] == [ID_B, ID_A]
    assert "Pursuit posture: prioritise" in ranked[0].reasons


def test_equal_posture_higher_fit_beats_higher_value() -> None:
    """Within same posture, fit strength outranks practical value."""
    high_value_weak_fit = make_opportunity(
        ID_A,
        pursuit_posture="consider",
        practical_value="career_priority",
        technical_fit="mixed",
        commercial_fit="mixed",
        portfolio_fit="mixed",  # 9
        company="Value Weak",
    )
    low_value_strong_fit = make_opportunity(
        ID_B,
        pursuit_posture="consider",
        practical_value="volume_obligation",
        technical_fit="strong",
        commercial_fit="strong",
        portfolio_fit="strong",  # 15
        company="Volume Strong",
    )
    ranked = rank_open_opportunities([high_value_weak_fit, low_value_strong_fit])
    assert [item.opportunity_id for item in ranked] == [ID_B, ID_A]
    assert ranked[0].fit_strength > ranked[1].fit_strength


def test_practical_value_beats_application_tier() -> None:
    """Effort tier must not outrank practical value (FR-009 M4 calibration)."""
    volume_platinum = make_opportunity(
        ID_A,
        pursuit_posture="consider",
        application_tier="platinum",
        practical_value="volume_obligation",
        technical_fit="moderate",
        commercial_fit="moderate",
        portfolio_fit="moderate",
    )
    career_bronze = make_opportunity(
        ID_B,
        pursuit_posture="consider",
        application_tier="bronze",
        practical_value="career_priority",
        technical_fit="moderate",
        commercial_fit="moderate",
        portfolio_fit="moderate",
    )
    ranked = rank_open_opportunities([volume_platinum, career_bronze])
    assert [item.opportunity_id for item in ranked] == [ID_B, ID_A]
    assert "Practical value: career_priority" in ranked[0].reasons
    assert "effort context" in ranked[0].reasons[3]


def test_unknown_fit_does_not_inflate_strength() -> None:
    known_weak = make_opportunity(
        ID_A,
        technical_fit="weak",
        commercial_fit="weak",
        portfolio_fit="weak",
    )
    unknown_dims = make_opportunity(
        ID_B,
        technical_fit="unknown",
        commercial_fit="unknown",
        portfolio_fit="unknown",
    )
    assert fit_strength(known_weak) == 3
    assert fit_strength(unknown_dims) == 0
    ranked = rank_open_opportunities([unknown_dims, known_weak])
    # Same posture/value defaults; known-weak (fit 3) ranks above unknown (fit 0).
    assert [item.opportunity_id for item in ranked] == [ID_A, ID_B]


def test_tie_break_by_opportunity_id() -> None:
    first = make_opportunity(
        ID_A,
        pursuit_posture="pursue",
        application_tier="gold",
        technical_fit="moderate",
        commercial_fit="moderate",
        portfolio_fit="moderate",
    )
    second = make_opportunity(
        ID_B,
        pursuit_posture="pursue",
        application_tier="gold",
        technical_fit="moderate",
        commercial_fit="moderate",
        portfolio_fit="moderate",
    )
    ranked = rank_open_opportunities([second, first])
    assert [item.opportunity_id for item in ranked] == [ID_A, ID_B]
    assert any("stable opportunity_id" in reason for reason in ranked[1].reasons)


def test_ranking_is_stable_and_reproducible() -> None:
    items = [
        make_opportunity(ID_C, pursuit_posture="consider", application_tier="silver"),
        make_opportunity(ID_A, pursuit_posture="prioritise", application_tier="platinum"),
        make_opportunity(ID_B, pursuit_posture="pursue", application_tier="gold"),
        make_opportunity(ID_D, status="rejected"),
        make_opportunity(ID_E, decision="skip"),
    ]
    first = [item.opportunity_id for item in rank_open_opportunities(items)]
    second = [item.opportunity_id for item in rank_open_opportunities(list(reversed(items)))]
    assert first == second == [ID_A, ID_B, ID_C]


def test_incomplete_legacy_ranks_after_complete() -> None:
    complete = make_opportunity(
        ID_B,
        pursuit_posture="do_not_prioritise",
        application_tier="bronze",
        technical_fit="weak",
        commercial_fit="weak",
        portfolio_fit="weak",
    )
    incomplete = make_opportunity(ID_A, incomplete=True, company="Legacy Co")
    ranked = rank_open_opportunities([incomplete, complete])
    assert [item.opportunity_id for item in ranked] == [ID_B, ID_A]
    assert "Incomplete strategy summary" in ranked[1].reasons[0]


def test_reasons_include_decision_status_and_follow_up() -> None:
    opp = make_opportunity(
        ID_A,
        status="deferred",
        decision="defer",
        follow_up_date=date(2026, 8, 1),
    )
    ranked = rank_open_opportunities([opp])
    reasons = " | ".join(ranked[0].reasons)
    assert "Owner deferred" in reasons
    assert "deferred" in reasons.lower()
    assert "2026-08-01" in reasons


def test_assessed_apply_does_not_claim_awaiting_owner_action() -> None:
    """FR-009 keeps status=assessed after apply — wording must not mislead."""
    applied = make_opportunity(ID_A, status="assessed", decision="apply")
    undecided = make_opportunity(ID_B, status="assessed", decision=None)
    applied_reasons = rank_open_opportunities([applied])[0].reasons
    undecided_reasons = rank_open_opportunities([undecided])[0].reasons
    assert "awaiting owner action" not in " | ".join(applied_reasons).lower()
    assert "ready for package preparation" in " | ".join(applied_reasons)
    assert "awaiting owner decision" in " | ".join(undecided_reasons)


def test_sort_key_ordering_matches_algorithm() -> None:
    prioritise = make_opportunity(ID_A, pursuit_posture="prioritise")
    pursue = make_opportunity(ID_B, pursuit_posture="pursue")
    assert sort_key(prioritise) < sort_key(pursue)


def test_comparison_service_counts_excluded() -> None:
    opportunities = [
        make_opportunity(ID_A, pursuit_posture="prioritise"),
        make_opportunity(ID_B, status="accepted"),
        make_opportunity(ID_C, decision="skip"),
    ]
    comparison = OpportunityComparisonService().compare_open(
        opportunities,
        generated_at=make_opportunity(ID_A).updated_at,
    )
    assert comparison.open_count == 1
    assert comparison.excluded_count == 2
    assert comparison.owner_review_required is True
    assert comparison.open_only is True
    assert len(comparison.items) == 1
    assert comparison.items[0].rank == 1
