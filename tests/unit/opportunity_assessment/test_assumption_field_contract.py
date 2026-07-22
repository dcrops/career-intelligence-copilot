"""FR-003 assumption field-contract regressions."""

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
from .test_models import _finding


def test_non_assumption_finding_with_assumption_text_fails() -> None:
    with pytest.raises(ValidationError, match="assumption text is only allowed"):
        FitFinding.model_validate(
            _finding(
                kind="gap",
                summary="Missing senior commercial AI ownership.",
                profile_evidence=[],
                assumption="The candidate may not have enough experience.",
            )
        )


@pytest.mark.parametrize(
    "kind",
    ["gap", "partial_alignment", "transferable_alignment", "uncertainty", "alignment"],
)
def test_non_assumption_kinds_accept_null_assumption(kind: str) -> None:
    payload = _finding(
        kind=kind,
        summary=f"Valid {kind} finding without assumption side-channel.",
        assumption=None,
    )
    if kind == "gap":
        payload["profile_evidence"] = []
    if kind == "uncertainty":
        payload["job_evidence"] = [{"source": "compensation"}]
        payload["profile_evidence"] = []
    finding = FitFinding.model_validate(payload)
    assert finding.kind == kind
    assert finding.assumption is None


def test_valid_assumption_finding_parses() -> None:
    finding = FitFinding.model_validate(
        {
            "kind": "assumption",
            "summary": "Compensation cannot be fully evaluated.",
            "importance": "minor",
            "assumption": "The role may be within the owner's acceptable range if disclosed.",
            "job_evidence": [],
            "profile_evidence": [],
        }
    )
    assert finding.kind == "assumption"
    assert finding.assumption is not None


def test_assumption_finding_missing_text_fails() -> None:
    with pytest.raises(ValidationError, match="assumption finding requires assumption text"):
        FitFinding.model_validate(
            {
                "kind": "assumption",
                "summary": "Missing assumption text.",
                "importance": "minor",
                "assumption": None,
                "job_evidence": [],
                "profile_evidence": [],
            }
        )


def test_prompt_forbids_assumption_on_non_assumption_kinds() -> None:
    assert ASSESSMENT_PROMPT_VERSION == "v8"
    assert "Never populate the assumption field unless kind is exactly" in (
        ASSESSMENT_INSTRUCTIONS_V1
    )
    assert "FindingFieldGuide" in ASSESSMENT_INSTRUCTIONS_V1


def test_assessor_context_includes_finding_field_guide() -> None:
    rendered = format_assessment_input(_job_analysis(), _profile())
    guide = rendered[
        rendered.index("<FindingFieldGuide>") : rendered.index("</FindingFieldGuide>")
    ]
    assert "partial_alignment:" in guide
    assert "assumption: forbidden" in guide
    assert "assumption: required" in guide


def test_mocked_senior_ai_engineer_assessment_has_no_assumption_side_channels() -> None:
    payload = dict(assessment_strong_ai_alignment())
    payload["technical_fit"] = {
        "dimension": "technical",
        "judgment": "mixed",
        "summary": "Independent AI delivery overlaps; senior commercial ownership is a gap.",
        "findings": [
            {
                "kind": "partial_alignment",
                "summary": "Independent AI engineering supports production AI delivery claims.",
                "importance": "material",
                "job_evidence": [
                    {"source": "seniority", "excerpt": "Senior AI Engineer"}
                ],
                "profile_evidence": [
                    {
                        "source": "experience",
                        "ref": "experience:chase-risk-compliance-ai-engineer",
                    }
                ],
                "assumption": None,
            },
            {
                "kind": "gap",
                "summary": "Senior commercial leadership of production AI is not evidenced.",
                "importance": "material",
                "job_evidence": [
                    {"source": "seniority", "excerpt": "Senior AI Engineer"}
                ],
                "profile_evidence": [],
                "assumption": None,
            },
        ],
    }
    payload["commercial_fit"] = {
        "dimension": "commercial",
        "judgment": "unknown",
        "summary": "Compensation is unstated.",
        "findings": [
            {
                "kind": "assumption",
                "summary": "Salary cannot be scored against a floor.",
                "importance": "minor",
                "assumption": "The role may be acceptable if compensation is disclosed later.",
                "job_evidence": [],
                "profile_evidence": [],
            }
        ],
    }

    job_payload = _job_analysis().model_dump(mode="python")
    job_payload["seniority"] = {
        "level": "senior",
        "ambiguous": False,
        "evidence": [{"excerpt": "Senior AI Engineer"}],
    }
    job = JobAnalysis.model_validate(job_payload)

    extraction = OpportunityAssessmentExtraction.model_validate(payload)
    assessor = OpenAIAssessor(
        client=_FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    )
    assessment = OpportunityAssessmentService(assessor).assess(job, _profile())

    for finding in (
        *assessment.technical_fit.findings,
        *assessment.portfolio_fit.findings,
    ):
        if finding.kind != "assumption":
            assert finding.assumption is None
    assert any(f.kind == "gap" for f in assessment.technical_fit.findings)
    assert any(f.kind == "partial_alignment" for f in assessment.technical_fit.findings)
    assert assessment.commercial_fit.findings[0].kind == "assumption"


def test_validation_diagnostics_for_assumption_misuse() -> None:
    exc = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit", "findings", 0),
                msg="assumption text is only allowed when kind is 'assumption'",
                type="value_error",
            )
        ]
    )
    message = str(exc)
    assert "technical_fit.findings.0" in message
    assert "assumption text is only allowed" in message
