"""Functional acceptance tests for FR-002 Job Analysis (public service boundary)."""

from __future__ import annotations

from pathlib import Path

import career_intelligence.job_analysis as job_analysis_api
import pytest
from career_intelligence.job_analysis import (
    JobAnalysis,
    JobAnalysisError,
    JobAnalysisService,
    JobAnalysisValidationError,
    JobPosting,
)
from career_intelligence.job_analysis.extractor import JobAnalysisPayload
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    REPRESENTATIVE_POSTINGS,
    posting_ai_engineer,
    posting_ambiguous_seniority,
    posting_contract,
    posting_missing_salary,
    posting_remote,
)


def _fixture_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


class _InvalidEvidenceExtractor:
    """Returns a mapping that violates evidence rules."""

    def extract(self, posting: JobPosting) -> JobAnalysisPayload:
        return {
            "role_family": {"family": "ai_engineering"},
            "seniority": {"level": "senior", "ambiguous": False},
            "technologies": [],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "location": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
            "employment": {},
            "experience_requirements": [],
        }


def test_valid_extraction_returns_job_analysis() -> None:
    service = _fixture_service()
    posting = posting_ai_engineer()

    analysis = service.analyse(posting)

    assert isinstance(analysis, JobAnalysis)
    assert analysis.posting is posting
    assert analysis.role_family.family == "ai_engineering"
    assert analysis.seniority.level == "senior"
    assert analysis.work_arrangement.arrangement == "hybrid"
    assert analysis.compensation.clarity == "stated"
    assert analysis.compensation.currency == "AUD"
    assert {tech.name: tech.level for tech in analysis.technologies} == {
        "Python": "required",
        "LangChain": "preferred",
    }


def test_unknown_posting_raises_stable_public_error() -> None:
    service = _fixture_service()
    posting = JobPosting(
        title="Mystery Role",
        company="Unknown Co",
        raw_text="A posting with no fixture marker and no extractor support.",
    )

    with pytest.raises(JobAnalysisError, match="No fixture analysis") as raised:
        service.analyse(posting)

    assert not isinstance(raised.value, JobAnalysisValidationError)


def test_validation_failures_translate_to_public_error() -> None:
    service = JobAnalysisService(_InvalidEvidenceExtractor())
    posting = posting_ai_engineer()

    with pytest.raises(JobAnalysisValidationError) as raised:
        service.analyse(posting)

    assert raised.value.errors
    assert all(error.loc and error.msg and error.type for error in raised.value.errors)
    assert any("evidence" in error.msg.lower() for error in raised.value.errors)


def test_extraction_is_deterministic() -> None:
    service = _fixture_service()
    posting = posting_ai_engineer()

    first = service.analyse(posting)
    second = service.analyse(posting)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_returned_models_are_stable_and_serialisable() -> None:
    analysis = _fixture_service().analyse(posting_ai_engineer())
    dumped = analysis.model_dump(mode="json")

    assert set(dumped) >= {
        "posting",
        "role_family",
        "seniority",
        "technologies",
        "responsibilities",
        "compensation",
        "location",
        "work_arrangement",
        "employment",
        "experience_requirements",
    }
    assert "technical_fit" not in dumped
    assert JobAnalysis.model_validate(dumped) == analysis


@pytest.mark.parametrize(
    ("key", "expected_family", "expected_arrangement"),
    [
        ("ai_engineer", "ai_engineering", "hybrid"),
        ("applied_ai_engineer", "ai_engineering", "hybrid"),
        ("data_engineer", "data_engineering", "hybrid"),
        ("ai_solutions_engineer", "ai_solutions", "hybrid"),
        ("remote", "ai_engineering", "remote"),
        ("contract", "ai_engineering", "hybrid"),
    ],
)
def test_representative_fixtures_extract(
    key: str, expected_family: str, expected_arrangement: str
) -> None:
    posting = REPRESENTATIVE_POSTINGS[key]()
    analysis = _fixture_service().analyse(posting)

    assert analysis.role_family.family == expected_family
    assert analysis.work_arrangement.arrangement == expected_arrangement


def test_ambiguous_seniority_fixture_preserves_conflict() -> None:
    analysis = _fixture_service().analyse(posting_ambiguous_seniority())

    assert analysis.seniority.ambiguous is True
    assert analysis.seniority.level == "unknown"
    assert set(analysis.seniority.candidate_levels) == {"senior", "lead"}
    assert analysis.seniority.evidence


def test_missing_salary_fixture_does_not_invent_compensation() -> None:
    analysis = _fixture_service().analyse(posting_missing_salary())

    assert analysis.compensation.clarity == "unstated"
    assert analysis.compensation.minimum is None
    assert analysis.compensation.maximum is None
    assert analysis.compensation.evidence == []


def test_contract_fixture_uses_day_rate_and_contract_engagement() -> None:
    analysis = _fixture_service().analyse(posting_contract())

    assert analysis.employment.engagement_type == "contract"
    assert analysis.employment.working_hours == "full_time"
    assert analysis.compensation.period == "day"
    assert analysis.compensation.minimum == 850
    assert analysis.compensation.maximum == 950


def test_remote_fixture_records_remote_australia() -> None:
    analysis = _fixture_service().analyse(posting_remote())

    assert analysis.work_arrangement.arrangement == "remote"
    assert analysis.location.summary == "Remote Australia"


def test_public_api_exports_service_and_errors_not_extractors() -> None:
    assert "JobAnalysisService" in job_analysis_api.__all__
    assert "JobAnalysisError" in job_analysis_api.__all__
    assert "JobAnalysisValidationError" in job_analysis_api.__all__
    assert "JobExtractor" not in job_analysis_api.__all__
    assert "JobAnalysisPayload" not in job_analysis_api.__all__
    assert "FixtureExtractor" not in job_analysis_api.__all__
    assert not hasattr(job_analysis_api, "JobExtractor")
    assert not hasattr(job_analysis_api, "JobAnalysisPayload")
    assert not hasattr(job_analysis_api, "FixtureExtractor")


def test_public_api_does_not_expose_fixture_module() -> None:
    assert "fixtures" not in job_analysis_api.__all__
    assert not hasattr(job_analysis_api, "FIXTURE_BUILDERS")


def test_downstream_modules_do_not_import_internal_extractors() -> None:
    source_root = Path(__file__).parents[2] / "src" / "career_intelligence"
    allowed_by_name = {
        "extractor.py",
        "fixture_extractor.py",
        "fixtures.py",
    }

    for source_file in source_root.rglob("*.py"):
        if source_file.name in allowed_by_name:
            continue
        text = source_file.read_text(encoding="utf-8")
        assert "job_analysis.fixture_extractor" not in text
        assert "job_analysis.fixtures" not in text
        if source_file.name != "service.py":
            assert "job_analysis.extractor" not in text
