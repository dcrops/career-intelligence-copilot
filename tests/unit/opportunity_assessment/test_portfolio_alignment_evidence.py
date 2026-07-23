"""Portfolio-fit alignment evidence-contract regressions (Job 012)."""

from __future__ import annotations

import pytest
from career_intelligence.opportunity_assessment.assessment_prompt import (
    ASSESSMENT_INSTRUCTIONS_V1,
    ASSESSMENT_PROMPT_VERSION,
)
from career_intelligence.opportunity_assessment.errors import (
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.extraction import (
    OpportunityAssessmentExtraction,
)
from career_intelligence.opportunity_assessment.fixtures import (
    assessment_strong_ai_alignment,
)
from career_intelligence.opportunity_assessment.models import FitFinding
from career_intelligence.opportunity_assessment.openai_assessor import (
    OpenAIAssessor,
    format_assessment_input,
)
from career_intelligence.opportunity_assessment.service import OpportunityAssessmentService
from pydantic import ValidationError

from .test_openai_assessor import (
    _FakeOpenAI,
    _FakeParseResult,
    _job_analysis,
    _profile,
)


def test_prompt_requires_job_evidence_for_every_alignment_finding() -> None:
    assert ASSESSMENT_PROMPT_VERSION == "v11"
    text = ASSESSMENT_INSTRUCTIONS_V1
    assert "alignment: non-empty job_evidence AND non-empty profile_evidence" in text
    assert "Never emit portfolio_fit" in text
    assert "Valid portfolio_fit alignment" in text
    assert '"job_evidence":[]' in text
    assert "MUST include non-empty job_evidence from JobAnalysis" in text


def test_finding_field_guide_forbids_portfolio_alignment_without_job_evidence() -> None:
    rendered = format_assessment_input(_job_analysis(), _profile())
    guide = rendered[
        rendered.index("<FindingFieldGuide>") : rendered.index("</FindingFieldGuide>")
    ]
    assert "job_evidence: required (non-empty)" in guide
    assert "alignment with job_evidence=[]" in guide


def test_portfolio_alignment_without_job_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="requires at least one job evidence ref"):
        FitFinding.model_validate(
            {
                "kind": "alignment",
                "summary": "Portfolio supports the role.",
                "importance": "material",
                "job_evidence": [],
                "profile_evidence": [
                    {
                        "source": "project",
                        "ref": "project:operational-intelligence-copilot",
                    }
                ],
                "assumption": None,
            }
        )


def test_valid_portfolio_alignment_with_job_and_profile_evidence_passes() -> None:
    finding = FitFinding.model_validate(
        {
            "kind": "alignment",
            "summary": (
                "Portfolio project demonstrates production-minded AI delivery "
                "relevant to a stated responsibility."
            ),
            "importance": "material",
            "job_evidence": [
                {
                    "source": "responsibility",
                    "item_index": 0,
                    "excerpt": "Build LLM applications",
                }
            ],
            "profile_evidence": [
                {
                    "source": "project",
                    "ref": "project:operational-intelligence-copilot",
                }
            ],
            "assumption": None,
        }
    )
    assert finding.kind == "alignment"
    assert len(finding.job_evidence) == 1
    assert len(finding.profile_evidence) == 1


def test_service_rejects_portfolio_alignment_missing_job_evidence() -> None:
    payload = dict(assessment_strong_ai_alignment())
    payload["portfolio_fit"] = {
        "dimension": "portfolio",
        "judgment": "strong",
        "summary": "Portfolio-only finding without job evidence.",
        "findings": [
            {
                "kind": "alignment",
                "summary": "Portfolio supports the opportunity narrative.",
                "importance": "material",
                "job_evidence": [],
                "profile_evidence": [
                    {
                        "source": "project",
                        "ref": "project:operational-intelligence-copilot",
                    }
                ],
                "assumption": None,
            }
        ],
    }

    with pytest.raises(ValidationError, match="job evidence"):
        OpportunityAssessmentExtraction.model_validate(payload)

    raw = dict(payload)
    raw.pop("job_analysis", None)
    assessor = OpenAIAssessor(
        client=_FakeOpenAI(result=_FakeParseResult(output_parsed=None))
    )

    class _StubAssessor:
        def assess(self, job_analysis, profile):  # noqa: ANN001
            return raw

    with pytest.raises(OpportunityAssessmentValidationError, match="job evidence"):
        OpportunityAssessmentService(_StubAssessor()).assess(_job_analysis(), _profile())
