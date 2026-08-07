"""Provenance helpers for FR-018 discovery (URL + email channels).

``AcquisitionResult`` (FR-008) remains the provenance carrier into AcquireNode.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

from career_intelligence.orchestration.acquisition import AcquisitionResult

from .email_parse import email_locator, parse_job_alert_email
from .errors import (
    DiscoveryProvenanceError,
    DiscoveryUnsupportedSourceError,
    DiscoveryValidationError,
)
from .models import OpportunitySource

_URL_ADAPTER = TypeAdapter(AnyHttpUrl)


def opportunity_source_from_url(
    url: str,
    *,
    requested_at: datetime | None = None,
) -> OpportunitySource:
    """Build a URL OpportunitySource; fail closed on invalid locators."""
    try:
        locator = str(_URL_ADAPTER.validate_python(url))
    except ValidationError as exc:
        raise DiscoveryValidationError(
            "invalid URL for OpportunitySource",
            detail=str(exc),
        ) from exc
    return OpportunitySource(
        source_kind="url",
        locator=locator,
        requested_at=requested_at or datetime.now(UTC),
    )


def opportunity_source_from_email_locator(
    locator: str,
    *,
    requested_at: datetime | None = None,
) -> OpportunitySource:
    """Build an email OpportunitySource from ``path.eml#job=N``."""
    try:
        return OpportunitySource(
            source_kind="email",
            locator=locator,
            requested_at=requested_at or datetime.now(UTC),
        )
    except ValidationError as exc:
        raise DiscoveryValidationError(
            "invalid email OpportunitySource locator",
            detail=str(exc),
        ) from exc


def opportunity_sources_from_email_file(
    path: Path | str,
    *,
    requested_at: datetime | None = None,
) -> list[OpportunitySource]:
    """Expand a job-alert ``.eml`` into one OpportunitySource per job."""
    try:
        parsed = parse_job_alert_email(path)
    except (DiscoveryValidationError, DiscoveryUnsupportedSourceError):
        raise
    stamp = requested_at or datetime.now(UTC)
    return [
        OpportunitySource(
            source_kind="email",
            locator=email_locator(parsed.path, job.index),
            requested_at=stamp,
        )
        for job in parsed.jobs
    ]


def assert_url_acquisition_provenance(result: AcquisitionResult) -> None:
    """Fail closed if an AcquisitionResult is unsuitable for the URL discovery path."""
    if result.source_kind != "url":
        raise DiscoveryProvenanceError(
            "URL discovery path requires source_kind='url'",
            detail=f"got {result.source_kind!r}",
        )
    if result.source_url is None:
        raise DiscoveryProvenanceError(
            "URL discovery path requires source_url for OpportunityIdentity facets"
        )
    if result.source_identifier is None:
        raise DiscoveryProvenanceError(
            "URL discovery path requires source_identifier (stable locator)"
        )
    if result.acquired_at is None:
        raise DiscoveryProvenanceError(
            "URL discovery path requires acquired_at"
        )


def assert_email_acquisition_provenance(result: AcquisitionResult) -> None:
    """Fail closed if an AcquisitionResult is unsuitable for the email discovery path.

    Required:

    - ``source_kind == "email"``
    - ``source_url`` (job URL extracted from the alert — drives FR-009 facets)
    - ``source_identifier`` (Message-ID + job index)
    - ``acquired_at``
    """
    if result.source_kind != "email":
        raise DiscoveryProvenanceError(
            "Email discovery path requires source_kind='email'",
            detail=f"got {result.source_kind!r}",
        )
    if result.source_url is None:
        raise DiscoveryProvenanceError(
            "Email discovery path requires source_url (job link from alert)"
        )
    if result.source_identifier is None:
        raise DiscoveryProvenanceError(
            "Email discovery path requires source_identifier "
            "(Message-ID#job=index or stable email ref)"
        )
    if result.acquired_at is None:
        raise DiscoveryProvenanceError(
            "Email discovery path requires acquired_at"
        )
    # original email reference is carried in warnings + source_identifier.
