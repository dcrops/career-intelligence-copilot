"""Executable thin Discovery Ingress (FR-018 M2/M4).

Coordination only: validate → classify/parse → acquire → provenance → definite
skip → ``ApplicationWorkflowRunner.start``. Does not persist Opportunities itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from career_intelligence.orchestration.acquisition import AcquisitionError
from career_intelligence.orchestration.runner import ApplicationWorkflowRunner
from career_intelligence.opportunities.service import OpportunityService

from .email_adapter import EmailAcquisitionAdapter
from .errors import (
    DiscoveryError,
    DiscoveryProvenanceError,
    DiscoveryUnsupportedSourceError,
    DiscoveryValidationError,
)
from .http import HttpFetchClient, HttpFetchError
from .idempotency import (
    find_definite_match,
    identity_probe_from_posting,
    identity_probe_from_url,
)
from .models import (
    DiscoveryFailureKind,
    DiscoveryItemOutcome,
    DiscoveryOutcome,
    DiscoveryRequest,
    OpportunitySource,
)
from .provenance import (
    assert_email_acquisition_provenance,
    assert_url_acquisition_provenance,
)
from .url_adapter import StaticAcquisitionAdapter, UrlAcquisitionAdapter
from .url_support import classify_supported_job_url


RunnerFactory = Callable[[], ApplicationWorkflowRunner]


@dataclass
class ThinDiscoveryIngress:
    """Production DiscoveryIngress implementation (ADR-010)."""

    opportunities: OpportunityService
    runner_factory: RunnerFactory
    http_client: HttpFetchClient | None = None
    offline_fixture_marker: str | None = None

    def discover(self, request: DiscoveryRequest) -> DiscoveryOutcome:
        items: list[DiscoveryItemOutcome] = []
        for source in request.sources:
            if source.source_kind == "email":
                items.append(self._discover_email(source, force=request.force))
            else:
                items.append(self._discover_url(source, force=request.force))
        return DiscoveryOutcome(items=items)

    def _discover_url(
        self,
        source: OpportunitySource,
        *,
        force: bool,
    ) -> DiscoveryItemOutcome:
        url = str(source.locator)
        try:
            classify_supported_job_url(url)
        except DiscoveryValidationError as exc:
            return _failed(source, "invalid_url", str(exc))
        except DiscoveryUnsupportedSourceError as exc:
            return _failed(source, "unsupported_source", str(exc))

        if not force:
            probe = identity_probe_from_url(url)
            if probe is not None:
                existing = find_definite_match(
                    probe, self.opportunities.list_opportunities()
                )
                if existing is not None:
                    return DiscoveryItemOutcome(
                        source=source,
                        status="skipped",
                        skip_reason="definite_identity_match",
                        matched_opportunity_id=existing.opportunity_id,
                        message="Already represented (definite identity match on URL facets)",
                    )

        adapter = UrlAcquisitionAdapter(
            url=url,
            client=self.http_client,
            offline_fixture_marker=self.offline_fixture_marker,
        )
        return self._acquire_and_run(
            source,
            adapter,
            force=force,
            provenance_assert=assert_url_acquisition_provenance,
        )

    def _discover_email(
        self,
        source: OpportunitySource,
        *,
        force: bool,
    ) -> DiscoveryItemOutcome:
        adapter = EmailAcquisitionAdapter(
            locator=str(source.locator),
            offline_fixture_marker=self.offline_fixture_marker,
            http_client=self.http_client,
        )
        # Pre-acquire skip: try URL facets after a cheap parse via adapter would
        # re-parse; instead acquire then skip — definite match still prevents
        # duplicate Opportunities. Optional: parse once for URL probe.
        try:
            from .email_parse import parse_email_locator, parse_job_alert_email

            path, index = parse_email_locator(str(source.locator))
            parsed = parse_job_alert_email(path)
            if index < len(parsed.jobs) and not force:
                probe = identity_probe_from_url(parsed.jobs[index].job_url)
                if probe is not None:
                    existing = find_definite_match(
                        probe, self.opportunities.list_opportunities()
                    )
                    if existing is not None:
                        return DiscoveryItemOutcome(
                            source=source,
                            status="skipped",
                            skip_reason="definite_identity_match",
                            matched_opportunity_id=existing.opportunity_id,
                            message=(
                                "Already represented (definite identity match on "
                                "email job URL facets)"
                            ),
                        )
        except DiscoveryValidationError as exc:
            return _failed(source, "invalid_url", str(exc))
        except DiscoveryUnsupportedSourceError as exc:
            return _failed(source, "unsupported_source", str(exc))

        return self._acquire_and_run(
            source,
            adapter,
            force=force,
            provenance_assert=assert_email_acquisition_provenance,
        )

    def _acquire_and_run(
        self,
        source: OpportunitySource,
        adapter: UrlAcquisitionAdapter | EmailAcquisitionAdapter,
        *,
        force: bool,
        provenance_assert: Callable[[object], None],
    ) -> DiscoveryItemOutcome:
        try:
            result = adapter.acquire()
        except AcquisitionError as exc:
            return _failed(
                source,
                _map_acquisition_failure(exc),
                str(exc.detail or exc),
            )
        except HttpFetchError as exc:
            return _failed(source, "network_failure", str(exc))
        except DiscoveryError as exc:
            return _failed(source, _map_discovery_detail(exc), str(exc))

        try:
            provenance_assert(result)
        except DiscoveryProvenanceError as exc:
            return _failed(source, "partial_metadata", str(exc))

        if not force:
            posting_probe = identity_probe_from_posting(result.posting)
            existing = find_definite_match(
                posting_probe, self.opportunities.list_opportunities()
            )
            if existing is not None:
                return DiscoveryItemOutcome(
                    source=source,
                    status="skipped",
                    skip_reason="definite_identity_match",
                    matched_opportunity_id=existing.opportunity_id,
                    message="Already represented (definite identity match after acquire)",
                )

        static = StaticAcquisitionAdapter(result)
        try:
            runner = self.runner_factory()
            state = runner.start(static)
        except Exception as exc:  # noqa: BLE001 — surface as runner_failure
            return _failed(source, "runner_failure", str(exc))

        opportunity_id = state.artefacts.opportunity_id
        # opportunity_id is allocated immediately before persist; analyse/assess
        # failures leave it unset — surface last_error instead of a generic mask.
        if opportunity_id is None:
            if state.status == "failed" and state.control.last_error is not None:
                return _failed(
                    source,
                    "runner_failure",
                    state.control.last_error.message,
                )
            return _failed(
                source,
                "runner_failure",
                "Workflow completed without allocating opportunity_id",
            )

        message = "Acquired into Horizon 1A workflow"
        if state.status == "awaiting_owner":
            message = "Acquired; awaiting owner review (apply/skip/defer)"
        elif state.status == "failed":
            return DiscoveryItemOutcome(
                source=source,
                status="failed",
                failure_kind="runner_failure",
                message=state.control.last_error.message
                if state.control.last_error
                else "Workflow failed",
                workflow_run_id=state.run_id,
            )

        return DiscoveryItemOutcome(
            source=source,
            status="acquired",
            opportunity_id=opportunity_id,
            workflow_run_id=state.run_id,
            message=message,
        )


def _failed(
    source: OpportunitySource,
    kind: DiscoveryFailureKind,
    message: str,
) -> DiscoveryItemOutcome:
    return DiscoveryItemOutcome(
        source=source,
        status="failed",
        failure_kind=kind,
        message=message[:500] if message else kind,
    )


def _map_acquisition_failure(exc: AcquisitionError) -> DiscoveryFailureKind:
    detail = (exc.detail or str(exc)).lower()
    text = f"{exc} {detail}".lower()
    if "unsupported" in text:
        return "unsupported_source"
    if "invalid" in text and ("url" in text or "email" in text or "locator" in text):
        return "invalid_url"
    if "timeout" in text or "network" in text or "http" in text or "fetch" in text:
        return "network_failure"
    if (
        "blocked" in text
        or "login" in text
        or "listing" in text
        or "expired" in text
        or "challenge" in text
        or "redirected away" in text
    ):
        return "adapter_failure"
    if "extract" in text or "insufficient" in text or "empty" in text or "malformed" in text:
        return "malformed_content"
    if "posting" in text or "provenance" in text:
        return "partial_metadata"
    return "adapter_failure"


def _map_discovery_detail(exc: DiscoveryError) -> DiscoveryFailureKind:
    detail = (exc.detail or "").lower()
    if detail == "blocked_response":
        return "adapter_failure"
    if detail == "malformed_content":
        return "malformed_content"
    return "adapter_failure"
