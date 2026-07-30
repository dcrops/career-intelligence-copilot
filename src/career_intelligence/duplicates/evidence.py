"""Deterministic facet comparison for duplicate evidence (FR-009 M3).

Normalisation is intentionally conservative: it removes formatting noise that the
same employer writes differently across platforms, and nothing else. No fuzzy or
probabilistic matching — the same two records always produce the same comparison.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from career_intelligence.opportunities.models import OpportunityIdentity

from .models import EVIDENCE_SIGNALS, EvidenceComparison, EvidenceSignal

_COMPANY_SUFFIXES = frozenset(
    {
        "pty",
        "ptyltd",
        "ltd",
        "limited",
        "inc",
        "incorporated",
        "llc",
        "plc",
        "co",
        "corp",
        "corporation",
        "group",
        "holdings",
    }
)
_TITLE_NOISE = frozenset(
    {
        "remote",
        "hybrid",
        "onsite",
        "onsight",
        "contract",
        "permanent",
        "fulltime",
        "parttime",
        "fixedterm",
    }
)
_BRACKETED = re.compile(r"[\(\[\{][^\)\]\}]*[\)\]\}]")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Platforms whose source_kind meaningfully identifies where the advert lives.
_IDENTIFYING_PLATFORMS = frozenset({"seek", "linkedin", "indeed", "recruiter"})


def normalise_company(value: str | None) -> str | None:
    """Casefold, drop punctuation, and remove legal-entity suffix tokens."""
    tokens = _tokens(value)
    if not tokens:
        return None
    trimmed = [token for token in tokens if token not in _COMPANY_SUFFIXES]
    return " ".join(trimmed or tokens)


def normalise_title(value: str | None) -> str | None:
    """Casefold, drop bracketed asides and work-arrangement noise tokens."""
    if value is None:
        return None
    without_brackets = _BRACKETED.sub(" ", value)
    tokens = _tokens(without_brackets)
    if not tokens:
        return None
    trimmed = [token for token in tokens if token not in _TITLE_NOISE]
    return " ".join(trimmed or tokens)


def location_tokens(value: str | None) -> frozenset[str]:
    """Token set for containment comparison (``Sydney NSW`` vs ``Sydney, NSW, AU``)."""
    return frozenset(_tokens(value))


def normalise_url(value: str | None) -> str | None:
    """Scheme/host/path only, casefolded host, query and fragment removed."""
    if not value:
        return None
    parsed = urlparse(str(value).strip())
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    path = (parsed.path or "").rstrip("/")
    return urlunparse(("https", host, path, "", "", "")).lower()


def compare_identities(
    left: OpportunityIdentity,
    right: OpportunityIdentity,
) -> EvidenceComparison:
    """Classify every comparable facet as matching, differing, or unknown.

    A facet missing on either side is ``unknown``, never a match. Live records
    exist with no platform job id or canonical URL at all, so absent data must not
    look like agreement.
    """
    matching: list[EvidenceSignal] = []
    differing: list[EvidenceSignal] = []
    unknown: list[EvidenceSignal] = []

    verdicts: dict[EvidenceSignal, bool | None] = {
        "platform": _compare_platform(left.source_kind, right.source_kind),
        "platform_job_id": _compare_exact(left.platform_job_id, right.platform_job_id),
        "canonical_url": _compare_url(left.canonical_url, right.canonical_url),
        "source_url": _compare_url(left.source_url, right.source_url),
        "company": _compare_values(
            normalise_company(left.company), normalise_company(right.company)
        ),
        "title": _compare_values(
            normalise_title(left.title), normalise_title(right.title)
        ),
        "location": _compare_locations(left.location_text, right.location_text),
        "content_fingerprint": _compare_exact(
            left.content_fingerprint, right.content_fingerprint
        ),
    }

    for signal in EVIDENCE_SIGNALS:
        verdict = verdicts[signal]
        if verdict is None:
            unknown.append(signal)
        elif verdict:
            matching.append(signal)
        else:
            differing.append(signal)

    return EvidenceComparison(
        matching=tuple(matching),
        differing=tuple(differing),
        unknown=tuple(unknown),
    )


def _compare_platform(left: str, right: str) -> bool | None:
    if left not in _IDENTIFYING_PLATFORMS or right not in _IDENTIFYING_PLATFORMS:
        # manual / import / other say nothing about where the advert came from.
        return None
    return left == right


def _compare_exact(left: str | None, right: str | None) -> bool | None:
    if left is None or right is None:
        return None
    return left == right


def _compare_values(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    return left == right


def _compare_url(left: object, right: object) -> bool | None:
    normalised_left = normalise_url(None if left is None else str(left))
    normalised_right = normalise_url(None if right is None else str(right))
    if normalised_left is None or normalised_right is None:
        return None
    return normalised_left == normalised_right


def _compare_locations(left: str | None, right: str | None) -> bool | None:
    left_tokens = location_tokens(left)
    right_tokens = location_tokens(right)
    if not left_tokens or not right_tokens:
        return None
    return left_tokens <= right_tokens or right_tokens <= left_tokens


def _tokens(value: str | None) -> list[str]:
    if value is None:
        return []
    lowered = value.strip().lower()
    if not lowered:
        return []
    return [token for token in _NON_ALNUM.split(lowered) if token]
