"""Normalisation helpers for technology object keys (FR-014 M2)."""

from __future__ import annotations

import re

_NON_ALNUM = re.compile(r"[^a-z0-9+#.]+")
_MULTI_DOT = re.compile(r"\.{2,}")


def normalise_object_key(label: str) -> str:
    """Return a stable lowercase key for matching technology labels.

    Examples: ``Node.js`` → ``nodejs``, ``C#`` → ``c#``, ``Vue.js`` → ``vuejs``.
    """
    text = " ".join(label.strip().casefold().split())
    text = text.replace(".js", "js").replace(".net", "net")
    text = _NON_ALNUM.sub("", text)
    text = _MULTI_DOT.sub(".", text)
    return text


def display_label(label: str) -> str:
    """Preserve a readable label while trimming whitespace."""
    return " ".join(label.strip().split())
