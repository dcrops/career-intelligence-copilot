"""Live outputs must not share a write path with immutable strategy fixtures."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from career_intelligence.job_analysis.fixtures import posting_applied_ai_engineer

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_live_strategy_write_does_not_touch_fixture_corpus(tmp_path: Path) -> None:
    strategy_runner = _load(
        "run_application_strategy_manual",
        _REPO_ROOT / "scripts" / "run_application_strategy_manual.py",
    )
    fixture_dir = tmp_path / "tests" / "fixtures" / "application_strategy"
    fixture_dir.mkdir(parents=True)
    sentinel = fixture_dir / "002_bluefin_ai_systems_developer.json"
    sentinel.write_text('{"immutable": true}', encoding="utf-8")
    before = sentinel.read_text(encoding="utf-8")

    job_file = tmp_path / "jobs" / "002_bluefin_ai_systems_developer.txt"
    job_file.parent.mkdir(parents=True)
    job_file.write_text(posting_applied_ai_engineer().raw_text, encoding="utf-8")

    exit_code = strategy_runner.main(
        [
            "--job-file",
            str(job_file),
            "--offline-fixtures",
            "--profile-path",
            str(_REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml"),
        ],
        repo_root=tmp_path,
    )
    assert exit_code == 0
    live = (
        tmp_path
        / "manual_validation"
        / "outputs"
        / "live"
        / "002_bluefin_ai_systems_developer.json"
    )
    assert live.is_file()
    assert sentinel.read_text(encoding="utf-8") == before
    payload = json.loads(live.read_text(encoding="utf-8"))
    assert "application_strategy" in payload
    assert payload.get("immutable") is not True


def test_cv_and_cover_letter_reuse_live_strategy_json(tmp_path: Path) -> None:
    strategy_runner = _load(
        "run_application_strategy_manual",
        _REPO_ROOT / "scripts" / "run_application_strategy_manual.py",
    )
    cv_runner = _load(
        "run_cv_generation_manual",
        _REPO_ROOT / "scripts" / "run_cv_generation_manual.py",
    )
    cl_runner = _load(
        "run_cover_letter_manual",
        _REPO_ROOT / "scripts" / "run_cover_letter_manual.py",
    )

    job_file = tmp_path / "jobs" / "zz_separation_fixture.txt"
    job_file.parent.mkdir(parents=True)
    job_file.write_text(posting_applied_ai_engineer().raw_text, encoding="utf-8")
    profile = _REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml"

    assert (
        strategy_runner.main(
            [
                "--job-file",
                str(job_file),
                "--offline-fixtures",
                "--profile-path",
                str(profile),
            ],
            repo_root=tmp_path,
        )
        == 0
    )
    live = (
        tmp_path
        / "manual_validation"
        / "outputs"
        / "live"
        / "zz_separation_fixture.json"
    )
    assert live.is_file()

    posting = strategy_runner.build_posting(
        job_file.read_text(encoding="utf-8"),
        title="AI Engineer",
        company="Example",
        source_url=None,
    )
    # Point CV finder at tmp_path live tree via repo_root.
    found = cv_runner.find_manual_validation_pipeline_json(
        job_file, repo_root=tmp_path
    )
    assert found == live.resolve()

    cv_result = cv_runner.run_cv_pipeline(
        posting=posting,
        job_file=job_file,
        strategy_json=found,
        profile_path=profile,
        override_material_benefit=True,
        output_dir=tmp_path / "cv_out",
        repo_root=tmp_path,
    )
    assert cv_result.upstream_mode == "reused_pipeline_json"
    assert cv_result.cv is not None

    # Cover letter resolve_strategy uses module-level live dir; pass strategy_json.
    strategy, source = cl_runner.resolve_strategy(
        job_file=None, strategy_json=live
    )
    assert strategy.owner_review_required is True
    assert str(live.resolve()) == source


def test_explicit_output_json_still_overrides_live_default(tmp_path: Path) -> None:
    strategy_runner = _load(
        "run_application_strategy_manual",
        _REPO_ROOT / "scripts" / "run_application_strategy_manual.py",
    )
    custom = tmp_path / "custom" / "out.json"
    job = tmp_path / "job.txt"
    assert strategy_runner.resolve_pipeline_json_path(
        job_file=job,
        output_json=custom,
        repo_root=tmp_path,
    ) == custom


def test_planner_corpus_tests_do_not_depend_on_live_tree() -> None:
    fixture = (
        _REPO_ROOT
        / "tests"
        / "fixtures"
        / "application_strategy"
        / "002_bluefin_ai_systems_developer.json"
    )
    assert fixture.is_file()
    live = (
        _REPO_ROOT
        / "manual_validation"
        / "outputs"
        / "live"
        / "002_bluefin_ai_systems_developer.json"
    )
    # Live may or may not exist; corpus must be the fixture path used by tests.
    from tests.unit.cv_generation import test_planner_corpus_regression as corpus

    assert corpus._OUTPUTS == _REPO_ROOT / "tests" / "fixtures" / "application_strategy"
    assert live != fixture
