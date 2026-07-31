"""Shared builders for FR-011 application preparation tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.application_preparation import (
    ApplicationPreparationOrchestrator,
    InMemoryPreparationRunStore,
)
from career_intelligence.opportunities import OpportunityService
from career_intelligence.profile import CareerProfile
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)

__all__ = [
    "approved_gate_options",
    "package_service",
    "preparation_orchestrator",
    "seed_applied_opportunity",
]


def preparation_orchestrator(
    tmp_path: Path,
    opportunities: OpportunityService,
    profile: CareerProfile,
    *,
    packages: ApplicationPackageService | None = None,
) -> ApplicationPreparationOrchestrator:
    pkg = packages or package_service(tmp_path, opportunities, profile)
    return ApplicationPreparationOrchestrator(
        opportunities,
        pkg,
        store=InMemoryPreparationRunStore(),
    )
