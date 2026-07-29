"""Deterministic theme-aware Professional Summary composition (FR-006b/c).

FR-006c Summary Intelligence powers this entry point: evidence-backed narrative
composition from plan themes and Career Profile facts. Does not invent
employers, technologies, metrics, or achievements.

Kept as the stable public API used by ``CvGenerationService``.
"""

from __future__ import annotations

from collections.abc import Sequence

from career_intelligence.cv_generation.summary_intelligence import (
    compose_summary_intelligence,
)


def compose_theme_aware_summary(
    *,
    source_summary: str,
    target_role: str,
    themes: Sequence[str],
    promoted_skills: Sequence[str],
    methodology_philosophy: str | None = None,
) -> str:
    """Build a role-aware summary from profile evidence and plan emphasis.

    Returns ``source_summary`` unchanged when no themes or promoted skills exist.
    """
    return compose_summary_intelligence(
        source_summary=source_summary,
        target_role=target_role,
        themes=themes,
        promoted_skills=promoted_skills,
        methodology_philosophy=methodology_philosophy,
    )
