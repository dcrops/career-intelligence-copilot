"""Helpers for FR-014 M1 truth-validation contract tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from career_intelligence.truth_validation import (
    ArtefactRef,
    CandidateEvidenceCatalogue,
    CatalogueEvidenceEntry,
    Claim,
    EvidenceProvenance,
    TruthFinding,
    TruthReport,
    new_catalogue_entry_id,
    new_claim_id,
    new_truth_finding_id,
    new_truth_report_id,
)

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
OPP_A = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"


def make_provenance(**overrides: Any) -> EvidenceProvenance:
    payload: dict[str, Any] = {
        "source_kind": "profile_skill",
        "authority": "candidate_authoritative",
        "provenance_ref": "skill:python",
        "excerpt": "Python",
    }
    payload.update(overrides)
    return EvidenceProvenance.model_validate(payload)


def make_catalogue_entry(**overrides: Any) -> CatalogueEvidenceEntry:
    payload: dict[str, Any] = {
        "entry_id": new_catalogue_entry_id(),
        "object_key": "python",
        "display_label": "Python",
        "aliases": ["py"],
        "claim_kinds": ["technology"],
        "recency": "current",
        "provenance": make_provenance(),
    }
    payload.update(overrides)
    if "provenance" in overrides and isinstance(overrides["provenance"], dict):
        payload["provenance"] = make_provenance(**overrides["provenance"])
    return CatalogueEvidenceEntry.model_validate(payload)


def make_catalogue(
    entries: list[CatalogueEvidenceEntry] | None = None,
    **overrides: Any,
) -> CandidateEvidenceCatalogue:
    payload: dict[str, Any] = {
        "catalogue_id": "cat_test",
        "built_at": NOW,
        "profile_fingerprint": "profile-fp-1",
        "entries": entries if entries is not None else [make_catalogue_entry()],
    }
    payload.update(overrides)
    return CandidateEvidenceCatalogue.model_validate(payload)


def make_claim(**overrides: Any) -> Claim:
    payload: dict[str, Any] = {
        "claim_id": new_claim_id(),
        "claim_class": "A",
        "claim_kind": "technology",
        "subject": "candidate",
        "predicate": "has_skill",
        "object_key": "python",
        "strength": "experienced",
        "surface_text": "I have experience with Python",
        "source_artefact": "cover_letter_markdown",
    }
    payload.update(overrides)
    return Claim.model_validate(payload)


def make_finding(**overrides: Any) -> TruthFinding:
    claim = overrides.pop("claim", None) or make_claim()
    payload: dict[str, Any] = {
        "finding_id": new_truth_finding_id(),
        "claim": claim,
        "detection_certainty": "certain",
        "evidence_status": "supported",
        "severity": "info",
        "evidence_citations": [make_provenance()],
        "recommended_action": "none",
    }
    payload.update(overrides)
    if "claim" in overrides and isinstance(overrides.get("claim"), dict):
        payload["claim"] = make_claim(**overrides["claim"])
    return TruthFinding.model_validate(payload)


def make_report(
    findings: list[TruthFinding] | None = None,
    **overrides: Any,
) -> TruthReport:
    payload: dict[str, Any] = {
        "report_id": new_truth_report_id(),
        "created_at": NOW,
        "gate": "post_edit_authoritative",
        "artefact": ArtefactRef(
            kind="cover_letter_markdown",
            path="career-documents/cover-letters/generated/example.md",
            content_fingerprint="md-fp-1",
        ),
        "opportunity_id": OPP_A,
        "catalogue_id": "cat_test",
        "coverage_status": "complete",
        "detection_performed": True,
        "validation_performed": True,
        "findings": findings if findings is not None else [],
        "outcome": "pass",
        "summary": "No material unsupported candidate claims.",
    }
    payload.update(overrides)
    return TruthReport.model_validate(payload)
