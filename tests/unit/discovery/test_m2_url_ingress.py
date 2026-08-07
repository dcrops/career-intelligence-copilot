"""FR-018 M2 unit tests — URL acquisition, idempotency, thin ingress."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from career_intelligence.discovery import (
    DiscoveryRequest,
    FakeHttpClient,
    HttpFetchError,
    HttpFetchResponse,
    ThinDiscoveryIngress,
    UrlAcquisitionAdapter,
    assert_url_acquisition_provenance,
    classify_supported_job_url,
    find_definite_match,
    identity_probe_from_posting,
    identity_probe_from_url,
    opportunity_source_from_url,
)
from career_intelligence.discovery.extract import extract_job_content_from_html
from career_intelligence.job_analysis.fixtures import MARKER_AI_ENGINEER
from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.opportunities.identity import build_identity
from career_intelligence.opportunities.models import Opportunity, OpportunityIdentity
from career_intelligence.orchestration.acquisition import AcquisitionResult
from tests.unit.orchestration.m1_helpers import offline_runner

FIXTURES = Path(__file__).parents[2] / "fixtures" / "discovery"
SEEK_URL = "https://www.seek.com.au/job/12345678"
SEEK_URL_TRACKED = "https://www.seek.com.au/job/12345678?utm_source=email&utm_medium=alert"
LINKEDIN_URL = "https://www.linkedin.com/jobs/view/9876543210"
INDEED_URL = "https://www.indeed.com/viewjob?jk=abcdef0123456789"
UNSUPPORTED_URL = "https://example.com/careers/ai-engineer"


def _html(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fake_ok(url: str, fixture: str) -> FakeHttpClient:
    return FakeHttpClient(
        responses={
            url: HttpFetchResponse(
                url=url,
                status_code=200,
                body=_html(fixture),
                content_type="text/html",
            )
        },
        calls=[],
    )


def test_classify_seek_ok() -> None:
    ref = classify_supported_job_url(SEEK_URL)
    assert ref.platform == "seek"
    assert ref.platform_job_id == "12345678"
    assert "/job/12345678" in ref.canonical_url


def test_classify_linkedin_and_indeed() -> None:
    assert classify_supported_job_url(LINKEDIN_URL).platform == "linkedin"
    assert classify_supported_job_url(INDEED_URL).platform == "indeed"


def test_classify_unsupported() -> None:
    from career_intelligence.discovery import DiscoveryUnsupportedSourceError

    with pytest.raises(DiscoveryUnsupportedSourceError):
        classify_supported_job_url(UNSUPPORTED_URL)


def test_url_adapter_seek_success() -> None:
    client = _fake_ok(SEEK_URL, "seek_ai_engineer.html")
    adapter = UrlAcquisitionAdapter(
        url=SEEK_URL,
        client=client,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    result = adapter.acquire()
    assert_url_acquisition_provenance(result)
    assert result.source_kind == "url"
    assert MARKER_AI_ENGINEER in result.raw_content
    assert "AI Engineer" in (result.title or "")
    assert client.calls == [SEEK_URL]


def test_url_adapter_strips_tracking_on_fetch() -> None:
    # Fetch uses strip_tracking_query — configure fake for cleaned URL.
    cleaned = "https://www.seek.com.au/job/12345678"
    client = FakeHttpClient(
        responses={
            cleaned: HttpFetchResponse(
                url=cleaned,
                status_code=200,
                body=_html("seek_ai_engineer.html"),
            )
        },
        calls=[],
    )
    result = UrlAcquisitionAdapter(url=SEEK_URL_TRACKED, client=client).acquire()
    assert result.source_identifier.endswith("/job/12345678")
    assert client.calls == [cleaned]


def test_url_adapter_timeout() -> None:
    from career_intelligence.orchestration.acquisition import AcquisitionError

    client = FakeHttpClient(
        responses={SEEK_URL: HttpFetchError("slow", kind="timeout")},
    )
    with pytest.raises(AcquisitionError, match="timeout"):
        UrlAcquisitionAdapter(url=SEEK_URL, client=client).acquire()


def test_url_adapter_http_error() -> None:
    from career_intelligence.orchestration.acquisition import AcquisitionError

    client = FakeHttpClient(
        responses={
            SEEK_URL: HttpFetchError("nope", kind="http_error", status_code=403)
        },
    )
    with pytest.raises(AcquisitionError):
        UrlAcquisitionAdapter(url=SEEK_URL, client=client).acquire()


def test_url_adapter_insufficient_content() -> None:
    from career_intelligence.orchestration.acquisition import AcquisitionError

    client = FakeHttpClient(
        responses={
            SEEK_URL: HttpFetchResponse(
                url=SEEK_URL,
                status_code=200,
                body=b"<html><body>short</body></html>",
            )
        }
    )
    with pytest.raises(AcquisitionError, match="extract"):
        UrlAcquisitionAdapter(url=SEEK_URL, client=client).acquire()


def test_blocked_page_fails() -> None:
    with pytest.raises(Exception, match="blocked|login"):
        extract_job_content_from_html(
            (FIXTURES / "linkedin_blocked.html").read_text(encoding="utf-8"),
            platform="linkedin",
        )


def test_provenance_failure_on_paste_kind() -> None:
    from career_intelligence.discovery import DiscoveryProvenanceError

    result = AcquisitionResult(
        source_kind="paste",
        raw_content="x" * 100,
        posting=JobPosting(raw_text="x" * 100),
    )
    with pytest.raises(DiscoveryProvenanceError):
        assert_url_acquisition_provenance(result)


def test_identity_probe_and_definite_skip(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from career_intelligence.opportunities import OpportunityService

    service = OpportunityService.from_path(tmp_path / "opps")
    # Seed via offline runner + paste with SEEK URL.
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    from career_intelligence.orchestration import PasteJobInput

    state = runner.start(
        PasteJobInput(
            raw_text=f"{MARKER_AI_ENGINEER}\nSeed posting for definite match.",
            title="AI Engineer",
            company="Example",
            source_url=SEEK_URL,
        )
    )
    assert state.artefacts.opportunity_id

    probe = identity_probe_from_url(SEEK_URL)
    assert probe is not None
    match = find_definite_match(probe, service.list_opportunities())
    assert match is not None
    assert match.opportunity_id == state.artefacts.opportunity_id


def test_fingerprint_only_does_not_definite_skip() -> None:
    from datetime import UTC, datetime

    left = OpportunityIdentity(
        opportunity_id="opp_01ARZ3NDEKTSV4RRFFQ69G5FAA",
        created_at=datetime.now(UTC),
        source_kind="manual",
        content_fingerprint="abc",
    )
    right_posting = JobPosting(raw_text="unrelated text for fingerprint test " * 5)
    # Force same fingerprint artificially
    probe = build_identity(right_posting, opportunity_id="opp_01ARZ3NDEKTSV4RRFFQ69G5FAB")
    probe = probe.model_copy(update={"content_fingerprint": "abc", "source_kind": "manual"})
    existing = Opportunity.model_construct(  # type: ignore[call-arg]
        identity=left,
        opportunity_id=left.opportunity_id,
    )
    # Opportunity.model_construct may be incomplete — use classify via find with fake list
    # Build minimal Opportunity through service is heavy; test classify_pair path:
    from career_intelligence.duplicates.detection import classify_pair
    from career_intelligence.duplicates.evidence import compare_identities

    confidence, _ = classify_pair(compare_identities(left, probe))
    assert confidence != "definite"
    assert confidence in {"possible", None} or confidence == "possible"


def test_ingress_acquires_once(tmp_path: Path) -> None:
    client = _fake_ok(SEEK_URL, "seek_ai_engineer.html")
    calls_before = list(client.calls or [])

    def factory():
        return offline_runner(opportunities_dir=tmp_path / "opps")

    from career_intelligence.opportunities import OpportunityService

    ingress = ThinDiscoveryIngress(
        opportunities=OpportunityService.from_path(tmp_path / "opps"),
        runner_factory=factory,
        http_client=client,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    source = opportunity_source_from_url(SEEK_URL)
    outcome = ingress.discover(DiscoveryRequest(sources=[source]))
    item = outcome.items[0]
    assert item.status == "acquired"
    assert item.opportunity_id
    assert item.workflow_run_id
    # One HTTP get for acquire; StaticAcquisitionAdapter avoids second fetch in runner.
    assert len(client.calls or []) == len(calls_before) + 1


def test_ingress_skips_duplicate(tmp_path: Path) -> None:
    client = _fake_ok(SEEK_URL, "seek_ai_engineer.html")

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
    second = ingress.discover(DiscoveryRequest(sources=[source]))
    assert second.items[0].status == "skipped"
    assert second.items[0].matched_opportunity_id == first.items[0].opportunity_id


def test_ingress_unsupported(tmp_path: Path) -> None:
    from career_intelligence.opportunities import OpportunityService

    ingress = ThinDiscoveryIngress(
        opportunities=OpportunityService.from_path(tmp_path / "opps"),
        runner_factory=lambda: offline_runner(opportunities_dir=tmp_path / "opps"),
    )
    source = opportunity_source_from_url(UNSUPPORTED_URL)
    item = ingress.discover(DiscoveryRequest(sources=[source])).items[0]
    assert item.status == "failed"
    assert item.failure_kind == "unsupported_source"


def test_ingress_runner_failure_surfaces(tmp_path: Path) -> None:
    client = _fake_ok(SEEK_URL, "seek_ai_engineer.html")

    def boom():
        raise RuntimeError("runner exploded")

    from career_intelligence.opportunities import OpportunityService

    ingress = ThinDiscoveryIngress(
        opportunities=OpportunityService.from_path(tmp_path / "opps"),
        runner_factory=boom,
        http_client=client,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    item = ingress.discover(
        DiscoveryRequest(sources=[opportunity_source_from_url(SEEK_URL)])
    ).items[0]
    assert item.status == "failed"
    assert item.failure_kind == "runner_failure"


def test_no_discovery_catalogue_writes(tmp_path: Path) -> None:
    """Ingress must not create files outside Opportunity / workflow stores."""
    opps = tmp_path / "opps"
    client = _fake_ok(SEEK_URL, "seek_ai_engineer.html")

    def factory():
        return offline_runner(opportunities_dir=opps)

    from career_intelligence.opportunities import OpportunityService

    ingress = ThinDiscoveryIngress(
        opportunities=OpportunityService.from_path(opps),
        runner_factory=factory,
        http_client=client,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    ingress.discover(DiscoveryRequest(sources=[opportunity_source_from_url(SEEK_URL)]))
    # Only opportunity YAML under opps — no discovery/ sibling catalogue.
    assert not (tmp_path / "discovery").exists()
    assert any(opps.glob("*.yaml")) or any(opps.rglob("*.yaml"))
