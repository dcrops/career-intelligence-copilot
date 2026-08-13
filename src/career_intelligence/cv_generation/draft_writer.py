"""Deterministic draft writers for approved TailoredCv artifacts.

Writes Markdown, HTML, PDF, typed JSON, and TailoringPlan JSON under a
caller-supplied directory (default: ``career-documents/cv/generated/``).

No submission or email. Owner review remains mandatory.
HTML uses the in-package renderer (no Pandoc). PDF is rendered from that HTML.
"""

from __future__ import annotations

import json
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.cv_generation.errors import CvHtmlRenderError, CvPdfRenderError
from career_intelligence.cv_generation.html_renderer import render_html
from career_intelligence.document_rendering.cv_markdown import (
    render_cv_html_from_markdown,
)
from career_intelligence.cv_generation.models import TailoredCv, TailoringPlan
from career_intelligence.cv_generation.pdf_renderer import (
    PdfRenderError,
    render_pdf_from_html,
)

_UNSAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass(frozen=True)
class DraftWriteResult:
    """Paths written for one TailoredCv draft set."""

    output_dir: Path
    stem: str
    markdown_path: Path
    json_path: Path
    plan_json_path: Path
    html_path: Path | None = None
    pdf_path: Path | None = None


def default_generated_dir(repo_root: Path) -> Path:
    return repo_root / "career-documents" / "cv" / "generated"


def build_draft_stem(
    *,
    company: str | None,
    title: str | None,
    when: datetime | None = None,
) -> str:
    """Build a repository-consistent filename stem for generated CV drafts."""
    stamp = (when or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    company_part = _slug(company or "company")
    title_part = _slug(title or "role")
    return f"{stamp}_{company_part}_{title_part}"


def write_tailored_cv_drafts(
    cv: TailoredCv,
    plan: TailoringPlan,
    *,
    output_dir: Path,
    stem: str | None = None,
) -> DraftWriteResult:
    """Write Markdown + HTML + PDF + TailoredCv JSON + TailoringPlan JSON.

    HTML and PDF are rendered before any files are written. If either render
    fails, no draft files are written. Writes use a temp-then-replace pattern.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_stem = stem or build_draft_stem(
        company=cv.job_analysis.posting.company,
        title=cv.job_analysis.posting.title,
    )
    markdown_path = output_dir / f"{resolved_stem}.md"
    json_path = output_dir / f"{resolved_stem}.json"
    plan_json_path = output_dir / f"{resolved_stem}.tailoring_plan.json"
    html_path = output_dir / f"{resolved_stem}.html"
    pdf_path = output_dir / f"{resolved_stem}.pdf"

    try:
        if cv.summary_source == "master_baseline":
            html_document = render_cv_html_from_markdown(
                cv.rendered_markdown,
                title=f"{cv.full_name} — {cv.target_role}",
            )
        else:
            html_document = render_html(cv)
    except CvHtmlRenderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise CvHtmlRenderError(f"HTML rendering failed: {exc}") from exc

    if not html_document.lstrip().lower().startswith("<!doctype html>"):
        raise CvHtmlRenderError("HTML renderer did not return a complete document")

    try:
        pdf_bytes = render_pdf_from_html(html_document)
    except PdfRenderError as exc:
        raise CvPdfRenderError(str(exc)) from exc

    markdown_body = cv.rendered_markdown
    cv_json = json.dumps(cv.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    plan_json = (
        json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    )

    _atomic_write_text(plan_json_path, plan_json)
    _atomic_write_text(json_path, cv_json)
    _atomic_write_text(markdown_path, markdown_body)
    _atomic_write_text(html_path, html_document)
    _atomic_write_bytes(pdf_path, pdf_bytes)

    return DraftWriteResult(
        output_dir=output_dir,
        stem=resolved_stem,
        markdown_path=markdown_path,
        json_path=json_path,
        plan_json_path=plan_json_path,
        html_path=html_path,
        pdf_path=pdf_path,
    )


def _atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)
    except OSError as error:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        if path.suffix == ".html":
            with suppress(OSError):
                path.unlink(missing_ok=True)
            raise CvHtmlRenderError(
                f"Could not write HTML draft {path}: {error}"
            ) from error
        raise


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    except OSError as error:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        with suppress(OSError):
            path.unlink(missing_ok=True)
        raise CvPdfRenderError(f"Could not write PDF draft {path}: {error}") from error


def _slug(value: str) -> str:
    cleaned = _UNSAFE_FILENAME.sub("_", value.strip().casefold())
    cleaned = cleaned.strip("._-")
    return cleaned[:48] or "item"
