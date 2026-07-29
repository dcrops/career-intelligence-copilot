"""Deterministic draft writers for approved CoverLetter artifacts.

Writes Markdown, HTML, typed JSON, and CoverLetterPlan JSON under
``career-documents/cover-letters/generated/`` by default.

No PDF/DOCX. No submission or email. Owner review remains mandatory.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.cover_letter.html_renderer import (
    CoverLetterHtmlRenderError,
    render_html,
)
from career_intelligence.cover_letter.models import CoverLetter, CoverLetterPlan

_UNSAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass(frozen=True)
class DraftWriteResult:
    """Paths written for one CoverLetter draft set."""

    output_dir: Path
    stem: str
    markdown_path: Path
    json_path: Path
    plan_json_path: Path
    html_path: Path | None = None


def default_generated_dir(repo_root: Path) -> Path:
    return repo_root / "career-documents" / "cover-letters" / "generated"


def build_draft_stem(
    *,
    company: str | None,
    title: str | None,
    when: datetime | None = None,
) -> str:
    stamp = (when or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    company_part = _slug(company or "company")
    title_part = _slug(title or "role")
    return f"{stamp}_{company_part}_{title_part}"


def write_cover_letter_drafts(
    letter: CoverLetter,
    plan: CoverLetterPlan,
    *,
    output_dir: Path,
    stem: str | None = None,
) -> DraftWriteResult:
    """Write Markdown + HTML + CoverLetter JSON + plan JSON for review.

    HTML is rendered before any files are written. If HTML rendering fails, no
    draft files are written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_stem = stem or build_draft_stem(
        company=letter.company,
        title=letter.role_title,
    )
    markdown_path = output_dir / f"{resolved_stem}.md"
    json_path = output_dir / f"{resolved_stem}.json"
    plan_json_path = output_dir / f"{resolved_stem}.cover_letter_plan.json"
    html_path = output_dir / f"{resolved_stem}.html"

    try:
        html_document = render_html(letter)
    except CoverLetterHtmlRenderError:
        raise

    _atomic_write_text(markdown_path, letter.rendered_markdown)
    _atomic_write_text(html_path, html_document)
    _atomic_write_text(
        json_path,
        json.dumps(letter.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
    )
    _atomic_write_text(
        plan_json_path,
        json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
    )
    return DraftWriteResult(
        output_dir=output_dir,
        stem=resolved_stem,
        markdown_path=markdown_path,
        json_path=json_path,
        plan_json_path=plan_json_path,
        html_path=html_path,
    )


def _slug(value: str) -> str:
    cleaned = _UNSAFE_FILENAME.sub("_", value.strip().casefold())
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned[:60] or "item"


def _atomic_write_text(path: Path, content: str) -> str:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return content
