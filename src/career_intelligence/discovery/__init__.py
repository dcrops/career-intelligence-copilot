"""Opportunity Discovery & Acquisition (FR-018) — public API.

M1: typed contracts + Protocol.
M2: URL adapter, thin ingress, injectable HTTP, idempotency helpers.
M3: SEEK hardening + OS trust-store TLS.
M4: email job-alert acquisition channel.
"""

from __future__ import annotations

from .email_adapter import EmailAcquisitionAdapter, expand_email_file_to_locators
from .email_parse import (
    ParsedEmailJob,
    ParsedJobAlertEmail,
    classify_job_alert_sender,
    email_locator,
    parse_email_locator,
    parse_job_alert_email,
)
from .errors import (
    DiscoveryError,
    DiscoveryProvenanceError,
    DiscoveryUnsupportedSourceError,
    DiscoveryValidationError,
)
from .http import (
    FakeHttpClient,
    HttpFetchClient,
    HttpFetchError,
    HttpFetchResponse,
    UrllibHttpClient,
    build_default_ssl_context,
)
from .idempotency import (
    find_definite_match,
    identity_probe_from_posting,
    identity_probe_from_url,
)
from .ingress import DiscoveryIngress
from .models import (
    ALLOWED_SOURCE_KINDS,
    DISCOVERY_FAILURE_KINDS,
    DISCOVERY_ITEM_STATUSES,
    DISCOVERY_SKIP_REASONS,
    M1_ALLOWED_SOURCE_KINDS,
    DiscoveryFailureKind,
    DiscoveryItemOutcome,
    DiscoveryItemStatus,
    DiscoveryOutcome,
    DiscoveryRequest,
    DiscoverySkipReason,
    OpportunitySource,
)
from .provenance import (
    assert_email_acquisition_provenance,
    assert_url_acquisition_provenance,
    opportunity_source_from_email_locator,
    opportunity_source_from_url,
    opportunity_sources_from_email_file,
)
from .thin_ingress import ThinDiscoveryIngress
from .types import DiscoverySourceKind
from .url_adapter import StaticAcquisitionAdapter, UrlAcquisitionAdapter, build_url_adapter
from .url_support import SUPPORTED_PLATFORMS, SupportedUrlRef, classify_supported_job_url

__all__ = [
    "ALLOWED_SOURCE_KINDS",
    "DISCOVERY_FAILURE_KINDS",
    "DISCOVERY_ITEM_STATUSES",
    "DISCOVERY_SKIP_REASONS",
    "M1_ALLOWED_SOURCE_KINDS",
    "SUPPORTED_PLATFORMS",
    "DiscoveryError",
    "DiscoveryFailureKind",
    "DiscoveryIngress",
    "DiscoveryItemOutcome",
    "DiscoveryItemStatus",
    "DiscoveryOutcome",
    "DiscoveryProvenanceError",
    "DiscoveryRequest",
    "DiscoverySkipReason",
    "DiscoverySourceKind",
    "DiscoveryUnsupportedSourceError",
    "DiscoveryValidationError",
    "EmailAcquisitionAdapter",
    "FakeHttpClient",
    "HttpFetchClient",
    "HttpFetchError",
    "HttpFetchResponse",
    "OpportunitySource",
    "ParsedEmailJob",
    "ParsedJobAlertEmail",
    "StaticAcquisitionAdapter",
    "SupportedUrlRef",
    "ThinDiscoveryIngress",
    "UrlAcquisitionAdapter",
    "UrllibHttpClient",
    "assert_email_acquisition_provenance",
    "assert_url_acquisition_provenance",
    "build_default_ssl_context",
    "build_url_adapter",
    "classify_job_alert_sender",
    "classify_supported_job_url",
    "email_locator",
    "expand_email_file_to_locators",
    "find_definite_match",
    "identity_probe_from_posting",
    "identity_probe_from_url",
    "opportunity_source_from_email_locator",
    "opportunity_source_from_url",
    "opportunity_sources_from_email_file",
    "parse_email_locator",
    "parse_job_alert_email",
]
