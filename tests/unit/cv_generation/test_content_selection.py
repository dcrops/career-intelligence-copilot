"""Unit tests for FR-006b content selection helpers."""

from __future__ import annotations

from career_intelligence.cv_generation.content_selection import (
    score_text,
    select_by_relevance,
    select_engineering_highlights,
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


def test_select_engineering_highlights_keeps_impact_lead_first() -> None:
    items = [
        "Designed and delivered a portfolio of AI applications across RAG.",
        "Built modular service architectures with FastAPI and Docker.",
        "Designed explainable, evidence-backed recommendation flows.",
        "Published architecture notes through a public portfolio.",
    ]
    selected = select_engineering_highlights(
        items,
        ["FastAPI", "Docker"],
        max_items=4,
    )
    assert selected[0].startswith("Designed and delivered a portfolio")
    assert "FastAPI" in selected[1]
    assert len(selected) == 4

