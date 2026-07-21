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
from career_intelligence.job_analysis.extraction import JobAnalysisExtraction
from career_intelligence.job_analysis.extractor import JobAnalysisPayload
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    REPRESENTATIVE_POSTINGS,
    analysis_for_ai_engineer,
    analysis_for_ambiguous_seniority,
    analysis_for_missing_salary,
    posting_ai_engineer,
    posting_ambiguous_seniority,
    posting_contract,
    posting_missing_salary,
    posting_remote,
)
from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor


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


class _FakeResponses:
    def __init__(self, result: object) -> None:
        self._result = result

    def parse(self, **kwargs: object) -> object:
        return self._result


class _FakeOpenAI:
    def __init__(self, result: object) -> None:
        self.responses = _FakeResponses(result)


class _FakeParseResult:
    def __init__(self, output_parsed: object) -> None:
        self.output_parsed = output_parsed
        self.output: list[object] = []


def _openai_service_with_payload(payload: dict[str, object]) -> JobAnalysisService:
    extraction = JobAnalysisExtraction.model_validate(payload)
    client = _FakeOpenAI(_FakeParseResult(extraction))
    return JobAnalysisService(OpenAIJobExtractor(client=client))


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


def test_openai_extractor_through_service_returns_trusted_job_analysis() -> None:
    posting = posting_ai_engineer()
    service = _openai_service_with_payload(analysis_for_ai_engineer())

    analysis = service.analyse(posting)

    assert isinstance(analysis, JobAnalysis)
    assert analysis.posting is posting
    assert analysis.role_family.family == "ai_engineering"
    assert analysis.seniority.level == "senior"
    assert {tech.name: tech.level for tech in analysis.technologies} == {
        "Python": "required",
        "LangChain": "preferred",
    }
    assert all(tech.evidence for tech in analysis.technologies)


def test_openai_extractor_preserves_ambiguity_through_service() -> None:
    analysis = _openai_service_with_payload(analysis_for_ambiguous_seniority()).analyse(
        posting_ambiguous_seniority()
    )

    assert analysis.seniority.ambiguous is True
    assert analysis.seniority.level == "unknown"
    assert set(analysis.seniority.candidate_levels) == {"senior", "lead"}


def test_openai_extractor_preserves_unstated_compensation_through_service() -> None:
    analysis = _openai_service_with_payload(analysis_for_missing_salary()).analyse(
        posting_missing_salary()
    )

    assert analysis.compensation.clarity == "unstated"
    assert analysis.compensation.minimum is None
    assert analysis.compensation.evidence == []


_BODY_WITHOUT_SENIORITY = """
AI Engineer role for production LLM applications.

Responsibilities
• Build and maintain LLM applications using Python

Requirements
• Strong Python required
• Production LLM experience required

Location & employment
Hybrid Melbourne. Full-time permanent.
""".strip()


def _base_payload_for_title_seniority(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [{"excerpt": "AI Engineer", "section": "Job title"}],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [{"excerpt": "Strong Python required", "section": "requirements"}],
            }
        ],
        "responsibilities": [
            {
                "description": "Build and maintain LLM applications using Python",
                "evidence": [
                    {
                        "excerpt": "Build and maintain LLM applications using Python",
                        "section": "responsibilities",
                    }
                ],
            }
        ],
        "compensation": {"clarity": "unstated"},
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [{"excerpt": "Hybrid Melbourne", "section": "location"}],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "evidence": [{"excerpt": "Hybrid Melbourne", "section": "location"}],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [{"excerpt": "Full-time permanent", "section": "employment"}],
        },
        "experience_requirements": [],
    }
    payload.update(overrides)
    return payload


def test_principal_only_in_title_yields_principal_seniority() -> None:
    posting = JobPosting(
        title="Principal AI Engineer",
        company="ABC Pty Ltd",
        raw_text=_BODY_WITHOUT_SENIORITY,
    )
    assert "Principal" not in posting.raw_text

    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            seniority={
                "level": "principal",
                "ambiguous": False,
                "evidence": [{"excerpt": "Principal AI Engineer", "section": "Job title"}],
            }
        )
    ).analyse(posting)

    assert analysis.posting is posting
    assert analysis.seniority.level == "principal"
    assert analysis.seniority.ambiguous is False
    assert analysis.seniority.evidence[0].section == "Job title"
    assert analysis.seniority.evidence[0].excerpt == "Principal AI Engineer"


