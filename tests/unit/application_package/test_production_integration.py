"""Production package path: Master-CV adapt + bounded cover-letter composition."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from career_intelligence.application_package import ApplicationPackageGenerationError
from career_intelligence.cover_letter.bounded_composer import (
    CoverLetterExtraction,
    FixtureCoverLetterComposer,
)
from career_intelligence.cover_letter.errors import CoverLetterError
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import (
    JsonDirectoryTruthReportStore,
    evaluate_package_truth,
)
from tests.unit.application_package.helpers import (
    STAMP,
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)
class _CountingComposer:
    def __init__(self) -> None:
        self.calls = 0
        self._inner = FixtureCoverLetterComposer()

    def compose(self, pack: object) -> CoverLetterExtraction:
        self.calls += 1
        return self._inner.compose(pack)


class _ExplodingComposer:
    def __init__(self) -> None:
        self.calls = 0

    def compose(self, pack: object) -> CoverLetterExtraction:
        self.calls += 1
        raise CoverLetterError("openai unavailable")


class _InventingComposer:
    def compose(self, pack: object) -> CoverLetterExtraction:
        return CoverLetterExtraction(
            paragraphs=[
                "I am excited to apply and will leverage TensorFlow synergies.",
                "I have commercial AI engineering employment at a vendor.",
                "I built the Redwolf Platform with 40% improvement.",
            ]
        )


def _independent_profile(base: CareerProfile) -> CareerProfile:
    payload = base.model_dump(mode="json")
    payload["experience"] = [
        {
            "id": "independent-ai",
            "kind": "independent_engineering",
            "organisation": "Chase Risk & Compliance",
            "title": "AI Engineer - Independent Research & Development",
            "start_date": "2025-12-01",
            "end_date": None,
            "location": "Melbourne",
            "highlights": [
                "Built independent AI portfolio systems with reviewable outputs."
            ],
            "technologies": ["Python"],
        },
        {
            "id": "example-role",
            "kind": "employment",
            "organisation": "Example Company",
            "title": "Data Engineer",
            "start_date": "2022-01-01",
            "end_date": "2023-01-01",
            "location": "Melbourne",
            "highlights": ["Built validated data pipelines."],
            "technologies": ["Python"],
        },
        {
            "id": "example-test-role",
            "kind": "employment",
            "organisation": "Test Org",
            "title": "Test Analyst",
            "start_date": "2018-01-01",
            "end_date": "2020-01-01",
            "location": "Melbourne",
            "highlights": ["Automated regression checks."],
            "technologies": ["Python"],
        },
    ]
    return CareerProfile.model_validate(payload)


def test_prepare_uses_master_adapt_without_llm_cv_rewrite(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    manifest = service.prepare(opportunity_id, **approved_gate_options())
    cv = json.loads(Path(manifest.cv.json_path).read_text(encoding="utf-8"))
    markdown = Path(manifest.cv.markdown_path).read_text(encoding="utf-8")
    assert cv["summary_source"] == "master_baseline"
    assert "Master CV" in " ".join(cv.get("assumptions") or [])
    assert "theme_aware" not in (cv.get("summary_source") or "")
    assert "A production-minded example kept verbatim." in markdown
    assert "Applies AI to improve engineering quality." not in markdown


def test_prepare_uses_one_bounded_llm_call_and_evidence_pack(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    profile = _independent_profile(profile)
    counter = _CountingComposer()
    service = package_service(tmp_path, opportunities, profile)
    service._cover_letter_composer = counter
    manifest = service.prepare(opportunity_id, **approved_gate_options())
    letter = json.loads(Path(manifest.cover_letter.json_path).read_text(encoding="utf-8"))
    markdown = Path(manifest.cover_letter.markdown_path).read_text(encoding="utf-8")
    pack_path = Path(manifest.cover_letter.markdown_path).with_name(
        f"{opportunity_id}.evidence_pack.json"
    )
    assert counter.calls == 1
    assert letter["composition_source"] == "bounded_llm_composition"
    assert pack_path.is_file()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    relationships = {item["relationship"] for item in pack["experience"]}
    assert "independent_rd" in relationships
    assert "commercial_employment" in relationships
    assert "independent research and development" in markdown.casefold()
    assert "commercial ai engineering employment" not in markdown.casefold()
    assert "tensorflow" not in markdown.casefold()
    assert "redwolf" not in markdown.casefold()


def test_technical_generation_failure_fails_closed_without_manifest(
    tmp_path: Path,
) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    exploding = _ExplodingComposer()
    service = package_service(tmp_path, opportunities, profile)
    service._cover_letter_composer = exploding
    with pytest.raises(ApplicationPackageGenerationError, match="failed closed"):
        service.prepare(opportunity_id, **approved_gate_options())
    assert exploding.calls == 1
    assert service.exists(opportunity_id) is False
    assert not (tmp_path / "cv_generated" / f"{opportunity_id}.md").exists()
    assert not (tmp_path / "cover_letter_generated" / f"{opportunity_id}.md").exists()


def test_inventing_composer_fails_closed_without_retry(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    service._cover_letter_composer = _InventingComposer()
    with pytest.raises(ApplicationPackageGenerationError, match="failed closed"):
        service.prepare(opportunity_id, **approved_gate_options())
    assert service.exists(opportunity_id) is False


def test_truth_failure_blocks_external_use_without_llm_retry(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    counter = _CountingComposer()
    service = package_service(tmp_path, opportunities, profile)
    service._cover_letter_composer = counter
    manifest = service.prepare(opportunity_id, **approved_gate_options())
    store = JsonDirectoryTruthReportStore(tmp_path / "truth_reports")
    passed = evaluate_package_truth(
        manifest=manifest,
        profile=profile,
        store=store,
        revalidate=True,
    )
    assert passed.external_use_allowed is True
    cl_path = Path(manifest.cover_letter.markdown_path)
    cl_path.write_text(
        cl_path.read_text(encoding="utf-8") + "\n\nI used TensorFlow in production.\n",
        encoding="utf-8",
        newline="\n",
    )
    blocked = evaluate_package_truth(
        manifest=service.get(opportunity_id),
        profile=profile,
        store=store,
        revalidate=True,
    )
    assert blocked.external_use_allowed is False
    assert counter.calls == 1


def test_owner_edited_cover_letter_survives_ordinary_prepare(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    first = service.prepare(opportunity_id, **approved_gate_options())
    path = Path(first.cover_letter.markdown_path)
    edited = path.read_text(encoding="utf-8") + "\nOwner cover-letter edit survives.\n"
    path.write_text(edited, encoding="utf-8", newline="\n")
    options = approved_gate_options()
    options["prepared_at"] = STAMP.replace(minute=30)
    second = service.prepare(opportunity_id, **options)
    assert "Owner cover-letter edit survives." in Path(
        second.cover_letter.markdown_path
    ).read_text(encoding="utf-8")
    assert (
        second.cover_letter_generated_markdown_sha256
        == first.cover_letter_generated_markdown_sha256
    )


def test_regenerate_overwrites_owner_edited_cover_letter(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    first = service.prepare(opportunity_id, **approved_gate_options())
    path = Path(first.cover_letter.markdown_path)
    path.write_text(
        path.read_text(encoding="utf-8") + "\nOwner cover-letter edit should go.\n",
        encoding="utf-8",
        newline="\n",
    )
    options = approved_gate_options()
    options["prepared_at"] = STAMP.replace(minute=45)
    options["regenerate"] = True
    second = service.prepare(opportunity_id, **options)
    assert "Owner cover-letter edit should go." not in Path(
        second.cover_letter.markdown_path
    ).read_text(encoding="utf-8")
    assert (
        second.cover_letter_generated_markdown_sha256
        == first.cover_letter_generated_markdown_sha256
    )


def test_historical_package_get_remains_compatible(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    first = service.prepare(opportunity_id, **approved_gate_options())
    reloaded = package_service(tmp_path, opportunities, profile)
    loaded = reloaded.get(opportunity_id)
    assert loaded.opportunity_id == first.opportunity_id
    assert loaded.owner_review_required is True
    assert Path(loaded.cv.markdown_path).is_file()
    assert Path(loaded.cover_letter.markdown_path).is_file()


def test_contact_overlay_still_required(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    options = approved_gate_options()
    options["cv_options"] = options["cv_options"].model_copy(update={"contact": None})
    options["cover_letter_options"] = options["cover_letter_options"].model_copy(
        update={"contact": None}
    )
    from career_intelligence.application_package import ApplicationPackageContactError

    with pytest.raises(ApplicationPackageContactError):
        service.prepare(opportunity_id, **options)
