"""Focused tests for the FR-006 manual validation runner."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from career_intelligence.job_analysis.fixtures import posting_applied_ai_engineer

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_cv_generation_manual.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_cv_generation_manual",
        _SCRIPT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parser_accepts_strategy_json_and_live_upstream() -> None:
    runner = _load_runner()
    args = runner.build_parser().parse_args(
        [
            "--job-file",
            "job.txt",
            "--strategy-json",
            "out.json",
            "--live-upstream",
            "--output-dir",
            "out",
            "--plan-only",
        ]
    )
    assert args.job_file == Path("job.txt")
    assert args.strategy_json == Path("out.json")
    assert args.live_upstream is True
    assert args.plan_only is True


def test_find_manual_validation_pipeline_json_uses_live_dir(tmp_path: Path) -> None:
    runner = _load_runner()
    job = tmp_path / "jobs" / "013_pay_com_au_ai_automation_engineer.txt"
    job.parent.mkdir(parents=True)
    job.write_text("placeholder", encoding="utf-8")
    live_dir = tmp_path / "manual_validation" / "outputs" / "live"
    live_dir.mkdir(parents=True)
    live = live_dir / "013_pay_com_au_ai_automation_engineer.json"
    live.write_text("{}", encoding="utf-8")
    # Fixture corpus must not be consulted by the live finder.
    fixture_dir = tmp_path / "tests" / "fixtures" / "application_strategy"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "013_pay_com_au_ai_automation_engineer.json").write_text(
        '{"should_not_be_used": true}', encoding="utf-8"
    )
    found = runner.find_manual_validation_pipeline_json(job, repo_root=tmp_path)
    assert found == live.resolve()


def test_find_manual_validation_pipeline_json_ignores_fixture_corpus(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    job = tmp_path / "jobs" / "013_pay_com_au_ai_automation_engineer.txt"
    job.parent.mkdir(parents=True)
    job.write_text("placeholder", encoding="utf-8")
    fixture_dir = tmp_path / "tests" / "fixtures" / "application_strategy"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "013_pay_com_au_ai_automation_engineer.json").write_text(
        "{}", encoding="utf-8"
    )
    assert (
        runner.find_manual_validation_pipeline_json(job, repo_root=tmp_path) is None
    )


def test_reuse_fr005_corpus_job_without_fixture_markers(tmp_path: Path) -> None:
    runner = _load_runner()
    job = (
        _REPO_ROOT
        / "manual_validation"
        / "jobs"
        / "013_pay_com_au_ai_automation_engineer.txt"
    )
    raw = job.read_text(encoding="utf-8")
    assert not runner.posting_has_fixture_marker(raw)

    posting = _load_runner()._load_strategy_runner().build_posting(
        raw,
        title="AI Automation Engineer",
        company="Pay.com.au",
        source_url=None,
    )
    # Seed live output under tmp_path so auto-reuse finds it (not the fixture tree).
    live_dir = tmp_path / "manual_validation" / "outputs" / "live"
    live_dir.mkdir(parents=True)
    fixture = (
        _REPO_ROOT
        / "tests"
        / "fixtures"
        / "application_strategy"
        / "013_pay_com_au_ai_automation_engineer.json"
    )
    live = live_dir / "013_pay_com_au_ai_automation_engineer.json"
    live.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
    tmp_job = tmp_path / "jobs" / "013_pay_com_au_ai_automation_engineer.txt"
    tmp_job.parent.mkdir(parents=True)
    tmp_job.write_text(raw, encoding="utf-8")

    # Job 013 is silver without consider_cv_tailoring — override for full FR-006 path.
    result = runner.run_cv_pipeline(
        posting=posting,
        job_file=tmp_job,
        strategy_json=None,
        profile_path=_REPO_ROOT / "data" / "career_profile.yaml",
        offline_fixtures=True,  # should be ignored in favour of reused JSON
        live_upstream=False,
        override_material_benefit=True,
        output_dir=tmp_path / "cv_out",
        plan_only=False,
        repo_root=tmp_path,
    )
    assert result.upstream_mode == "reused_pipeline_json"
    assert result.upstream_source is not None
    assert "013_pay_com_au_ai_automation_engineer.json" in result.upstream_source
    assert "live" in Path(result.upstream_source).parts
    assert result.plan is not None
    assert result.cv is not None
    assert result.drafts is not None
    assert result.drafts.markdown_path.is_file()
    assert any("offline-fixtures was ignored" in note for note in result.notes)

    report = runner.format_report(result)
    assert "reused_pipeline_json" in report
    assert "upstream_source:" in report


def test_strategy_json_explicit_path_platinum_job(tmp_path: Path) -> None:
    """Explicit ``--strategy-json`` reuse for the platinum Bluefin fixture.

    Uses ``tests/fixtures/application_strategy/002_bluefin_ai_systems_developer.json``
    (immutable regression corpus). Live owner runs write under
    ``manual_validation/outputs/live/`` and must not mutate this fixture.
    """
    runner = _load_runner()
    strategy_json = (
        _REPO_ROOT
        / "tests"
        / "fixtures"
        / "application_strategy"
        / "002_bluefin_ai_systems_developer.json"
    )
    result = runner.run_cv_pipeline(
        posting=None,
        job_file=None,
        strategy_json=strategy_json,
        profile_path=_REPO_ROOT / "data" / "career_profile.yaml",
        output_dir=tmp_path,
    )
    assert result.upstream_mode == "reused_pipeline_json"
    assert result.cv is not None
    assert result.strategy.application_tier == "platinum"
    assert result.drafts is not None
    assert result.drafts.markdown_path.is_file()


def test_corpus_silver_job_surfaces_material_benefit_gate(tmp_path: Path) -> None:
    runner = _load_runner()
    job = (
        _REPO_ROOT
        / "manual_validation"
        / "jobs"
        / "013_pay_com_au_ai_automation_engineer.txt"
    )
    strategy_json = (
        _REPO_ROOT
        / "tests"
        / "fixtures"
        / "application_strategy"
        / "013_pay_com_au_ai_automation_engineer.json"
    )
    result = runner.run_cv_pipeline(
        posting=None,
        job_file=job,
        strategy_json=strategy_json,
        profile_path=_REPO_ROOT / "data" / "career_profile.yaml",
        override_material_benefit=False,
        output_dir=tmp_path,
    )
    assert result.upstream_mode == "reused_pipeline_json"
    assert result.plan is None
    assert result.gate_message is not None
    assert "Material-benefit" in result.gate_message



def test_offline_fixtures_without_marker_and_without_json_fails_clearly(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    job = tmp_path / "real_looking_job.txt"
    job.write_text("AI Engineer. Python required. No fixture marker.", encoding="utf-8")
    posting = runner._load_strategy_runner().build_posting(
        job.read_text(encoding="utf-8"),
        title="AI Engineer",
        company="Example",
        source_url=None,
    )
    with pytest.raises(SystemExit, match=r"CIC-FIXTURE"):
        runner.run_cv_pipeline(
            posting=posting,
            job_file=job,
            offline_fixtures=True,
            live_upstream=False,
            output_dir=tmp_path / "out",
            repo_root=tmp_path,  # no manual_validation/outputs here
        )


def test_offline_cv_pipeline_writes_drafts_and_report(tmp_path: Path) -> None:
    runner = _load_runner()
    posting = posting_applied_ai_engineer()
    result = runner.run_cv_pipeline(
        posting=posting,
        profile_path=_REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml",
        volume_applications_enabled=False,
        offline_fixtures=True,
        model=None,
        owner_approved_to_tailor=True,
        tailoring_plan_approved=True,
        include_extended_history=False,
        override_material_benefit=False,
        output_dir=tmp_path,
        plan_only=False,
    )

    assert result.upstream_mode == "offline_fixture"
    assert result.plan is not None
    assert result.cv is not None
    assert result.drafts is not None
    assert result.drafts.markdown_path.is_file()
    assert result.drafts.json_path.is_file()
    assert result.drafts.plan_json_path.is_file()

    markdown = result.drafts.markdown_path.read_text(encoding="utf-8")
    assert result.cv.full_name in markdown
    payload = json.loads(result.drafts.json_path.read_text(encoding="utf-8"))
    assert payload["owner_review_required"] is True
    assert payload["certifications_source"] == "profile_active_baseline"

    report = runner.format_report(result)
    assert "application_tier:" in report
    assert "tailoring_allowed:" in report
    assert "Top JD priorities:" in report
    assert "Projects promoted:" in report
    assert "Skills promoted:" in report
    assert "Skills not emphasised" in report
    assert "experience_guidance:" in report
    assert "Draft outputs" in report
    assert str(result.drafts.markdown_path) in report
    assert "Q1." in report and "Q2." in report


def test_plan_only_writes_plan_json_without_cv(tmp_path: Path) -> None:
    runner = _load_runner()
    posting = posting_applied_ai_engineer()
    result = runner.run_cv_pipeline(
        posting=posting,
        profile_path=_REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml",
        volume_applications_enabled=False,
        offline_fixtures=True,
        model=None,
        owner_approved_to_tailor=True,
        tailoring_plan_approved=False,
        include_extended_history=False,
        override_material_benefit=False,
        output_dir=tmp_path,
        plan_only=True,
    )
    assert result.plan is not None
    assert result.cv is None
    assert result.drafts is not None
    assert result.drafts.plan_json_path.is_file()
    assert not result.drafts.markdown_path.is_file()
    plan_payload = json.loads(result.drafts.plan_json_path.read_text(encoding="utf-8"))
    assert "skills_to_promote" in plan_payload