def test_senior_only_in_title_yields_senior_seniority() -> None:
    posting = JobPosting(
        title="Senior AI Engineer",
        company="ABC Pty Ltd",
        raw_text=_BODY_WITHOUT_SENIORITY,
    )
    assert "Senior" not in posting.raw_text

    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            seniority={
                "level": "senior",
                "ambiguous": False,
                "evidence": [{"excerpt": "Senior AI Engineer", "section": "Job title"}],
            }
        )
    ).analyse(posting)

    assert analysis.seniority.level == "senior"
    assert analysis.seniority.evidence[0].section == "Job title"


def test_no_seniority_anywhere_yields_unknown() -> None:
    posting = JobPosting(
        title="AI Engineer",
        company="ABC Pty Ltd",
        raw_text=_BODY_WITHOUT_SENIORITY,
    )

    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            seniority={"level": "unknown", "ambiguous": False, "candidate_levels": []}
        )
    ).analyse(posting)

    assert analysis.seniority.level == "unknown"
    assert analysis.seniority.ambiguous is False
    assert analysis.seniority.candidate_levels == []
    assert analysis.seniority.evidence == []


def test_conflicting_title_and_body_seniority_is_ambiguous() -> None:
    body = (
        _BODY_WITHOUT_SENIORITY
        + "\n\nThis is a mid-level individual contributor role reporting to a Lead."
    )
    posting = JobPosting(
        title="Senior AI Engineer",
        company="ABC Pty Ltd",
        raw_text=body,
    )

    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            seniority={
                "level": "unknown",
                "ambiguous": True,
                "candidate_levels": ["senior", "mid"],
                "evidence": [
                    {"excerpt": "Senior AI Engineer", "section": "Job title"},
                    {
                        "excerpt": "mid-level individual contributor role",
                        "section": "about",
                    },
                ],
            }
        )
    ).analyse(posting)

    assert analysis.seniority.ambiguous is True
    assert analysis.seniority.level == "unknown"
    assert set(analysis.seniority.candidate_levels) == {"senior", "mid"}
    sections = {item.section for item in analysis.seniority.evidence}
    assert "Job title" in sections


def test_explicit_full_time_permanent_employment_through_service() -> None:
    posting = JobPosting(
        title="AI Engineer",
        company="Example Co",
        raw_text="Build LLM apps with Python. Full-time permanent role. Hybrid Melbourne.",
    )
    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            employment={
                "working_hours": "full_time",
                "engagement_type": "permanent",
                "evidence": [
                    {"excerpt": "Full-time permanent role", "section": "employment"}
                ],
            }
        )
    ).analyse(posting)

    assert analysis.employment.working_hours == "full_time"
    assert analysis.employment.engagement_type == "permanent"
    assert analysis.employment.evidence


def test_explicit_contract_engagement_through_service() -> None:
    posting = JobPosting(
        title="AI Engineer",
        company="Example Co",
        raw_text="Build LLM apps with Python. 6 month contract. Hybrid Melbourne.",
    )
    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            employment={
                "working_hours": "unspecified",
                "engagement_type": "contract",
                "evidence": [{"excerpt": "6 month contract", "section": "employment"}],
            }
        )
    ).analyse(posting)

    assert analysis.employment.working_hours == "unspecified"
    assert analysis.employment.engagement_type == "contract"
    assert analysis.employment.evidence


def test_explicit_part_time_working_hours_through_service() -> None:
    posting = JobPosting(
        title="AI Engineer",
        company="Example Co",
        raw_text="Build LLM apps with Python. Part-time. Hybrid Melbourne.",
    )
    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            employment={
                "working_hours": "part_time",
                "engagement_type": "unspecified",
                "evidence": [{"excerpt": "Part-time", "section": "employment"}],
            }
        )
    ).analyse(posting)

    assert analysis.employment.working_hours == "part_time"
    assert analysis.employment.engagement_type == "unspecified"


def test_recruiter_tone_does_not_imply_employment_through_service() -> None:
    posting = JobPosting(
        title="Software Engineer",
        company="Example Co",
        raw_text=(
            "Join our team. In-office environment. Junior opportunity. Great career. "
            "Build software with Python."
        ),
    )
    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            employment={
                "working_hours": "unspecified",
                "engagement_type": "unspecified",
                "evidence": [],
            }
        )
    ).analyse(posting)

    assert analysis.employment.working_hours == "unspecified"
    assert analysis.employment.engagement_type == "unspecified"
    assert analysis.employment.evidence == []


