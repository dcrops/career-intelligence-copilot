"""Unit tests for the FR-003 opportunity-assessment domain contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.job_analysis.models import JobAnalysis, JobPosting
from career_intelligence.opportunity_assessment.models import (
    AssessmentSummary,
    FitDimensionAssessment,
    FitFinding,
    JobEvidenceRef,
    OpportunityAssessment,
    ProfileEvidenceRef,
)


def _posting(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "raw_text": "Senior AI Engineer. Python required. Hybrid Melbourne.",
        "title": "Senior AI Engineer",
        "company": "Example AI Co",
    }
    payload.update(overrides)
    return payload


def _job_analysis(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "posting": _posting(),
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
    payload.update(overrides)
    return payload


def _finding(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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
    payload.update(overrides)
    return payload


def _dimension(dimension: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "dimension": dimension,
        "judgment": "moderate",
        "summary": f"{dimension.title()} fit summary.",
        "findings": [_finding()],
    }
    payload.update(overrides)
    return payload


def _valid_assessment(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "job_analysis": _job_analysis(),
        "technical_fit": _dimension("technical"),
        "commercial_fit": _dimension("commercial"),
        "portfolio_fit": _dimension("portfolio"),
        "summary": {
            "summary": "Overall fit is moderate with some open commercial unknowns.",
            "key_alignments": ["Python requirement supported by profile."],
            "key_gaps": ["Compensation unstated."],
        },
    }
    payload.update(overrides)
    return payload


def test_valid_opportunity_assessment_parses() -> None:
    assessment = OpportunityAssessment.model_validate(_valid_assessment())

    assert assessment.technical_fit.dimension == "technical"
    assert assessment.commercial_fit.judgment == "moderate"
    assert assessment.summary.key_gaps == ["Compensation unstated."]
    assert assessment.job_analysis.role_family.family == "ai_engineering"


def test_dimension_field_must_match_facet_name() -> None:
    with pytest.raises(ValidationError, match="technical_fit.dimension"):
        OpportunityAssessment.model_validate(
            _valid_assessment(technical_fit=_dimension("commercial"))
        )


def test_assumption_finding_requires_assumption_text() -> None:
    with pytest.raises(ValidationError, match="assumption finding requires assumption text"):
        FitFinding.model_validate(
            _finding(
                kind="assumption",
                assumption=None,
                job_evidence=[],
                profile_evidence=[],
            )
        )


def test_non_assumption_finding_rejects_assumption_text() -> None:
    with pytest.raises(ValidationError, match="assumption text is only allowed"):
        FitFinding.model_validate(_finding(assumption="Salary minimum not recorded."))


def test_alignment_finding_requires_job_and_profile_evidence() -> None:
    with pytest.raises(ValidationError, match="requires at least one profile evidence ref"):
        FitFinding.model_validate(_finding(profile_evidence=[]))

    with pytest.raises(ValidationError, match="requires at least one job evidence ref"):
        FitFinding.model_validate(_finding(job_evidence=[]))


def test_partial_alignment_requires_profile_evidence() -> None:
    with pytest.raises(ValidationError, match="partial_alignment"):
        FitFinding.model_validate(
            _finding(kind="partial_alignment", profile_evidence=[])
        )

    finding = FitFinding.model_validate(
        _finding(
            kind="partial_alignment",
            summary="AI delivery overlaps product work; direct PM tenure is missing.",
            profile_evidence=[
                {
                    "source": "experience",
                    "ref": "experience:chase-risk-compliance-ai-engineer",
                }
            ],
        )
    )
    assert finding.kind == "partial_alignment"
    assert finding.profile_evidence


def test_transferable_alignment_requires_profile_evidence() -> None:
    with pytest.raises(ValidationError, match="transferable_alignment"):
        FitFinding.model_validate(
            _finding(kind="transferable_alignment", profile_evidence=[])
        )

    finding = FitFinding.model_validate(
        _finding(
            kind="transferable_alignment",
            summary="Portfolio problem framing transfers to product discovery work.",
            profile_evidence=[
                {
                    "source": "project",
                    "ref": "project:operational-intelligence-copilot",
                }
            ],
        )
    )
    assert finding.kind == "transferable_alignment"
    assert finding.profile_evidence


def test_gap_finding_allows_missing_profile_evidence() -> None:
    finding = FitFinding.model_validate(
        _finding(
            kind="gap",
            summary="Required production AI experience not evidenced in profile.",
            profile_evidence=[],
        )
    )

    assert finding.kind == "gap"
    assert finding.profile_evidence == []


def test_uncertainty_finding_allows_empty_evidence() -> None:
    finding = FitFinding.model_validate(
        {
            "kind": "uncertainty",
            "summary": "Compensation is unstated in the analysed job.",
            "importance": "material",
            "job_evidence": [{"source": "compensation"}],
        }
    )

    assert finding.profile_evidence == []


def test_technology_job_evidence_requires_item_index() -> None:
    with pytest.raises(ValidationError):
        JobEvidenceRef.model_validate({"source": "technology", "name": "Python"})


def test_forbidden_quota_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        OpportunityAssessment.model_validate(
            _valid_assessment(quota_candidate=True)  # type: ignore[arg-type]
        )


def test_forbidden_tier_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        FitDimensionAssessment.model_validate(
            _dimension("technical", tier="gold")  # type: ignore[arg-type]
        )


def test_assessment_summary_caps_optional_lists() -> None:
    with pytest.raises(ValidationError):
        AssessmentSummary.model_validate(
            {
                "summary": "Too many alignments.",
                "key_alignments": [f"item-{index}" for index in range(6)],
            }
        )


def test_job_analysis_reference_is_preserved() -> None:
    job_analysis = JobAnalysis.model_validate(_job_analysis())
    assessment = OpportunityAssessment.model_validate(
        _valid_assessment(job_analysis=job_analysis.model_dump(mode="python"))
    )

    assert assessment.job_analysis == job_analysis


def test_profile_schema_version_is_not_part_of_domain_model() -> None:
    with pytest.raises(ValidationError):
        OpportunityAssessment.model_validate(
            _valid_assessment(profile_schema_version="1")  # type: ignore[arg-type]
        )


def test_posting_only_job_analysis_remains_valid_input() -> None:
    posting = JobPosting(raw_text="Minimal posting for model wiring.")
    job_analysis = JobAnalysis.model_validate(
        {
            "posting": posting.model_dump(mode="python"),
            "role_family": {"family": "unknown"},
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": [],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
        }
    )
    assessment = OpportunityAssessment.model_validate(
        _valid_assessment(job_analysis=job_analysis.model_dump(mode="python"))
    )

    assert assessment.job_analysis.posting.raw_text == "Minimal posting for model wiring."
