"""Functional journeys for FR-014 M3 owner CLI and external-use gates."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.truth_validation import (
    JsonDirectoryTruthReportStore,
    TruthGateError,
    TruthValidationService,
    evaluate_package_truth,
    require_package_external_use,
)
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)
from tests.unit.application_strategy.helpers import fixtures_dir

runner = CliRunner()
PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"
REDWOLF = (
    "Roles centred on Python, TypeScript, and Vue are where I do my best "
    "engineering work."
)


def test_m3_owner_journeys(tmp_path: Path) -> None:
    opportunities, oid, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    packages.prepare(oid, **approved_gate_options())  # type: ignore[arg-type]
    truth = tmp_path / "truth_reports"
    store = JsonDirectoryTruthReportStore(truth)
    service = TruthValidationService()

    # 1 Redwolf FAIL
    failed = service.validate_markdown(
        markdown=REDWOLF,
        profile=profile,
        artefact_kind="cover_letter_markdown",
    )
    assert failed.outcome == "fail"
    keys = {f.claim.object_key for f in failed.findings if f.severity == "blocking"}
    assert "typescript" in keys and "vue" in keys
    assert any(
        f.claim.object_key == "python" and f.evidence_status == "supported"
        for f in failed.findings
    )

    # 2 Corrected PASS + Class B employer context
    corrected = (
        "I have experience with Python.\n"
        "The role uses TypeScript and Vue.\n"
    )
    passed = service.validate_markdown(
        markdown=corrected,
        profile=profile,
        artefact_kind="cover_letter_markdown",
    )
    assert passed.outcome == "pass"

    # 3 Supported candidate statement
    supported = service.validate_markdown(
        markdown="I have experience with Python.\n",
        profile=profile,
        artefact_kind="cover_letter_markdown",
    )
    assert supported.outcome == "pass"

    # 4–6 Package both docs; stale blocks; one failing CL blocks
    manifest = packages.get(oid, verify=True)
    status = evaluate_package_truth(
        manifest=manifest, profile=profile, store=store, revalidate=True
    )
    assert status.external_use_allowed

    Path(manifest.cover_letter.markdown_path).write_text(
        Path(manifest.cover_letter.markdown_path).read_text(encoding="utf-8")
        + "\nedit\n",
        encoding="utf-8",
    )
    stale = evaluate_package_truth(
        manifest=manifest, profile=profile, store=store, revalidate=False
    )
    assert not stale.external_use_allowed

    Path(manifest.cover_letter.markdown_path).write_text(REDWOLF, encoding="utf-8")
    with pytest.raises(TruthGateError):
        require_package_external_use(
            manifest=manifest, profile=profile, store=store, revalidate=True
        )

    # 7 CLI validate-package + submission check after restore
    Path(manifest.cover_letter.markdown_path).write_text(
        "I have experience with Python.\n", encoding="utf-8"
    )
    common = [
        "--dir",
        str(tmp_path),
        "--packages-dir",
        str(tmp_path / "application_packages"),
        "--cv-dir",
        str(tmp_path / "cv_generated"),
        "--cover-letter-dir",
        str(tmp_path / "cover_letter_generated"),
        "--profile",
        str(PROFILE),
        "--truth-reports-dir",
        str(truth),
        "--attempts-dir",
        str(tmp_path / "attempts"),
    ]
    pkg_common = [
        c
        for i, c in enumerate(common)
        if not (c == "--attempts-dir" or (i and common[i - 1] == "--attempts-dir"))
    ]
    ok = runner.invoke(app, ["truth", "validate-package", oid, *pkg_common])
    assert ok.exit_code == 0, ok.output
    ready = runner.invoke(app, ["submission", "check", oid, *common])
    assert ready.exit_code == 0, ready.output
