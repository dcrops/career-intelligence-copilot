"""Persistence boundary for Application Package manifests (FR-010)."""

from __future__ import annotations

from typing import Protocol

from .models import ApplicationPackageManifest


class ApplicationPackageStore(Protocol):
    """Replaceable store — no path-specific surface on the public service."""

    def get(self, opportunity_id: str) -> ApplicationPackageManifest:
        """Load the current package manifest for an opportunity."""

    def save(self, manifest: ApplicationPackageManifest) -> ApplicationPackageManifest:
        """Persist the current package (replaces any previous manifest)."""

    def exists(self, opportunity_id: str) -> bool:
        """Return whether a package manifest is present."""
