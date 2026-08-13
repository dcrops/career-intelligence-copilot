"""Guard owner-edited Markdown against silent package regeneration.

Stores the SHA-256 of last *generated* Markdown. If the file on disk differs
(or no fingerprint exists for an existing file), ordinary ``prepare`` re-renders
HTML/PDF only and does not overwrite prose. Explicit ``regenerate=True``
overwrites.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def markdown_sha256(path: Path) -> str:
    """Return hex SHA-256 of the file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def should_preserve_owner_markdown(
    markdown_path: Path,
    generated_fingerprint: str | None,
    *,
    regenerate: bool,
) -> bool:
    """True when existing Markdown must not be replaced by generation."""
    if regenerate:
        return False
    if not markdown_path.is_file():
        return False
    if generated_fingerprint is None:
        # Pre-guard packages: existing prose is ambiguous — do not overwrite.
        return True
    return markdown_sha256(markdown_path) != generated_fingerprint
