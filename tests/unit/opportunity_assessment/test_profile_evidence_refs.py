"""Profile evidence ref exact-catalogue regressions."""

from __future__ import annotations

from pathlib import Path

import pytest
from career_intelligence.opportunity_assessment.assessment_prompt import (
    ASSESSMENT_INSTRUCTIONS_V1,
    ASSESSMENT_PROMPT_VERSION,
)
from career_intelligence.opportunity_assessment.errors import (
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.models import (
    OpportunityAssessment,
    ProfileEvidenceRef,
)
from career_intelligence.opportunity_assessment.openai_assessor import (
    format_assessment_input,
)
from career_intelligence.opportunity_assessment.refs import validate_references
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import posting_applied_ai_engineer
from career_intelligence.profile import CareerProfileService
from pydantic import ValidationError


def _golden_profile():
    return CareerProfileService.from_path(
        Path(__file__).parents[2] / "fixtures" / "golden" / "career_profile.yaml"
    ).load()


def _minimal_profile():
    return CareerProfileService.from_path(
        Path(__file__).parents[2] / "fixtures" / "minimal_valid_profile.yaml"
    ).load()


def _job():
    return JobAnalysisService(FixtureExtractor()).analyse(posting_applied_ai_engineer())


def _assessment_with_experience_ref(job, experience_ref: str) -> OpportunityAssessment:
    return OpportunityAssessment.model_validate(
        {
            "job_analysis": job.model_dump(mode="json"),
            "technical_fit": {
                "dimension": "technical",
                "judgment": "moderate",
                "summary": "Technical fit uses one experience ref.",
                "findings": [
                    {
                        "kind": "partial_alignment",
                        "summary": "Profile experience partially supports the role.",
                        "importance": "material",
                        "job_evidence": [
                            {"source": "seniority", "excerpt": "AI Engineer"}
                        ],
                        "profile_evidence": [
                            {"source": "experience", "ref": experience_ref}
                        ],
                        "assumption": None,
                    }
                ],
            },
            "commercial_fit": {
                "dimension": "commercial",
                "judgment": "unknown",
                "summary": "Compensation is unstated.",
                "findings": [
                    {
                        "kind": "uncertainty",
                        "summary": "Salary is unstated.",
                        "importance": "minor",
                        "job_evidence": [{"source": "compensation"}],
                        "profile_evidence": [],
                        "assumption": None,
                    }
                ],
            },
            "portfolio_fit": {
                "dimension": "portfolio",
                "judgment": "moderate",
                "summary": "Portfolio supports a truthful narrative.",
                "findings": [
                    {
                        "kind": "alignment",
                        "summary": "Project evidence supports Python delivery.",
                        "importance": "material",
                        "job_evidence": [
                            {
                                "source": "technology",
                                "item_index": 0,
                                "name": "Python",
                            }
                        ],
                        "profile_evidence": [
                            {
                                "source": "project",
                                "ref": "project:example-project",
                            }
                        ],
                        "assumption": None,
                    }
                ],
            },
            "summary": {
                "summary": "Ref-contract regression assessment.",
                "key_alignments": [],
                "key_gaps": [],
            },
        }
    )


def test_canonical_experience_ids_include_chase_without_trailing_period() -> None:
    ids = {entry.id for entry in _golden_profile().experience}
    assert "chase-risk-compliance-ai-engineer" in ids
    assert "chase-risk-compliance-ai-engineer." not in ids


def test_exact_canonical_experience_ref_accepted() -> None:
    ref = ProfileEvidenceRef.model_validate(
        {
            "source": "experience",
            "ref": "experience:chase-risk-compliance-ai-engineer",
        }
    )
    assert ref.ref == "experience:chase-risk-compliance-ai-engineer"


def test_trailing_punctuation_on_experience_ref_rejected() -> None:
    with pytest.raises(ValidationError, match="trailing punctuation"):
        ProfileEvidenceRef.model_validate(
            {
                "source": "experience",
                "ref": "experience:chase-risk-compliance-ai-engineer.",
            }
        )


def test_invented_experience_id_rejected_by_reference_validation() -> None:
    profile = _minimal_profile()
    assert not any(
        entry.id == "chase-risk-compliance-ai-engineer" for entry in profile.experience
    )
    assessment = _assessment_with_experience_ref(
        _job(), "experience:chase-risk-compliance-ai-engineer"
    )
    with pytest.raises(OpportunityAssessmentValidationError, match="unknown experience id"):
        validate_references(assessment, profile)


def test_valid_minimal_profile_experience_ref_passes() -> None:
    profile = _minimal_profile()
    assessment = _assessment_with_experience_ref(_job(), "experience:example-role")
    validate_references(assessment, profile)


def test_prompt_and_cite_guide_require_exact_catalogue_tokens() -> None:
    assert ASSESSMENT_PROMPT_VERSION == "v11"
    assert "trailing punctuation" in ASSESSMENT_INSTRUCTIONS_V1
    assert "Do not invent experience/project IDs" in ASSESSMENT_INSTRUCTIONS_V1

    rendered = format_assessment_input(_job(), _minimal_profile())
    guide = rendered[
        rendered.index("<ProfileEvidenceCiteGuide>") : rendered.index(
            "</ProfileEvidenceCiteGuide>"
        )
    ]
    assert "trailing" in guide.casefold()
    assert "experience:example-role" in guide
    assert "experience:chase-risk-compliance-ai-engineer" not in guide
