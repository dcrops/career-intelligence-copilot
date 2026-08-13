"""AAS-0 preflight gating: truth remains hard; mtime touch is soft."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0 import run_assist  # noqa: E402


@dataclass(frozen=True)
class _FakeDoc:
    artefact_kind: str = "cv"
    outcome: str = "PASS"
    fresh: bool = True
    external_use_allowed: bool = True


@dataclass(frozen=True)
class _FakeTruth:
    external_use_allowed: bool
    documents: tuple[_FakeDoc, ...] = (_FakeDoc(),)
    messages: tuple[str, ...] = ()


def _fake_inputs(
    *,
    truth_allowed: bool = True,
    notes: tuple[str, ...] = (),
    blocking_warnings: tuple[str, ...] = (),
):
    return SimpleNamespace(
        opportunity_id="opp_test",
        company="Acme",
        title="Engineer",
        apply_url="https://www.seek.com.au/job/1",
        authoritative_cv_pdf=Path("auth-cv.pdf"),
        authoritative_cover_letter_pdf=Path("auth-cl.pdf"),
        cv_markdown=Path("cv.md"),
        cover_letter_markdown=Path("cl.md"),
        cv_pdf=Path("export-cv.pdf"),
        cover_letter_pdf=Path("export-cl.pdf"),
        known=SimpleNamespace(as_lookup=lambda: {"full_name": "Test"}),
        truth=_FakeTruth(external_use_allowed=truth_allowed),
        package_ok=True,
        warnings=blocking_warnings,
        notes=notes,
        blocking_warnings=blocking_warnings,
    )


def test_mtime_touch_only_preflight_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = _fake_inputs(
        notes=(
            "CV: Markdown mtime is newer than PDF, but deterministic HTML "
            "content is unchanged (touch/save false positive).",
        ),
    )
    monkeypatch.setattr(run_assist, "load_spike_inputs", lambda *_a, **_k: inputs)
    code = run_assist.main(["--preflight-only", "--opportunity-id", "opp_test"])
    assert code == 0


def test_content_drift_preflight_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = _fake_inputs(
        blocking_warnings=(
            "CV: Markdown mtime is newer than PDF and freshly rendered HTML "
            "differs from on-disk doc.html. Document content may have drifted; "
            "run render-only refresh + truth validation before live AAS.",
        ),
    )
    monkeypatch.setattr(run_assist, "load_spike_inputs", lambda *_a, **_k: inputs)
    code = run_assist.main(["--preflight-only", "--opportunity-id", "opp_test"])
    assert code == 2


def test_truth_not_allowed_blocks_even_with_html_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _fake_inputs(
        truth_allowed=False,
        notes=(
            "CV: Markdown mtime is newer than PDF, but deterministic HTML "
            "content is unchanged (touch/save false positive).",
        ),
        blocking_warnings=(
            "Package external-use gate is NOT allowed: stale report",
        ),
    )
    monkeypatch.setattr(run_assist, "load_spike_inputs", lambda *_a, **_k: inputs)
    code = run_assist.main(["--preflight-only", "--opportunity-id", "opp_test"])
    assert code == 2


def test_authorize_live_refuses_on_blocking_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _fake_inputs(
        blocking_warnings=("CV: Document content may have drifted",),
    )
    monkeypatch.setattr(run_assist, "load_spike_inputs", lambda *_a, **_k: inputs)
    monkeypatch.setattr(run_assist, "run_live", MagicMock(return_value=0))
    code = run_assist.main(
        ["--authorize-live", "--opportunity-id", "opp_test"],
    )
    assert code == 2
    run_assist.run_live.assert_not_called()
