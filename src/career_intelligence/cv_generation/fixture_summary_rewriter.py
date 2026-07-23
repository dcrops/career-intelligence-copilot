"""Deterministic offline summary rewriter for FR-006 Phase C tests."""

from __future__ import annotations

from .summary_rewriter import SummaryRewriteExtraction, SummaryRewriteInput
from .summary_validation import word_count


class FixtureSummaryRewriter:
    """Template-based rewriter — no network, stable across runs."""

    def rewrite(self, rewrite_input: SummaryRewriteInput) -> SummaryRewriteExtraction:
        themes = [item.theme for item in rewrite_input.mandatory_themes]
        skills = [item.skill_name for item in rewrite_input.preferred_skills[:4]]
        projects = [item.name for item in rewrite_input.preferred_projects[:2]]

        parts: list[str] = []
        if rewrite_input.source_summary:
            # Keep a short factual anchor from the source without copying all of it.
            first_sentence = rewrite_input.source_summary.split(".")[0].strip()
            if first_sentence:
                parts.append(first_sentence + ".")

        if themes:
            parts.append(
                "This tailored summary emphasises "
                + ", ".join(themes)
                + "."
            )
        if skills:
            parts.append(
                "Relevant capabilities include " + ", ".join(skills) + "."
            )
        if projects:
            parts.append(
                "Supporting portfolio work includes " + ", ".join(projects) + "."
            )
        if not parts:
            parts.append(rewrite_input.source_summary)

        summary = " ".join(parts).strip()
        # Ensure hard max is respected for fixture stability.
        while word_count(summary) > 140 and " " in summary:
            summary = summary.rsplit(" ", 1)[0].rstrip(".,;") + "."
        return SummaryRewriteExtraction(summary=summary)
