"""Deterministic content selection helpers for FR-006b CV quality.

Selects and orders existing Career Profile strings by overlap with plan
emphasis terms. Never invents highlights, outcomes, or demonstrates items.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def select_by_relevance(
    items: Sequence[str],
    terms: Sequence[str],
    *,
    max_items: int,
    min_items: int = 1,
) -> list[str]:
    """Return up to ``max_items`` existing strings, preferring term overlap.

    When scores tie, original order is preserved. If nothing scores, the first
    ``min_items`` (or ``max_items`` if smaller) items are retained.
    """
    if not items:
        return []
    limit = max(1, max_items)
    floor = max(0, min(min_items, limit, len(items)))
    term_tokens = {_tokens(term) for term in terms if term.strip()}
    term_tokens = {tokens for tokens in term_tokens if tokens}

    scored: list[tuple[int, int, str]] = []
    for index, item in enumerate(items):
        item_tokens = _tokens(item)
        score = 0
        if term_tokens and item_tokens:
            score = max(len(item_tokens & tokens) for tokens in term_tokens)
            # Prefer phrase containment for multi-word terms.
            folded = item.casefold()
            for term in terms:
                needle = term.casefold().strip()
                if len(needle) >= 3 and needle in folded:
                    score += 2
        scored.append((score, index, item))

    scored.sort(key=lambda row: (-row[0], row[1]))
    selected = [item for score, _index, item in scored if score > 0][:limit]
    if len(selected) < floor:
        for _score, _index, item in scored:
            if item in selected:
                continue
            selected.append(item)
            if len(selected) >= floor:
                break
    return selected[:limit]


def score_text(text: str, terms: Sequence[str]) -> int:
    """Simple overlap score for ranking projects or experience entries."""
    if not text.strip() or not terms:
        return 0
    tokens = _tokens(text)
    folded = text.casefold()
    score = 0
    for term in terms:
        term_tokens = _tokens(term)
        if term_tokens:
            score += len(tokens & term_tokens)
        needle = term.casefold().strip()
        if len(needle) >= 3 and needle in folded:
            score += 2
    return score


def _tokens(value: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(value.casefold()))
