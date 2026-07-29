"""Deterministic Markdown rendering of an approved CoverLetter."""

from __future__ import annotations

from .models import CoverLetter

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


def render_markdown(letter: CoverLetter) -> str:
    """Render a submit-ready Markdown cover letter with signature block."""
    lines: list[str] = [
        f"# {letter.full_name}",
        "",
        f"**{letter.role_title} - {letter.company}**",
        "",
        "---",
        "",
        letter.salutation,
        "",
    ]
    for paragraph in letter.paragraphs:
        lines.append(paragraph)
        lines.append("")
    lines.extend(_signature_lines(letter))
    lines.append("---")
    lines.append("")
    lines.append("_Owner review required before any external use._")
    lines.append("")
    return "\n".join(lines)


def _signature_lines(letter: CoverLetter) -> list[str]:
    lines = [
        "Kind regards,",
        "",
        letter.full_name,
        "",
    ]
    contact = letter.contact or {}
    for key in _CONTACT_ORDER:
        value = contact.get(key)
        if not value:
            continue
        if key in _LINK_LABELS:
            display = _compact_url(value)
            lines.append(f"**{_LINK_LABELS[key]}:** [{display}]({value})")
        else:
            lines.append(value)
    if any(contact.get(key) for key in _CONTACT_ORDER):
        lines.append("")
    return lines


def _compact_url(url: str) -> str:
    display = url.strip()
    for prefix in ("https://", "http://"):
        if display.startswith(prefix):
            display = display[len(prefix) :]
            break
    return display.rstrip("/")
