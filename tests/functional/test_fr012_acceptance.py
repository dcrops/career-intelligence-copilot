"""Functional acceptance for FR-012 Phase 2 subset — ranked open opportunities (M4).

Exercises only the public OpportunityComparisonService boundary with trusted
Opportunity aggregates. No OpenAI, re-analysis, or OpportunityService mutation.
"""

from __future__ import annotations

from datetime import UTC, datetime

import career_intelligence.opportunity_comparison as comparison_api
from career_intelligence.opportunity_comparison import (
    OpportunityComparison,
    OpportunityComparisonService,
    RankedOpportunity,
)
from tests.unit.opportunity_comparison.helpers import (
    ID_A,
    ID_B,
    ID_C,
    ID_D,
    ID_E,
    make_opportunity,
)


def test_public_api_exports() -> None:
    assert hasattr(comparison_api, "OpportunityComparisonService")
    assert hasattr(comparison_api, "OpportunityComparison")
    assert hasattr(comparison_api, "RankedOpportunity")


def test_compare_open_ranks_with_rationale() -> None:
    """Acceptance: open opportunities ranked with explainable reasons."""
    opportunities = [
        make_opportunity(
            ID_C,
            pursuit_posture="consider",
            application_tier="platinum",
            technical_fit="strong",
            commercial_fit="strong",
            portfolio_fit="strong",
            company="Consider Co",
        ),
        make_opportunity(
            ID_A,
            pursuit_posture="prioritise",
            application_tier="bronze",
            technical_fit="weak",
            commercial_fit="weak",
            portfolio_fit="weak",
            company="Prioritise Co",
        ),
        make_opportunity(
            ID_B,
            pursuit_posture="pursue",
            application_tier="gold",
            technical_fit="moderate",
            commercial_fit="moderate",
            portfolio_fit="moderate",
            company="Pursue Co",
        ),
        make_opportunity(ID_D, status="rejected", company="Closed Co"),
        make_opportunity(ID_E, decision="skip", company="Skipped Co"),
    ]

    comparison = OpportunityComparisonService().compare_open(
        opportunities,
        generated_at=datetime(2026, 7, 24, 1, 0, 0, tzinfo=UTC),
    )

    assert isinstance(comparison, OpportunityComparison)
    assert comparison.open_count == 3
    assert comparison.excluded_count == 2
    assert comparison.owner_review_required is True
    assert [item.opportunity_id for item in comparison.items] == [ID_A, ID_B, ID_C]

    for item in comparison.items:
        assert isinstance(item, RankedOpportunity)
        assert item.rank >= 1
        assert len(item.reasons) >= 1
        assert "Pursuit posture:" in item.reasons[0]


def test_fit_before_tier_within_same_posture() -> None:
    high_tier = make_opportunity(
        ID_A,
        pursuit_posture="consider",
        application_tier="gold",
        technical_fit="mixed",
        commercial_fit="mixed",
        portfolio_fit="mixed",
    )
    high_fit = make_opportunity(
        ID_B,
        pursuit_posture="consider",
        application_tier="silver",
        technical_fit="strong",
        commercial_fit="strong",
        portfolio_fit="strong",
    )
    comparison = OpportunityComparisonService().compare_open([high_tier, high_fit])
    assert [item.opportunity_id for item in comparison.items] == [ID_B, ID_A]


def test_empty_open_set() -> None:
    comparison = OpportunityComparisonService().compare_open(
        [make_opportunity(ID_A, status="withdrawn")]
    )
    assert comparison.open_count == 0
    assert comparison.items == []
    assert comparison.excluded_count == 1
