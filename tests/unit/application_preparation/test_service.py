"""Unit tests for FR-011 M0 Application Preparation Orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.application_preparation import (
    PREPARATION_STEPS,
    PreparationRunNotFoundError,
)
from career_intelligence.cv_generation import TailoringOptions
from tests.unit.application_preparation.helpers import (
    approved_gate_options,
    package_service,
    preparation_orchestrator,
    seed_applied_opportunity,
)


def test_run_completes_validate_then_prepare(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    orchestrator = preparation_orchestrator(
        tmp_path, opportunities, profile, packages=packages
    )

    state = orchestrator.run(opportunity_id, **approved_gate_options())

    assert state.status == "completed"
    assert state.opportunity_id == opportunity_id
    assert [step.step_id for step in state.completed_steps] == list(PREPARATION_STEPS)
    assert state.package is not None
    assert state.package.opportunity_id == opportunity_id
    assert state.error is None

    manifest = packages.get(opportunity_id, verify=True)
    assert manifest.prepared_at == state.package.prepared_at
    reloaded = orchestrator.get(state.run_id)
    assert reloaded.model_dump() == state.model_dump()


def test_non_apply_fails_at_validate_preconditions(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path, decision="skip"
    )
    packages = package_service(tmp_path, opportunities, profile)
    orchestrator = preparation_orchestrator(
        tmp_path, opportunities, profile, packages=packages
    )

    state = orchestrator.run(opportunity_id, **approved_gate_options())

    assert state.status == "failed"
    assert state.error is not None
    assert state.error.step_id == "validate_preconditions"
    assert "apply" in state.error.message
    assert state.completed_steps == []
    assert state.package is None
    assert packages.exists(opportunity_id) is False


def test_missing_opportunity_fails_at_validate(tmp_path: Path) -> None:
    opportunities, _, profile = seed_applied_opportunity(tmp_path)
    orchestrator = preparation_orchestrator(tmp_path, opportunities, profile)
    missing_id = "opp_01K00000000000000000000000"

    state = orchestrator.run(missing_id, **approved_gate_options())

    assert state.status == "failed"
    assert state.error is not None
    assert state.error.step_id == "validate_preconditions"
    assert state.package is None


def test_gate_failure_fails_at_prepare_package(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    orchestrator = preparation_orchestrator(
        tmp_path, opportunities, profile, packages=packages
    )
    # Preconditions pass; FR-006/007 gates still refuse without approval.
    state = orchestrator.run(
        opportunity_id,
        tailoring_options=TailoringOptions(owner_approved_to_tailor=False),
    )

    assert state.status == "failed"
    assert [step.step_id for step in state.completed_steps] == [
        "validate_preconditions"
    ]
    assert state.error is not None
    assert state.error.step_id == "prepare_package"
    assert state.package is None
    assert packages.exists(opportunity_id) is False


def test_get_unknown_run_fails_closed(tmp_path: Path) -> None:
    opportunities, _, profile = seed_applied_opportunity(tmp_path)
    orchestrator = preparation_orchestrator(tmp_path, opportunities, profile)

    with pytest.raises(PreparationRunNotFoundError):
        orchestrator.get("apr_01K00000000000000000000000")


def test_json_store_round_trip(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    from career_intelligence.application_preparation import (
        ApplicationPreparationOrchestrator,
    )

    orchestrator = ApplicationPreparationOrchestrator(
        opportunities,
        packages,
        runs_root=tmp_path / "preparation_runs",
    )
    state = orchestrator.run(opportunity_id, **approved_gate_options())
    reloaded = ApplicationPreparationOrchestrator(
        opportunities,
        packages,
        runs_root=tmp_path / "preparation_runs",
    ).get(state.run_id)

    assert reloaded.model_dump() == state.model_dump()
    assert (tmp_path / "preparation_runs" / f"{state.run_id}.json").is_file()
