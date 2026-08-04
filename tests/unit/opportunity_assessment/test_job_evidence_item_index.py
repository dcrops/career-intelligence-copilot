"""Regression tests for job_evidence item_index extraction constraints."""

from __future__ import annotations

import pytest
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import posting_applied_ai_engineer
from career_intelligence.opportunity_assessment.errors import (
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.extraction import (
    OpportunityAssessmentExtraction,
    request_constrained_extraction_type,
)
from career_intelligence.opportunity_assessment.job_evidence_indexes import (
    inject_job_evidence_item_index_enums,
    job_analysis_list_lengths,
    validate_job_evidence_item_index,
    validate_job_evidence_indexes_in_payload,
)
from career_intelligence.opportunity_assessment.openai_assessor import _coerce_extraction
from career_intelligence.opportunity_assessment.refs import validate_references
from career_intelligence.profile import CareerProfileService
from pathlib import Path


def _job():
    return JobAnalysisService(FixtureExtractor()).analyse(posting_applied_ai_engineer())


def _profile():
    return CareerProfileService.from_path(
        Path(__file__).parents[2] / "fixtures" / "minimal_valid_profile.yaml"
    ).load()


def _lengths():
    return job_analysis_list_lengths(_job())


def test_valid_first_and_last_responsibility_indexes() -> None:
    lengths = _lengths()
    n = lengths["responsibility"]
    assert n >= 1
    validate_job_evidence_item_index(
        source="responsibility", item_index=0, lengths=lengths
    )
    validate_job_evidence_item_index(
        source="responsibility", item_index=n - 1, lengths=lengths
    )


def test_negative_index_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        validate_job_evidence_item_index(
            source="technology", item_index=-1, lengths=_lengths()
        )


def test_index_equal_to_collection_length_rejected() -> None:
    lengths = _lengths()
    n = lengths["technology"]
    with pytest.raises(ValueError, match="out of range"):
        validate_job_evidence_item_index(
            source="technology", item_index=n, lengths=lengths
        )


def test_large_out_of_range_index_rejected() -> None:
    with pytest.raises(ValueError, match="out of range"):
        validate_job_evidence_item_index(
            source="responsibility", item_index=9, lengths={"responsibility": 6}
        )


def test_responsibility_index_cannot_use_technology_length() -> None:
    """A responsibility index must be validated against responsibilities only."""
    lengths = {"technology": 10, "responsibility": 2, "experience_requirement": 1}
    validate_job_evidence_item_index(
        source="technology", item_index=9, lengths=lengths
    )
    with pytest.raises(ValueError, match="out of range"):
        validate_job_evidence_item_index(
            source="responsibility", item_index=9, lengths=lengths
        )


def test_empty_collection_cannot_accept_an_index() -> None:
    lengths = {"technology": 0, "responsibility": 3, "experience_requirement": 0}
    with pytest.raises(ValueError, match="0 technology"):
        validate_job_evidence_item_index(
            source="technology", item_index=0, lengths=lengths
        )


def test_schema_enums_are_per_collection() -> None:
    job = _job()
    lengths = job_analysis_list_lengths(job)
    schema = request_constrained_extraction_type(
        ["experience:example-role"], job
    ).model_json_schema()
    defs = schema.get("$defs") or {}
    tech = defs.get("ExtractionTechnologyJobEvidenceRef") or {}
    resp = defs.get("ExtractionResponsibilityJobEvidenceRef") or {}
    tech_enum = (tech.get("properties") or {}).get("item_index", {}).get("enum")
    resp_enum = (resp.get("properties") or {}).get("item_index", {}).get("enum")
    assert tech_enum == list(range(lengths["technology"]))
    assert resp_enum == list(range(lengths["responsibility"]))
    assert tech_enum != resp_enum or lengths["technology"] == lengths["responsibility"]


def test_inject_empty_collection_is_unsatisfiable() -> None:
    schema = OpportunityAssessmentExtraction.model_json_schema()
    patched = inject_job_evidence_item_index_enums(
        schema,
        {"technology": 0, "responsibility": 2, "experience_requirement": 1},
    )
    tech = (patched.get("$defs") or {}).get("ExtractionTechnologyJobEvidenceRef") or {}
    item = (tech.get("properties") or {}).get("item_index") or {}
    assert item.get("maximum") == -1
    assert item.get("minimum") == 0


def test_coerce_rejects_out_of_range_before_domain() -> None:
    job = _job()
    n_resp = len(job.responsibilities)
    payload = {
        "technical_fit": {
            "dimension": "technical",
            "judgment": "unknown",
            "summary": "Technical.",
            "findings": [
                {
                    "kind": "uncertainty",
                    "summary": "Uncertain.",
                    "importance": "minor",
                    "job_evidence": [
                        {
                            "source": "responsibility",
                            "item_index": n_resp + 3,
                        }
                    ],
                    "profile_evidence": [],
                    "assumption": None,
                }
            ],
        },
        "commercial_fit": {
            "dimension": "commercial",
            "judgment": "unknown",
            "summary": "Commercial.",
            "findings": [
                {
                    "kind": "uncertainty",
                    "summary": "Uncertain.",
                    "importance": "minor",
                }
            ],
        },
        "portfolio_fit": {
            "dimension": "portfolio",
            "judgment": "unknown",
            "summary": "Portfolio.",
            "findings": [
                {
                    "kind": "uncertainty",
                    "summary": "Uncertain.",
                    "importance": "minor",
                }
            ],
        },
        "summary": {"summary": "item_index regression."},
    }
    with pytest.raises(OpportunityAssessmentValidationError, match="out of range"):
        _coerce_extraction(payload, catalogue=[], job_analysis=job)


def test_domain_validation_still_rejects_out_of_range() -> None:
    from career_intelligence.opportunity_assessment.models import OpportunityAssessment

    job = _job()
    profile = _profile()
    n = len(job.responsibilities)
    assessment = OpportunityAssessment.model_validate(
        {
            "job_analysis": job.model_dump(mode="json"),
            "technical_fit": {
                "dimension": "technical",
                "judgment": "moderate",
                "summary": "Technical.",
                "findings": [
                    {
                        "kind": "partial_alignment",
                        "summary": "Partial.",
                        "importance": "material",
                        "job_evidence": [
                            {"source": "responsibility", "item_index": n + 1}
                        ],
                        "profile_evidence": [
                            {"source": "experience", "ref": "experience:example-role"}
                        ],
                        "assumption": None,
                    }
                ],
            },
            "commercial_fit": {
                "dimension": "commercial",
                "judgment": "unknown",
                "summary": "Commercial.",
                "findings": [
                    {
                        "kind": "uncertainty",
                        "summary": "Uncertain.",
                        "importance": "minor",
                    }
                ],
            },
            "portfolio_fit": {
                "dimension": "portfolio",
                "judgment": "unknown",
                "summary": "Portfolio.",
                "findings": [
                    {
                        "kind": "uncertainty",
                        "summary": "Uncertain.",
                        "importance": "minor",
                    }
                ],
            },
            "summary": {"summary": "Domain item_index regression."},
        }
    )
    with pytest.raises(Exception, match="out of range"):
        validate_references(assessment, profile)


def test_payload_walk_rejects_cross_collection_misuse() -> None:
    job = _job()
    lengths = job_analysis_list_lengths(job)
    tech_n = lengths["technology"]
    # Valid for technology, invalid if claimed as responsibility with same number
    # when responsibility is shorter — construct a payload using responsibility
    # with technology's last index when tech_n > responsibility length.
    if tech_n <= lengths["responsibility"]:
        pytest.skip("fixture collections do not diverge enough")
    payload = {
        "job_evidence": [
            {"source": "responsibility", "item_index": tech_n - 1}
        ]
    }
    with pytest.raises(ValueError, match="out of range"):
        validate_job_evidence_indexes_in_payload(payload, job)
