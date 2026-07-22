"""Unit tests for OpportunityAssessmentService trust-boundary behaviour."""

from __future__ import annotations

import pytest
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment import (
    OpportunityAssessment,
    OpportunityAssessmentError,
    OpportunityAssessmentService,
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.assessor import OpportunityAssessmentPayload
from career_intelligence.profile import CareerProfile, CareerProfileService


def _golden_profile() -> CareerProfile:
    path = (
        pytest.importorskip("pathlib").Path(__file__).parents[2]
        / "fixtures"
        / "golden"
        / "career_profile.yaml"
    )
    return CareerProfileService.from_path(path).load()


def _job_analysis() -> JobAnalysis:
    return JobAnalysis.model_validate(
        {
            "posting": {
                "raw_text": "Senior AI Engineer. Python required. Hybrid Melbourne.",
                "title": "Senior AI Engineer",
            },
            "role_family": {
                "family": "ai_engineering",
                "evidence": [{"excerpt": "Senior AI Engineer", "section": "title"}],
            },
            "seniority": {
                "level": "senior",
                "ambiguous": False,
                "evidence": [{"excerpt": "Senior AI Engineer", "section": "title"}],
            },
            "technologies": [
                {
                    "name": "Python",
                    "level": "required",
                    "evidence": [{"excerpt": "Python required", "section": "requirements"}],
                }
            ],
            "responsibilities": [],
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
            "employment": {},
            "experience_requirements": [],
        }
    )


def _assessment_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "technical_fit": {
            "dimension": "technical",
            "judgment": "moderate",
            "summary": "Python aligns with profile skills.",
            "findings": [
                {
                    "kind": "alignment",
                    "summary": "Required Python aligns with demonstrated profile skills.",
                    "importance": "material",
                    "job_evidence": [
                        {
                            "source": "technology",
                            "item_index": 0,
                            "name": "Python",
                            "excerpt": "Python required",
                        }
                    ],
                    "profile_evidence": [{"source": "skill", "ref": "skill:Python"}],
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
                    "summary": "Compensation is unstated in the analysed job.",
                    "importance": "material",
                    "job_evidence": [{"source": "compensation"}],
                }
            ],
        },
        "portfolio_fit": {
            "dimension": "portfolio",
            "judgment": "moderate",
            "summary": "Portfolio projects support an AI engineering narrative.",
            "findings": [
                {
                    "kind": "partial_alignment",
                    "summary": "Portfolio projects demonstrate applied AI engineering capability.",
                    "importance": "material",
                    "job_evidence": [{"source": "role_family", "excerpt": "Senior AI Engineer"}],
                    "profile_evidence": [
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot",
                        }
                    ],
                }
            ],
        },
        "summary": {
            "summary": "Moderate overall fit with unstated compensation.",
            "key_alignments": ["Python requirement supported."],
            "key_gaps": ["Compensation unstated."],
        },
    }
    payload.update(overrides)
    return payload


class _StaticPayloadAssessor:
    def __init__(self, payload: OpportunityAssessmentPayload) -> None:
        self._payload = payload

    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessmentPayload:
        _ = job_analysis, profile
        return self._payload


class _FailingAssessor:
    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessmentPayload:
        _ = job_analysis, profile
        raise OpportunityAssessmentError("assessor failed")


def test_service_requires_an_assessor() -> None:
    with pytest.raises(TypeError):
        OpportunityAssessmentService()  # type: ignore[call-arg]


def test_valid_payload_becomes_trusted_opportunity_assessment() -> None:
    job_analysis = _job_analysis()
    profile = _golden_profile()
    service = OpportunityAssessmentService(_StaticPayloadAssessor(_assessment_payload()))

    assessment = service.assess(job_analysis, profile)

    assert isinstance(assessment, OpportunityAssessment)
    assert assessment.technical_fit.judgment == "moderate"
    assert assessment.commercial_fit.findings[0].kind == "uncertainty"


def test_returned_assessment_contains_exact_original_job_analysis() -> None:
    job_analysis = _job_analysis()
    profile = _golden_profile()
    assessment = OpportunityAssessmentService(
        _StaticPayloadAssessor(_assessment_payload())
    ).assess(job_analysis, profile)

    assert assessment.job_analysis is job_analysis


def test_assessor_payload_cannot_replace_input_job_analysis() -> None:
    caller_analysis = _job_analysis()
    other_analysis = JobAnalysis.model_validate(
        {
            "posting": {"raw_text": "Other posting that must not replace caller input."},
            "role_family": {"family": "unknown"},
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": [],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
        }
    )
    payload = _assessment_payload(
        job_analysis=other_analysis.model_dump(mode="python"),
    )
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(caller_analysis, _golden_profile())

    assert any(error.loc == ("job_analysis",) for error in raised.value.errors)


def test_assessor_payload_cannot_embed_profile() -> None:
    profile = _golden_profile()
    payload = _assessment_payload(profile=profile.model_dump(mode="python"))
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(_job_analysis(), profile)

    assert any(error.loc == ("profile",) for error in raised.value.errors)


def test_unknown_profile_reference_is_rejected() -> None:
    payload = _assessment_payload(
        technical_fit={
            "dimension": "technical",
            "judgment": "weak",
            "summary": "Invalid profile reference.",
            "findings": [
                {
                    "kind": "alignment",
                    "summary": "Invalid project reference.",
                    "importance": "material",
                    "job_evidence": [{"source": "role_family"}],
                    "profile_evidence": [
                        {"source": "project", "ref": "project:does-not-exist"}
                    ],
                }
            ],
        }
    )
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(_job_analysis(), _golden_profile())

    assert any("unknown project id" in error.msg for error in raised.value.errors)


def test_out_of_range_technology_index_is_rejected() -> None:
    payload = _assessment_payload(
        technical_fit={
            "dimension": "technical",
            "judgment": "weak",
            "summary": "Invalid technology index.",
            "findings": [
                {
                    "kind": "alignment",
                    "summary": "Invalid technology index.",
                    "importance": "material",
                    "job_evidence": [
                        {
                            "source": "technology",
                            "item_index": 99,
                            "name": "Python",
                        }
                    ],
                    "profile_evidence": [{"source": "skill", "ref": "skill:Python"}],
                }
            ],
        }
    )
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(_job_analysis(), _golden_profile())

    assert any("out of range" in error.msg for error in raised.value.errors)


def test_schema_invalid_mapping_becomes_validation_error() -> None:
    payload = _assessment_payload(
        technical_fit={
            "dimension": "technical",
            "judgment": "not-a-real-judgment",
            "summary": "Invalid judgment.",
            "findings": [
                {
                    "kind": "uncertainty",
                    "summary": "Placeholder.",
                    "importance": "minor",
                }
            ],
        }
    )
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(_job_analysis(), _golden_profile())

    assert raised.value.errors
    assert isinstance(raised.value, OpportunityAssessmentError)


def test_service_propagates_assessor_error() -> None:
    service = OpportunityAssessmentService(_FailingAssessor())

    with pytest.raises(OpportunityAssessmentError, match="assessor failed") as raised:
        service.assess(_job_analysis(), _golden_profile())

    assert not isinstance(raised.value, OpportunityAssessmentValidationError)
