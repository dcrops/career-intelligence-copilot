"""Unit tests for the internal JobAnalysisExtraction schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.job_analysis.extraction import JobAnalysisExtraction
from career_intelligence.job_analysis.models import JobAnalysis


def test_extraction_fields_match_job_analysis_minus_posting() -> None:
    assert set(JobAnalysis.model_fields) - {"posting"} == set(
        JobAnalysisExtraction.model_fields
    )


def test_extraction_reuses_nested_job_analysis_types() -> None:
    for name in JobAnalysisExtraction.model_fields:
        assert (
            JobAnalysisExtraction.model_fields[name].annotation
            == JobAnalysis.model_fields[name].annotation
        )


def test_extraction_rejects_posting_field() -> None:
    payload = {
        "role_family": {"family": "unknown"},
        "seniority": {"level": "unknown", "ambiguous": False},
        "compensation": {"clarity": "unstated"},
        "work_arrangement": {"arrangement": "unspecified"},
        "posting": {"raw_text": "should not be accepted"},
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        JobAnalysisExtraction.model_validate(payload)
