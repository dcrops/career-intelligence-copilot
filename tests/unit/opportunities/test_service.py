"""Unit tests for OpportunityService (M1)."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.opportunities import OpportunityService

from .helpers import create_opportunity, trusted_pipeline


def test_create_from_strategy_preserves_summary(tmp_path: Path) -> None:
    posting, analysis, assessment, match, strategy = trusted_pipeline()
    service = OpportunityService.from_path(tmp_path)
    opportunity = service.create_from_strategy(
        posting=posting,
        job_analysis=analysis,
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    assert opportunity.status == "assessed"
    assert opportunity.strategy_summary.pursuit_posture == strategy.pursuit_posture
    assert opportunity.strategy_summary.application_tier == strategy.application_tier
    assert opportunity.strategy_summary.practical_value == strategy.practical_value
    assert (
        opportunity.strategy_summary.technical_fit == assessment.technical_fit.judgment
    )
    assert (
        opportunity.strategy_summary.commercial_fit
        == assessment.commercial_fit.judgment
    )
    assert (
        opportunity.strategy_summary.portfolio_fit == assessment.portfolio_fit.judgment
    )
    assert opportunity.identity.source_kind == "seek"
    assert opportunity.identity.platform_job_id == "93487188"
    assert len(opportunity.artifact_paths) == 5


def test_get_and_list_through_public_service(tmp_path: Path) -> None:
    service, first, _ = create_opportunity(tmp_path, company="First Co")
    _, second, _ = create_opportunity(tmp_path, company="Second Co")
    assert service.get(first.opportunity_id).identity.company == "First Co"
    ids = [item.opportunity_id for item in service.list_opportunities()]
    assert set(ids) == {first.opportunity_id, second.opportunity_id}
    # Newest first (ULID descending).
    assert ids == sorted(ids, reverse=True)


def test_create_does_not_import_openai(tmp_path: Path, monkeypatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "openai", None)
    create_opportunity(tmp_path)
