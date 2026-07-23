"""Unit tests for certification baseline, extended-history isolation, and drafts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from career_intelligence.cv_generation import (
    active_certifications_baseline,
    build_draft_stem,
    is_extended_history_experience_id,
    temporary_extended_history_experience_ids,
    write_tailored_cv_drafts,
)
from career_intelligence.cv_generation.baseline import CERTIFICATIONS_BASELINE_ASSUMPTION
from career_intelligence.profile.models import Certification
from tests.unit.cv_generation.helpers import make_cv, make_plan, minimal_profile


def test_certifications_are_profile_baseline_not_plan_content() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "certifications": [
                Certification.model_validate(
                    {
                        "id": "aws-certified-developer-associate",
                        "name": "AWS Certified Developer - Associate",
                        "issuer": "Amazon Web Services",
                        "status": "active",
                        "date_obtained": "2022-01",
                        "expiry_date": None,
                        "url": None,
                    }
                ),
                Certification.model_validate(
                    {
                        "id": "expired-example",
                        "name": "Expired Example",
                        "issuer": "Example",
                        "status": "expired",
                        "date_obtained": "2018-01",
                        "expiry_date": "2020-01",
                        "url": None,
                    }
                ),
            ]
        }
    )
    baseline = active_certifications_baseline(profile)
    assert [item["certification_id"] for item in baseline] == [
        "aws-certified-developer-associate"
    ]

    plan = make_plan(profile=profile)
    assert not hasattr(plan, "certifications")
    assert "certifications" not in plan.model_fields

    cv = make_cv(profile=profile, plan=plan)
    assert cv.certifications_source == "profile_active_baseline"
    assert [c.certification_id for c in cv.certifications] == [
        "aws-certified-developer-associate"
    ]
    assert "profile baseline" in cv.rendered_markdown.casefold()
    assert CERTIFICATIONS_BASELINE_ASSUMPTION in cv.assumptions


def test_extended_history_rule_is_isolated_in_experience_scope() -> None:
    ids = temporary_extended_history_experience_ids()
    assert "bakers-delight-test-analyst-2009" in ids
    assert is_extended_history_experience_id("bakers-delight-test-analyst-2009")
    assert not is_extended_history_experience_id("nbn-data-engineer-2020")
    assert not is_extended_history_experience_id("example-role")

    # The temporary rule must remain a single frozenset definition site.
    import career_intelligence.cv_generation.experience_scope as scope
    import inspect

    source = inspect.getsource(scope)
    assert source.count("bakers-delight-test-analyst-2009") == 1
    assert "TEMPORARY OWNER-PROFILE RULE" in source


def test_build_draft_stem_is_filesystem_safe() -> None:
    stem = build_draft_stem(
        company="Example AI Co!",
        title="Senior AI Engineer / Lead",
        when=datetime(2026, 7, 23, 5, 0, tzinfo=timezone.utc),
    )
    assert stem.startswith("20260723T050000Z_")
    assert " " not in stem
    assert "/" not in stem
    assert "!" not in stem


def test_write_tailored_cv_drafts_writes_markdown_json_and_plan(
    tmp_path: Path,
) -> None:
    plan = make_plan()
    cv = make_cv(plan=plan)
    result = write_tailored_cv_drafts(
        cv,
        plan,
        output_dir=tmp_path,
        stem="test_stem",
    )
    assert result.markdown_path == tmp_path / "test_stem.md"
    assert result.json_path == tmp_path / "test_stem.json"
    assert result.plan_json_path == tmp_path / "test_stem.tailoring_plan.json"

    markdown = result.markdown_path.read_text(encoding="utf-8")
    assert markdown == cv.rendered_markdown
    assert "# " in markdown

    cv_payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert cv_payload["owner_review_required"] is True
    assert cv_payload["certifications_source"] == "profile_active_baseline"
    assert "rendered_markdown" in cv_payload

    plan_payload = json.loads(result.plan_json_path.read_text(encoding="utf-8"))
    assert "jd_priorities" in plan_payload
    assert plan_payload["owner_review_recommended"] is True
