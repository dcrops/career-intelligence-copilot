"""Hybrid role-family classification regressions for FR-002."""

from typing import get_args

import pytest
from career_intelligence.job_analysis import (
    JobAnalysisService,
    JobAnalysisValidationError,
    JobPosting,
)
from career_intelligence.job_analysis.extraction import JobAnalysisExtraction
from career_intelligence.job_analysis.extraction_prompt import (
    EXTRACTION_INSTRUCTIONS_V1,
    EXTRACTION_PROMPT_VERSION,
)
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    analysis_for_ai_engineer,
    analysis_for_data_engineer,
    analysis_for_junior_software_devops,
    analysis_for_network_engineer_automation_ai,
    posting_data_engineer,
    posting_junior_software_devops,
    posting_network_engineer_automation_ai,
)
from career_intelligence.job_analysis.models import RoleFamily, RoleFamilyAssessment
from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor
from pydantic import ValidationError

from .test_openai_extractor import _FakeOpenAI, _FakeParseResult, _valid_extraction_payload


def test_prompt_version_is_v8_with_hybrid_guidance() -> None:
    assert EXTRACTION_PROMPT_VERSION == "v8"
    text = EXTRACTION_INSTRUCTIONS_V1.casefold()
    assert "network_engineering" in text
    assert "hybrid" in text
    assert "primary profession" in text
    assert "evidence=[]" in text
    assert "ai product manager" in text
    assert "data engineer with genai" in text


def test_network_engineering_is_supported_role_family() -> None:
    assert "network_engineering" in get_args(RoleFamily)


def test_network_engineer_fixture_classifies_network_not_other() -> None:
    analysis = JobAnalysisService(FixtureExtractor()).analyse(
        posting_network_engineer_automation_ai()
    )

    assert analysis.role_family.family == "network_engineering"
    assert analysis.role_family.family != "other"
    assert analysis.role_family.evidence
    tech_names = {tech.name.casefold() for tech in analysis.technologies}
    assert "llms" in tech_names or "llm" in tech_names
    assert "rag" in tech_names
    assert any("python" in name for name in tech_names)


def test_data_engineer_with_ai_capabilities_stays_data_engineering() -> None:
    analysis = JobAnalysisService(FixtureExtractor()).analyse(posting_data_engineer())
    assert analysis.role_family.family == "data_engineering"
    assert analysis.role_family.family != "ai_engineering"


def test_software_engineer_building_ai_features_stays_software() -> None:
    analysis = JobAnalysisService(FixtureExtractor()).analyse(
        posting_junior_software_devops()
    )
    assert analysis.role_family.family == "software_engineering"
    assert analysis.role_family.family != "ai_engineering"


def test_ai_product_manager_uses_ai_adjacent_not_ai_engineering() -> None:
    payload = _valid_extraction_payload(
        role_family={
            "family": "ai_adjacent",
            "evidence": [
                {
                    "excerpt": "AI Product Manager — own roadmap and prioritisation",
                    "section": "Job title",
                }
            ],
        },
        seniority={
            "level": "mid",
            "ambiguous": False,
            "evidence": [{"excerpt": "AI Product Manager", "section": "Job title"}],
        },
        technologies=[
            {
                "name": "product discovery",
                "level": "required",
                "evidence": [{"excerpt": "product discovery", "section": "duties"}],
            }
        ],
        responsibilities=[
            {
                "description": "Own roadmap and prioritisation for AI products",
                "evidence": [{"excerpt": "own roadmap", "section": "duties"}],
            }
        ],
    )
    extraction = JobAnalysisExtraction.model_validate(payload)
    assert extraction.role_family.family == "ai_adjacent"
    assert extraction.role_family.family != "ai_engineering"
    assert extraction.role_family.evidence


def test_other_requires_evidence_like_any_known_family() -> None:
    with pytest.raises(ValidationError, match="known role family requires"):
        RoleFamilyAssessment.model_validate({"family": "other", "evidence": []})

    accepted = RoleFamilyAssessment.model_validate(
        {
            "family": "other",
            "evidence": [
                {
                    "excerpt": "Facilities Operations Coordinator",
                    "section": "Job title",
                }
            ],
        }
    )
    assert accepted.family == "other"
    assert accepted.evidence


def test_mocked_other_without_evidence_fails_openai_extractor() -> None:
    client = _FakeOpenAI(
        result=_FakeParseResult(
            output_parsed={
                "role_family": {"family": "other", "evidence": []},
                "seniority": {"level": "unknown", "ambiguous": False},
                "technologies": [],
                "responsibilities": [],
                "compensation": {"clarity": "unstated"},
                "location": {"clarity": "unstated"},
                "work_arrangement": {"arrangement": "unspecified"},
                "employment": {},
                "experience_requirements": [],
            }
        )
    )
    extractor = OpenAIJobExtractor(client=client)
    posting = JobPosting(
        title="Network Engineer - Automation & AI",
        raw_text="Access Network Engineer. Layer 2 & 3 networking.",
    )
    with pytest.raises((JobAnalysisValidationError, ValidationError)):
        extractor.extract(posting)


def test_mocked_network_engineering_with_evidence_parses() -> None:
    extraction = JobAnalysisExtraction.model_validate(
        analysis_for_network_engineer_automation_ai()
    )
    client = _FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    payload = OpenAIJobExtractor(client=client).extract(
        posting_network_engineer_automation_ai()
    )

    assert payload["role_family"]["family"] == "network_engineering"
    assert payload["role_family"]["evidence"]
    assert any(
        "Layer 2" in item["excerpt"] or "Access Network" in item["excerpt"]
        for item in payload["role_family"]["evidence"]
    )


def test_existing_fixture_payloads_still_validate() -> None:
    for builder in (
        analysis_for_ai_engineer,
        analysis_for_data_engineer,
        analysis_for_junior_software_devops,
        analysis_for_network_engineer_automation_ai,
    ):
        JobAnalysisExtraction.model_validate(builder())
