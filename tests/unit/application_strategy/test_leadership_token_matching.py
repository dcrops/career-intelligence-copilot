"""FR-005 leadership-token matching regressions."""

from __future__ import annotations

from career_intelligence.application_strategy.deterministic_planner import (
    _job_expects_senior_commercial_leadership,
    _token_matches,
)
from tests.unit.application_strategy.helpers import job_analysis


def test_cto_does_not_match_inside_victoria() -> None:
    assert not _token_matches("cto", "melbourne victoria hybrid")
    assert not _token_matches("cto", "south melbourne, victoria")


def test_ceo_and_cto_match_as_whole_tokens() -> None:
    assert _token_matches("cto", "reporting to the cto on ai delivery")
    assert _token_matches("ceo", "partnering with the ceo and product leaders")
    assert _token_matches("cto", "work with the ceo/cto on special projects")
    assert _token_matches("leadership", "technical leadership of production ai")


def test_job_leadership_helper_ignores_victoria_false_positive() -> None:
    analysis = job_analysis(
        posting={
            "raw_text": (
                "Senior AI Engineer in Melbourne VIC (Hybrid), Victoria. "
                "Python required. Build production agents for internal tools."
            ),
            "title": "Senior AI Engineer",
        },
        location={
            "clarity": "stated",
            "summary": "Melbourne VIC (Hybrid), Victoria",
            "evidence": [{"excerpt": "Melbourne VIC (Hybrid)", "section": "location"}],
        },
    )
    assert _job_expects_senior_commercial_leadership(analysis) is False


def test_job_leadership_helper_detects_real_cto_signal() -> None:
    analysis = job_analysis(
        posting={
            "raw_text": (
                "Senior AI Engineer. Working one-on-one with the CEO/CTO on "
                "high-impact AI initiatives. Python required. Melbourne."
            ),
            "title": "Senior AI Engineer",
        },
        responsibilities=[
            {
                "description": "Working one-on-one with the CEO/CTO on high-impact projects.",
                "evidence": [
                    {
                        "excerpt": "Working one-on-one with the CEO/CTO",
                        "section": "responsibilities",
                    }
                ],
            }
        ],
    )
    assert _job_expects_senior_commercial_leadership(analysis) is True
