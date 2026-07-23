"""Fail-closed validation for Phase C rewritten summaries."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .summary_rewriter import SUMMARY_HARD_MAX_WORDS, SummaryRewriteInput

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_YEAR_CLAIM_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\b",
    re.IGNORECASE,
)
_TECH_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[./+][a-z0-9]+)*", re.IGNORECASE)

_COMMERCIAL_CLAIM_PHRASES = (
    "commercially deployed",
    "commercial deployment",
    "production deployment for clients",
    "client delivery",
    "paid consulting",
    "employed as an ai engineer",
    "commercial ai engineering employment",
    "production ai systems for customers",
)


@dataclass(frozen=True)
class SummaryValidationResult:
    ok: bool
    errors: tuple[str, ...] = ()


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def validate_rewritten_summary(
    summary: str,
    rewrite_input: SummaryRewriteInput,
    *,
    known_employers: tuple[str, ...] = (),
    known_projects: tuple[str, ...] = (),
    known_certifications: tuple[str, ...] = (),
    known_technologies: tuple[str, ...] = (),
) -> SummaryValidationResult:
    """Reject invented tech/employers/projects/certs/years/commercial claims."""
    errors: list[str] = []
    text = summary.strip()
    if not text:
        return SummaryValidationResult(ok=False, errors=("summary is empty",))

    words = word_count(text)
    if words > SUMMARY_HARD_MAX_WORDS:
        errors.append(
            f"summary exceeds hard maximum of {SUMMARY_HARD_MAX_WORDS} words "
            f"(got {words})"
        )

    folded = text.casefold()
    source_folded = rewrite_input.source_summary.casefold()

    for prohibited in rewrite_input.prohibited_technologies:
        if _contains_phrase(folded, prohibited.casefold()):
            errors.append(f"summary mentions prohibited technology '{prohibited}'")

    allowed_tech = {_norm(item) for item in rewrite_input.allowed_technologies}
    # Tokens already present in the source summary remain permitted.
    for item in (*rewrite_input.allowed_technologies, *known_technologies):
        if _contains_phrase(source_folded, item.casefold()):
            allowed_tech.add(_norm(item))

    catalogue = {
        _norm(item)
        for item in (
            *rewrite_input.allowed_technologies,
            *rewrite_input.prohibited_technologies,
            *known_technologies,
        )
        if item.strip()
    }
    for token in sorted(catalogue, key=len, reverse=True):
        if token in allowed_tech:
            continue
        if _contains_phrase(folded, token):
            errors.append(
                f"summary mentions technology '{token}' outside the allowlist"
            )

    for name in _disallowed_named_mentions(
        folded,
        known_names=known_employers,
        allowed=set(rewrite_input.allowed_employers),
        source_folded=source_folded,
    ):
        errors.append(f"summary invents or alters employer '{name}'")

    for name in _disallowed_named_mentions(
        folded,
        known_names=known_projects,
        allowed=set(rewrite_input.allowed_project_names),
        source_folded=source_folded,
    ):
        errors.append(f"summary invents or alters project '{name}'")

    for name in _disallowed_named_mentions(
        folded,
        known_names=known_certifications,
        allowed=set(rewrite_input.allowed_certifications),
        source_folded=source_folded,
    ):
        errors.append(f"summary invents or alters certification '{name}'")

    source_year_values = {
        match.group(1)
        for match in _YEAR_CLAIM_RE.finditer(rewrite_input.source_summary)
    }
    for match in _YEAR_CLAIM_RE.finditer(text):
        if match.group(1) not in source_year_values:
            errors.append(
                f"summary invents years-of-experience claim '{match.group(0)}'"
            )

    for phrase in _COMMERCIAL_CLAIM_PHRASES:
        if phrase in folded and phrase not in source_folded:
            errors.append(
                f"summary introduces unsupported commercial claim '{phrase}'"
            )

    if errors:
        return SummaryValidationResult(ok=False, errors=tuple(dict.fromkeys(errors)))
    return SummaryValidationResult(ok=True)


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _contains_phrase(haystack_folded: str, needle_folded: str) -> bool:
    needle = _norm(needle_folded)
    if not needle:
        return False
    if re.search(r"[^a-z0-9]", needle):
        return needle in haystack_folded
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])")
    return pattern.search(haystack_folded) is not None


def _disallowed_named_mentions(
    summary_folded: str,
    *,
    known_names: tuple[str, ...],
    allowed: set[str],
    source_folded: str,
) -> list[str]:
    allowed_folded = {_norm(name) for name in allowed}
    bad: list[str] = []
    # Longer names first to avoid partial double-counts in messaging.
    for name in sorted(known_names, key=len, reverse=True):
        key = _norm(name)
        if not key or key in allowed_folded:
            continue
        if _contains_phrase(source_folded, key):
            continue
        if _contains_phrase(summary_folded, key):
            bad.append(name)
    return bad
