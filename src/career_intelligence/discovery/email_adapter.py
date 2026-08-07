"""Email job-alert acquisition adapter (FR-018 M4).

Reads one job from an owner-supplied ``.eml`` digest and returns FR-008
``AcquisitionResult`` with ``source_kind="email"``.

When a job URL is present and offline fixtures are not in use, optionally
enriches ``raw_content`` via the existing URL adapter (fail-soft: email card
text remains if fetch/extract fails). Provenance stays email (Message-ID#job).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import AnyHttpUrl, ValidationError

from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.orchestration.acquisition import (
    AcquisitionError,
    AcquisitionResult,
)
from career_intelligence.orchestration.state_helpers import utc_now
from career_intelligence.orchestration.types import AcquisitionSourceKind

from .email_parse import parse_email_locator, parse_job_alert_email
from .errors import DiscoveryUnsupportedSourceError, DiscoveryValidationError
from .http import HttpFetchClient


# Prefer URL body when it clearly exceeds alert-card text, or when the email
# body looks like a card and the URL body carries job-description signals.
_ENRICH_MIN_GAIN_CHARS = 200
_JD_SIGNALS = (
    "responsibilities",
    "requirements",
    "about the role",
    "about us",
    "qualifications",
    "what you'll",
    "what you will",
    "you will",
    "we are looking",
)


def _has_jd_signals(text: str) -> bool:
    lower = text.lower()
    return any(signal in lower for signal in _JD_SIGNALS)


def _should_prefer_url_body(*, email_raw: str, url_raw: str) -> bool:
    if len(url_raw) >= len(email_raw) + _ENRICH_MIN_GAIN_CHARS:
        return True
    if not _has_jd_signals(email_raw) and _has_jd_signals(url_raw):
        return True
    return False


@dataclass
class EmailAcquisitionAdapter:
    """Acquire one job from a job-alert ``.eml`` (locator path#job=N)."""

    locator: str
    """``/path/to/alert.eml#job=0`` style locator."""
    offline_fixture_marker: str | None = None
    http_client: HttpFetchClient | None = None
    """Optional client for job-URL enrichment (defaults inside UrlAcquisitionAdapter)."""
    enrich_from_job_url: bool = True
    """When True and not offline, attempt URL body enrichment after email parse."""

    @property
    def source_kind(self) -> AcquisitionSourceKind:
        return "email"

    def acquire(self) -> AcquisitionResult:
        try:
            path, index = parse_email_locator(self.locator)
            parsed = parse_job_alert_email(path)
        except DiscoveryValidationError as exc:
            raise AcquisitionError(
                "Invalid email acquisition locator or MIME",
                detail=str(exc),
            ) from exc
        except DiscoveryUnsupportedSourceError as exc:
            raise AcquisitionError(
                "Unsupported job-alert email",
                detail=str(exc),
            ) from exc

        if index >= len(parsed.jobs):
            raise AcquisitionError(
                "Email job index out of range",
                detail=f"index={index} jobs={len(parsed.jobs)}",
            )

        job = parsed.jobs[index]
        raw = job.snippet
        title = job.title
        company = job.company
        warnings: list[str] = [
            f"acquired from job-alert email ({parsed.platform})",
            f"email_message_id={parsed.message_id}",
            f"email_from={parsed.from_addr}",
            f"email_path={parsed.path}",
        ]

        if (
            self.enrich_from_job_url
            and self.offline_fixture_marker is None
            and job.job_url
        ):
            raw, title, company, enrich_warnings = _try_enrich_from_job_url(
                job_url=job.job_url,
                email_raw=raw,
                email_title=title,
                email_company=company,
                http_client=self.http_client,
            )
            warnings.extend(enrich_warnings)

        if self.offline_fixture_marker:
            if self.offline_fixture_marker not in raw:
                raw = f"{self.offline_fixture_marker}\n{raw}"
            warnings.append("offline fixture marker injected for deterministic analysis")

        try:
            posting = JobPosting.model_validate(
                {
                    "raw_text": raw,
                    "title": title,
                    "company": company,
                    "source_url": job.job_url,
                }
            )
        except ValidationError as exc:
            raise AcquisitionError(
                "Failed to build JobPosting from email job alert",
                detail=str(exc),
            ) from exc

        source_identifier = f"{parsed.message_id}#job={index}"
        source_url: AnyHttpUrl | None = posting.source_url
        return AcquisitionResult(
            source_kind="email",
            source_identifier=source_identifier,
            source_url=source_url,
            raw_content=raw,
            posting=posting,
            title=posting.title,
            company=posting.company,
            warnings=warnings,
            acquired_at=utc_now(),
        )


def _try_enrich_from_job_url(
    *,
    job_url: str,
    email_raw: str,
    email_title: str | None,
    email_company: str | None,
    http_client: HttpFetchClient | None,
) -> tuple[str, str | None, str | None, list[str]]:
    """Fetch job URL body; fail-soft back to email card text."""
    from .url_adapter import UrlAcquisitionAdapter

    warnings: list[str] = []
    try:
        url_result = UrlAcquisitionAdapter(
            url=job_url,
            client=http_client,
        ).acquire()
    except AcquisitionError as exc:
        warnings.append(
            f"job_url_enrichment_failed: {exc}"
            + (f" ({exc.detail})" if exc.detail else "")
        )
        return email_raw, email_title, email_company, warnings
    except Exception as exc:  # noqa: BLE001 — never fail email acquire on enrich
        warnings.append(f"job_url_enrichment_failed: {type(exc).__name__}: {exc}")
        return email_raw, email_title, email_company, warnings

    enriched = url_result.raw_content
    if not _should_prefer_url_body(email_raw=email_raw, url_raw=enriched):
        warnings.append(
            "job_url_enrichment_skipped: fetched body not preferred over email card "
            f"(email={len(email_raw)} url={len(enriched)})"
        )
        return email_raw, email_title, email_company, warnings
    warnings.append("enriched_from_job_url")
    warnings.append(f"job_url_enrichment_raw_len={len(enriched)}")
    for w in url_result.warnings:
        warnings.append(f"url_fetch: {w}")

    # Prefer email card title/company (clean); URL titles are often
    # "Company hiring Role in City | LinkedIn".
    title = email_title or url_result.title
    company = email_company or url_result.company
    return enriched, title, company, warnings


def expand_email_file_to_locators(path: Path | str) -> list[str]:
    """Parse digest and return one locator per job (for CLI / request expansion)."""
    from .email_parse import email_locator

    parsed = parse_job_alert_email(path)
    return [email_locator(parsed.path, job.index) for job in parsed.jobs]
