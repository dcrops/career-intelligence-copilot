"""Golden journey: persist trusted strategies → compare open opportunities (M4).

Composes FR-001–FR-005 fixture pipeline with OpportunityService persistence and
OpportunityComparisonService ranking. Offline only — no OpenAI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from career_intelligence.application_strategy import ApplicationStrategyService
from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunity_comparison import OpportunityComparisonService
from tests.unit.application_strategy.helpers import (
    job_analysis,
    job_tech_evidence,
    minimal_profile,
    opportunity_assessment,
    portfolio_match,
    valid_strategy_payload,
)
from tests.unit.opportunities.helpers import _StaticPayloadPlanner


def _fit_dimension(dimension: str, judgment: str) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "judgment": judgment,
        "summary": f"{dimension} fit is {judgment}.",
        "findings": [
            {
                "kind": "alignment",
                "summary": f"Synthetic {dimension} finding ({judgment}).",
                "importance": "material",
                "job_evidence": [
                    {
                        "source": "technology",
                        "item_index": 0,
                        "name": "Python",
                    }
                ],
                "profile_evidence": [{"source": "skill", "ref": "skill:Python"}],
            }
        ],
    }


def _persist(
    store: Path,
    *,
    company: str,
    title: str,
    source_url: str,
    posture: str,
    tier: str,
    technical_fit: str,
    commercial_fit: str,
    portfolio_fit: str,
) -> str:
    analysis = job_analysis(
        posting={
            "raw_text": f"{title} at {company}. Python required. Hybrid Melbourne.",
            "title": title,
            "company": company,
            "source_url": source_url,
        }
    )
    assessment = opportunity_assessment(
        analysis,
        technical_fit=_fit_dimension("technical", technical_fit),
        commercial_fit=_fit_dimension("commercial", commercial_fit),
        portfolio_fit=_fit_dimension("portfolio", portfolio_fit),
    )
    match = portfolio_match(analysis)
    profile = minimal_profile()
    effort_by_tier = {
        "platinum": "full",
        "gold": "targeted",
        "silver": "minimal",
        "bronze": "none",
    }
    evidence = [job_tech_evidence()]
    strategy = ApplicationStrategyService(
        _StaticPayloadPlanner(
            valid_strategy_payload(
                pursuit_posture=posture,
                application_tier=tier,
                effort_level=effort_by_tier[tier],
                reasons=[
                    {
                        "kind": "alignment",
                        "summary": "Synthetic strategy reason for ranking journey.",
                        "importance": "material",
                        "evidence": evidence,
                    }
                ],
                risks_or_gaps=[],
                manual_checks=[],
                next_actions=[
                    {
                        "kind": "consider_owner_review",
                        "summary": "Review this strategy before taking any external action.",
                        "evidence": evidence,
                    }
                ],
                portfolio_emphasis=[],
            )
        )
    ).plan(assessment, match, profile)
    opportunity = OpportunityService.from_path(store).create_from_strategy(
        posting=analysis.posting,
        job_analysis=analysis,
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    summary = opportunity.strategy_summary
    assert summary is not None
    assert summary.pursuit_posture == posture
    assert summary.application_tier == tier
    assert summary.technical_fit == technical_fit
    assert summary.commercial_fit == commercial_fit
    assert summary.portfolio_fit == portfolio_fit
    return opportunity.opportunity_id


def test_golden_ranked_comparison_stable_order(tmp_path: Path) -> None:
    """Owner-facing path: multiple persisted opportunities → explainable ranking."""
    id_prioritise = _persist(
        tmp_path,
        company="Harbour Labs",
        title="Applied AI Engineer",
        source_url="https://au.seek.com/job/10000001",
        posture="prioritise",
        tier="bronze",
        technical_fit="weak",
        commercial_fit="weak",
        portfolio_fit="weak",
    )
    id_pursue = _persist(
        tmp_path,
        company="Pay.com.au",
        title="AI Automation Engineer",
        source_url="https://au.seek.com/job/10000002",
        posture="pursue",
        tier="gold",
        technical_fit="moderate",
        commercial_fit="moderate",
        portfolio_fit="moderate",
    )
    id_consider_strong = _persist(
        tmp_path,
        company="Officeworks",
        title="AI Engineer",
        source_url="https://au.seek.com/job/10000003",
        posture="consider",
        tier="silver",
        technical_fit="strong",
        commercial_fit="strong",
        portfolio_fit="strong",
    )
    id_consider_weak = _persist(
        tmp_path,
        company="Bluefin Resources",
        title="AI Systems Developer",
        source_url="https://au.seek.com/job/10000004",
        posture="consider",
        tier="gold",
        technical_fit="mixed",
        commercial_fit="mixed",
        portfolio_fit="mixed",
    )

    service = OpportunityService.from_path(tmp_path)
    closed_id = _persist(
        tmp_path,
        company="Closed Corp",
        title="Former Role",
        source_url="https://au.seek.com/job/10000005",
        posture="prioritise",
        tier="platinum",
        technical_fit="strong",
        commercial_fit="strong",
        portfolio_fit="strong",
    )
    service.update_outcome(closed_id, status="withdrawn", outcome="withdrawn")

    skip_id = _persist(
        tmp_path,
        company="Skip Corp",
        title="Skipped Role",
        source_url="https://au.seek.com/job/10000006",
        posture="prioritise",
        tier="platinum",
        technical_fit="strong",
        commercial_fit="strong",
        portfolio_fit="strong",
    )
    service.record_decision(skip_id, "skip")

    opportunities = service.list_opportunities()
    comparison = OpportunityComparisonService().compare_open(opportunities)

    assert comparison.open_count == 4
    assert comparison.excluded_count == 2
    ordered = [item.opportunity_id for item in comparison.items]
    assert ordered == [
        id_prioritise,
        id_pursue,
        id_consider_strong,
        id_consider_weak,
    ]

    again = OpportunityComparisonService().compare_open(opportunities)
    assert [item.opportunity_id for item in again.items] == ordered

    assert any("prioritise" in reason for reason in comparison.items[0].reasons)
    assert any("Fit strength" in reason for reason in comparison.items[2].reasons)
    assert comparison.owner_review_required is True
