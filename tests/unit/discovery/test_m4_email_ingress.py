"""FR-018 M4 — email job-alert acquisition tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.discovery import (
    DiscoveryProvenanceError,
    DiscoveryRequest,
    DiscoveryUnsupportedSourceError,
    DiscoveryValidationError,
    EmailAcquisitionAdapter,
    ThinDiscoveryIngress,
    assert_email_acquisition_provenance,
    classify_job_alert_sender,
    email_locator,
    opportunity_source_from_url,
    opportunity_sources_from_email_file,
    parse_job_alert_email,
)
from career_intelligence.job_analysis.fixtures import MARKER_AI_ENGINEER
from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.orchestration.acquisition import AcquisitionResult
from tests.unit.orchestration.m1_helpers import offline_runner

FIXTURES = Path(__file__).parents[2] / "fixtures" / "discovery"


def test_classify_sender() -> None:
    assert classify_job_alert_sender("jobmail@seek.com.au") == "seek"
    assert classify_job_alert_sender("jobs-listings@linkedin.com") == "linkedin"
    assert classify_job_alert_sender("alert@indeed.com") == "indeed"
    assert classify_job_alert_sender("boss@recruiter.example") is None


def test_parse_seek_digest() -> None:
    parsed = parse_job_alert_email(FIXTURES / "seek_job_alert.eml")
    assert parsed.platform == "seek"
    assert len(parsed.jobs) == 2
    assert parsed.jobs[0].job_url.endswith("/job/93312273")
    assert parsed.jobs[0].title == "AI Engineer"


def test_parse_linkedin_and_indeed() -> None:
    li = parse_job_alert_email(FIXTURES / "linkedin_job_alert.eml")
    assert li.platform == "linkedin" and len(li.jobs) == 1
    ind = parse_job_alert_email(FIXTURES / "indeed_job_alert.eml")
    assert ind.platform == "indeed" and "jk=" in ind.jobs[0].job_url


def test_parse_linkedin_comm_jobs_view_alert() -> None:
    """Live LinkedIn digests use /comm/jobs/view/<id>/ — must normalise to /jobs/view/<id>."""
    parsed = parse_job_alert_email(FIXTURES / "linkedin_job_alert_comm.eml")
    assert parsed.platform == "linkedin"
    urls = {job.job_url for job in parsed.jobs}
    assert "https://www.linkedin.com/jobs/view/4381552675" in urls
    assert "https://www.linkedin.com/jobs/view/4444879919" in urls
    # Legacy /jobs/view/ path still recognised in the same digest.
    assert "https://www.linkedin.com/jobs/view/4429615445" in urls
    assert all("/comm/" not in url for url in urls)
    by_url = {job.job_url: job for job in parsed.jobs}
    assert by_url["https://www.linkedin.com/jobs/view/4381552675"].title == (
        "AI Software Engineer (Back End)"
    )
    assert by_url["https://www.linkedin.com/jobs/view/4381552675"].company == "Maincode"
    assert by_url["https://www.linkedin.com/jobs/view/4444879919"].company == "pay.com.au"


def test_normalise_linkedin_comm_href() -> None:
    from career_intelligence.discovery.email_parse import _normalise_job_url

    assert (
        _normalise_job_url(
            "linkedin",
            "https://www.linkedin.com/comm/jobs/view/4381552675/?trackingId=abc",
        )
        == "https://www.linkedin.com/jobs/view/4381552675"
    )
    assert (
        _normalise_job_url(
            "linkedin",
            "https://www.linkedin.com/jobs/view/4429615445",
        )
        == "https://www.linkedin.com/jobs/view/4429615445"
    )


def test_unsupported_sender_fail_closed() -> None:
    with pytest.raises(DiscoveryUnsupportedSourceError):
        parse_job_alert_email(FIXTURES / "unsupported_newsletter.eml")


def test_supported_sender_without_jobs_fail_closed() -> None:
    with pytest.raises(DiscoveryUnsupportedSourceError):
        parse_job_alert_email(FIXTURES / "malformed_seek_no_jobs.eml")


def test_email_adapter_acquire_and_provenance() -> None:
    locator = email_locator(FIXTURES / "seek_job_alert.eml", 0)
    result = EmailAcquisitionAdapter(
        locator=locator,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    ).acquire()
    assert_email_acquisition_provenance(result)
    assert result.source_kind == "email"
    assert result.source_url is not None
    assert "93312273" in str(result.source_url)
    assert MARKER_AI_ENGINEER in result.raw_content
    assert "email_message_id=" in " ".join(result.warnings)
    # Offline marker must skip live URL enrichment.
    assert not any("enriched_from_job_url" in w for w in result.warnings)


def test_email_adapter_enriches_from_job_url() -> None:
    """Email card text is insufficient; URL body enrichment supplies the JD."""
    from career_intelligence.discovery import FakeHttpClient, HttpFetchResponse

    locator = email_locator(FIXTURES / "linkedin_job_alert_comm.eml", 0)
    job_url = "https://www.linkedin.com/jobs/view/4381552675"
    html = """
    <html><head><title>AI Software Engineer (Back End)</title>
    <meta property="og:title" content="AI Software Engineer (Back End)" /></head>
    <body>
    <div class="description__text show-more-less-html">
    <p>About The Role</p>
    <p>Maincode is training Matilda, a large language model built in Australia.</p>
    <p>Responsibilities include building backend APIs, infrastructure, and reliability.</p>
    <p>Requirements: Python, distributed systems, cloud deployment, and LLM serving.</p>
    <p>Location: Melbourne, VIC. Full-time.</p>
    </div>
    </body></html>
    """
    client = FakeHttpClient(
        responses={
            job_url: HttpFetchResponse(
                url=job_url,
                status_code=200,
                body=html.encode("utf-8"),
                content_type="text/html",
            )
        },
        calls=[],
    )
    result = EmailAcquisitionAdapter(
        locator=locator,
        http_client=client,
    ).acquire()
    assert_email_acquisition_provenance(result)
    assert result.source_kind == "email"
    assert result.title == "AI Software Engineer (Back End)"
    assert result.company == "Maincode"
    assert "enriched_from_job_url" in " ".join(result.warnings)
    assert "Responsibilities include building backend APIs" in result.raw_content
    assert len(result.raw_content) > 200


def test_email_adapter_enrichment_fail_soft() -> None:
    """URL enrich failure must not abort email acquisition."""
    from career_intelligence.discovery import FakeHttpClient, HttpFetchResponse

    locator = email_locator(FIXTURES / "linkedin_job_alert_comm.eml", 0)
    job_url = "https://www.linkedin.com/jobs/view/4381552675"
    client = FakeHttpClient(
        responses={
            job_url: HttpFetchResponse(
                url=job_url,
                status_code=403,
                body=b"blocked",
                content_type="text/html",
            )
        },
        calls=[],
    )
    result = EmailAcquisitionAdapter(
        locator=locator,
        http_client=client,
    ).acquire()
    assert result.source_kind == "email"
    assert any("job_url_enrichment_failed" in w for w in result.warnings)
    assert result.title == "AI Software Engineer (Back End)"
    assert len(result.raw_content) < 800


def test_email_provenance_rejects_url_kind() -> None:
    result = AcquisitionResult(
        source_kind="url",
        raw_content="x" * 100,
        posting=JobPosting(raw_text="x" * 100),
        source_identifier="https://www.seek.com.au/job/1",
        source_url="https://www.seek.com.au/job/1",
    )
    with pytest.raises(DiscoveryProvenanceError):
        assert_email_acquisition_provenance(result)


def test_expand_sources_from_file() -> None:
    sources = opportunity_sources_from_email_file(FIXTURES / "seek_job_alert.eml")
    assert len(sources) == 2
    assert all(s.source_kind == "email" for s in sources)
    assert sources[0].locator.endswith("#job=0")
    assert sources[1].locator.endswith("#job=1")


def test_ingress_email_acquire_and_duplicate_skip(tmp_path: Path) -> None:
    sources = opportunity_sources_from_email_file(FIXTURES / "linkedin_job_alert.eml")
    assert len(sources) == 1

    def factory():
        return offline_runner(opportunities_dir=tmp_path / "opps")

    from career_intelligence.opportunities import OpportunityService

    service = OpportunityService.from_path(tmp_path / "opps")
    ingress = ThinDiscoveryIngress(
        opportunities=service,
        runner_factory=factory,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    first = ingress.discover(DiscoveryRequest(sources=sources))
    assert first.items[0].status == "acquired"
    assert first.items[0].opportunity_id

    second = ingress.discover(DiscoveryRequest(sources=sources))
    assert second.items[0].status == "skipped"
    assert second.items[0].matched_opportunity_id == first.items[0].opportunity_id


def test_ingress_seek_digest_two_jobs(tmp_path: Path) -> None:
    sources = opportunity_sources_from_email_file(FIXTURES / "seek_job_alert.eml")

    def factory():
        return offline_runner(opportunities_dir=tmp_path / "opps")

    from career_intelligence.opportunities import OpportunityService

    ingress = ThinDiscoveryIngress(
        opportunities=OpportunityService.from_path(tmp_path / "opps"),
        runner_factory=factory,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    outcome = ingress.discover(DiscoveryRequest(sources=sources))
    assert outcome.acquired_count == 2
    assert outcome.failed_count == 0


def test_url_path_still_works_alongside_email_contracts(tmp_path: Path) -> None:
    """Regression: URL discover contracts unchanged."""
    source = opportunity_source_from_url("https://www.seek.com.au/job/12345678")
    assert source.source_kind == "url"
    from career_intelligence.discovery import FakeHttpClient, HttpFetchResponse

    client = FakeHttpClient(
        responses={
            "https://www.seek.com.au/job/12345678": HttpFetchResponse(
                url="https://www.seek.com.au/job/12345678",
                status_code=200,
                body=(FIXTURES / "seek_ai_engineer.html").read_bytes(),
                content_type="text/html",
            )
        },
        calls=[],
    )

    def factory():
        return offline_runner(opportunities_dir=tmp_path / "opps")

    from career_intelligence.opportunities import OpportunityService

    ingress = ThinDiscoveryIngress(
        opportunities=OpportunityService.from_path(tmp_path / "opps"),
        runner_factory=factory,
        http_client=client,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    item = ingress.discover(DiscoveryRequest(sources=[source])).items[0]
    assert item.status == "acquired"


def test_missing_eml_file() -> None:
    with pytest.raises(DiscoveryValidationError):
        parse_job_alert_email(FIXTURES / "does_not_exist.eml")


LIVE_LINKEDIN_EML = Path(__file__).parents[3] / "linkedin_alert.eml"


@pytest.mark.skipif(
    not LIVE_LINKEDIN_EML.is_file(),
    reason="Owner live LinkedIn digest linkedin_alert.eml not present",
)
def test_live_linkedin_eml_parses_cards_and_creates_opportunity(tmp_path: Path) -> None:
    """Regression: live LinkedIn .eml must yield titled cards and persist via runner."""
    parsed = parse_job_alert_email(LIVE_LINKEDIN_EML)
    assert parsed.platform == "linkedin"
    assert len(parsed.jobs) >= 1
    assert all(job.title for job in parsed.jobs)
    assert all(job.company for job in parsed.jobs)
    assert all("/comm/" not in job.job_url for job in parsed.jobs)

    sources = opportunity_sources_from_email_file(LIVE_LINKEDIN_EML)
    # One job is enough to prove Opportunity allocation; full digest is slow offline.
    sources = sources[:1]

    def factory():
        return offline_runner(opportunities_dir=tmp_path / "opps")

    from career_intelligence.opportunities import OpportunityService

    ingress = ThinDiscoveryIngress(
        opportunities=OpportunityService.from_path(tmp_path / "opps"),
        runner_factory=factory,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    item = ingress.discover(DiscoveryRequest(sources=sources)).items[0]
    assert item.status == "acquired"
    assert item.opportunity_id is not None


def test_ingress_surfaces_runner_last_error_when_no_opportunity_id(
    tmp_path: Path,
) -> None:
    """Analyse/assess failure must not be masked as missing opportunity_id."""
    from career_intelligence.orchestration.models import WorkflowErrorInfo
    from tests.unit.orchestration.helpers import make_control, make_state, now

    class _FailingRunner:
        def start(self, _adapter):  # noqa: ANN001
            return make_state(
                control=make_control(
                    status="failed",
                    completed_at=now(),
                    last_error=WorkflowErrorInfo(
                        message="Opportunity assessment validation failed",
                        recoverable=True,
                        node_id="assess",
                    ),
                )
            )

    sources = opportunity_sources_from_email_file(FIXTURES / "linkedin_job_alert.eml")
    from career_intelligence.opportunities import OpportunityService

    ingress = ThinDiscoveryIngress(
        opportunities=OpportunityService.from_path(tmp_path / "opps"),
        runner_factory=lambda: _FailingRunner(),  # type: ignore[return-value, arg-type]
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    item = ingress.discover(DiscoveryRequest(sources=sources)).items[0]
    assert item.status == "failed"
    assert item.failure_kind == "runner_failure"
    assert "assessment validation failed" in (item.message or "").lower()
    assert "without allocating opportunity_id" not in (item.message or "").lower()
