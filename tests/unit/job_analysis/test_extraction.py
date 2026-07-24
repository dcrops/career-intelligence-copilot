"""Unit tests for the internal JobAnalysisExtraction schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.job_analysis.extraction import (
    ExtractedPostingIdentity,
    JobAnalysisExtraction,
)
from career_intelligence.job_analysis.models import JobAnalysis

_EXTRACTION_ONLY_FIELDS = frozenset({"posting_identity"})


def test_extraction_fields_match_job_analysis_minus_posting_plus_identity() -> None:
    analysis_fields = set(JobAnalysis.model_fields) - {"posting"}
    extraction_fields = set(JobAnalysisExtraction.model_fields)
    assert extraction_fields - _EXTRACTION_ONLY_FIELDS == analysis_fields
    assert _EXTRACTION_ONLY_FIELDS <= extraction_fields


def test_extraction_reuses_nested_job_analysis_types() -> None:
    for name in JobAnalysisExtraction.model_fields:
        if name in _EXTRACTION_ONLY_FIELDS:
            continue
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


def test_extracted_identity_requires_evidence_when_set() -> None:
    with pytest.raises(ValidationError, match="evidence"):
        ExtractedPostingIdentity.model_validate({"title": "AI Engineer"})


def test_extracted_identity_allows_nulls_without_evidence() -> None:
    identity = ExtractedPostingIdentity.model_validate({})
    assert identity.title is None
    assert identity.company is None
