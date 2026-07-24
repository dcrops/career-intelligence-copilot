"""Unit tests for FR-006b content selection helpers."""

from __future__ import annotations

from career_intelligence.cv_generation.content_selection import (
    score_text,
    select_by_relevance,
)


def test_select_by_relevance_prefers_overlapping_items() -> None:
    items = [
        "Built Selenium suites for regression testing",
        "Designed RAG retrieval with OpenAI APIs",
        "Maintained Jenkins pipelines",
    ]
    selected = select_by_relevance(
        items,
        ["OpenAI APIs", "RAG"],
        max_items=2,
        min_items=1,
    )
    assert selected[0].startswith("Designed RAG")
    assert len(selected) <= 2


def test_select_by_relevance_keeps_floor_when_no_overlap() -> None:
    items = ["Alpha", "Beta", "Gamma"]
    selected = select_by_relevance(items, ["Unrelated"], max_items=2, min_items=2)
    assert selected == ["Alpha", "Beta"]


def test_score_text_rewards_term_overlap() -> None:
    assert score_text("Python FastAPI OpenAI APIs", ["Python", "OpenAI APIs"]) > score_text(
        "Jenkins Maven", ["Python", "OpenAI APIs"]
    )
