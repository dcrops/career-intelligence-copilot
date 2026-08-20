"""Deterministic validators for bounded cover-letter positioning output."""

from __future__ import annotations

import re

from career_intelligence.document_positioning.catalogue import (
    aliases_for_identity,
    normalise_label,
)
from career_intelligence.document_positioning.letter_pack import CoverLetterPositioningPack
from career_intelligence.document_positioning.models import SupportStatus

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_YEAR_CLAIM_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\b", re.IGNORECASE)
_METRIC_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%|\b(?:aud|usd)\s*\$?\d", re.IGNORECASE)
_MAX_LETTER_WORDS = 450

_GENERIC_OPENINGS = (
    "i am excited",
    "i'm excited",
    "i am passionate",
    "i am writing to apply",
    "i am applying for",
    "i would like to apply",
    "please find attached",
    "i wish to apply",
    "it is with great",
    "dear hiring manager",
)

_COMMERCIAL_AI_PHRASES = (
    "employed as an ai engineer",
    "commercial ai engineering employment",
    "paid ai engineering role",
    "ai engineering consultant",
)

_ML_PHRASES = (
    "tensorflow",
    "pytorch",
    "keras",
    "scikit-learn",
    "deep learning",
    "machine learning engineer",
    "ml expertise",
)

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

_BIOGRAPHY_MARKERS = (
    "qa →",
    "qa ->",
    "tester-to-data",
    "testing to data",
    "test analyst then",
)


def validate_cover_letter_positioning_output(
    paragraphs: list[str],
    pack: CoverLetterPositioningPack,
) -> list[str]:
    errors: list[str] = []
    if not paragraphs:
        return ["letter paragraphs are empty"]
    opening = paragraphs[0].casefold()
    body = " ".join(paragraphs)
    folded = body.casefold()
    words = len(_WORD_RE.findall(body))
    if words > _MAX_LETTER_WORDS:
        errors.append(
            f"letter exceeds hard maximum of {_MAX_LETTER_WORDS} words (got {words})"
        )

    for phrase in _GENERIC_OPENINGS:
        if phrase in opening:
            errors.append(f"generic opening pattern '{phrase}' is not allowed")

    normalised = [" ".join(item.split()).casefold() for item in paragraphs]
    if len(set(normalised)) != len(normalised):
        errors.append("duplicate evidence paragraph rejected")
    for index, left in enumerate(normalised):
        left_words = set(_WORD_RE.findall(left))
        if len(left_words) < 8:
            continue
        for right in normalised[index + 1 :]:
            right_words = set(_WORD_RE.findall(right))
            if not left_words or not right_words:
                continue
            overlap = len(left_words & right_words) / max(
                1, min(len(left_words), len(right_words))
            )
            if overlap >= 0.9:
                errors.append("duplicate evidence paragraph rejected")
                break

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

    packed_years = _packed_year_tokens(pack)
    for match in _YEAR_CLAIM_RE.finditer(body):
        if match.group(1) not in packed_years:
            errors.append(f"invents years-of-experience claim '{match.group(0)}'")

    packed_text = " ".join(
        [
            *pack.opening_facts,
            *pack.body_facts,
            *pack.closing_facts,
            *pack.claimable_direct_labels,
        ]
    )
    if _METRIC_RE.search(body) and not _METRIC_RE.search(packed_text):
        errors.append("invents a metric not present in packed evidence")

    if not pack.commercial_ai_employment:
        for phrase in _COMMERCIAL_AI_PHRASES:
            if _has_unnegated_phrase(folded, phrase):
                errors.append(
                    "composed prose recasts independent AI work as commercial "
                    f"AI employment ('{phrase}')"
                )

    if not pack.candidate_has_ml_expertise:
        for phrase in _ML_PHRASES:
            if phrase in folded:
                errors.append(
                    f"composed prose claims unsupported ML expertise ('{phrase}')"
                )

    for source in pack.selected_sources:
        if not _source_represented(source.name, source.organisation, folded):
            errors.append(
                f"selected evidence source '{source.name}' is not represented in output"
            )

    if pack.trajectory_mode == "ai_lead":
        for marker in _BIOGRAPHY_MARKERS:
            if marker in folded:
                errors.append(
                    "ai_lead letter must not force a full QA → data → AI biography"
                )
                break

    related_requested = [
        item.label
        for item in pack.employer_needs
        if item.status is SupportStatus.SUPPORTED_RELATED
    ]
    for label in related_requested:
        needle = normalise_label(label)
        if not needle:
            continue
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", folded):
            if _is_employer_context(folded, match.start()):
                continue
            if _looks_like_candidate_claim(folded, match.start(), match.end()):
                errors.append(
                    f"RELATED requested identity '{label}' claimed as candidate experience"
                )
                break

    if "aws bedrock" in folded:
        if not _is_employer_context(folded, folded.find("aws bedrock")):
            errors.append("RELATED Bedrock must not be claimed as candidate experience")

    return list(dict.fromkeys(errors))


def _source_represented(name: str, organisation: str | None, folded: str) -> bool:
    needles = [name.casefold()]
    if organisation:
        needles.append(organisation.casefold())
    significant = [
        token
        for token in _WORD_RE.findall(name.casefold())
        if token not in {"the", "and", "for", "with", "from", "a", "an"}
        and len(token) >= 4
    ]
    if any(needle in folded for needle in needles if len(needle) >= 4):
        return True
    if significant and all(token in folded for token in significant[:2]):
        return True
    if "trajectory" in name.casefold() or "qa" in name.casefold():
        return ("tester" in folded or "qa" in folded or "testing" in folded) and (
            "data engineer" in folded or "data engineering" in folded
        )
    return False


def _packed_year_tokens(pack: CoverLetterPositioningPack) -> set[str]:
    blob = " ".join((*pack.opening_facts, *pack.body_facts, *pack.argument_spine))
    return {match.group(1) for match in _YEAR_CLAIM_RE.finditer(blob)}


def _forbidden_phrases(pack: CoverLetterPositioningPack) -> tuple[str, ...]:
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


def _has_unnegated_phrase(folded: str, phrase: str) -> bool:
    start = 0
    while True:
        pos = folded.find(phrase, start)
        if pos < 0:
            return False
        window = folded[max(0, pos - 24) : pos]
        if not re.search(r"\bnot\b(?:\s+conventional)?\s+$", window):
            return True
        start = pos + len(phrase)
