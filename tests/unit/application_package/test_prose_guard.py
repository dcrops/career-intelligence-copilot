"""Tests for owner-edit Markdown preservation helper."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_package.prose_guard import (
    markdown_sha256,
    should_preserve_owner_markdown,
)


def test_should_preserve_when_hash_differs(tmp_path: Path) -> None:
    path = tmp_path / "cv.md"
    path.write_text("generated\n", encoding="utf-8", newline="\n")
    fingerprint = markdown_sha256(path)
    path.write_text("owner edited\n", encoding="utf-8", newline="\n")
    assert should_preserve_owner_markdown(path, fingerprint, regenerate=False) is True
    assert should_preserve_owner_markdown(path, fingerprint, regenerate=True) is False


def test_should_not_preserve_matching_generated_draft(tmp_path: Path) -> None:
    path = tmp_path / "cv.md"
    path.write_text("generated\n", encoding="utf-8", newline="\n")
    fingerprint = markdown_sha256(path)
    assert should_preserve_owner_markdown(path, fingerprint, regenerate=False) is False


def test_existing_file_without_fingerprint_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "cv.md"
    path.write_text("ambiguous\n", encoding="utf-8", newline="\n")
    assert should_preserve_owner_markdown(path, None, regenerate=False) is True
    assert should_preserve_owner_markdown(path, None, regenerate=True) is False
