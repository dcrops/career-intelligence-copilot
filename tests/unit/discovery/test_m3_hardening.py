"""FR-018 M3 — SEEK hardening, SSL context, LinkedIn/Indeed fail-closed gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.discovery import (
    DiscoveryRequest,
    FakeHttpClient,
    HttpFetchError,
    HttpFetchResponse,
    ThinDiscoveryIngress,
    UrlAcquisitionAdapter,
    build_default_ssl_context,
    classify_supported_job_url,
    opportunity_source_from_url,
)
from career_intelligence.discovery.extract import extract_job_content_from_html
from career_intelligence.discovery.http import UrllibHttpClient
from career_intelligence.job_analysis.fixtures import MARKER_AI_ENGINEER
from career_intelligence.opportunities.identity import derive_source_facets
from tests.unit.orchestration.m1_helpers import offline_runner

FIXTURES = Path(__file__).parents[2] / "fixtures" / "discovery"
SEEK_URL = "https://www.seek.com.au/job/12345678"
SEEK_AU_HOST = "https://au.seek.com/job/12345678"
LINKEDIN_SLUG = (
    "https://au.linkedin.com/jobs/view/senior-ai-engineer-at-fyndr-group-4429615445"
)
LINKEDIN_VIEW = "https://www.linkedin.com/jobs/view/4429615445"
INDEED_URL = "https://au.indeed.com/viewjob?jk=abcdef0123456789"
UNSUPPORTED = "https://www.thoughtworks.com/careers/jobs/7920279"


def _html(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_build_default_ssl_context_verifies() -> None:
    ctx = build_default_ssl_context()
    assert ctx.check_hostname is True
    assert ctx.verify_mode.name == "CERT_REQUIRED"


def test_seek_canonical_stable_across_hosts() -> None:
    a = classify_supported_job_url(SEEK_URL)
    b = classify_supported_job_url(SEEK_AU_HOST)
    assert a.canonical_url == b.canonical_url == "https://www.seek.com.au/job/12345678"
    assert a.platform_job_id == b.platform_job_id == "12345678"


def test_linkedin_slug_classifies() -> None:
    ref = classify_supported_job_url(LINKEDIN_SLUG)
    assert ref.platform == "linkedin"
    assert ref.platform_job_id == "4429615445"
    assert ref.canonical_url == LINKEDIN_VIEW


def test_seek_title_cleaning() -> None:
    html = """<!DOCTYPE html><html><head>
    <title>AI Engineer Job in Cremorne, Melbourne VIC - SEEK</title>
    </head><body>
    <div data-automation="jobAdDetails">
    <p>We are hiring an AI Engineer to build production systems.</p>
    <p>Requirements: Python, FastAPI, cloud deployment, and LLM evaluation.</p>
    <p>Location: Melbourne VIC. Permanent full-time.</p>
    </div></body></html>"""
    extracted = extract_job_content_from_html(html, platform="seek")
    assert extracted.title == "AI Engineer"


def test_linkedin_expired_redirect_fail_closed() -> None:
    html = _html("linkedin_listing_redirect.html")
    with pytest.raises(Exception) as excinfo:
        extract_job_content_from_html(
            html.decode("utf-8"),
            platform="linkedin",
            final_url=(
                "https://www.linkedin.com/jobs/digital-project-manager-jobs"
                "?trk=expired_jd_redirect"
            ),
        )
    assert getattr(excinfo.value, "detail", "") == "blocked_response"


def test_linkedin_listing_title_fail_closed() -> None:
    html = _html("linkedin_listing_redirect.html")
    with pytest.raises(Exception) as excinfo:
        extract_job_content_from_html(
            html.decode("utf-8"),
            platform="linkedin",
            final_url="https://www.linkedin.com/jobs/view/4429615445",
        )
    assert getattr(excinfo.value, "detail", "") == "blocked_response"


def test_adapter_rejects_linkedin_redirect_body() -> None:
    client = FakeHttpClient(
        responses={
            LINKEDIN_VIEW: HttpFetchResponse(
                url=(
                    "https://www.linkedin.com/jobs/digital-project-manager-jobs"
                    "?trk=expired_jd_redirect"
                ),
                status_code=200,
                body=_html("linkedin_listing_redirect.html"),
                content_type="text/html",
            )
        },
        calls=[],
    )
    with pytest.raises(Exception) as excinfo:
        UrlAcquisitionAdapter(url=LINKEDIN_VIEW, client=client).acquire()
    assert "blocked" in str(getattr(excinfo.value, "detail", "")).lower() or "blocked" in str(
        excinfo.value
    ).lower()


def test_adapter_maps_indeed_http_403() -> None:
    client = FakeHttpClient(
        responses={
            "https://au.indeed.com/viewjob?jk=abcdef0123456789": HttpFetchError(
                "HTTP 403 fetching URL",
                kind="http_error",
                status_code=403,
                detail="Forbidden",
            )
        },
        calls=[],
    )
    with pytest.raises(Exception) as excinfo:
        UrlAcquisitionAdapter(url=INDEED_URL, client=client).acquire()
    assert "403" in str(getattr(excinfo.value, "detail", ""))


def test_unsupported_careers_still_fail_closed() -> None:
    from career_intelligence.discovery import DiscoveryUnsupportedSourceError

    with pytest.raises(DiscoveryUnsupportedSourceError):
        classify_supported_job_url(UNSUPPORTED)


def test_ingress_seek_acquire_and_duplicate_skip(tmp_path: Path) -> None:
    client = FakeHttpClient(
        responses={
            SEEK_URL: HttpFetchResponse(
                url=SEEK_URL,
                status_code=200,
                body=_html("seek_ai_engineer.html"),
                content_type="text/html",
            )
        },
        calls=[],
    )

    def factory():
        return offline_runner(opportunities_dir=tmp_path / "opps")

    from career_intelligence.opportunities import OpportunityService

    service = OpportunityService.from_path(tmp_path / "opps")
    ingress = ThinDiscoveryIngress(
        opportunities=service,
        runner_factory=factory,
        http_client=client,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    source = opportunity_source_from_url(SEEK_URL)
    first = ingress.discover(DiscoveryRequest(sources=[source]))
    assert first.items[0].status == "acquired"
    assert first.items[0].opportunity_id
    second = ingress.discover(DiscoveryRequest(sources=[source]))
    assert second.items[0].status == "skipped"
    assert second.items[0].skip_reason == "definite_identity_match"
    assert second.items[0].matched_opportunity_id == first.items[0].opportunity_id


def test_urllib_client_uses_injected_ssl_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure UrllibHttpClient passes an SSL context into urlopen (M3 TLS path)."""
    captured: dict[str, object] = {}

    class _Resp:
        status = 200
        headers = {"Content-Type": "text/html"}

        def read(self) -> bytes:
            return b"<html><body>ok enough text for nothing</body></html>"

        def geturl(self) -> str:
            return "https://example.com"

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(req: object, timeout: float = 20.0, context: object = None) -> _Resp:
        captured["context"] = context
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr(
        "career_intelligence.discovery.http.urlopen",
        fake_urlopen,
    )
    sentinel = object()
    client = UrllibHttpClient(ssl_context=sentinel)  # type: ignore[arg-type]
    result = client.get("https://example.com/job")
    assert result.status_code == 200
    assert captured["context"] is sentinel


def test_derive_facets_seek_www() -> None:
    kind, job_id, canonical = derive_source_facets("https://www.seek.com.au/job/1")
    assert (kind, job_id, canonical) == ("seek", "1", "https://www.seek.com.au/job/1")
