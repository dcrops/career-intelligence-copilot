"""Unit tests for FR-010 M0 Application Package Preparation."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.application_package import (
    ApplicationPackageEligibilityError,
    ApplicationPackageNotFoundError,
)
from career_intelligence.cover_letter import CoverLetterPlanGateError
from career_intelligence.cv_generation import TailoringOptions, TailoringPlanGateError
from career_intelligence.opportunities import ARTIFACT_FILENAMES
from tests.unit.application_package.helpers import (
    STAMP,
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)


def test_apply_opportunity_produces_package_manifest(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)

    manifest = service.prepare(opportunity_id, **approved_gate_options())

    assert manifest.opportunity_id == opportunity_id
    assert manifest.prepared_at == STAMP
    assert manifest.owner_review_required is True
    assert Path(manifest.cv.markdown_path).is_file()
    assert Path(manifest.cv.html_path).is_file()
    assert Path(manifest.cover_letter.markdown_path).is_file()
    assert Path(manifest.cover_letter.html_path).is_file()
    assert service.get(opportunity_id) == manifest


def test_non_apply_decisions_are_rejected(tmp_path: Path) -> None:
    for decision in ("skip", "defer"):
        opportunities, opportunity_id, profile = seed_applied_opportunity(
            tmp_path / decision, decision=decision
        )
        service = package_service(tmp_path / decision, opportunities, profile)
        with pytest.raises(ApplicationPackageEligibilityError, match="apply"):
            service.prepare(opportunity_id, **approved_gate_options())


def test_undecided_opportunity_is_rejected(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path, decision=""
    )
    service = package_service(tmp_path, opportunities, profile)
    with pytest.raises(ApplicationPackageEligibilityError, match="apply"):
        service.prepare(opportunity_id, **approved_gate_options())


def test_manifest_references_and_evidence_traceability(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    before = opportunities.get(opportunity_id)
    service = package_service(tmp_path, opportunities, profile)

    manifest = service.prepare(opportunity_id, **approved_gate_options())

    assert manifest.evidence.opportunity_id == opportunity_id
    assert set(manifest.evidence.artifact_paths) == set(ARTIFACT_FILENAMES)
    assert manifest.evidence.artifact_paths == before.artifact_paths
    assert (
        manifest.evidence.acquisition.source_kind == before.identity.source_kind
    )
    assert manifest.evidence.acquisition.company == before.identity.company
    assert manifest.evidence.acquisition.title == before.identity.title
    assert (
        manifest.evidence.acquisition.content_fingerprint
        == before.identity.content_fingerprint
    )
    assert manifest.evidence.strategy_summary == before.strategy_summary
    assert manifest.cv.stem == opportunity_id
    assert manifest.cover_letter.stem == opportunity_id


def test_regeneration_replaces_previous_package(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    first = service.prepare(opportunity_id, **approved_gate_options())

    second_stamp = STAMP.replace(minute=30)
    options = approved_gate_options()
    options["prepared_at"] = second_stamp
    second = service.prepare(opportunity_id, **options)

    assert second.prepared_at == second_stamp
    assert second.opportunity_id == first.opportunity_id
    assert service.get(opportunity_id).prepared_at == second_stamp
    assert Path(second.cv.markdown_path) == Path(first.cv.markdown_path)
    assert Path(second.cv.markdown_path).is_file()


def test_existing_approval_gates_remain_enforced(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)

    with pytest.raises(TailoringPlanGateError, match="owner_approved_to_tailor"):
        service.prepare(
            opportunity_id,
            tailoring_options=TailoringOptions(owner_approved_to_tailor=False),
        )

    options = approved_gate_options()
    options["cover_letter_plan_options"] = options["cover_letter_plan_options"].model_copy(
        update={"owner_approved_to_plan": False}
    )
    with pytest.raises(CoverLetterPlanGateError, match="owner_approved_to_plan"):
        service.prepare(opportunity_id, **options)


def test_upstream_artifacts_remain_immutable(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    before = opportunities.get(opportunity_id)
    before_files = {
        name: (tmp_path / relative).read_bytes()
        for name, relative in before.artifact_paths.items()
    }
    service = package_service(tmp_path, opportunities, profile)

    service.prepare(opportunity_id, **approved_gate_options())

    after = opportunities.get(opportunity_id)
    assert after.artifact_paths == before.artifact_paths
    assert after.strategy_summary == before.strategy_summary
    assert after.decision == before.decision
    assert after.status == before.status
    for name, relative in after.artifact_paths.items():
        assert (tmp_path / relative).read_bytes() == before_files[name]


def test_get_missing_package_raises(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    with pytest.raises(ApplicationPackageNotFoundError):
        service.get(opportunity_id)


def test_load_artifacts_via_opportunity_service(tmp_path: Path) -> None:
    opportunities, opportunity_id, _profile = seed_applied_opportunity(tmp_path)
    artifacts = opportunities.load_artifacts(opportunity_id)
    opportunity = opportunities.get(opportunity_id)
    assert artifacts.strategy.application_tier == opportunity.strategy_summary.application_tier
    assert artifacts.job_analysis.posting.company == opportunity.identity.company
