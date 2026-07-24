"""Standalone HTML rendering for approved TailoredCv drafts.

Produces a complete UTF-8 HTML document matching Master CV print presentation.
No Pandoc, browser JS, or network access. Content is derived from TailoredCv
(same fields as submit-ready Markdown) so Markdown and HTML stay aligned.
"""

from __future__ import annotations

import html
import re
from functools import lru_cache
from importlib import resources
from pathlib import Path

from career_intelligence.cv_generation.errors import CvHtmlRenderError
from career_intelligence.cv_generation.models import (
    RenderedExperience,
    RenderedProject,
    TailoredCv,
)
from career_intelligence.cv_generation.render_markdown import (
    _KIND_LABELS,
    _bold_terms,
    _curate_skills_for_submit,
    _emphasis_terms,
    _format_month,
)

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def render_html(cv: TailoredCv, *, title: str | None = None) -> str:
    """Render a complete standalone HTML document for a TailoredCv."""
    try:
        document_title = title or f"{cv.full_name} — {cv.target_role}"
        body = _render_body(cv)
        css = load_cv_print_css()
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            f"  <title>{_esc(document_title)}</title>\n"
            "  <style>\n"
            f"{css.rstrip()}\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            f"{body}"
            "</body>\n"
            "</html>\n"
        )
    except CvHtmlRenderError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert unexpected failures
        raise CvHtmlRenderError(f"HTML rendering failed: {exc}") from exc


def load_cv_print_css() -> str:
    """Return shared print CSS packaged with the CV generation module."""
    return _cached_cv_print_css()


def clear_cv_print_css_cache() -> None:
    """Clear cached CSS (tests / after asset updates)."""
    _cached_cv_print_css.cache_clear()


@lru_cache(maxsize=1)
def _cached_cv_print_css() -> str:
    package = resources.files("career_intelligence.cv_generation")
    css_path = package.joinpath("assets/cv_print.css")
    try:
        return css_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, TypeError):
        # Fallback for editable installs where package traversal differs.
        fallback = Path(__file__).resolve().parent / "assets" / "cv_print.css"
        if not fallback.is_file():
            raise CvHtmlRenderError(
                f"Shared CV print CSS not found at {fallback}"
            ) from None
        return fallback.read_text(encoding="utf-8")


def _render_body(cv: TailoredCv) -> str:
    emphasis = _emphasis_terms(cv)
    parts: list[str] = []
    parts.append(f"<h1>{_esc(cv.full_name)}</h1>\n")
    parts.append('<hr class="header-rule" />\n')
    parts.extend(_render_contact_block(cv.contact))
    parts.append(f'<p class="role">{_esc(cv.target_role)}</p>\n')

    if cv.summary:
        parts.append("<h2>Professional Summary</h2>\n")
        parts.append(f"<p>{_inline_to_html(cv.summary)}</p>\n")

    if cv.selected_engineering_highlights:
        parts.append("<h2>Selected Engineering Highlights</h2>\n")
        parts.append("<ul>\n")
        for highlight in cv.selected_engineering_highlights:
            parts.append(
                f"  <li>{_inline_to_html(_bold_terms(highlight, emphasis))}</li>\n"
            )
        parts.append("</ul>\n")

    emphasised, additional = _curate_skills_for_submit(cv.skills)
    if emphasised or additional:
        parts.append("<h2>Core Skills</h2>\n")
        parts.append('<div class="skills">\n')
        if emphasised:
            joined = " · ".join(
                f"<strong>{_esc(skill.skill_name)}</strong>" for skill in emphasised
            )
            parts.append(f"  <p>{joined}</p>\n")
        if additional:
            joined = " · ".join(_esc(skill.skill_name) for skill in additional)
            parts.append(f"  <p><strong>Also:</strong> {joined}</p>\n")
        parts.append("</div>\n")

    if cv.experience:
        parts.append("<h2>Professional Experience</h2>\n")
        for entry in cv.experience:
            parts.append(_render_experience(entry, emphasis))

    if cv.projects:
        parts.append("<h2>Featured AI Projects</h2>\n")
        for project in cv.projects:
            parts.append(_render_project(project, emphasis))

    if cv.engineering_methodology is not None:
        parts.append('<div class="methodology">\n')
        parts.append("<h2>AI Engineering Methodology</h2>\n")
        parts.append(
            f"<p>{_inline_to_html(cv.engineering_methodology.philosophy)}</p>\n"
        )
        for category in cv.engineering_methodology.categories:
            practices = " · ".join(_esc(item) for item in category.practices)
            parts.append(
                f"<p><strong>{_esc(category.name)}:</strong> {practices}</p>\n"
            )
        parts.append("</div>\n")

    if cv.certifications:
        parts.append('<div class="closing">\n')
        parts.append("<h2>Certifications</h2>\n")
        parts.append("<ul>\n")
        for cert in cv.certifications:
            parts.append(
                "  <li>"
                f"<strong>{_esc(cert.name)}</strong> — {_esc(cert.issuer)}"
                "</li>\n"
            )
        parts.append("</ul>\n")
        parts.append("</div>\n")

    return "".join(parts)


