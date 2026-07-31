"""Shared builders for FR-010 application package tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterPlanOptions,
)
from career_intelligence.cv_generation import CvGenerationOptions, TailoringOptions
from career_intelligence.opportunities import OpportunityService
from career_intelligence.profile import CareerProfile
from tests.unit.application_strategy.helpers import minimal_profile
from tests.unit.opportunities.helpers import create_opportunity

STAMP = datetime(2026, 7, 30, 15, 0, 0, tzinfo=UTC)


def approved_gate_options() -> dict[str, object]:
    """Explicit FR-006 / FR-007 owner-approval options required for package prepare."""
    return {
        "tailoring_options": TailoringOptions(owner_approved_to_tailor=True),
        "cv_options": CvGenerationOptions(tailoring_plan_approved=True),
        "cover_letter_plan_options": CoverLetterPlanOptions(owner_approved_to_plan=True),
        "cover_letter_options": CoverLetterGenerationOptions(
            cover_letter_plan_approved=True
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
    return ApplicationPackageService(
        opportunities,
        profile=profile,
        packages_root=tmp_path / "application_packages",
        cv_output_dir=tmp_path / "cv_generated",
        cover_letter_output_dir=tmp_path / "cover_letter_generated",
    )