def test_software_engineer_ai_live_eval_employment_remains_unspecified() -> None:
    """Live Job #2 regression: office/seniority cues must not invent employment."""
    posting = JobPosting(
        title="Software Engineer (AI)",
        company="Example Co",
        raw_text=(
            "This is a junior-to-mid level opportunity to join our engineering team. "
            "You will work in an in-office environment building AI-assisted products "
            "with Python. Great career growth."
        ),
    )
    assert "full-time" not in posting.raw_text.lower()
    assert "permanent" not in posting.raw_text.lower()
    assert "contract" not in posting.raw_text.lower()

    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            role_family={
                "family": "software_engineering",
                "evidence": [
                    {"excerpt": "Software Engineer (AI)", "section": "Job title"}
                ],
            },
            seniority={
                "level": "unknown",
                "ambiguous": True,
                "candidate_levels": ["entry", "mid"],
                "evidence": [
                    {
                        "excerpt": "junior-to-mid level opportunity",
                        "section": "about",
                    }
                ],
            },
            work_arrangement={
                "arrangement": "onsite",
                "details": "in-office environment",
                "evidence": [
                    {"excerpt": "in-office environment", "section": "location"}
                ],
            },
            employment={
                "working_hours": "unspecified",
                "engagement_type": "unspecified",
                "evidence": [],
            },
        )
    ).analyse(posting)

    assert analysis.employment.working_hours == "unspecified"
    assert analysis.employment.engagement_type == "unspecified"
    assert analysis.employment.evidence == []


def test_software_engineer_ai_known_claims_require_evidence() -> None:
    """v4 regression: known role family / tech / responsibilities must carry evidence."""
    posting = JobPosting(
        title="Software Engineer (AI)",
        company="Example Co",
        raw_text=(
            "Software Engineer (AI). Build products with Python, React, TypeScript, "
            "C#, Node.js, SQL, AWS, Docker and CI/CD. Responsibilities include designing "
            "APIs, collaborating with product, and shipping AI-assisted features. "
            "Junior-to-mid level opportunity. In-office environment."
        ),
    )
    analysis = _openai_service_with_payload(
        {
            "role_family": {
                "family": "software_engineering",
                "evidence": [
                    {"excerpt": "Software Engineer (AI)", "section": "Job title"}
                ],
            },
            "seniority": {
                "level": "unknown",
                "ambiguous": True,
                "candidate_levels": ["entry", "mid"],
                "evidence": [
                    {
                        "excerpt": "Junior-to-mid level opportunity",
                        "section": "about",
                    }
                ],
            },
            "technologies": [
                {
                    "name": name,
                    "level": "required",
                    "evidence": [{"excerpt": name, "section": "requirements"}],
                }
                for name in (
                    "Python",
                    "React",
                    "TypeScript",
                    "C#",
                    "Node.js",
                    "SQL",
                    "AWS",
                    "Docker",
                    "CI/CD",
                )
            ],
            "responsibilities": [
                {
                    "description": description,
                    "evidence": [{"excerpt": description, "section": "responsibilities"}],
                }
                for description in (
                    "designing APIs",
                    "collaborating with product",
                    "shipping AI-assisted features",
                )
            ],
            "compensation": {"clarity": "unstated"},
            "location": {"clarity": "unstated"},
            "work_arrangement": {
                "arrangement": "onsite",
                "details": "in-office environment",
                "evidence": [
                    {"excerpt": "In-office environment", "section": "location"}
                ],
            },
            "employment": {
                "working_hours": "unspecified",
                "engagement_type": "unspecified",
                "evidence": [],
            },
            "experience_requirements": [],
        }
    ).analyse(posting)

    assert analysis.role_family.family == "software_engineering"
    assert analysis.role_family.evidence
    assert len(analysis.technologies) == 9
    assert all(tech.evidence for tech in analysis.technologies)
    assert len(analysis.responsibilities) == 3
    assert all(item.evidence for item in analysis.responsibilities)
    assert analysis.employment.working_hours == "unspecified"
    assert analysis.employment.engagement_type == "unspecified"


