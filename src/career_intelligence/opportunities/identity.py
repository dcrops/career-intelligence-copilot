"""Deterministic OpportunityIdentity facet derivation from JobPosting."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse, urlunparse

from career_intelligence.job_analysis.models import JobAnalysis, JobPosting

from .models import OpportunityIdentity, SourceKind
from .ulid import generate_ulid

_SEEK_JOB_PATH = re.compile(r"^/job/(\d+)/?", re.IGNORECASE)
_INDEED_JK = re.compile(r"^[a-f0-9]{16,32}$", re.IGNORECASE)


def new_opportunity_id() -> str:
    """Return a permanent ``opp_<ULID>`` identifier."""
    return f"opp_{generate_ulid()}"


def content_fingerprint(raw_text: str) -> str:
    """Stable SHA-256 of normalised posting body text."""
    normalised = "\n".join(line.rstrip() for line in raw_text.strip().splitlines())
    normalised = normalised.strip().lower()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def build_identity(
    posting: JobPosting,
    *,
    job_analysis: JobAnalysis | None = None,
    opportunity_id: str | None = None,
    created_at: datetime | None = None,
    include_fingerprint: bool = True,
) -> OpportunityIdentity:
    """Create OpportunityIdentity from posting (and optional analysis for location)."""
    source_kind, platform_job_id, canonical_url = derive_source_facets(
        str(posting.source_url) if posting.source_url is not None else None
    )
    location_text: str | None = None
    if job_analysis is not None and job_analysis.location.summary:
        location_text = job_analysis.location.summary

    fingerprint = content_fingerprint(posting.raw_text) if include_fingerprint else None

    return OpportunityIdentity(
        opportunity_id=opportunity_id or new_opportunity_id(),
        created_at=created_at or datetime.now(UTC),
        source_kind=source_kind,
        platform_job_id=platform_job_id,
        canonical_url=canonical_url,
        source_url=posting.source_url,
        company=posting.company,
        title=posting.title,
        location_text=location_text,
        content_fingerprint=fingerprint,
    )


def derive_source_facets(
    source_url: str | None,
) -> tuple[SourceKind, str | None, str | None]:
    """Return ``(source_kind, platform_job_id, canonical_url)`` without rejecting unknowns."""
    if not source_url:
        return "manual", None, None

    parsed = urlparse(source_url.strip())
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""

    if "seek.com" in host or host.endswith("seek.com.au"):
        match = _SEEK_JOB_PATH.match(path)
        if match:
            job_id = match.group(1)
            canonical = urlunparse(
                (parsed.scheme or "https", parsed.netloc, f"/job/{job_id}", "", "", "")
            )
            return "seek", job_id, canonical
        return "seek", None, _strip_query_fragment(parsed)

    if "linkedin.com" in host:
        query = parse_qs(parsed.query)
        job_ids = query.get("currentJobId") or query.get("currentjobid")
        if job_ids and job_ids[0].isdigit():
            job_id = job_ids[0]
            canonical = f"https://www.linkedin.com/jobs/view/{job_id}"
            return "linkedin", job_id, canonical
        view_match = re.search(r"/jobs/view/(\d+)", path)
        if view_match:
            job_id = view_match.group(1)
            return "linkedin", job_id, f"https://www.linkedin.com/jobs/view/{job_id}"
        return "linkedin", None, None

    if "indeed.com" in host:
        query = parse_qs(parsed.query)
        jk_values = query.get("jk")
        if jk_values and _INDEED_JK.match(jk_values[0]):
            jk = jk_values[0]
            canonical = f"https://www.indeed.com/viewjob?jk={jk}"
            return "indeed", jk, canonical
        return "indeed", None, _strip_query_fragment(parsed)

    return "other", None, _strip_query_fragment(parsed)


def _strip_query_fragment(parsed) -> str:
    return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", "", ""))
