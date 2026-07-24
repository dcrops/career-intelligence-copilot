"""Tests for M4a identity enrichment persistence, CLI, and backfill."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunity_comparison import OpportunityComparisonService
from tests.unit.opportunities.helpers import create_opportunity, trusted_pipeline

runner = CliRunner()


def test_persisted_opportunity_keeps_posting_identity(tmp_path: Path) -> None:
    service, opportunity, (posting, *_rest) = create_opportunity(
        tmp_path,
        company="Maincode",
        title="AI Infrastructure Engineer",
    )
    assert opportunity.identity.title == "AI Infrastructure Engineer"
    assert opportunity.identity.company == "Maincode"
    assert posting.title == "AI Infrastructure Engineer"
    reloaded = service.get(opportunity.opportunity_id)
    assert reloaded.identity.title == "AI Infrastructure Engineer"
    assert reloaded.identity.company == "Maincode"


def test_list_and_compare_render_title_and_company(tmp_path: Path) -> None:
    _, opportunity, _ = create_opportunity(
        tmp_path,
        company="Maincode",
        title="AI Infrastructure Engineer",
    )
    listed = runner.invoke(app, ["opportunity", "list", "--dir", str(tmp_path)])
    assert listed.exit_code == 0
    assert "Maincode" in listed.output
    assert "AI Infrastructure Engineer" in listed.output

    compared = runner.invoke(app, ["opportunity", "compare", "--dir", str(tmp_path)])
    assert compared.exit_code == 0
    assert "Maincode" in compared.output
    assert "AI Infrastructure Engineer" in compared.output
    assert opportunity.opportunity_id in compared.output


def test_missing_identity_renders_explicit_unset(tmp_path: Path) -> None:
    posting, analysis, assessment, match, strategy = trusted_pipeline(
        company="Temp",
        title="Temp",
    )
    # Simulate historical blank identity by clearing after strategy create path
    blank_posting = JobPosting(raw_text=posting.raw_text)
    service = OpportunityService.from_path(tmp_path)
    opportunity = service.create_from_strategy(
        posting=blank_posting,
        job_analysis=analysis.model_copy(update={"posting": blank_posting}),
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    assert opportunity.identity.title is None
    assert opportunity.identity.company is None

    listed = runner.invoke(app, ["opportunity", "list", "--dir", str(tmp_path)])
    assert listed.exit_code == 0
    assert "—" in listed.output


def test_backfill_identity_from_posting_artifact(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(
        tmp_path,
        company="Pay.com.au",
        title="AI Automation Engineer",
    )
    # Simulate index identity loss while posting.json remains trusted.
    blank_identity = opportunity.identity.model_copy(
        update={"title": None, "company": None}
    )
    service._store.save(  # noqa: SLF001
        opportunity.model_copy(update={"identity": blank_identity}, deep=True)
    )
    results = service.backfill_identity_from_posting_artifacts()
    updated = [item for item in results if item["result"] == "updated"]
    assert len(updated) == 1
    restored = service.get(opportunity.opportunity_id)
    assert restored.identity.title == "AI Automation Engineer"
    assert restored.identity.company == "Pay.com.au"


def test_backfill_skips_when_posting_also_blank(tmp_path: Path) -> None:
    posting, analysis, assessment, match, strategy = trusted_pipeline()
    blank_posting = JobPosting(raw_text=posting.raw_text)
    service = OpportunityService.from_path(tmp_path)
    opportunity = service.create_from_strategy(
        posting=blank_posting,
        job_analysis=analysis.model_copy(update={"posting": blank_posting}),
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    results = service.backfill_identity_from_posting_artifacts()
    assert results[0]["opportunity_id"] == opportunity.opportunity_id
    assert results[0]["result"] == "skipped"
    assert "lacks title/company" in str(results[0]["reason"])


def test_comparison_service_receives_identity() -> None:
    # Pure ranking still receives company/title from Opportunity identity.
    from tests.unit.opportunity_comparison.helpers import ID_A, make_opportunity

    ranked = OpportunityComparisonService().compare_open(
        [
            make_opportunity(
                ID_A,
                company="Maincode",
                title="AI Infrastructure Engineer",
            )
        ]
    )
    assert ranked.items[0].company == "Maincode"
    assert ranked.items[0].title == "AI Infrastructure Engineer"
