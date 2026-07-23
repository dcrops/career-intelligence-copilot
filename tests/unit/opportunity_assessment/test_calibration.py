"""FR-003 judgment/industry calibration regressions (Job 009 findings)."""

from __future__ import annotations

from typing import Any

import pytest
from career_intelligence.opportunity_assessment.assessment_prompt import (
    ASSESSMENT_INSTRUCTIONS_V1,
    ASSESSMENT_PROMPT_VERSION,
)
from career_intelligence.opportunity_assessment.calibration import validate_calibration
from career_intelligence.opportunity_assessment.errors import (
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.models import (
    FitDimensionAssessment,
    OpportunityAssessment,
)
from career_intelligence.opportunity_assessment.service import OpportunityAssessmentService
from pydantic import ValidationError

from tests.unit.application_strategy.helpers import job_analysis, minimal_profile
from tests.unit.opportunity_assessment.test_models import _finding


def _dim(
    dimension: str,
    judgment: str,
    summary: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "judgment": judgment,
        "summary": summary,
        "findings": findings,
    }


def _production_llm_job(**overrides: object):
    return job_analysis(
        posting={
            "raw_text": (
                "Senior AI Automation Engineer. Proven experience designing, "
                "building and shipping LLM/agent applications to production. "
                "3+ years experience in the retail or related industry. Melbourne."
            ),
            "title": "Senior AI Automation Engineer",
        },
        seniority={
            "level": "senior",
            "ambiguous": False,
            "evidence": [{"excerpt": "Senior AI Automation Engineer", "section": "title"}],
        },
        experience_requirements=[
            {
                "description": "3+ years experience in the retail or related industry",
                "level": "required",
                "evidence": [
                    {
                        "excerpt": "3+ years experience in the retail or related industry",
                        "section": "requirements",
                    }
                ],
            },
            {
                "description": (
                    "Proven experience designing, building and shipping "
                    "LLM/agent applications to production"
                ),
                "level": "required",
                "evidence": [
                    {
                        "excerpt": (
                            "Proven experience designing, building and shipping "
                            "LLM/agent applications to production"
                        ),
                        "section": "requirements",
                    }
                ],
            },
        ],
        **overrides,
    )


def _assessment_payload(
    analysis,
    *,
    commercial: dict[str, Any],
    technical: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "job_analysis": analysis.model_dump(mode="json"),
        "technical_fit": technical
        or _dim(
            "technical",
            "strong",
            "Technical skills align.",
            [_finding(summary="Required Python aligns with profile skills.")],
        ),
        "commercial_fit": commercial,
        "portfolio_fit": portfolio
        or _dim(
            "portfolio",
            "strong",
            "Portfolio supports the narrative.",
            [
                _finding(
                    summary="Portfolio project supports agent delivery narrative.",
                    profile_evidence=[
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        "summary": {
            "summary": "Calibration regression assessment.",
            "key_alignments": [],
            "key_gaps": [],
        },
    }


def test_material_gap_rejects_strong_dimension_judgment() -> None:
    with pytest.raises(ValidationError, match="inconsistent with material"):
        FitDimensionAssessment.model_validate(
            _dim(
                "commercial",
                "strong",
                "Overstated commercial fit.",
                [
                    _finding(
                        kind="gap",
                        summary=(
                            "Proven production LLM/agent delivery is not sufficiently "
                            "evidenced in the profile."
                        ),
                        job_evidence=[
                            {
                                "source": "experience_requirement",
                                "item_index": 1,
                                "name": (
                                    "Proven experience designing, building and shipping "
                                    "LLM/agent applications to production"
                                ),
                            }
                        ],
                        profile_evidence=[],
                    )
                ],
            )
        )


def test_material_production_gap_allows_mixed_commercial_judgment() -> None:
    dimension = FitDimensionAssessment.model_validate(
        _dim(
            "commercial",
            "mixed",
            "Production delivery gap keeps commercial fit mixed.",
            [
                _finding(
                    kind="gap",
                    summary=(
                        "Proven production LLM/agent delivery is not sufficiently "
                        "evidenced in commercial employment."
                    ),
                    job_evidence=[
                        {
                            "source": "experience_requirement",
                            "item_index": 1,
                        }
                    ],
                    profile_evidence=[],
                )
            ],
        )
    )
    assert dimension.judgment == "mixed"


def test_nbn_cannot_support_retail_industry_alignment() -> None:
    analysis = _production_llm_job()
    profile = minimal_profile()
    assessment = OpportunityAssessment.model_validate(
        _assessment_payload(
            analysis,
            commercial=_dim(
                "commercial",
                "mixed",
                "Retail claim is mis-grounded.",
                [
                    _finding(
                        kind="alignment",
                        summary=(
                            "Candidate has over 3 years of experience in the retail "
                            "industry."
                        ),
                        job_evidence=[
                            {
                                "source": "experience_requirement",
                                "item_index": 0,
                                "name": "3+ years experience in the retail or related industry",
                                "excerpt": "3+ years experience in the retail or related industry",
                            }
                        ],
                        profile_evidence=[
                            {
                                "source": "experience",
                                "ref": "experience:example-role",
                            }
                        ],
                    ),
                    _finding(
                        kind="gap",
                        summary=(
                            "Proven production LLM/agent delivery is not evidenced "
                            "in commercial employment."
                        ),
                        job_evidence=[{"source": "experience_requirement", "item_index": 1}],
                        profile_evidence=[],
                    ),
                ],
            ),
        )
    )
    with pytest.raises(OpportunityAssessmentValidationError, match="industry requirement"):
        validate_calibration(assessment, profile)


def test_nbn_employment_cannot_support_retail_industry_alignment() -> None:
    analysis = _production_llm_job()
    profile = minimal_profile()
    nbn_entry = profile.experience[0].model_copy(
        update={
            "id": "nbn-data-engineer-2020",
            "organisation": "nbn Australia",
            "title": "Data Engineer",
            "highlights": ["Developed enterprise data pipelines."],
        }
    )
    profile = profile.model_copy(update={"experience": [nbn_entry]})
    assessment = OpportunityAssessment.model_validate(
        _assessment_payload(
            analysis,
            commercial=_dim(
                "commercial",
                "mixed",
                "nbn is not retail evidence.",
                [
                    _finding(
                        kind="alignment",
                        summary="Candidate has retail industry experience.",
                        job_evidence=[
                            {
                                "source": "experience_requirement",
                                "item_index": 0,
                                "excerpt": "3+ years experience in the retail or related industry",
                            }
                        ],
                        profile_evidence=[
                            {
                                "source": "experience",
                                "ref": "experience:nbn-data-engineer-2020",
                            }
                        ],
                    ),
                    _finding(
                        kind="gap",
                        summary="Production LLM/agent delivery employment is missing.",
                        job_evidence=[{"source": "experience_requirement", "item_index": 1}],
                        profile_evidence=[],
                    ),
                ],
            ),
        )
    )
    with pytest.raises(OpportunityAssessmentValidationError, match="industry requirement"):
        validate_calibration(assessment, profile)


def test_bakers_delight_supports_retail_industry_alignment() -> None:
    analysis = _production_llm_job()
    profile = minimal_profile()
    retail_entry = profile.experience[0].model_copy(
        update={
            "id": "bakers-delight-test-analyst-2015",
            "organisation": "Bakers Delight",
            "title": "Test Analyst",
        }
    )
    profile = profile.model_copy(update={"experience": [retail_entry]})
    assessment = OpportunityAssessment.model_validate(
        _assessment_payload(
            analysis,
            commercial=_dim(
                "commercial",
                "mixed",
                "Retail employment supports industry requirement; production gap remains.",
                [
                    _finding(
                        kind="alignment",
                        summary="Retail employment supports the industry requirement.",
                        job_evidence=[
                            {
                                "source": "experience_requirement",
                                "item_index": 0,
                                "excerpt": "3+ years experience in the retail or related industry",
                            }
                        ],
                        profile_evidence=[
                            {
                                "source": "experience",
                                "ref": "experience:bakers-delight-test-analyst-2015",
                            }
                        ],
                    ),
                    _finding(
                        kind="gap",
                        summary="Production LLM/agent delivery employment is missing.",
                        job_evidence=[{"source": "experience_requirement", "item_index": 1}],
                        profile_evidence=[],
                    ),
                ],
            ),
        )
    )
    validate_calibration(assessment, profile)


def test_independent_engineering_cannot_align_commercial_production_delivery() -> None:
    analysis = _production_llm_job()
    profile = minimal_profile()
    independent = profile.experience[0].model_copy(
        update={
            "id": "chase-risk-compliance-ai-engineer",
            "kind": "independent_engineering",
            "organisation": "Chase Risk & Compliance",
            "title": "AI Engineer - Independent Research & Development",
        }
    )
    profile = profile.model_copy(update={"experience": [independent]})
    assessment = OpportunityAssessment.model_validate(
        _assessment_payload(
            analysis,
            commercial=_dim(
                "commercial",
                "mixed",
                "Independent work is not commercial production employment.",
                [
                    _finding(
                        kind="alignment",
                        summary=(
                            "Independent engineering demonstrates shipping production "
                            "LLM/agent applications."
                        ),
                        job_evidence=[
                            {
                                "source": "experience_requirement",
                                "item_index": 1,
                                "excerpt": (
                                    "Proven experience designing, building and shipping "
                                    "LLM/agent applications to production"
                                ),
                            }
                        ],
                        profile_evidence=[
                            {
                                "source": "experience",
                                "ref": "experience:chase-risk-compliance-ai-engineer",
                            }
                        ],
                    )
                ],
            ),
        )
    )
    with pytest.raises(
        OpportunityAssessmentValidationError,
        match="independent_engineering",
    ):
        validate_calibration(assessment, profile)


def test_service_rejects_strong_commercial_with_production_gap() -> None:
    analysis = _production_llm_job()
    profile = minimal_profile()

    class _Assessor:
        def assess(self, job_analysis, career_profile):  # noqa: ANN001
            payload = _assessment_payload(
                analysis,
                commercial=_dim(
                    "commercial",
                    "strong",
                    "Invalid strong commercial fit.",
                    [
                        _finding(
                            kind="gap",
                            summary=(
                                "Proven production LLM/agent delivery is not "
                                "sufficiently evidenced."
                            ),
                            job_evidence=[
                                {"source": "experience_requirement", "item_index": 1}
                            ],
                            profile_evidence=[],
                        )
                    ],
                ),
            )
            payload.pop("job_analysis")
            return payload

    with pytest.raises(OpportunityAssessmentValidationError, match="inconsistent with material"):
        OpportunityAssessmentService(_Assessor()).assess(analysis, profile)


def test_prompt_documents_judgment_calibration() -> None:
    assert ASSESSMENT_PROMPT_VERSION == "v11"
    assert 'MUST NOT be "strong"' in ASSESSMENT_INSTRUCTIONS_V1
    assert 'never "strong"' in ASSESSMENT_INSTRUCTIONS_V1
    assert "genuinely supports that industry" in ASSESSMENT_INSTRUCTIONS_V1