def test_known_technology_with_empty_evidence_fails_through_service() -> None:
    posting = JobPosting(
        title="Software Engineer (AI)",
        company="Example Co",
        raw_text="Build products with Python. In-office environment.",
    )
    bad_payload = _base_payload_for_title_seniority(
        technologies=[
            {
                "name": "Python",
                "level": "required",
                "evidence": [],
            }
        ]
    )
    client = _FakeOpenAI(_FakeParseResult(bad_payload))
    service = JobAnalysisService(OpenAIJobExtractor(client=client))

    with pytest.raises(JobAnalysisValidationError) as raised:
        service.analyse(posting)

    assert any("evidence" in error.msg.lower() for error in raised.value.errors)


def test_principal_ai_engineer_live_eval_employment_remains_unspecified() -> None:
    """Live Job #1 regression: title seniority must not invent employment terms."""
    posting = JobPosting(
        title="Principal AI Engineer",
        company="Example Co",
        raw_text=_BODY_WITHOUT_SENIORITY.replace(
            "Full-time permanent.",
            "Hybrid Melbourne office presence expected.",
        ),
    )
    assert "full-time" not in posting.raw_text.lower()
    assert "permanent" not in posting.raw_text.lower()
    assert "contract" not in posting.raw_text.lower()

    analysis = _openai_service_with_payload(
        _base_payload_for_title_seniority(
            seniority={
                "level": "principal",
                "ambiguous": False,
                "evidence": [
                    {"excerpt": "Principal AI Engineer", "section": "Job title"}
                ],
            },
            employment={
                "working_hours": "unspecified",
                "engagement_type": "unspecified",
                "evidence": [],
            },
        )
    ).analyse(posting)

    assert analysis.seniority.level == "principal"
    assert analysis.employment.working_hours == "unspecified"
    assert analysis.employment.engagement_type == "unspecified"
    assert analysis.employment.evidence == []


def test_inferred_employment_without_evidence_fails_through_service() -> None:
    posting = JobPosting(
        title="Software Engineer (AI)",
        company="Example Co",
        raw_text="Junior-to-mid level opportunity. In-office environment. Python.",
    )
    # Bypass JobAnalysisExtraction pre-validation: live models can emit this shape.
    bad_payload = _base_payload_for_title_seniority(
        employment={
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [],
        }
    )
    client = _FakeOpenAI(_FakeParseResult(bad_payload))
    service = JobAnalysisService(OpenAIJobExtractor(client=client))

    with pytest.raises(JobAnalysisValidationError) as raised:
        service.analyse(posting)

    assert any("evidence" in error.msg.lower() for error in raised.value.errors)


def test_public_api_exports_service_and_errors_not_extractors() -> None:
    assert "JobAnalysisService" in job_analysis_api.__all__
    assert "JobAnalysisError" in job_analysis_api.__all__
    assert "JobAnalysisValidationError" in job_analysis_api.__all__
    assert "JobExtractor" not in job_analysis_api.__all__
    assert "JobAnalysisPayload" not in job_analysis_api.__all__
    assert "FixtureExtractor" not in job_analysis_api.__all__
    assert "OpenAIJobExtractor" not in job_analysis_api.__all__
    assert "JobAnalysisExtraction" not in job_analysis_api.__all__
    assert not hasattr(job_analysis_api, "JobExtractor")
    assert not hasattr(job_analysis_api, "JobAnalysisPayload")
    assert not hasattr(job_analysis_api, "FixtureExtractor")
    assert not hasattr(job_analysis_api, "OpenAIJobExtractor")
    assert not hasattr(job_analysis_api, "JobAnalysisExtraction")


def test_public_api_does_not_expose_fixture_module() -> None:
    assert "fixtures" not in job_analysis_api.__all__
    assert not hasattr(job_analysis_api, "FIXTURE_BUILDERS")


def test_downstream_modules_do_not_import_internal_extractors() -> None:
    source_root = Path(__file__).parents[2] / "src" / "career_intelligence"
    allowed_by_name = {
        "extractor.py",
        "extraction.py",
        "extraction_prompt.py",
        "fixture_extractor.py",
        "fixtures.py",
        "openai_extractor.py",
    }

    for source_file in source_root.rglob("*.py"):
        if source_file.name in allowed_by_name:
            continue
        text = source_file.read_text(encoding="utf-8")
        assert "job_analysis.fixture_extractor" not in text
        assert "job_analysis.fixtures" not in text
        assert "job_analysis.openai_extractor" not in text
        assert "job_analysis.extraction" not in text
        if source_file.name != "service.py":
            assert "job_analysis.extractor" not in text
