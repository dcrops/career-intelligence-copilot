"""Deterministic theme-aware Professional Summary composition (FR-006b).

Composes a scan-friendly lead from plan themes / promoted skills, then retains
the Career Profile summary as grounded supporting prose. Does not invent
employers, technologies, metrics, or achievements.
"""

from __future__ import annotations

from collections.abc import Sequence

_HARD_MAX_WORDS = 140


def compose_theme_aware_summary(
    *,
    source_summary: str,
    target_role: str,
    themes: Sequence[str],
    promoted_skills: Sequence[str],
) -> str:
    """Build a role-aware summary from profile prose and plan emphasis labels.

    Returns ``source_summary`` unchanged when no themes or promoted skills exist.
    """
    body = " ".join(source_summary.split()).strip()
    if not body:
        return body

    focus = _dedupe_preserve([*themes, *promoted_skills], limit=4)
    focus = [
        term
        for term in focus
        if term.casefold() != target_role.casefold()
    ][:4]
    if not focus:
        return body

    lead = f"{target_role} with strengths in {_oxford_join(focus)}."
    # Avoid a near-duplicate lead when the profile summary already opens the same way.
    if body.casefold().startswith(lead.casefold()):
        return _clamp_words(body, _HARD_MAX_WORDS)

    if body.casefold().startswith(target_role.casefold()):
        remainder = body[len(target_role) :].lstrip(" ,")
        if remainder.casefold().startswith("with "):
            remainder = remainder[5:]
        if remainder:
            remainder = remainder[0].upper() + remainder[1:]
            composed = f"{lead} Background: {remainder}"
        else:
            composed = lead
    else:
        composed = f"{lead} {body}"
    return _clamp_words(composed, _HARD_MAX_WORDS)


def _dedupe_preserve(values: Sequence[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _oxford_join(items: Sequence[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _clamp_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    truncated = " ".join(words[:limit]).rstrip(".,;:")
    # Prefer ending on a sentence boundary inside the window.
    for sep in (". ", "; "):
        idx = truncated.rfind(sep)
        if idx >= max(40, len(truncated) // 3):
            return truncated[: idx + 1].strip()
    return truncated + "."
