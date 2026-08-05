"""FR-014 M3 gates, persistence, and stale-hash tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import (
    JsonDirectoryTruthReportStore,
    TruthGateError,
    TruthValidationService,
    evaluate_package_truth,
    markdown_content_hash,
    require_package_external_use,
)
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)
from tests.unit.application_strategy.helpers import fixtures_dir
from tests.unit.submission.helpers_m1 import make_orchestrator

PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"
REDWOLF = (
    "Roles centred on Python, TypeScript, and Vue are where I do my best "
    "engineering work."
)


def _profile_with_fastapi() -> CareerProfile:
    from career_intelligence.profile import CareerProfileService

    base = CareerProfileService.from_path(PROFILE).load()
    data = base.model_dump(mode="python")
    data["skills"]["technical"].append(
        {"name": "FastAPI", "evidence": "project:example-project"}
    )
    data["projects"][0]["technologies"] = ["Python", "FastAPI"]
    return CareerProfile.model_validate(data)


def test_persist_and_load_current_report(tmp_path: Path) -> None:
    profile = _profile_with_fastapi()
    service = TruthValidationService()
    store = JsonDirectoryTruthReportStore(tmp_path / "truth")
    report = service.validate_markdown(
        markdown="I have experience with Python.",
        profile=profile,
        opportunity_id="opp_01ARZ3NDEKTSV4RRFFQ69G5FAA",
        artefact_kind="cover_letter_markdown",
    )
    path = store.save(report, as_current=True)
    assert path.is_file()
    loaded = store.load_current(
        "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA", "cover_letter_markdown"
    )
    assert loaded is not None
    assert loaded.report_id == report.report_id
    assert loaded.artefact.content_fingerprint == markdown_content_hash(
        "I have experience with Python."
    )


def test_stale_report_blocks_external_use(tmp_path: Path) -> None:
    opportunities, oid, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    packages.prepare(oid, **approved_gate_options())  # type: ignore[arg-type]
    manifest = packages.get(oid, verify=True)
    store = JsonDirectoryTruthReportStore(tmp_path / "truth")
    status = evaluate_package_truth(
        manifest=manifest,
        profile=profile,
        store=store,
        revalidate=True,
    )
    assert status.external_use_allowed

    cl_path = Path(manifest.cover_letter.markdown_path)
    cl_path.write_text(cl_path.read_text(encoding="utf-8") + "\nEdited.\n", encoding="utf-8")
    stale = evaluate_package_truth(
        manifest=manifest,
        profile=profile,
        store=store,
        revalidate=False,
    )
    assert not stale.external_use_allowed
    assert any("stale" in msg.lower() for msg in stale.messages)


def test_redwolf_markdown_blocks_then_corrected_passes(tmp_path: Path) -> None:
    profile = _profile_with_fastapi()
    service = TruthValidationService()
    md = tmp_path / "letter.md"
    md.write_text(REDWOLF, encoding="utf-8")
    failed = service.validate_markdown_path(
        md, profile=profile, artefact_kind="cover_letter_markdown"
    )
    assert failed.outcome == "fail"

    md.write_text(
        "I have experience with Python and FastAPI in production services.\n",
        encoding="utf-8",
    )
    passed = service.validate_markdown_path(
        md, profile=profile, artefact_kind="cover_letter_markdown"
    )
    assert passed.outcome == "pass"


def test_submission_gate_blocks_without_truth_reports(tmp_path: Path) -> None:
    opportunities, oid, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    packages.prepare(oid, **approved_gate_options())  # type: ignore[arg-type]
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    # Re-enable truth gate for this regression.
    orchestrator._enable_truth_gate = True  # noqa: SLF001
    orchestrator._truth_root = tmp_path / "truth"  # noqa: SLF001
    ready = orchestrator.check_readiness(oid)
    assert ready.ready is False
    assert any("Truth" in msg or "truth" in msg for msg in ready.messages)
    with pytest.raises(Exception, match="Truth validation blocks|Truth validation"):
        orchestrator.submit(
            oid,
            channel="fake",
            owner_approved_submit=True,
            destination="https://example.com/job",
        )
    assert fake.call_count == 0


def test_submission_allows_after_validate_package(tmp_path: Path) -> None:
    opportunities, oid, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    packages.prepare(oid, **approved_gate_options())  # type: ignore[arg-type]
    store = JsonDirectoryTruthReportStore(tmp_path / "truth")
    require_package_external_use(
        manifest=packages.get(oid, verify=True),
        profile=profile,
        store=store,
        revalidate=True,
    )
    from career_intelligence.submission import SubmissionOrchestrator
    from career_intelligence.submission.fake_adapter import FakeSubmissionAdapter
    from career_intelligence.submission.manual_adapter import ManualAssistedAdapter
    from career_intelligence.submission.memory_store import InMemorySubmissionAttemptStore

    fake = FakeSubmissionAdapter()
    orchestrator = SubmissionOrchestrator(
        opportunities,
        packages,
        store=InMemorySubmissionAttemptStore(),
        adapters={"fake": fake, "manual_assisted": ManualAssistedAdapter()},
        truth_reports_root=tmp_path / "truth",
        enable_truth_gate=True,
    )
    ready = orchestrator.check_readiness(oid)
    assert ready.ready is True
    attempt = orchestrator.submit(
        oid,
        channel="fake",
        owner_approved_submit=True,
        destination="https://example.com/job",
    )
    assert attempt.status == "submitted"
    assert fake.call_count == 1


def test_one_failing_document_blocks_package(tmp_path: Path) -> None:
    opportunities, oid, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    packages.prepare(oid, **approved_gate_options())  # type: ignore[arg-type]
    manifest = packages.get(oid, verify=True)
    store = JsonDirectoryTruthReportStore(tmp_path / "truth")
    evaluate_package_truth(
        manifest=manifest, profile=profile, store=store, revalidate=True
    )
    Path(manifest.cover_letter.markdown_path).write_text(REDWOLF, encoding="utf-8")
    with pytest.raises(TruthGateError):
        require_package_external_use(
            manifest=manifest,
            profile=profile,
            store=store,
            revalidate=True,
        )
