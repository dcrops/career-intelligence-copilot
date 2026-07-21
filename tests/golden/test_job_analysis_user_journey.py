"""Golden journeys for FR-002 Job Analysis via the fixture extractor."""

from __future__ import annotations

from career_intelligence.job_analysis import JobAnalysis, JobAnalysisService, JobPosting
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_ai_solutions_engineer,
    posting_ambiguous_seniority,
    posting_contract,
    posting_data_engineer,
    posting_missing_salary,
)


def _fixture_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def test_ai_engineer_posting_to_analysis_journey() -> None:
    """AI Engineer → JobPosting → JobAnalysisService → JobAnalysis (offline)."""
    posting = posting_ai_engineer()
    assert isinstance(posting, JobPosting)
    assert posting.title == "Senior AI Engineer"

    analysis = _fixture_service().analyse(posting)

    assert isinstance(analysis, JobAnalysis)
    assert analysis.posting is posting
    assert analysis.role_family.family == "ai_engineering"
    assert analysis.seniority.level == "senior"
    assert analysis.seniority.ambiguous is False
    assert analysis.location.summary == "Melbourne"
    assert analysis.work_arrangement.arrangement == "hybrid"
    assert analysis.work_arrangement.details == "3 days in the CBD office"
    assert analysis.employment.working_hours == "full_time"
    assert analysis.employment.engagement_type == "permanent"
    assert analysis.compensation.clarity == "stated"
    assert analysis.compensation.minimum == 150_000
    assert analysis.compensation.maximum == 180_000
    assert analysis.compensation.currency == "AUD"
    assert analysis.compensation.period == "year"

    tech_levels = {tech.name: tech.level for tech in analysis.technologies}
    assert tech_levels["Python"] == "required"
    assert tech_levels["LangChain"] == "preferred"
    assert all(tech.evidence for tech in analysis.technologies)
    assert analysis.responsibilities
    assert all(item.evidence for item in analysis.responsibilities)
    assert any(req.minimum_years == 5 for req in analysis.experience_requirements)


def test_data_engineer_journey_classifies_role_family() -> None:
    analysis = _fixture_service().analyse(posting_data_engineer())

    assert analysis.role_family.family == "data_engineering"
    assert {tech.name for tech in analysis.technologies} >= {"Python", "SQL"}
    assert analysis.compensation.currency == "AUD"


def test_ai_solutions_engineer_journey() -> None:
    analysis = _fixture_service().analyse(posting_ai_solutions_engineer())

    assert analysis.role_family.family == "ai_solutions"
    assert analysis.location.summary == "Brisbane"
    assert analysis.employment.engagement_type == "permanent"


def test_ambiguous_seniority_and_missing_salary_journeys() -> None:
    ambiguous = _fixture_service().analyse(posting_ambiguous_seniority())
    assert ambiguous.seniority.ambiguous is True
    assert ambiguous.seniority.level == "unknown"
    assert "senior" in ambiguous.seniority.candidate_levels
    assert "lead" in ambiguous.seniority.candidate_levels

    missing = _fixture_service().analyse(posting_missing_salary())
    assert missing.compensation.clarity == "unstated"
    assert missing.compensation.minimum is None


def test_contract_day_rate_journey() -> None:
    analysis = _fixture_service().analyse(posting_contract())

    assert analysis.employment.engagement_type == "contract"
    assert analysis.compensation.period == "day"
    assert analysis.work_arrangement.arrangement == "hybrid"
