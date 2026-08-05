"""Unit tests for FR-014 M2 catalogue builder and technology validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import (
    TruthValidationService,
    build_catalogue_from_profile,
    catalogue_supports_technology,
    validate_catalogue_contract,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
REDWOLF = (
    "Roles centred on Python, TypeScript, and Vue are where I do my best "
    "engineering work."
)


def _profile_with_python_fastapi() -> CareerProfile:
    profile = CareerProfileService.from_path(
        FIXTURES / "minimal_valid_profile.yaml"
    ).load()
    data = profile.model_dump(mode="python")
    data["skills"]["technical"].append(
        {"name": "FastAPI", "evidence": "project:example-project"}
    )
    data["projects"][0]["technologies"] = ["Python", "FastAPI"]
    return CareerProfile.model_validate(data)


def test_catalogue_from_profile_includes_python_and_is_authoritative() -> None:
    profile = _profile_with_python_fastapi()
    catalogue = build_catalogue_from_profile(profile)
    validate_catalogue_contract(catalogue)
    assert catalogue_supports_technology(catalogue, "Python") is not None
    assert catalogue_supports_technology(catalogue, "FastAPI") is not None
    assert catalogue_supports_technology(catalogue, "Vue") is None
    assert all(
        entry.provenance.authority == "candidate_authoritative"
        for entry in catalogue.entries
    )


def test_redwolf_typescript_vue_fail_python_supported() -> None:
    profile = _profile_with_python_fastapi()
    service = TruthValidationService()
    report = service.validate_markdown(
        markdown=REDWOLF,
        profile=profile,
        context_technology_labels=["Python", "TypeScript", "Vue"],
    )
    assert report.detection_performed is True
    assert report.validation_performed is True
    assert report.coverage_status == "complete"
    assert report.outcome == "fail"

    assert any(
        finding.claim.object_key == "typescript" and finding.severity == "blocking"
        for finding in report.findings
    )
    assert any(
        finding.claim.object_key in {"vue", "vuejs"} and finding.severity == "blocking"
        for finding in report.findings
    )
    python = next(
        finding
        for finding in report.findings
        if finding.claim.object_key == "python"
    )
    assert python.evidence_status == "supported"
    assert python.severity == "info"
    assert python.claim.claim_class == "A"


def test_supported_python_fastapi_claims_pass() -> None:
    profile = _profile_with_python_fastapi()
    service = TruthValidationService()
    markdown = "I have experience with Python and FastAPI in production services."
    report = service.validate_markdown(markdown=markdown, profile=profile)
    assert report.outcome == "pass"
    assert all(
        finding.evidence_status == "supported"
        for finding in report.findings
        if finding.claim.claim_class == "A"
    )


def test_employer_context_typescript_vue_pass() -> None:
    profile = _profile_with_python_fastapi()
    service = TruthValidationService()
    markdown = "The role uses TypeScript and Vue extensively."
    report = service.validate_markdown(
        markdown=markdown,
        profile=profile,
        context_technology_labels=["TypeScript", "Vue"],
    )
    assert report.outcome == "pass"
    assert report.findings
    assert all(finding.claim.claim_class == "B" for finding in report.findings)
    assert all(
        finding.evidence_status == "not_applicable" for finding in report.findings
    )


def test_jd_context_labels_do_not_authorize_capability() -> None:
    profile = _profile_with_python_fastapi()
    service = TruthValidationService()
    report = service.validate_markdown(
        markdown="I am proficient in Vue.",
        profile=profile,
        context_technology_labels=["Vue", "TypeScript"],
    )
    assert report.outcome == "fail"
    finding = report.findings[0]
    assert finding.claim.claim_class == "A"
    assert finding.evidence_status == "unsupported"
    assert finding.severity == "blocking"
    assert finding.evidence_citations == []


def test_aspiration_vue_not_blocking() -> None:
    profile = _profile_with_python_fastapi()
    service = TruthValidationService()
    report = service.validate_markdown(
        markdown="I am interested in expanding into Vue.",
        profile=profile,
        context_technology_labels=["Vue"],
    )
    assert report.outcome in {"pass", "warning"}
    assert report.findings[0].claim.claim_class == "C"
    assert report.findings[0].severity in {"info", "warning"}


def test_bare_tech_mention_not_a_claim() -> None:
    """False-positive safeguard: unframed tech tokens are not Class A claims."""
    profile = _profile_with_python_fastapi()
    service = TruthValidationService()
    report = service.validate_markdown(
        markdown="Keywords: TypeScript, Vue, React.",
        profile=profile,
        context_technology_labels=["TypeScript", "Vue", "React"],
    )
    assert report.outcome == "pass"
    assert report.findings == []


def test_empty_markdown_complete_coverage_may_pass() -> None:
    profile = _profile_with_python_fastapi()
    service = TruthValidationService()
    report = service.validate_markdown(markdown="", profile=profile)
    assert report.outcome == "pass"
    assert report.detection_performed is True
    assert report.validation_performed is True
    assert report.coverage_status == "complete"


def test_requires_profile_or_catalogue() -> None:
    service = TruthValidationService()
    with pytest.raises(ValueError, match="profile or catalogue"):
        service.validate_markdown(markdown=REDWOLF)
