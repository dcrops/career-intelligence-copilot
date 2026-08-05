"""Content hashing for truth-validation freshness (FR-014 M3).

Freshness is proven by comparing the hash of current Markdown bytes to the hash
recorded on the TruthReport. Timestamps alone are never sufficient.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def markdown_content_hash(markdown: str) -> str:
    """Return full SHA-256 hex digest of Markdown text (UTF-8)."""
    return sha256(markdown.encode("utf-8")).hexdigest()


def read_markdown(path: Path) -> str:
    """Read Markdown from disk as UTF-8 text."""
    return path.read_text(encoding="utf-8")


def hashes_match(expected: str | None, actual: str) -> bool:
    """True when a stored fingerprint matches current Markdown bytes."""
    if expected is None or not expected.strip():
        return False
    return expected == actual
