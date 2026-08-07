"""Typed contracts for Opportunity Discovery & Acquisition (FR-018).

OpportunitySource, DiscoveryRequest/Outcome, item statuses.
Reuses FR-008 ``AcquisitionAdapter`` / ``AcquisitionResult`` — does not redefine
them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from career_intelligence.opportunities.models import OpportunityId

from .types import DiscoverySourceKind

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

DiscoveryItemStatus = Literal["acquired", "skipped", "failed"]
DiscoverySkipReason = Literal["definite_identity_match"]
DiscoveryFailureKind = Literal[
    "invalid_url",
    "unsupported_source",
    "network_failure",
    "adapter_failure",
    "malformed_content",
    "partial_metadata",
    "runner_failure",
    "other",
]

DISCOVERY_ITEM_STATUSES: tuple[DiscoveryItemStatus, ...] = (
    "acquired",
    "skipped",
    "failed",
)
DISCOVERY_SKIP_REASONS: tuple[DiscoverySkipReason, ...] = ("definite_identity_match",)
DISCOVERY_FAILURE_KINDS: tuple[DiscoveryFailureKind, ...] = (
    "invalid_url",
    "unsupported_source",
    "network_failure",
    "adapter_failure",
    "malformed_content",
    "partial_metadata",
    "runner_failure",
    "other",
)

# M4 production allow-list: URL + email job-alert file locators.
ALLOWED_SOURCE_KINDS: frozenset[DiscoverySourceKind] = frozenset({"url", "email"})
# Backward-compatible alias (M1 name).
M1_ALLOWED_SOURCE_KINDS = ALLOWED_SOURCE_KINDS


class DiscoveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OpportunitySource(DiscoveryModel):
    """Transient ingress locator — not a durable business record.

    Dissolves into ``AcquisitionResult`` provenance once acquire succeeds.
    Must never be persisted as a parallel Opportunity catalogue.

    Locator rules:
    - ``url``: http(s) job URL
    - ``email``: path to ``.eml`` with ``#job=<index>`` (digest expansion)
    """

    source_kind: DiscoverySourceKind
    locator: NonEmptyString
    requested_at: datetime | None = None

    @model_validator(mode="after")
    def _locator_matches_kind(self) -> OpportunitySource:
        if self.source_kind == "url":
            parsed = urlparse(self.locator)
            if parsed.scheme.lower() not in {"http", "https"}:
                raise ValueError("url OpportunitySource.locator must use http or https")
            if not parsed.netloc:
                raise ValueError("url OpportunitySource.locator is missing a host")
        elif self.source_kind == "email":
            path_part = self.locator.split("#", 1)[0]
            if not path_part.lower().endswith(".eml"):
                raise ValueError(
                    "email OpportunitySource.locator must point to a .eml file"
                )
            fragment = ""
            if "#" in self.locator:
                fragment = self.locator.split("#", 1)[1]
            if not fragment.startswith("job=") or not fragment[4:].isdigit():
                raise ValueError(
                    "email OpportunitySource.locator requires #job=<non-negative int>"
                )
        return self


class DiscoveryRequest(DiscoveryModel):
    """Owner-facing discovery request (URL and/or email job-alert sources)."""

    sources: list[OpportunitySource] = Field(min_length=1)
    force: bool = False
    """When true, ingress may re-run despite definite identity match."""

    @model_validator(mode="after")
    def _allowed_source_kinds(self) -> DiscoveryRequest:
        for source in self.sources:
            if source.source_kind not in ALLOWED_SOURCE_KINDS:
                raise ValueError(
                    f"Allowed source_kind values: {sorted(ALLOWED_SOURCE_KINDS)}; "
                    f"got {source.source_kind!r}"
                )
        return self


class DiscoveryItemOutcome(DiscoveryModel):
    """Per-source result of a discovery attempt."""

    source: OpportunitySource
    status: DiscoveryItemStatus
    skip_reason: DiscoverySkipReason | None = None
    failure_kind: DiscoveryFailureKind | None = None
    message: NonEmptyString | None = None
    opportunity_id: OpportunityId | None = None
    matched_opportunity_id: OpportunityId | None = None
    workflow_run_id: NonEmptyString | None = None

    @model_validator(mode="after")
    def _status_fields_consistent(self) -> DiscoveryItemOutcome:
        if self.status == "acquired":
            if self.opportunity_id is None:
                raise ValueError("acquired items require opportunity_id")
            if self.skip_reason is not None or self.failure_kind is not None:
                raise ValueError("acquired items must not set skip_reason or failure_kind")
            if self.matched_opportunity_id is not None:
                raise ValueError("acquired items must not set matched_opportunity_id")
        elif self.status == "skipped":
            if self.skip_reason is None:
                raise ValueError("skipped items require skip_reason")
            if self.failure_kind is not None:
                raise ValueError("skipped items must not set failure_kind")
            if self.opportunity_id is not None:
                raise ValueError("skipped items must not set opportunity_id")
            if self.matched_opportunity_id is None:
                raise ValueError("skipped items require matched_opportunity_id")
        elif self.status == "failed":
            if self.failure_kind is None:
                raise ValueError("failed items require failure_kind")
            if self.skip_reason is not None:
                raise ValueError("failed items must not set skip_reason")
            if self.opportunity_id is not None or self.matched_opportunity_id is not None:
                raise ValueError("failed items must not set opportunity ids")
        return self


class DiscoveryOutcome(DiscoveryModel):
    """Aggregate outcome for one DiscoveryRequest."""

    items: list[DiscoveryItemOutcome] = Field(min_length=1)

    @property
    def acquired_count(self) -> int:
        return sum(1 for item in self.items if item.status == "acquired")

    @property
    def skipped_count(self) -> int:
        return sum(1 for item in self.items if item.status == "skipped")

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status == "failed")