def _render_contact_block(contact: dict[str, str] | None) -> list[str]:
    if not contact:
        return []
    parts: list[str] = []
    location = contact.get("location")
    if location:
        parts.append(f'<p class="contact">{_esc(location)}</p>\n')

    primary: list[str] = []
    email = contact.get("email")
    if email:
        primary.append(f'<a href="mailto:{_esc_attr(email)}">{_esc(email)}</a>')
    phone = contact.get("phone")
    if phone:
        tel = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        if tel.startswith("0") and len(tel) == 10:
            tel = f"+61{tel[1:]}"
        primary.append(f'<a href="tel:{_esc_attr(tel)}">{_esc(phone)}</a>')
    if primary:
        parts.append(f'<p class="contact">{" · ".join(primary)}</p>\n')

    links: list[str] = []
    for key, label in (
        ("linkedin_url", "LinkedIn"),
        ("portfolio_url", "Portfolio"),
        ("github_url", "GitHub"),
    ):
        url = contact.get(key)
        if not url:
            continue
        display = _compact_url_display(url)
        links.append(
            f'<p class="contact"><strong>{label}:</strong> '
            f'<a href="{_esc_attr(url)}">{_esc(display)}</a></p>\n'
        )
    parts.extend(links)

    extras = [
        f"{_esc(key)}: {_esc(value)}"
        for key, value in contact.items()
        if key
        not in {
            "email",
            "phone",
            "location",
            "linkedin_url",
            "portfolio_url",
            "github_url",
        }
        and value
    ]
    if extras:
        parts.append(f'<p class="contact">{" · ".join(extras)}</p>\n')
    return parts


def _render_experience(entry: RenderedExperience, emphasis: set[str]) -> str:
    end = _format_month(entry.end_date) if entry.end_date else "Present"
    start = _format_month(entry.start_date)
    meta_parts = [f"{start} – {end}"]
    kind_label = _KIND_LABELS.get(entry.kind)
    if kind_label:
        meta_parts.append(kind_label)
    if entry.location:
        meta_parts.append(entry.location)
    chunks = [
        '<div class="experience">\n',
        f"<h3>{_esc(entry.title)} — {_esc(entry.organisation)}</h3>\n",
        f'<p class="meta">{_esc(" · ".join(meta_parts))}</p>\n',
        "<ul>\n",
    ]
    for highlight in entry.highlights:
        chunks.append(
            f"  <li>{_inline_to_html(_bold_terms(highlight, emphasis))}</li>\n"
        )
    chunks.append("</ul>\n")
    if entry.technologies:
        tech_html = ", ".join(
            f"<strong>{_esc(tech)}</strong>"
            if tech.casefold() in {t.casefold() for t in emphasis}
            else _esc(tech)
            for tech in entry.technologies
        )
        chunks.append(f"<p><strong>Technologies:</strong> {tech_html}</p>\n")
    chunks.append("</div>\n")
    return "".join(chunks)


def _render_project(project: RenderedProject, emphasis: set[str]) -> str:
    chunks = [
        '<div class="project">\n',
        f"<h3>{_esc(project.name)}</h3>\n",
        f"<p><strong>Overview:</strong> {_inline_to_html(project.summary)}</p>\n",
    ]
    if project.demonstrates:
        chunks.append("<p><strong>Engineering Highlights:</strong></p>\n")
        chunks.append("<ul>\n")
        for item in project.demonstrates:
            chunks.append(
                f"  <li>{_inline_to_html(_bold_terms(item, emphasis))}</li>\n"
            )
        chunks.append("</ul>\n")
    if project.outcomes:
        chunks.append("<p><strong>Outcomes:</strong></p>\n")
        chunks.append("<ul>\n")
        for outcome in project.outcomes:
            chunks.append(
                f"  <li>{_inline_to_html(_bold_terms(outcome, emphasis))}</li>\n"
            )
        chunks.append("</ul>\n")
    if project.technologies:
        emphasis_folded = {term.casefold() for term in emphasis}
        techs = " · ".join(
            f"<strong>{_esc(tech)}</strong>"
            if tech.casefold() in emphasis_folded
            else _esc(tech)
            for tech in project.technologies
        )
        chunks.append(
            f'<p class="stack"><strong>Technology Stack:</strong> {techs}</p>\n'
        )
    chunks.append("</div>\n")
    return "".join(chunks)


def _inline_to_html(text: str) -> str:
    """Convert inline Markdown emphasis/links to HTML with safe escaping."""
    if not text:
        return ""
    placeholders: list[tuple[str, str]] = []

    def _stash_link(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2)
        token = f"@@LINK{len(placeholders)}@@"
        display = _compact_url_display(url) if _looks_like_url(label) else label
        placeholders.append(
            (
                token,
                f'<a href="{_esc_attr(url)}">{_esc(display)}</a>',
            )
        )
        return token

    working = _LINK_RE.sub(_stash_link, text)
    working = _esc(working)
    working = _BOLD_RE.sub(r"<strong>\1</strong>", working)
    working = _ITALIC_RE.sub(r"<em>\1</em>", working)
    for token, replacement in placeholders:
        working = working.replace(_esc(token), replacement)
    return working


def _compact_url_display(url: str) -> str:
    display = url.strip()
    for prefix in ("https://", "http://"):
        if display.casefold().startswith(prefix):
            display = display[len(prefix) :]
            break
    if display.casefold().startswith("www."):
        display = display[4:]
    return display.rstrip("/") or url


def _looks_like_url(value: str) -> bool:
    folded = value.casefold()
    return folded.startswith(("http://", "https://", "www."))


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _esc_attr(value: str) -> str:
    return html.escape(value, quote=True)
