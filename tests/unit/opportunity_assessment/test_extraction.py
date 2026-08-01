"""Unit tests for the internal OpportunityAssessmentExtraction schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.opportunity_assessment.extraction import (
    AlignmentExtractionFinding,
    OpportunityAssessmentExtraction,
)
from career_intelligence.opportunity_assessment.models import OpportunityAssessment


def test_extraction_fields_match_opportunity_assessment_minus_job_analysis() -> None:
    assert set(OpportunityAssessment.model_fields) - {"job_analysis"} == set(
        OpportunityAssessmentExtraction.model_fields
    )


def test_extraction_uses_schema_enforced_finding_types() -> None:
    """Extraction findings are not domain FitFinding — JSON Schema must carry minItems."""
    for name in ("technical_fit", "commercial_fit", "portfolio_fit"):
        assert (
            OpportunityAssessmentExtraction.model_fields[name].annotation
            is not OpportunityAssessment.model_fields[name].annotation
        )

    schema = AlignmentExtractionFinding.model_json_schema()
    assert schema["properties"]["profile_evidence"]["minItems"] == 1
    assert schema["properties"]["job_evidence"]["minItems"] == 1


def test_extraction_rejects_alignment_with_empty_profile_evidence() -> None:
    with pytest.raises(ValidationError):
        AlignmentExtractionFinding.model_validate(
            {
                "kind": "alignment",
                "summary": "Hybrid Melbourne matches preference",
                "importance": "minor",
                "job_evidence": [{"source": "work_arrangement"}],
                "profile_evidence": [],
                "assumption": None,
            }
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
