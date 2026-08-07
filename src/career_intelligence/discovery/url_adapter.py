"""URL acquisition adapter (FR-018 M2).

Fetches one owner-supplied supported job URL and returns FR-008 AcquisitionResult.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import AnyHttpUrl, ValidationError

from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.orchestration.acquisition import (
    AcquisitionAdapter,
    AcquisitionError,
    AcquisitionResult,
)
from career_intelligence.orchestration.state_helpers import utc_now
from career_intelligence.orchestration.types import AcquisitionSourceKind

from .extract import extract_job_content_from_html
from .http import FakeHttpClient, HttpFetchClient, HttpFetchError, UrllibHttpClient
from .url_support import classify_supported_job_url, strip_tracking_query


@dataclass
class UrlAcquisitionAdapter:
    """Acquire a single supported job-board URL via injectable HTTP client."""

    url: str
    client: HttpFetchClient | None = None
    timeout_seconds: float = 20.0
    """Optional fixture marker appended to raw_text for offline FixtureExtractor."""
    offline_fixture_marker: str | None = None

    @property
    def source_kind(self) -> AcquisitionSourceKind:
        return "url"

    def acquire(self) -> AcquisitionResult:
        try:
            ref = classify_supported_job_url(self.url)
        except Exception as exc:
            raise AcquisitionError(
                "URL is invalid or unsupported for acquisition",
                detail=str(exc),
            ) from exc

        fetch_url = strip_tracking_query(ref.original_url)
        client = self.client or UrllibHttpClient()
        try:
            response = client.get(fetch_url, timeout_seconds=self.timeout_seconds)
        except HttpFetchError as exc:
            detail = exc.detail or str(exc)
            if exc.kind == "http_error" and exc.status_code is not None:
                detail = f"HTTP {exc.status_code}: {detail}"
            raise AcquisitionError(
                f"Failed to fetch job URL ({exc.kind})",
                detail=detail,
            ) from exc

        try:
            html = response.body.decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            raise AcquisitionError(
                "Failed to decode HTML body as text",
                detail=str(exc),
            ) from exc

        # Detect anti-bot / empty / non-job landings via extractor.
        try:
            extracted = extract_job_content_from_html(
                html,
                platform=ref.platform,
                final_url=response.url,
            )
        except Exception as exc:
            detail = getattr(exc, "detail", None) or str(exc)
            raise AcquisitionError(
                "Failed to extract job advertisement content from HTML",
                detail=detail,
            ) from exc

        raw = extracted.raw_text
        warnings = list(extracted.warnings)
        if response.url and response.url.rstrip("/") != fetch_url.rstrip("/"):
            warnings.append(f"fetch redirected to {response.url}")
        if self.offline_fixture_marker:
            if self.offline_fixture_marker not in raw:
                raw = f"{self.offline_fixture_marker}\n{raw}"
            warnings.append("offline fixture marker injected for deterministic analysis")

        if response.status_code >= 400:
            raise AcquisitionError(
                f"HTTP {response.status_code} for job URL",
                detail=fetch_url,
            )

        provenance_url = ref.canonical_url
        try:
            posting = JobPosting.model_validate(
                {
                    "raw_text": raw,
                    "title": extracted.title,
                    "company": extracted.company,
                    "source_url": provenance_url,
                }
            )
        except ValidationError as exc:
            raise AcquisitionError(
                "Failed to build JobPosting from extracted content",
                detail=str(exc),
            ) from exc

        source_url: AnyHttpUrl | None = posting.source_url
        return AcquisitionResult(
            source_kind="url",
            source_identifier=ref.source_identifier,
            source_url=source_url,
            raw_content=raw,
            posting=posting,
            title=posting.title,
            company=posting.company,
            warnings=warnings,
            acquired_at=utc_now(),
        )


@dataclass(frozen=True)
class StaticAcquisitionAdapter:
    """Replay a completed AcquisitionResult (avoids double-fetch in ingress)."""

    result: AcquisitionResult

    @property
    def source_kind(self) -> AcquisitionSourceKind:
        return self.result.source_kind

    def acquire(self) -> AcquisitionResult:
        return self.result


def build_url_adapter(
    url: str,
    *,
    client: HttpFetchClient | None = None,
    offline_fixture_marker: str | None = None,
) -> AcquisitionAdapter:
    return UrlAcquisitionAdapter(
        url=url,
        client=client,
        offline_fixture_marker=offline_fixture_marker,
    )


# Re-export for tests / wiring convenience
__all__ = [
    "FakeHttpClient",
    "StaticAcquisitionAdapter",
    "UrlAcquisitionAdapter",
    "UrllibHttpClient",
    "build_url_adapter",
]
