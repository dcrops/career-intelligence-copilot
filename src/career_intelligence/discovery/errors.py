"""Typed errors for Opportunity Discovery (FR-018 M1)."""

from __future__ import annotations


class DiscoveryError(Exception):
    """Base fail-closed discovery error."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


class DiscoveryValidationError(DiscoveryError):
    """Request or source failed schema / M1 scope validation."""


class DiscoveryUnsupportedSourceError(DiscoveryError):
    """Source kind is not allowed in the current milestone."""


class DiscoveryProvenanceError(DiscoveryError):
    """AcquisitionResult lacks required provenance for the discovery path."""
