"""Functional: external packages must include navigable candidate contact."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.application_package import (
    ApplicationPackageContactError,
    ApplicationPackageService,
)
from career_intelligence.cover_letter import CoverLetterGenerationOptions
from career_intelligence.cv_generation import ContactDetails, CvGenerationOptions
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)


def test_package_prepare_includes_contact_and_portfolio_nav(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path,
        source_url="https://au.seek.com/job/30303030",
        title="AI Engineer",
        company="Contact Co",
        raw_text=(
            "AI Engineer. Python. LangChain. Production AI systems. "
            "Contact Co Melbourne hybrid."
        ),
    )
    service = package_service(tmp_path, opportunities, profile)
    manifest = service.prepare(opportunity_id, **approved_gate_options())

    cv_md = Path(manifest.cv.markdown_path).read_text(encoding="utf-8")
    cl_md = Path(manifest.cover_letter.markdown_path).read_text(encoding="utf-8")

    assert "David Cropper" in cv_md or profile.identity.full_name in cv_md
    assert "candidate@example.com" in cv_md
    assert "0400 000 000" in cv_md
    assert "Melbourne, VIC" in cv_md
    assert "linkedin.com/in/example" in cv_md
    assert "example.com/portfolio" in cv_md
    assert "github.com/example" in cv_md

    assert profile.identity.full_name in cl_md
    assert "candidate@example.com" in cl_md
    assert "0400 000 000" in cl_md
    assert "**Portfolio:**" in cl_md
    assert "**GitHub:**" in cl_md
    assert "https://example.com/portfolio/" in cl_md
    assert "https://github.com/example" in cl_md
    assert "available in my portfolio" not in cl_md.casefold()


def test_package_prepare_fails_closed_without_contact(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    options = approved_gate_options()
    options["cv_options"] = CvGenerationOptions(tailoring_plan_approved=True)
    options["cover_letter_options"] = CoverLetterGenerationOptions(
        cover_letter_plan_approved=True
    )
    with pytest.raises(ApplicationPackageContactError, match="contact"):
        service.prepare(opportunity_id, **options)


def test_explicit_partial_overlay_still_fails_for_external_package(
    tmp_path: Path,
) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    options = approved_gate_options()
    partial = ContactDetails(email="candidate@example.com")
    options["cv_options"] = CvGenerationOptions(
        tailoring_plan_approved=True,
        contact=partial,
    )
    options["cover_letter_options"] = CoverLetterGenerationOptions(
        cover_letter_plan_approved=True,
        contact=partial,
    )
    with pytest.raises(ApplicationPackageContactError, match="phone"):
        service.prepare(opportunity_id, **options)
