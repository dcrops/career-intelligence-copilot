"""Unit tests for the internal OpportunityAssessmentExtraction schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.opportunity_assessment.extraction import OpportunityAssessmentExtraction
from career_intelligence.opportunity_assessment.models import OpportunityAssessment


def test_extraction_fields_match_opportunity_assessment_minus_job_analysis() -> None:
    assert set(OpportunityAssessment.model_fields) - {"job_analysis"} == set(
        OpportunityAssessmentExtraction.model_fields
    )


def test_extraction_reuses_nested_assessment_types() -> None:
    for name in OpportunityAssessmentExtraction.model_fields:
        assert (
            OpportunityAssessmentExtraction.model_fields[name].annotation
            == OpportunityAssessment.model_fields[name].annotation
        )


def test_extraction_rejects_job_analysis_field() -> None:
    payload = {
        "technical_fit": {
            "dimension": "technical",
            "judgment": "unknown",
            "summary": "Placeholder.",
            "findings": [
                {
                    "kind": "uncertainty",
                    "summary": "Placeholder uncertainty.",
                    "importance": "minor",
                }
            ],
        },
        "commercial_fit": {
            "dimension": "commercial",
            "judgment": "unknown",
            "summary": "Placeholder.",
            "findings": [
                {
                    "kind": "uncertainty",
                    "summary": "Placeholder uncertainty.",
                    "importance": "minor",
                }
            ],
        },
        "portfolio_fit": {
            "dimension": "portfolio",
            "judgment": "unknown",
            "summary": "Placeholder.",
            "findings": [
                {
                    "kind": "uncertainty",
                    "summary": "Placeholder uncertainty.",
                    "importance": "minor",
                }
            ],
        },
        "summary": {"summary": "Placeholder synthesis."},
        "job_analysis": {"posting": {"raw_text": "should not be accepted"}},
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        OpportunityAssessmentExtraction.model_validate(payload)
