"""Unit tests for TailoringPlan models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.cv_generation.models import TailoringPlan
from tests.unit.application_strategy.helpers import job_analysis
from tests.unit.cv_generation.helpers import make_plan


def test_tailoring_plan_requires_owner_review_recommended() -> None:
    plan = make_plan()
    assert plan.owner_review_recommended is True


def test_tailoring_plan_rejects_non_contiguous_ranks() -> None:
    plan = make_plan()
    payload = plan.model_dump(mode="json")
    if payload["jd_priorities"]:
        payload["jd_priorities"][0]["rank"] = 3
        with pytest.raises(ValidationError, match="contiguous"):
            TailoringPlan.model_validate(payload)


def test_tailoring_plan_forbids_extra_fields() -> None:
    plan = make_plan()
    payload = plan.model_dump(mode="json")
    payload["cv_body"] = "invented"
    with pytest.raises(ValidationError):
        TailoringPlan.model_validate(payload)


def test_plan_binds_job_analysis_identity() -> None:
    from tests.unit.cv_generation.helpers import strategy_from_payload

    analysis = job_analysis()
    plan = make_plan(strategy=strategy_from_payload(job_analysis=analysis))
    assert plan.job_analysis.posting.title == analysis.posting.title
