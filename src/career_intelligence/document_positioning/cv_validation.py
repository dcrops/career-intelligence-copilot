"""Deterministic validators for bounded CV positioning output."""

from __future__ import annotations

import re

from career_intelligence.document_positioning.catalogue import (
    aliases_for_identity,
    normalise_label,
)
from career_intelligence.document_positioning.cv_pack import CvPositioningPack
from career_intelligence.document_positioning.models import SupportStatus

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_YEAR_CLAIM_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\b", re.IGNORECASE)
_METRIC_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%|\b(?:aud|usd)\s*\$?\d", re.IGNORECASE)
_MAX_SUMMARY_WORDS = 180

_CLAIM_HINTS = (
    "experience",
    "experienced",
    "expertise",
    "expert",
    "built",
    "building",
    "developed",
    "using",
    "used",
    "hands-on",
    "proficient",
    "skilled",
    "engineer",
    "applications",
)

_EMPLOYER_CONTEXT = (
    "role",
    "employer",
    "asked",
    "asking",
    "requirement",
    "advertised",
    "vacancy",
    "do not",
    "must not",
    "gap",
    "not claim",
    "transfer",
    "focused",
    "environment",
)


def positioned_text(summary: str, relevance_lines: tuple[str, ...]) -> str:
    return "\n".join((summary, *relevance_lines))


def sanitize_optional_relevance_lines(
    *,
    summary: str,
    relevance_lines: tuple[tuple[str, str], ...],
    pack: CvPositioningPack,
    all_master_project_names: tuple[str, ...] = (),
) -> tuple[tuple[str, str], ...]:
    """Drop optional relevance lines that fail their own contract.

    Summary and other non-optional violations are not repaired here.
    """
    summary_errors = set(
        validate_positioning_output(
            summary=summary,
            relevance_lines=(),
            pack=pack,
            all_master_project_names=all_master_project_names,
        )
    )
    kept: list[tuple[str, str]] = []
    for pair in relevance_lines:
        errors = set(
            validate_positioning_output(
                summary=summary,
                relevance_lines=(pair,),
                pack=pack,
                all_master_project_names=all_master_project_names,
            )
        )
        extra = errors - summary_errors
        if extra:
            continue
        kept.append(pair)
    return tuple(kept)


def validate_positioning_output(
    *,
    summary: str,
    relevance_lines: tuple[tuple[str, str], ...],
    pack: CvPositioningPack,
    all_master_project_names: tuple[str, ...] = (),
) -> list[str]:
    errors: list[str] = []
    text = summary.strip()
    if not text:
        return ["summary is empty"]
    words = len(_WORD_RE.findall(text))
    if words > _MAX_SUMMARY_WORDS:
        errors.append(
            f"summary exceeds hard maximum of {_MAX_SUMMARY_WORDS} words (got {words})"
        )

    combined = positioned_text(text, tuple(line for _name, line in relevance_lines))
    folded = combined.casefold()
    source_folded = pack.master_summary.casefold()

    for phrase in _forbidden_phrases(pack):
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", folded):
            if _is_employer_context(folded, match.start()):
                continue
            if _looks_like_candidate_claim(folded, match.start(), match.end()):
                errors.append(
                    f"forbidden candidate claim '{phrase}' appears in positioned prose"
                )
                break

    for label in pack.unsupported_labels:
        needle = normalise_label(label)
        if not needle or len(needle) < 3:
            continue
        if needle in {"ai tools"}:
            continue
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", folded):
            if _is_employer_context(folded, match.start()):
                continue
            if _looks_like_candidate_claim(folded, match.start(), match.end()):
                errors.append(
                    f"unsupported capability '{label}' claimed as candidate experience"
                )
                break

    source_years = {match.group(1) for match in _YEAR_CLAIM_RE.finditer(pack.master_summary)}
    for match in _YEAR_CLAIM_RE.finditer(combined):
        if match.group(1) not in source_years:
            errors.append(f"invents years-of-experience claim '{match.group(0)}'")

    if _METRIC_RE.search(combined) and not _METRIC_RE.search(pack.master_summary):
        errors.append("invents a metric not present in packed Master evidence")

    known_projects = {item.name.casefold() for item in pack.selected_projects}
    for name, line in relevance_lines:
        if name.casefold() not in known_projects:
            errors.append(f"project relevance names unknown project '{name}'")
            continue
        project = next(
            item for item in pack.selected_projects if item.name.casefold() == name.casefold()
        )
        allowed = {
            normalise_label(tech) for tech in project.technologies
        } | {normalise_label(label) for label in pack.claimable_direct_labels} | {
            normalise_label(label) for label in pack.related_profile_labels
        }
        for need in pack.employer_needs:
            if (
                need.status is SupportStatus.SUPPORTED_RELATED
                and need.requested_identity
            ):
                requested = normalise_label(need.label)
                if requested and requested in normalise_label(line) and requested not in allowed:
                    errors.append(
                        f"project relevance claims related-only identity '{need.label}'"
                    )

    for highlight in pack.selected_highlights:
        if highlight not in pack.master_highlights:
            errors.append("selected highlight is not an existing Master highlight")

    if "aws bedrock" in folded and "aws bedrock" not in source_folded:
        if not _is_employer_context(folded, folded.find("aws bedrock")):
            errors.append("RELATED Bedrock must not be claimed as candidate experience")

    selected_projects = {item.name.casefold() for item in pack.selected_projects}
    summary_folded = text.casefold()
    for name in all_master_project_names:
        key = name.casefold()
        if key in selected_projects:
            continue
        index = summary_folded.find(key)
        if index < 0:
            continue
        if _is_employer_context(summary_folded, index):
            continue
        errors.append(f"summary claims unpacked project '{name}'")

    return list(dict.fromkeys(errors))


def _forbidden_phrases(pack: CvPositioningPack) -> tuple[str, ...]:
    phrases: list[str] = []
    seen: set[str] = set()
    for item in pack.forbidden_claims:
        candidates = [item.may_not_claim]
        if item.identity:
            candidates.extend(aliases_for_identity(item.identity))
        for phrase in candidates:
            key = phrase.casefold().strip()
            if len(key) < 3 or key in seen:
                continue
            seen.add(key)
            phrases.append(key)
    return tuple(phrases)


def _is_employer_context(folded: str, index: int) -> bool:
    window = folded[max(0, index - 56) : index + 24]
    return any(token in window for token in _EMPLOYER_CONTEXT)


def _looks_like_candidate_claim(folded: str, start: int, end: int) -> bool:
    window = folded[max(0, start - 28) : min(len(folded), end + 28)]
    return any(hint in window for hint in _CLAIM_HINTS)
