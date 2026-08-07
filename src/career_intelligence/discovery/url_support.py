"""Supported job-board URL classification and normalisation (FR-018 M2)."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse, urlunparse

from career_intelligence.opportunities.identity import derive_source_facets
from career_intelligence.opportunities.models import SourceKind

from .errors import DiscoveryUnsupportedSourceError, DiscoveryValidationError

# Platforms we attempt HTTP acquisition for in M2 (owner-supplied URLs only).
SUPPORTED_PLATFORMS: frozenset[SourceKind] = frozenset({"seek", "linkedin", "indeed"})


@dataclass(frozen=True)
class SupportedUrlRef:
    """Normalised owner URL for a supported board."""

    original_url: str
    canonical_url: str
    platform: SourceKind
    platform_job_id: str | None
    source_identifier: str


def classify_supported_job_url(url: str) -> SupportedUrlRef:
    """Return supported URL ref or raise unsupported / invalid.

    Does not fetch. Requires a recognisable Seek / LinkedIn / Indeed job locator
    with enough structure to form a stable identifier. Generic websites fail closed.
    """
    raw = url.strip()
    if not raw:
        raise DiscoveryValidationError("URL is empty")

    parsed = urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise DiscoveryValidationError(
            "URL must use http or https",
            detail=parsed.scheme,
        )
    if not parsed.hostname:
        raise DiscoveryValidationError("URL is missing a hostname")

    platform, platform_job_id, canonical = derive_source_facets(raw)
    if platform not in SUPPORTED_PLATFORMS:
        raise DiscoveryUnsupportedSourceError(
            "URL host is not a supported job board for URL discovery",
            detail=parsed.hostname.lower(),
        )

    if platform == "seek" and platform_job_id is None:
        raise DiscoveryUnsupportedSourceError(
            "SEEK URL must include /job/<id> for M2 acquisition",
            detail=raw,
        )
    if platform == "linkedin" and platform_job_id is None:
        raise DiscoveryUnsupportedSourceError(
            "LinkedIn URL must include /jobs/view/<id> or currentJobId for M2",
            detail=raw,
        )
    if platform == "indeed" and platform_job_id is None:
        raise DiscoveryUnsupportedSourceError(
            "Indeed URL must include jk= job key for M2 acquisition",
            detail=raw,
        )

    if not canonical:
        # Should not happen when platform_job_id is set, but fail closed.
        raise DiscoveryUnsupportedSourceError(
            "Could not derive canonical URL for supported platform",
            detail=raw,
        )

    # Stable identifier: prefer canonical; preserve original as provenance separately.
    return SupportedUrlRef(
        original_url=raw,
        canonical_url=canonical,
        platform=platform,
        platform_job_id=platform_job_id,
        source_identifier=canonical,
    )


def strip_tracking_query(url: str) -> str:
    """Drop common tracking params while keeping job-defining query keys (e.g. jk)."""
    parsed = urlparse(url.strip())
    query = parse_qs(parsed.query, keep_blank_values=False)
    keep: dict[str, list[str]] = {}
    for key, values in query.items():
        lowered = key.lower()
        if lowered in {"jk", "currentjobid"}:
            keep[key] = values
        # Drop utm_*, tracking, fbclid, etc.
    from urllib.parse import urlencode

    new_query = urlencode(keep, doseq=True)
    return urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path,
            "",
            new_query,
            "",
        )
    )
