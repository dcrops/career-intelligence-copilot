"""Regression tests for profile evidence ref canonicalisation (extraction boundary)."""

from __future__ import annotations

import pytest

from career_intelligence.opportunity_assessment.extraction import (
    OpportunityAssessmentExtraction,
    catalogue_constrained_extraction_type,
)
from career_intelligence.opportunity_assessment.models import ProfileEvidenceRef
from career_intelligence.opportunity_assessment.openai_assessor import _coerce_extraction
from career_intelligence.opportunity_assessment.profile_evidence_canonicalisation import (
    canonicalize_profile_evidence_ref,
)
from pydantic import ValidationError


_CATALOGUE = frozenset(
    {
        "experience:nbn-data-engineer-2020",
        "experience:ai-engineering-development-2025",
        "project:operational-intelligence-copilot",
    }
)


def test_trailing_full_stop_canonicalises_to_exact_token() -> None:
    assert (
        canonicalize_profile_evidence_ref(
            "experience:nbn-data-engineer-2020.", _CATALOGUE
        )
        == "experience:nbn-data-engineer-2020"
    )


def test_trailing_comma_canonicalises_to_exact_token() -> None:
    assert (
        canonicalize_profile_evidence_ref(
            "experience:nbn-data-engineer-2020,", _CATALOGUE
        )
        == "experience:nbn-data-engineer-2020"
    )


def test_closing_brace_bracket_contamination_canonicalises() -> None:
    assert (
        canonicalize_profile_evidence_ref(
            "experience:ai-engineering-development-2025},",
            _CATALOGUE,
        )
        == "experience:ai-engineering-development-2025"
    )
    assert (
        canonicalize_profile_evidence_ref(
            "[experience:nbn-data-engineer-2020]",
            _CATALOGUE,
        )
        == "experience:nbn-data-engineer-2020"
    )


def test_valid_exact_token_unchanged() -> None:
    token = "experience:nbn-data-engineer-2020"
    assert canonicalize_profile_evidence_ref(token, _CATALOGUE) == token


def test_unknown_token_remains_rejected() -> None:
    with pytest.raises(ValueError, match="unknown profile evidence ref"):
        canonicalize_profile_evidence_ref(
            "experience:not-a-real-role-2099.", _CATALOGUE
        )


def test_token_without_namespace_remains_rejected_even_after_peeling() -> None:
    """Missing namespace must not be silently mapped to a catalogue token."""
    with pytest.raises(ValueError, match="unknown profile evidence ref"):
        canonicalize_profile_evidence_ref(
            "ai-engineering-development-2025},", _CATALOGUE
        )


def test_ambiguous_canonicalisation_remains_rejected() -> None:
    """If peeling could match more than one catalogue token, reject."""
    catalogue_ambiguous = frozenset({"experience:x", "experience:x."})
    with pytest.raises(ValueError, match="ambiguous profile evidence ref"):
        canonicalize_profile_evidence_ref("experience:x.)", catalogue_ambiguous)


def test_domain_validator_still_rejects_trailing_punctuation() -> None:
    with pytest.raises(ValidationError, match="trailing punctuation"):
        ProfileEvidenceRef.model_validate(
            {
                "source": "experience",
                "ref": "experience:nbn-data-engineer-2020.",
            }
        )


def test_coerce_extraction_canonicalises_contaminated_refs() -> None:
    payload = {
        "technical_fit": {
            "dimension": "technical",
            "judgment": "moderate",
            "summary": "Technical fit.",
            "findings": [
                {
                    "kind": "partial_alignment",
                    "summary": "Experience supports delivery.",
                    "importance": "material",
                    "job_evidence": [{"source": "seniority", "excerpt": "Engineer"}],
                    "profile_evidence": [
                        {
                            "source": "experience",
                            "ref": "experience:nbn-data-engineer-2020.",
                        }
                    ],
                    "assumption": None,
                }
            ],
        },
        "commercial_fit": {
            "dimension": "commercial",
            "judgment": "unknown",
            "summary": "Commercial unknown.",
            "findings": [
                {
                    "kind": "uncertainty",
                    "summary": "Salary unstated.",
                    "importance": "minor",
                    "job_evidence": [{"source": "compensation"}],
                    "profile_evidence": [],
                    "assumption": None,
                }
            ],
        },
        "portfolio_fit": {
            "dimension": "portfolio",
            "judgment": "moderate",
            "summary": "Portfolio supports narrative.",
            "findings": [
                {
                    "kind": "alignment",
                    "summary": "Project supports Python delivery.",
                    "importance": "material",
                    "job_evidence": [
                        {"source": "technology", "item_index": 0, "name": "Python"}
                    ],
                    "profile_evidence": [
                        {
                            "source": "project",
                            "ref": "project:operational-intelligence-copilot},",
                        }
                    ],
                    "assumption": None,
                }
            ],
        },
        "summary": {"summary": "Canonicalisation regression assessment."},
    }
    extraction = _coerce_extraction(payload, catalogue=list(_CATALOGUE))
    tech_ref = extraction.technical_fit.findings[0].profile_evidence[0].ref
    port_ref = extraction.portfolio_fit.findings[0].profile_evidence[0].ref
    assert tech_ref == "experience:nbn-data-engineer-2020"
    assert port_ref == "project:operational-intelligence-copilot"


def test_coerce_extraction_rejects_unknown_after_peeling() -> None:
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
                    "job_evidence": [],
                    "profile_evidence": [
                        {"source": "experience", "ref": "experience:missing-role."}
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
        "summary": {"summary": "Unknown ref regression."},
    }
    with pytest.raises(Exception, match="unknown profile evidence ref"):
        _coerce_extraction(payload, catalogue=list(_CATALOGUE))


def test_catalogue_constrained_schema_enums_ref() -> None:
    ordered = [
        "experience:nbn-data-engineer-2020",
        "experience:ai-engineering-development-2025",
        "project:operational-intelligence-copilot",
    ]
    constrained = catalogue_constrained_extraction_type(ordered)
    schema = constrained.model_json_schema()
    defs = schema.get("$defs") or {}
    ref_def = defs.get("ExtractionProfileEvidenceRef") or {}
    ref_schema = (ref_def.get("properties") or {}).get("ref") or {}
    assert ref_schema.get("enum") == ordered
