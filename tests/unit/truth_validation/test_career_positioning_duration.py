"""Career positioning duration claims — overall vs domain-specific inflation."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.profile import CareerProfileService
from career_intelligence.truth_validation import (
    AI_ENGINEERING_DURATION_KEY,
    COMMERCIAL_AI_KEY,
    DATA_ENGINEERING_DURATION_KEY,
    OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY,
    TruthValidationService,
    build_catalogue_from_profile,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
LIVE_PROFILE = Path(__file__).resolve().parents[3] / "data" / "career_profile.yaml"

_APPROVED = (
    "Experienced engineer with 10+ years across testing, automation, data "
    "engineering and applied AI engineering."
)


def _live_profile():
    return CareerProfileService.from_path(LIVE_PROFILE).load()


def _report(markdown: str):
    return TruthValidationService().validate_markdown(
        markdown=markdown, profile=_live_profile()
    )


def _duration_finding(report, key: str):
    return next(
        item
        for item in report.findings
        if item.claim.claim_kind == "duration" and item.claim.object_key == key
    )


def test_catalogue_overall_engineering_floor_from_chronology() -> None:
    profile = _live_profile()
    catalogue = build_catalogue_from_profile(profile)
    entry = next(
        item
        for item in catalogue.entries
        if item.object_key == OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY
    )
    assert entry.supported_years is not None
    assert entry.supported_years >= 10.0
    # Must not treat identity.summary as duration evidence provenance.
    assert "identity" not in (entry.provenance.provenance_ref or "")
    assert entry.provenance.source_kind == "profile_experience"


def test_approved_overall_positioning_supported() -> None:
    report = _report(_APPROVED)
    finding = _duration_finding(report, OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY)
    assert finding.evidence_status == "supported"
    assert finding.severity == "info"


def test_block_ten_plus_years_of_ai_engineering() -> None:
    report = _report("I have 10+ years of AI engineering experience.")
    finding = _duration_finding(report, AI_ENGINEERING_DURATION_KEY)
    assert finding.severity == "blocking"


def test_block_ten_plus_years_as_ai_engineer() -> None:
    report = _report("I have 10+ years as an AI Engineer.")
    finding = _duration_finding(report, AI_ENGINEERING_DURATION_KEY)
    assert finding.severity == "blocking"


def test_block_ten_plus_years_of_data_engineering() -> None:
    report = _report("I have 10+ years of data engineering.")
    finding = _duration_finding(report, DATA_ENGINEERING_DURATION_KEY)
    assert finding.severity == "blocking"


def test_block_ten_plus_years_of_data_and_ai_engineering() -> None:
    report = _report("I have 10+ years of data and AI engineering.")
    finding = _duration_finding(report, AI_ENGINEERING_DURATION_KEY)
    assert finding.severity == "blocking"


def test_block_ten_plus_years_of_commercial_ai_engineering() -> None:
    report = _report("I have 10+ years of commercial AI engineering.")
    finding = _duration_finding(report, COMMERCIAL_AI_KEY)
    assert finding.severity == "blocking"


def test_summary_text_is_not_catalogue_duration_evidence() -> None:
    """identity.summary must not inflate domain duration support."""
    profile = _live_profile()
    catalogue = build_catalogue_from_profile(profile)
    ai = next(
        item
        for item in catalogue.entries
        if item.object_key == AI_ENGINEERING_DURATION_KEY
    )
    # Live independent AI tenure is far below 10 years.
    assert ai.supported_years is None or ai.supported_years < 5.0
