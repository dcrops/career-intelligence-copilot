"""Unit tests for FR-018 M1 discovery contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from career_intelligence.discovery import (
    DiscoveryIngress,
    DiscoveryItemOutcome,
    DiscoveryOutcome,
    DiscoveryProvenanceError,
    DiscoveryRequest,
    DiscoveryValidationError,
    OpportunitySource,
    assert_url_acquisition_provenance,
    opportunity_source_from_url,
)
from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.orchestration.acquisition import AcquisitionResult

OPP_A = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"
OPP_B = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAB"
FIXED_AT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
SAMPLE_URL = "https://www.seek.com.au/job/12345678"


def test_opportunity_source_from_url_ok() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    assert source.source_kind == "url"
    assert str(source.locator).rstrip("/") == SAMPLE_URL
    assert source.requested_at == FIXED_AT


def test_opportunity_source_rejects_non_http_scheme() -> None:
    with pytest.raises(ValidationError):
        OpportunitySource(source_kind="url", locator="ftp://example.com/job/1")


def test_opportunity_source_from_url_invalid() -> None:
    with pytest.raises(DiscoveryValidationError):
        opportunity_source_from_url("not-a-url")


def test_discovery_request_requires_sources() -> None:
    with pytest.raises(ValidationError):
        DiscoveryRequest(sources=[])


def test_discovery_request_accepts_url_source() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    request = DiscoveryRequest(sources=[source], force=False)
    assert len(request.sources) == 1
    assert request.force is False


def test_item_outcome_acquired_requires_opportunity_id() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    with pytest.raises(ValidationError):
        DiscoveryItemOutcome(source=source, status="acquired")


def test_item_outcome_acquired_ok() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    item = DiscoveryItemOutcome(
        source=source,
        status="acquired",
        opportunity_id=OPP_A,
        workflow_run_id="run_test",
    )
    assert item.opportunity_id == OPP_A


def test_item_outcome_skipped_requires_match() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    with pytest.raises(ValidationError):
        DiscoveryItemOutcome(
            source=source,
            status="skipped",
            skip_reason="definite_identity_match",
        )


def test_item_outcome_skipped_ok() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    item = DiscoveryItemOutcome(
        source=source,
        status="skipped",
        skip_reason="definite_identity_match",
        matched_opportunity_id=OPP_B,
        message="Already persisted",
    )
    assert item.matched_opportunity_id == OPP_B


def test_item_outcome_failed_requires_kind() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    with pytest.raises(ValidationError):
        DiscoveryItemOutcome(source=source, status="failed", message="boom")


def test_item_outcome_failed_ok() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    item = DiscoveryItemOutcome(
        source=source,
        status="failed",
        failure_kind="network_failure",
        message="timeout",
    )
    assert item.failure_kind == "network_failure"


def test_discovery_outcome_counts() -> None:
    source = opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)
    outcome = DiscoveryOutcome(
        items=[
            DiscoveryItemOutcome(
                source=source,
                status="acquired",
                opportunity_id=OPP_A,
            ),
            DiscoveryItemOutcome(
                source=source,
                status="skipped",
                skip_reason="definite_identity_match",
                matched_opportunity_id=OPP_B,
            ),
            DiscoveryItemOutcome(
                source=source,
                status="failed",
                failure_kind="malformed_content",
                message="empty body",
            ),
        ]
    )
    assert outcome.acquired_count == 1
    assert outcome.skipped_count == 1
    assert outcome.failed_count == 1


def test_discovery_ingress_protocol_runtime_checkable() -> None:
    class _Stub:
        def discover(self, request: DiscoveryRequest) -> DiscoveryOutcome:
            source = request.sources[0]
            return DiscoveryOutcome(
                items=[
                    DiscoveryItemOutcome(
                        source=source,
                        status="failed",
                        failure_kind="other",
                        message="stub only",
                    )
                ]
            )

    stub = _Stub()
    assert isinstance(stub, DiscoveryIngress)
    result = stub.discover(
        DiscoveryRequest(sources=[opportunity_source_from_url(SAMPLE_URL, requested_at=FIXED_AT)])
    )
    assert result.failed_count == 1


def _posting(*, source_url: str | None = SAMPLE_URL) -> JobPosting:
    return JobPosting(
        raw_text="Senior AI Engineer\n\nBuild production systems.",
        title="Senior AI Engineer",
        company="Example",
        source_url=source_url,
    )


def test_assert_url_provenance_ok() -> None:
    result = AcquisitionResult(
        source_kind="url",
        raw_content=_posting().raw_text,
        posting=_posting(),
        source_identifier=SAMPLE_URL,
        source_url=SAMPLE_URL,
        acquired_at=FIXED_AT,
    )
    assert_url_acquisition_provenance(result)


def test_assert_url_provenance_rejects_paste_kind() -> None:
    result = AcquisitionResult(
        source_kind="paste",
        raw_content=_posting().raw_text,
        posting=_posting(source_url=None),
        acquired_at=FIXED_AT,
    )
    with pytest.raises(DiscoveryProvenanceError, match="source_kind"):
        assert_url_acquisition_provenance(result)


def test_assert_url_provenance_rejects_missing_source_url() -> None:
    result = AcquisitionResult(
        source_kind="url",
        raw_content=_posting().raw_text,
        posting=_posting(source_url=None),
        source_identifier=SAMPLE_URL,
        source_url=None,
        acquired_at=FIXED_AT,
    )
    with pytest.raises(DiscoveryProvenanceError, match="source_url"):
        assert_url_acquisition_provenance(result)


def test_assert_url_provenance_rejects_missing_identifier() -> None:
    result = AcquisitionResult(
        source_kind="url",
        raw_content=_posting().raw_text,
        posting=_posting(),
        source_identifier=None,
        source_url=SAMPLE_URL,
        acquired_at=FIXED_AT,
    )
    with pytest.raises(DiscoveryProvenanceError, match="source_identifier"):
        assert_url_acquisition_provenance(result)


def test_assert_url_provenance_rejects_missing_acquired_at() -> None:
    result = AcquisitionResult(
        source_kind="url",
        raw_content=_posting().raw_text,
        posting=_posting(),
        source_identifier=SAMPLE_URL,
        source_url=SAMPLE_URL,
        acquired_at=None,
    )
    with pytest.raises(DiscoveryProvenanceError, match="acquired_at"):
        assert_url_acquisition_provenance(result)
