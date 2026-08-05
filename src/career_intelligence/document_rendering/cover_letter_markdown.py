"""Parse generated cover-letter Markdown into presentation fields.

Used only by the render-only path so owner edits in Markdown flow into HTML/PDF
without reconstructing JobAnalysis or invoking the composer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_intelligence.document_rendering.errors import DocumentRenderInputError

_ROLE_LINE = re.compile(r"^\*\*(.+?)\s+-\s+(.+?)\*\*\s*$")
_LINK_LINE = re.compile(
    r"^\*\*(LinkedIn|Portfolio|GitHub):\*\*\s+\[([^\]]+)\]\(([^)]+)\)\s*$",
    re.IGNORECASE,
)
_LINK_KEYS = {
    "linkedin": "linkedin_url",
    "portfolio": "portfolio_url",
    "github": "github_url",
}


@dataclass(frozen=True)
class CoverLetterPresentation:
    """Presentation-only fields required by the cover-letter HTML renderer."""

    full_name: str
    role_title: str
    company: str
    salutation: str
    paragraphs: list[str]
    contact: dict[str, str]


def parse_cover_letter_markdown(markdown: str) -> CoverLetterPresentation:
    """Parse a generated (possibly owner-edited) cover-letter Markdown draft."""
    text = markdown.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise DocumentRenderInputError("Cover letter Markdown is empty")

    lines = text.split("\n")
    if not lines[0].startswith("# "):
        raise DocumentRenderInputError(
            "Cover letter Markdown must start with an H1 full name"
        )
    full_name = lines[0][2:].strip()
    if not full_name:
        raise DocumentRenderInputError("Cover letter Markdown is missing a full name")

    role_title = ""
    company = ""
    body_start = 1
    for index, line in enumerate(lines[1:], start=1):
        match = _ROLE_LINE.match(line.strip())
        if match:
            role_title = match.group(1).strip()
            company = match.group(2).strip()
            body_start = index + 1
            break
    if not role_title or not company:
        raise DocumentRenderInputError(
            "Cover letter Markdown must include a '**Role - Company**' line"
        )

    # Skip horizontal rule / blank lines before salutation.
    cursor = body_start
    while cursor < len(lines) and lines[cursor].strip() in {"", "---"}:
        cursor += 1
    if cursor >= len(lines):
        raise DocumentRenderInputError("Cover letter Markdown is missing a salutation")
    salutation = lines[cursor].strip()
    cursor += 1

    # Collect body until "Kind regards,"
    body_lines: list[str] = []
    while cursor < len(lines):
        if lines[cursor].strip().casefold() == "kind regards,":
            break
        body_lines.append(lines[cursor])
        cursor += 1
    if cursor >= len(lines):
        raise DocumentRenderInputError(
            "Cover letter Markdown is missing a 'Kind regards,' signature"
        )

    paragraphs = [
        block.strip()
        for block in "\n".join(body_lines).split("\n\n")
        if block.strip()
    ]
    if len(paragraphs) < 1:
        raise DocumentRenderInputError("Cover letter Markdown has no body paragraphs")

    # Signature: Kind regards, / Name / contact lines
    cursor += 1
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1
    # Optional repeated full name line
    if cursor < len(lines) and lines[cursor].strip() == full_name:
        cursor += 1
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1

    contact: dict[str, str] = {}
    while cursor < len(lines):
        raw = lines[cursor].strip()
        cursor += 1
        if not raw:
            continue
        link = _LINK_LINE.match(raw)
        if link:
            key = _LINK_KEYS[link.group(1).casefold()]
            contact[key] = link.group(3).strip()
            continue
        if "@" in raw and "email" not in contact:
            contact["email"] = raw
            continue
        if re.search(r"\d", raw) and len(raw) <= 24 and "phone" not in contact:
            contact["phone"] = raw
            continue
        if "location" not in contact and not raw.startswith("**"):
            contact["location"] = raw

    return CoverLetterPresentation(
        full_name=full_name,
        role_title=role_title,
        company=company,
        salutation=salutation,
        paragraphs=paragraphs,
        contact=contact,
    )
