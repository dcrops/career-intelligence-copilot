"""FR-003 evidence-contract regressions for partial/transferable alignment."""

from __future__ import annotations

import pytest
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.assessment_prompt import (
    ASSESSMENT_INSTRUCTIONS_V1,
    ASSESSMENT_PROMPT_VERSION,
)
from career_intelligence.opportunity_assessment.errors import (
    ErrorDetail,
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.extraction import (
    OpportunityAssessmentExtraction,
)
from career_intelligence.opportunity_assessment.models import FitFinding
from career_intelligence.opportunity_assessment.fixtures import (
    assessment_strong_ai_alignment,
)
from career_intelligence.opportunity_assessment.openai_assessor import (
    OpenAIAssessor,
    format_assessment_input,
)
from career_intelligence.opportunity_assessment.service import OpportunityAssessmentService
from career_intelligence.profile import CareerProfileService
from pydantic import ValidationError

from .test_openai_assessor import (
    _FakeOpenAI,
    _FakeParseResult,
    _job_analysis,
    _profile,
)


def _fixtures_profile():
    from pathlib import Path

    return CareerProfileService.from_path(
        Path(__file__).parents[2] / "fixtures" / "golden" / "career_profile.yaml"
    ).load()


def test_prompt_documents_per_kind_evidence_contract() -> None:
    assert ASSESSMENT_PROMPT_VERSION == "v8"
    text = ASSESSMENT_INSTRUCTIONS_V1
    for kind in (
        "alignment",
        "partial_alignment",
        "transferable_alignment",
        "gap",
        "conflict",
        "uncertainty",
        "assumption",
    ):
        assert kind in text
    assert "Never emit a required evidence-reference array as empty" in text
    assert "Never fabricate evidence IDs" in text
    assert "Never populate the assumption field unless kind is exactly" in text
    assert "FindingFieldGuide" in text


def test_profile_refs_survive_into_assessor_context() -> None:
    profile = _fixtures_profile()
    job = JobAnalysis.model_validate(
        {
            "posting": {
                "raw_text": "Associate AI Product Manager. Roadmap ownership.",
                "title": "Associate AI Product Manager",
            },
            "role_family": {
                "family": "ai_adjacent",
                "evidence": [{"excerpt": "Associate AI Product Manager"}],
            },
            "seniority": {
                "level": "entry",
                "ambiguous": False,
                "evidence": [{"excerpt": "Associate"}],
            },
            "technologies": [],
            "responsibilities": [
                {
                    "description": "Own product roadmap and prioritisation",
                    "evidence": [{"excerpt": "roadmap"}],
                }
            ],
            "compensation": {"clarity": "unstated"},
            "location": {
                "clarity": "stated",
                "summary": "Melbourne VIC (Hybrid)",
                "evidence": [{"excerpt": "Melbourne"}],
            },
            "work_arrangement": {
                "arrangement": "hybrid",
                "evidence": [{"excerpt": "Hybrid"}],
            },
            "employment": {
                "working_hours": "full_time",
                "evidence": [{"excerpt": "Full time"}],
            },
            "experience_requirements": [],
        }
    )
    rendered = format_assessment_input(job, profile)
    assert "<ProfileEvidenceCiteGuide>" in rendered
    assert "project:operational-intelligence-copilot" in rendered
    assert "experience:chase-risk-compliance-ai-engineer" in rendered
    cite_guide = rendered[
        rendered.index("<ProfileEvidenceCiteGuide>") : rendered.index(
            "</ProfileEvidenceCiteGuide>"
        )
    ]
    assert '"ref": "project:operational-intelligence-copilot"' in cite_guide


def test_mocked_ai_product_manager_assessment_keeps_honest_gaps() -> None:
    payload = dict(assessment_strong_ai_alignment())
    payload["technical_fit"] = {
        "dimension": "technical",
        "judgment": "mixed",
        "summary": "AI delivery evidence overlaps; direct PM tenure is missing.",
        "findings": [
            {
                "kind": "partial_alignment",
                "summary": "AI application delivery overlaps AI product work.",
                "importance": "material",
                "job_evidence": [
                    {
                        "source": "responsibility",
                        "item_index": 0,
                        "excerpt": "Own product roadmap",
                    }
                ],
                "profile_evidence": [
                    {
                        "source": "experience",
                        "ref": "experience:chase-risk-compliance-ai-engineer",
                    }
                ],
            },
            {
                "kind": "gap",
                "summary": "No commercial Product Manager employment is evidenced.",
                "importance": "material",
                "job_evidence": [
                    {"source": "role_family", "excerpt": "Product Manager"}
                ],
                "profile_evidence": [],
            },
        ],
    }
    payload["portfolio_fit"] = {
        "dimension": "portfolio",
        "judgment": "moderate",
        "summary": "Portfolio shows transferable problem framing, not PM tenure.",
        "findings": [
            {
                "kind": "transferable_alignment",
                "summary": "Portfolio problem definition transfers to discovery work.",
                "importance": "material",
                "job_evidence": [
                    {
                        "source": "responsibility",
                        "item_index": 0,
                        "excerpt": "Own product roadmap",
                    }
                ],
                "profile_evidence": [
                    {
                        "source": "project",
                        "ref": "project:operational-intelligence-copilot",
                    }
                ],
            }
        ],
    }

    job_payload = _job_analysis().model_dump(mode="python")
    job_payload["responsibilities"] = [
        {
            "description": "Own product roadmap and prioritisation",
            "evidence": [{"excerpt": "Own product roadmap"}],
        }
    ]
    job_payload["role_family"] = {
        "family": "ai_adjacent",
        "evidence": [{"excerpt": "Associate AI Product Manager"}],
    }
    job = JobAnalysis.model_validate(job_payload)

    extraction = OpportunityAssessmentExtraction.model_validate(payload)
    assessor = OpenAIAssessor(
        client=_FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    )
    assessment = OpportunityAssessmentService(assessor).assess(job, _profile())

    assert assessment.technical_fit.judgment == "mixed"
    partial = next(
        f for f in assessment.technical_fit.findings if f.kind == "partial_alignment"
    )
    assert partial.profile_evidence
    gap = next(f for f in assessment.technical_fit.findings if f.kind == "gap")
    assert gap.profile_evidence == []
    transferable = next(
        f
        for f in assessment.portfolio_fit.findings
        if f.kind == "transferable_alignment"
    )
    assert transferable.profile_evidence[0].ref.startswith("project:")


def test_unsupported_claim_uses_gap_not_empty_profile_transferable() -> None:
    with pytest.raises(ValidationError, match="profile evidence"):
        FitFinding.model_validate(
            {
                "kind": "transferable_alignment",
                "summary": "Claimed transferability without profile support.",
                "importance": "material",
                "job_evidence": [{"source": "role_family", "excerpt": "Product Manager"}],
                "profile_evidence": [],
            }
        )

    gap = FitFinding.model_validate(
        {
            "kind": "gap",
            "summary": "No matching product-management evidence in the profile.",
            "importance": "material",
            "job_evidence": [{"source": "role_family", "excerpt": "Product Manager"}],
            "profile_evidence": [],
        }
    )
    assert gap.kind == "gap"


def test_validation_error_diagnostics_include_dimension_and_finding_path() -> None:
    exc = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit", "findings", 2),
                msg="partial_alignment finding requires at least one profile evidence ref",
                type="value_error",
            ),
            ErrorDetail(
                loc=("portfolio_fit", "findings", 1),
                msg="transferable_alignment finding requires at least one profile evidence ref",
                type="value_error",
            ),
        ]
    )
    message = str(exc)
    assert "technical_fit.findings.2" in message
    assert "partial_alignment" in message
    assert "portfolio_fit.findings.1" in message
    assert "transferable_alignment" in message
