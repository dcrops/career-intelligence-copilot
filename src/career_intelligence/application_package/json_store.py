"""JSON directory adapter for Application Package manifests.

Package-private. Downstream callers must use ``ApplicationPackageService``.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .errors import (
    ApplicationPackageNotFoundError,
    ApplicationPackageStorageError,
    ApplicationPackageValidationError,
    ErrorDetail,
)
from .models import ApplicationPackageManifest

_MANIFEST_FILENAME = "manifest.json"


class JsonDirectoryPackageStore:
    """Persist one replaceable manifest per opportunity under ``root/{id}/``."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def get(self, opportunity_id: str) -> ApplicationPackageManifest:
        path = self._manifest_path(opportunity_id)
        if not path.is_file():
            raise ApplicationPackageNotFoundError(
                f"Application package not found: {opportunity_id}"
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return ApplicationPackageManifest.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            if isinstance(error, ValidationError):
                raise ApplicationPackageValidationError(
                    [ErrorDetail.from_pydantic(item) for item in error.errors()]
                ) from error
            raise ApplicationPackageStorageError(
                f"Could not load package manifest for {opportunity_id}: {error}"
            ) from error

    def save(self, manifest: ApplicationPackageManifest) -> ApplicationPackageManifest:
        directory = self.root / manifest.opportunity_id
        path = directory / _MANIFEST_FILENAME
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            directory.mkdir(parents=True, exist_ok=True)
            payload = (
                json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False)
                + "\n"
            )
            temporary.write_text(payload, encoding="utf-8", newline="\n")
            temporary.replace(path)
        except OSError as error:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
            raise ApplicationPackageStorageError(
                f"Could not write package manifest for {manifest.opportunity_id}: {error}"
            ) from error
        return manifest

    def exists(self, opportunity_id: str) -> bool:
        return self._manifest_path(opportunity_id).is_file()

    def _manifest_path(self, opportunity_id: str) -> Path:
        return self.root / opportunity_id / _MANIFEST_FILENAME
