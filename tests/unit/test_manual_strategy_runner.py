"""Focused tests for the FR-001→FR-005 manual validation runner."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from career_intelligence.job_analysis.fixtures import posting_applied_ai_engineer
from career_intelligence.job_analysis.models import JobPosting

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_application_strategy_manual.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_application_strategy_manual",
        _SCRIPT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parser_accepts_volume_and_output_json() -> None:
    runner = _load_runner()
    args = runner.build_parser().parse_args(
        [
            "--job-file",
            "job.txt",
            "--volume-applications-enabled",
            "--output-json",
            "out.json",
            "--offline-fixtures",
            "--title",
            "AI Engineer",
            "--persist",
            "--opportunities-dir",
            "tmp-opps",
        ]
    )
    assert args.job_file == Path("job.txt")
    assert args.volume_applications_enabled is True
    assert args.output_json == Path("out.json")
    assert args.offline_fixtures is True
    assert args.title == "AI Engineer"
    assert args.persist is True
    assert args.opportunities_dir == Path("tmp-opps")


def test_read_job_text_from_file(tmp_path: Path) -> None:
    runner = _load_runner()
    job_file = tmp_path / "job.txt"
    job_file.write_text("Senior AI Engineer\nPython required.\n", encoding="utf-8")
    assert "Python required" in runner.read_job_text(job_file)


def test_build_posting_preserves_provenance() -> None:
    runner = _load_runner()
    posting = runner.build_posting(
        "Body text",
        title="AI Engineer",
        company="Example Co",
        source_url="https://example.com/jobs/1",
    )
    assert isinstance(posting, JobPosting)
    assert posting.title == "AI Engineer"
    assert posting.company == "Example Co"
    assert str(posting.source_url) == "https://example.com/jobs/1"


def test_offline_pipeline_and_report_serialisation(tmp_path: Path) -> None:
    runner = _load_runner()
    posting = posting_applied_ai_engineer()
    result = runner.run_pipeline(
        posting=posting,
        profile_path=_REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml",
        volume_applications_enabled=False,
        offline_fixtures=True,
        model=None,
    )

    modes = {item.name: item.mode for item in result.components}
    assert modes["JobAnalysis"] == "offline_fixture"
    assert modes["OpportunityAssessment"] == "offline_fixture"
    assert modes["PortfolioMatch"] == "deterministic_production"
    assert modes["ApplicationStrategy"] == "deterministic_production"
    assert result.strategy.owner_review_required is True

    report = runner.format_report(result)
    assert "pursuit_posture:" in report
    assert "application_tier:" in report
    assert "Next actions" in report
    assert "offline_fixture" in report
    assert "WARNING: offline fixture mode" in report

    output = tmp_path / "result.json"
    runner.write_json(output, result)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "application_strategy" in payload
    assert "opportunity_assessment" in payload
    assert "portfolio_match" in payload
    assert payload["application_strategy"]["owner_review_required"] is True

    # Evidence refs already use namespace:id; display must not double-prefix.
    assert "preference:preference:" not in report
    if "preference:locations" in report:
        assert "preference:preference:locations" not in report


def test_default_run_does_not_persist(tmp_path: Path) -> None:
    runner = _load_runner()
    posting = posting_applied_ai_engineer()
    result = runner.run_pipeline(
        posting=posting,
        profile_path=_REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml",
        volume_applications_enabled=False,
        offline_fixtures=True,
        model=None,
    )
    assert result.strategy.owner_review_required is True
    assert not (tmp_path / "index.yaml").exists()


def test_persist_creates_opportunity_and_five_snapshots(tmp_path: Path) -> None:
    runner = _load_runner()
    posting = posting_applied_ai_engineer()
    result = runner.run_pipeline(
        posting=posting,
        profile_path=_REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml",
        volume_applications_enabled=False,
        offline_fixtures=True,
        model=None,
    )
    opportunity = runner.persist_opportunity(result, opportunities_dir=tmp_path)
    assert opportunity.opportunity_id.startswith("opp_")
    assert len(opportunity.opportunity_id) == 30
    artifact_dir = tmp_path / "artifacts" / opportunity.opportunity_id
    for name in (
        "posting.json",
        "job_analysis.json",
        "assessment.json",
        "portfolio_match.json",
        "strategy.json",
    ):
        assert (artifact_dir / name).is_file()
    assert (tmp_path / "index.yaml").is_file()


def test_main_persist_flag_writes_store(tmp_path: Path) -> None:
    runner = _load_runner()
    job_file = tmp_path / "job.txt"
    job_file.write_text(posting_applied_ai_engineer().raw_text, encoding="utf-8")
    exit_code = runner.main(
        [
            "--job-file",
            str(job_file),
            "--offline-fixtures",
            "--profile-path",
            str(_REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml"),
            "--persist",
            "--opportunities-dir",
            str(tmp_path / "opps"),
        ]
    )
    assert exit_code == 0
    assert (tmp_path / "opps" / "index.yaml").is_file()


def test_live_mode_fails_clearly_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    posting = JobPosting(raw_text="AI Engineer. Python required.")
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        runner.run_pipeline(
            posting=posting,
            profile_path=_REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml",
            volume_applications_enabled=False,
            offline_fixtures=False,
            model=None,
        )


def test_pipeline_failure_diagnostics_include_validation_field() -> None:
    runner = _load_runner()
    from career_intelligence.job_analysis.errors import ErrorDetail, JobAnalysisValidationError
    from career_intelligence.opportunity_assessment.errors import (
        OpportunityAssessmentValidationError,
    )

    ja_exc = JobAnalysisValidationError(
        [
            ErrorDetail(
                loc=("role_family",),
                msg="known role family requires at least one evidence item",
                type="value_error",
            )
        ]
    )
    message = runner._format_pipeline_failure(ja_exc)
    assert "JobAnalysis failed" in message
    assert "role_family" in message
    assert "known role family requires at least one evidence item" in message

    oa_exc = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit", "findings", 2),
                msg="partial_alignment finding requires at least one profile evidence ref",
                type="value_error",
            )
        ]
    )
    oa_message = runner._format_pipeline_failure(oa_exc)
    assert "OpportunityAssessment failed" in oa_message
    assert "technical_fit.findings.2" in oa_message
    assert "partial_alignment" in oa_message

    assumption_exc = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit", "findings", 0),
                msg="assumption text is only allowed when kind is 'assumption'",
                type="value_error",
            ),
            ErrorDetail(
                loc=("commercial_fit", "findings", 0),
                msg="assumption text is only allowed when kind is 'assumption'",
                type="value_error",
            ),
        ]
    )
    assumption_message = runner._format_pipeline_failure(assumption_exc)
    assert "OpportunityAssessment failed" in assumption_message
    assert "technical_fit.findings.0" in assumption_message
    assert "commercial_fit.findings.0" in assumption_message
    assert "assumption text is only allowed when kind is 'assumption'" in assumption_message
    assert "Traceback" not in assumption_message
