"""Shared builders for FR-010 application package tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterPlanOptions,
)
from career_intelligence.cover_letter.bounded_composer import FixtureCoverLetterComposer
from career_intelligence.cv_generation import (
    ContactDetails,
    CvGenerationOptions,
    TailoringOptions,
)
from career_intelligence.opportunities import OpportunityService
from career_intelligence.profile import CareerProfile
from tests.unit.application_strategy.helpers import minimal_profile
from tests.unit.opportunities.helpers import create_opportunity

STAMP = datetime(2026, 7, 30, 15, 0, 0, tzinfo=UTC)

MINI_MASTER_CV = """# Test Candidate

Melbourne, VIC

**AI Engineer**

---

## Professional Summary

Experienced engineer with commercial data engineering and independent AI work.

## Technical Skills

**AI Engineering:** Python · FastAPI

## Professional Experience

### Data Engineer — Example Company

*Jan 2022 – Jan 2023 · Melbourne*

- Built validated data pipelines.

## Featured AI Projects

### Example Project

**Overview:** A production-minded example kept verbatim.

**Engineering Highlights:**

- Kept highlight

## AI Engineering Methodology

Applies AI to improve engineering quality.

## Certifications

- Example Cert
"""


def write_mini_master(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MINI_MASTER_CV, encoding="utf-8", newline="\n")
    return path


def approved_gate_options(*, master_cv_path: Path | None = None) -> dict[str, object]:
    """Explicit FR-006 / FR-007 owner-approval options required for package prepare."""
    contact = ContactDetails(
        email="candidate@example.com",
        phone="0400 000 000",
        location="Melbourne, VIC",
        linkedin_url="https://www.linkedin.com/in/example/",
        portfolio_url="https://example.com/portfolio/",
        github_url="https://github.com/example",
    )
    cv_kwargs: dict[str, object] = {
        "tailoring_plan_approved": True,
        "adapt_from_master": True,
        "rewrite_summary": False,
        "contact": contact,
    }
    if master_cv_path is not None:
        cv_kwargs["master_cv_path"] = str(master_cv_path)
    return {
        "tailoring_options": TailoringOptions(owner_approved_to_tailor=True),
        "cv_options": CvGenerationOptions(**cv_kwargs),
        "cover_letter_plan_options": CoverLetterPlanOptions(owner_approved_to_plan=True),
        "cover_letter_options": CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=contact,
        ),
        "prepared_at": STAMP,
    }


def seed_applied_opportunity(
    tmp_path: Path,
    *,
    decision: str = "apply",
    **pipeline_kwargs: object,
) -> tuple[OpportunityService, str, CareerProfile]:
    """Create a persisted Opportunity with artefacts and optional owner decision."""
    opportunities, opportunity, _pipeline = create_opportunity(tmp_path, **pipeline_kwargs)
    if decision:
        opportunities.record_decision(opportunity.opportunity_id, decision)  # type: ignore[arg-type]
    profile = minimal_profile()
    return opportunities, opportunity.opportunity_id, profile


def package_service(
    tmp_path: Path,
    opportunities: OpportunityService,
    profile: CareerProfile,
) -> ApplicationPackageService:
    master_path = write_mini_master(tmp_path / "master_cv.md")
    return ApplicationPackageService(
        opportunities,
        profile=profile,
        packages_root=tmp_path / "application_packages",
        cv_output_dir=tmp_path / "cv_generated",
        cover_letter_output_dir=tmp_path / "cover_letter_generated",
        cover_letter_composer=FixtureCoverLetterComposer(),
        master_cv_path=master_path,
    )
