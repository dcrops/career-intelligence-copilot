"""Shared builders for FR-012 M1 submission orchestrator tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.opportunities import OpportunityService
from career_intelligence.profile import CareerProfile
from career_intelligence.submission import (
    FakeSubmissionAdapter,
    InMemorySubmissionAttemptStore,
    ManualAssistedAdapter,
    SubmissionOrchestrator,
)
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)

DESTINATION = "https://example.com/jobs/apply/1"


def prepared_workspace(
    tmp_path: Path,
    *,
    decision: str = "apply",
) -> tuple[
    OpportunityService,
    ApplicationPackageService,
    CareerProfile,
    str,
]:
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path,
        decision=decision,
    )
    packages = package_service(tmp_path, opportunities, profile)
    if decision == "apply":
        packages.prepare(opportunity_id, **approved_gate_options())  # type: ignore[arg-type]
    return opportunities, packages, profile, opportunity_id


def make_orchestrator(
    tmp_path: Path,
    opportunities: OpportunityService,
    packages: ApplicationPackageService,
    *,
    fake: FakeSubmissionAdapter | None = None,
    manual: ManualAssistedAdapter | None = None,
    store: InMemorySubmissionAttemptStore | None = None,
) -> tuple[SubmissionOrchestrator, FakeSubmissionAdapter, ManualAssistedAdapter]:
    fake_adapter = fake or FakeSubmissionAdapter()
    manual_adapter = manual or ManualAssistedAdapter()
    orchestrator = SubmissionOrchestrator(
        opportunities,
        packages,
        store=store or InMemorySubmissionAttemptStore(),
        adapters={
            "fake": fake_adapter,
            "manual_assisted": manual_adapter,
        },
        enable_truth_gate=False,
    )
    return orchestrator, fake_adapter, manual_adapter
