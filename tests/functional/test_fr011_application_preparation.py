"""Functional journey for FR-011 M0 Application Preparation Orchestration."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.application_preparation import (
    ApplicationPreparationOrchestrator,
)
from career_intelligence.opportunities import OpportunityService
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)


def test_orchestrated_preparation_produces_verifiable_package(
    tmp_path: Path,
) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path,
        source_url="https://au.seek.com/job/20101010",
        title="Senior AI Engineer",
        company="Prep Co",
        raw_text="Senior AI Engineer. Python required. Hybrid Melbourne. Prep Co.",
    )
    packages = package_service(tmp_path, opportunities, profile)
    orchestrator = ApplicationPreparationOrchestrator(
        opportunities,
        packages,
        runs_root=tmp_path / "preparation_runs",
    )

    state = orchestrator.run(opportunity_id, **approved_gate_options())
    assert state.status == "completed"
    assert state.package is not None

    reloaded_opportunities = OpportunityService.from_path(tmp_path)
    reloaded_packages = ApplicationPackageService(
        reloaded_opportunities,
        profile=profile,
        packages_root=tmp_path / "application_packages",
        cv_output_dir=tmp_path / "cv_generated",
        cover_letter_output_dir=tmp_path / "cover_letter_generated",
    )
    manifest = reloaded_packages.get(opportunity_id, verify=True)
    assert manifest.opportunity_id == opportunity_id
    assert manifest.prepared_at == state.package.prepared_at
    assert Path(manifest.cv.markdown_path).is_file()
    assert Path(manifest.cover_letter.markdown_path).is_file()

    # Upstream Opportunity evidence remains untouched.
    artifacts = reloaded_opportunities.load_artifacts(opportunity_id)
    assert artifacts.strategy is not None
