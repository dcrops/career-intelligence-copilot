"""Owner manual workflow: job TXT → strategy JSON → CV → cover letter."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from career_intelligence.job_analysis.fixtures import posting_applied_ai_engineer

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str, relative: str):
    path = _REPO_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_owner_manual_workflow_strategy_json_feeds_cv_and_cover_letter(
    tmp_path: Path,
) -> None:
    """Regression for the intended FR-005 → FR-006 → FR-007 owner path.

    Architecture (A): strategy runner persists ``manual_validation/outputs/{stem}.json``;
    CV and cover-letter runners reuse that JSON. Cover letter does not regenerate
    live upstream.
    """
    strategy_runner = _load_script(
        "run_application_strategy_manual_workflow",
        "scripts/run_application_strategy_manual.py",
    )
    cv_runner = _load_script(
        "run_cv_generation_manual_workflow",
        "scripts/run_cv_generation_manual.py",
    )
    cover_runner = _load_script(
        "run_cover_letter_manual_workflow",
        "scripts/run_cover_letter_manual.py",
    )

    job_file = tmp_path / "manual_validation" / "jobs" / "zz_owner_workflow_fixture.txt"
    job_file.parent.mkdir(parents=True)
    job_file.write_text(posting_applied_ai_engineer().raw_text, encoding="utf-8")
    profile = _REPO_ROOT / "tests" / "fixtures" / "golden" / "career_profile.yaml"

    # 1) Application strategy → persisted pipeline JSON (default path, no --output-json)
    exit_code = strategy_runner.main(
        [
            "--job-file",
            str(job_file),
            "--offline-fixtures",
            "--profile-path",
            str(profile),
            "--title",
            "Applied AI Engineer",
            "--company",
            "Harbour Labs",
        ],
        repo_root=tmp_path,
    )
    assert exit_code == 0

    strategy_json = (
        tmp_path
        / "manual_validation"
        / "outputs"
        / "zz_owner_workflow_fixture.json"
    )
    assert strategy_json.is_file()
    payload = json.loads(strategy_json.read_text(encoding="utf-8"))
    assert "application_strategy" in payload
    assert payload["application_strategy"]["application_tier"] in {
        "platinum",
        "gold",
        "silver",
        "bronze",
    }

    # 2) CV generation reuses the persisted strategy JSON
    cv_out = tmp_path / "cv_out"
    cv_result = cv_runner.run_cv_pipeline(
        posting=None,
        job_file=job_file,
        strategy_json=strategy_json,
        profile_path=profile,
        output_dir=cv_out,
        plan_only=False,
    )
    assert cv_result.upstream_mode == "reused_pipeline_json"
    assert cv_result.upstream_source is not None
    assert strategy_json.name in cv_result.upstream_source
    assert cv_result.plan is not None
    assert cv_result.cv is not None
    assert cv_result.drafts is not None
    assert cv_result.drafts.markdown_path.is_file()

    # 3) Cover letter reuses the same persisted strategy JSON (no live upstream)
    cl_out = tmp_path / "cover_out"
    cover_result = cover_runner.run(
        job_file=job_file,
        strategy_json=strategy_json,
        profile_path=profile,
        output_dir=cl_out,
        owner_approved_to_plan=True,
        cover_letter_plan_approved=True,
        override_material_benefit=False,
        plan_only=False,
    )
    assert cover_result.gate_message is None
    assert cover_result.plan is not None
    assert cover_result.letter is not None
    assert cover_result.markdown_path is not None
    assert cover_result.markdown_path.is_file()
    assert cover_result.letter.owner_review_required is True
