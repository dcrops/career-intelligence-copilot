"""Unit tests for FR-010 M1 Application Package durability and regeneration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from career_intelligence.application_package import (
    ApplicationPackageIntegrityError,
    ApplicationPackageNotFoundError,
)
from tests.unit.application_package.helpers import (
    STAMP,
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)


def test_exists_and_reload_current_package(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)

    assert service.exists(opportunity_id) is False
    with pytest.raises(ApplicationPackageNotFoundError):
        service.get(opportunity_id)

    prepared = service.prepare(opportunity_id, **approved_gate_options())
    assert service.exists(opportunity_id) is True
    reloaded = service.get(opportunity_id)
    assert reloaded == prepared
    assert Path(reloaded.cv.markdown_path).is_file()
    assert Path(reloaded.cover_letter.html_path).is_file()


def test_persisted_manifest_uses_relative_draft_paths(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    service.prepare(opportunity_id, **approved_gate_options())

    raw = json.loads(
        (tmp_path / "application_packages" / opportunity_id / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert raw["cv"]["output_dir"] == "."
    assert raw["cv"]["markdown_path"] == f"{opportunity_id}.md"
    assert raw["cover_letter"]["html_path"] == f"{opportunity_id}.html"
    assert not Path(raw["cv"]["markdown_path"]).is_absolute()

    resolved = service.get(opportunity_id)
    assert Path(resolved.cv.markdown_path).is_absolute()
    assert Path(resolved.cv.markdown_path).name == f"{opportunity_id}.md"


def test_prepare_with_same_stamp_is_byte_idempotent(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    options = approved_gate_options()

    first = service.prepare(opportunity_id, **options)
    first_cv = Path(first.cv.markdown_path).read_bytes()
    first_cl = Path(first.cover_letter.markdown_path).read_bytes()
    first_manifest = (
        tmp_path / "application_packages" / opportunity_id / "manifest.json"
    ).read_text(encoding="utf-8")

    second = service.prepare(opportunity_id, **options)
    assert second == first
    assert Path(second.cv.markdown_path).read_bytes() == first_cv
    assert Path(second.cover_letter.markdown_path).read_bytes() == first_cl
    assert (
        tmp_path / "application_packages" / opportunity_id / "manifest.json"
    ).read_text(encoding="utf-8") == first_manifest


def test_repeated_regeneration_overwrites_and_updates_prepared_at(
    tmp_path: Path,
) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    first = service.prepare(opportunity_id, **approved_gate_options())

    stamps = [STAMP.replace(hour=hour) for hour in (16, 17, 18)]
    previous = first
    for stamp in stamps:
        options = approved_gate_options()
        options["prepared_at"] = stamp
        current = service.prepare(opportunity_id, **options)
        assert current.prepared_at == stamp
        assert current.cv.markdown_path == previous.cv.markdown_path
        assert current.cover_letter.plan_json_path == previous.cover_letter.plan_json_path
        assert current.evidence.artifact_paths == previous.evidence.artifact_paths
        assert service.get(opportunity_id).prepared_at == stamp
        previous = current


def test_failed_regeneration_keeps_previous_package(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    first = service.prepare(opportunity_id, **approved_gate_options())
    first_manifest = (
        tmp_path / "application_packages" / opportunity_id / "manifest.json"
    ).read_text(encoding="utf-8")

    options = approved_gate_options()
    options["prepared_at"] = STAMP.replace(hour=20)
    with patch(
        "career_intelligence.application_package.service.write_cover_letter_drafts",
        side_effect=RuntimeError("simulated draft failure"),
    ), pytest.raises(RuntimeError, match="simulated draft failure"):
        service.prepare(opportunity_id, **options)

    assert service.exists(opportunity_id) is True
    reloaded = service.get(opportunity_id)
    assert reloaded.prepared_at == first.prepared_at
    assert reloaded == first
    assert (
        tmp_path / "application_packages" / opportunity_id / "manifest.json"
    ).read_text(encoding="utf-8") == first_manifest


def test_missing_draft_fails_integrity_check(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    prepared = service.prepare(opportunity_id, **approved_gate_options())

    Path(prepared.cv.markdown_path).unlink()
    with pytest.raises(ApplicationPackageIntegrityError, match="cv.markdown_path"):
        service.get(opportunity_id)

    unchecked = service.get(opportunity_id, verify=False)
    assert unchecked.opportunity_id == opportunity_id
    assert not Path(unchecked.cv.markdown_path).is_file()


def test_m0_absolute_paths_still_resolve(tmp_path: Path) -> None:
    """Legacy absolute draft paths in a stored manifest remain loadable."""
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    prepared = service.prepare(opportunity_id, **approved_gate_options())

    legacy = {
        "opportunity_id": opportunity_id,
        "prepared_at": STAMP.isoformat().replace("+00:00", "Z"),
        "evidence": prepared.evidence.model_dump(mode="json"),
        "cv": {
            "stem": opportunity_id,
            "output_dir": str(tmp_path / "cv_generated"),
            "markdown_path": prepared.cv.markdown_path,
            "json_path": prepared.cv.json_path,
            "plan_json_path": prepared.cv.plan_json_path,
            "html_path": prepared.cv.html_path,
        },
        "cover_letter": {
            "stem": opportunity_id,
            "output_dir": str(tmp_path / "cover_letter_generated"),
            "markdown_path": prepared.cover_letter.markdown_path,
            "json_path": prepared.cover_letter.json_path,
            "plan_json_path": prepared.cover_letter.plan_json_path,
            "html_path": prepared.cover_letter.html_path,
        },
        "owner_review_required": True,
    }
    manifest_path = tmp_path / "application_packages" / opportunity_id / "manifest.json"
    manifest_path.write_text(
        json.dumps(legacy, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    loaded = service.get(opportunity_id)
    assert Path(loaded.cv.markdown_path).is_file()
    assert Path(loaded.cover_letter.html_path).is_file()


def test_upstream_evidence_immutable_across_repeated_regeneration(
    tmp_path: Path,
) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    before = {
        name: (tmp_path / relative).read_bytes()
        for name, relative in opportunities.get(opportunity_id).artifact_paths.items()
    }
    service = package_service(tmp_path, opportunities, profile)

    for hour in (15, 16, 17):
        options = approved_gate_options()
        options["prepared_at"] = STAMP.replace(hour=hour)
        service.prepare(opportunity_id, **options)

    after = opportunities.get(opportunity_id)
    for name, relative in after.artifact_paths.items():
        assert (tmp_path / relative).read_bytes() == before[name]
    assert after.status == "assessed"
