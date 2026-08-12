"""Standalone HTML rendering for approved CoverLetter drafts.

Reuses the shared CV print CSS so cover letters and CVs feel like one suite.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from career_intelligence.cover_letter.errors import CoverLetterError
from career_intelligence.cover_letter.models import CoverLetter
from career_intelligence.cv_generation.html_renderer import load_cv_print_css

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")

_CONTACT_ORDER = (
    "email",
    "phone",
    "location",
    "linkedin_url",
    "portfolio_url",
    "github_url",
)

_LINK_LABELS = {
    "linkedin_url": "LinkedIn",
    "portfolio_url": "Portfolio",
    "github_url": "GitHub",
}


class CoverLetterHtmlRenderError(CoverLetterError):
    """Raised when CoverLetter HTML rendering fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class CoverLetterHtmlView:
    """Presentation fields shared by model render and Markdown re-render."""

    full_name: str
    role_title: str
    company: str
    salutation: str
    paragraphs: list[str]
    contact: dict[str, str] | None = None


def render_html(letter: CoverLetter, *, title: str | None = None) -> str:
    """Render a complete standalone HTML document for a CoverLetter."""
    view = CoverLetterHtmlView(
        full_name=letter.full_name,
        role_title=letter.role_title,
        company=letter.company,
        salutation=letter.salutation,
        paragraphs=list(letter.paragraphs),
        contact=dict(letter.contact) if letter.contact else None,
    )
    return render_html_from_view(view, title=title)


def render_html_from_view(
    view: CoverLetterHtmlView,
    *,
    title: str | None = None,
) -> str:
    """Render HTML from presentation fields (generation or render-only path)."""
    try:
        document_title = title or f"{view.full_name} - {view.role_title}"
        body = _render_body(view)
        css = load_cv_print_css()
        # Cover letters are shorter; keep CV typography with a slight page padding cue.
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            f"  <title>{_esc(document_title)}</title>\n"
            "  <style>\n"
            f"{css.rstrip()}\n"
            "  body.cover-letter .letter-meta { margin: 0 0 1.25rem; }\n"
            "  body.cover-letter .signature { margin-top: 1.75rem; }\n"
            "  body.cover-letter .signature p { margin: 0.15rem 0; }\n"
            "  </style>\n"
            "</head>\n"
            '<body class="cover-letter">\n'
            f"{body}"
            "</body>\n"
            "</html>\n"
        )
    except CoverLetterHtmlRenderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise CoverLetterHtmlRenderError(f"HTML rendering failed: {exc}") from exc


def _render_body(view: CoverLetterHtmlView) -> str:
    parts: list[str] = [
        f"<h1>{_esc(view.full_name)}</h1>\n",
        f'<p class="role letter-meta">{_esc(view.role_title)} - '
        f"{_esc(view.company)}</p>\n",
    ]
    parts.extend(_render_header_contact(view.contact))
    parts.append('<hr class="header-rule" />\n')
    parts.append(f"<p>{_esc(view.salutation)}</p>\n")
    for paragraph in view.paragraphs:
        chunks = [chunk.strip() for chunk in paragraph.split("\n\n") if chunk.strip()]
        if not chunks:
            continue
        for chunk in chunks:
            parts.append(f"<p>{_inline_to_html(chunk)}</p>\n")
    parts.extend(_render_signature(view))
    return "".join(parts)


def _render_header_contact(contact: dict[str, str] | None) -> list[str]:
    if not contact:
        return []
    parts: list[str] = []
    for key in _CONTACT_ORDER:
        value = contact.get(key)
        if not value:
            continue
        if key == "email":
            parts.append(
                f'<p class="contact"><a href="mailto:{_esc_attr(value)}">'
                f"{_esc(value)}</a></p>\n"
            )
        elif key == "phone":
            tel = re.sub(r"[^\d+]", "", value)
            parts.append(
                f'<p class="contact"><a href="tel:{_esc_attr(tel)}">'
                f"{_esc(value)}</a></p>\n"
            )
        elif key == "location":
            parts.append(f'<p class="contact">{_esc(value)}</p>\n')
        elif key in _LINK_LABELS:
            display = _compact_url(value)
            parts.append(
                f'<p class="contact"><strong>{_esc(_LINK_LABELS[key])}:</strong> '
                f'<a href="{_esc_attr(value)}">{_esc(display)}</a></p>\n'
            )
    return parts


def _render_signature(view: CoverLetterHtmlView) -> list[str]:
    parts = [
        '<div class="signature">\n',
        "<p>Kind regards,</p>\n",
        f"<p><strong>{_esc(view.full_name)}</strong></p>\n",
    ]
    contact = view.contact or {}
    for key in _CONTACT_ORDER:
        value = contact.get(key)
        if not value:
            continue
        if key == "email":
            parts.append(
                f'<p class="contact"><a href="mailto:{_esc_attr(value)}">'
                f"{_esc(value)}</a></p>\n"
            )
        elif key == "phone":
            tel = re.sub(r"[^\d+]", "", value)
            parts.append(
                f'<p class="contact"><a href="tel:{_esc_attr(tel)}">'
                f"{_esc(value)}</a></p>\n"
            )
        elif key == "location":
            parts.append(f'<p class="contact">{_esc(value)}</p>\n')
        elif key in _LINK_LABELS:
            display = _compact_url(value)
            parts.append(
                f'<p class="contact"><strong>{_esc(_LINK_LABELS[key])}:</strong> '
                f'<a href="{_esc_attr(value)}">{_esc(display)}</a></p>\n'
            )
    parts.append("</div>\n")
    return parts


def _inline_to_html(text: str) -> str:
    if not text:
        return ""
    placeholders: list[tuple[str, str]] = []

    def _stash_link(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2)
        token = f"@@LINK{len(placeholders)}@@"
        placeholders.append(
            (token, f'<a href="{_esc_attr(url)}">{_esc(label)}</a>')
        )
        return token

    working = _LINK_RE.sub(_stash_link, text)
    working = _esc(working)
    working = _BOLD_RE.sub(r"<strong>\1</strong>", working)
    working = _ITALIC_RE.sub(r"<em>\1</em>", working)
    for token, replacement in placeholders:
        working = working.replace(_esc(token), replacement)
    return working


def _compact_url(url: str) -> str:
    display = url.strip()
    for prefix in ("https://", "http://"):
        if display.startswith(prefix):
            display = display[len(prefix) :]
            break
    return display.rstrip("/")


def _esc(value: str) -> str:
    return html.escape(value, quote=False)


def _esc_attr(value: str) -> str:
    return html.escape(value, quote=True)
