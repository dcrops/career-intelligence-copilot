"""Functional journeys for FR-010 Application Package Preparation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from career_intelligence.application_package import (
    ApplicationPackageEligibilityError,
    ApplicationPackageService,
)
from career_intelligence.opportunities import OpportunityService
from tests.unit.application_package.helpers import (
    STAMP,
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)


def test_apply_to_package_journey_is_traceable_and_reloadable(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path,
        source_url="https://au.seek.com/job/10101010",
        title="Senior AI Engineer",
        company="Package Co",
        raw_text="Senior AI Engineer. Python required. Hybrid Melbourne. Package Co.",
    )
    service = package_service(tmp_path, opportunities, profile)

    first = service.prepare(opportunity_id, **approved_gate_options())
    reloaded_opportunities = OpportunityService.from_path(tmp_path)
    reloaded = ApplicationPackageService(
        reloaded_opportunities,
        profile=profile,
        packages_root=tmp_path / "application_packages",
        cv_output_dir=tmp_path / "cv_generated",
        cover_letter_output_dir=tmp_path / "cover_letter_generated",
    )
    second = reloaded.get(opportunity_id)

    assert second.model_dump() == first.model_dump()
    assert second.evidence.opportunity_id == opportunity_id
    assert "strategy.json" in second.evidence.artifact_paths
    assert Path(second.cv.html_path).is_file()
    assert Path(second.cover_letter.markdown_path).is_file()
    assert second.owner_review_required is True


def test_skip_cannot_produce_package_in_same_workspace(tmp_path: Path) -> None:
    opportunities, apply_id, profile = seed_applied_opportunity(
        tmp_path,
        decision="apply",
        source_url="https://au.seek.com/job/11110001",
        title="AI Engineer",
        company="Apply Co",
        raw_text="AI Engineer. Python. Apply Co distinct body one.",
    )
    _, skip_id, _ = seed_applied_opportunity(
        tmp_path,
        decision="skip",
        source_url="https://au.seek.com/job/11110002",
        title="Data Engineer",
        company="Skip Co",
        raw_text="Data Engineer. SQL. Skip Co distinct body two.",
    )
    service = package_service(tmp_path, opportunities, profile)

    packaged = service.prepare(apply_id, **approved_gate_options())
    assert packaged.opportunity_id == apply_id

    with pytest.raises(ApplicationPackageEligibilityError, match="apply"):
        service.prepare(skip_id, **approved_gate_options())


def test_regeneration_is_idempotent_for_paths_and_evidence(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    before_artifacts = {
        name: (tmp_path / relative).read_bytes()
        for name, relative in opportunities.get(opportunity_id).artifact_paths.items()
    }
    service = package_service(tmp_path, opportunities, profile)

    first = service.prepare(opportunity_id, **approved_gate_options())
    options = approved_gate_options()
    options["prepared_at"] = STAMP.replace(hour=16)
    second = service.prepare(opportunity_id, **options)

    assert second.cv.markdown_path == first.cv.markdown_path
    assert second.cover_letter.html_path == first.cover_letter.html_path
    assert second.evidence.artifact_paths == first.evidence.artifact_paths
    after = opportunities.get(opportunity_id)
    for name, relative in after.artifact_paths.items():
        assert (tmp_path / relative).read_bytes() == before_artifacts[name]


def test_durability_journey_reload_regenerate_and_failure_safety(
    tmp_path: Path,
) -> None:
    """End-to-end: create → reload → regenerate → failed regen keeps prior package."""
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path,
        source_url="https://au.seek.com/job/20202020",
        title="AI Engineer",
        company="Durable Co",
        raw_text="AI Engineer. Python. Durable Co distinct body for M1.",
    )
    service = package_service(tmp_path, opportunities, profile)
    created = service.prepare(opportunity_id, **approved_gate_options())

    reloaded_opportunities = OpportunityService.from_path(tmp_path)
    reloaded_service = ApplicationPackageService(
        reloaded_opportunities,
        profile=profile,
        packages_root=tmp_path / "application_packages",
        cv_output_dir=tmp_path / "cv_generated",
        cover_letter_output_dir=tmp_path / "cover_letter_generated",
    )
    assert reloaded_service.exists(opportunity_id) is True
    assert reloaded_service.get(opportunity_id) == created

    options = approved_gate_options()
    options["prepared_at"] = STAMP.replace(hour=16)
    regenerated = reloaded_service.prepare(opportunity_id, **options)
    assert regenerated.prepared_at != created.prepared_at
    assert regenerated.cv.markdown_path == created.cv.markdown_path

    options["prepared_at"] = STAMP.replace(hour=17)
    with patch(
        "career_intelligence.application_package.service.write_cover_letter_drafts",
        side_effect=RuntimeError("forced failure"),
    ), pytest.raises(RuntimeError, match="forced failure"):
        reloaded_service.prepare(opportunity_id, **options)

    assert reloaded_service.get(opportunity_id) == regenerated
    raw = json.loads(
        (tmp_path / "application_packages" / opportunity_id / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert raw["cv"]["markdown_path"] == f"{opportunity_id}.md"
    assert raw["prepared_at"].startswith("2026-07-30T16:00:00")
