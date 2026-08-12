"""Public API for Application Package Preparation (FR-010).

Composes existing FR-006 Tailoring Plan / Tailored CV and FR-007 Cover Letter
generation into one owner-reviewable package per Opportunity with decision
``apply``. Persists only the package manifesto of artefact references — never
duplicates generated document content into Opportunity persistence.
"""

from .errors import (
    ApplicationPackageContactError,
    ApplicationPackageEligibilityError,
    ApplicationPackageError,
    ApplicationPackageIntegrityError,
    ApplicationPackageNotFoundError,
    ApplicationPackageStorageError,
    ApplicationPackageValidationError,
    ErrorDetail,
)
from .models import (
    AcquisitionProvenance,
    ApplicationPackageManifest,
    DocumentArtefactRefs,
    EvidenceTrace,
)
from .service import DEFAULT_PACKAGES_ROOT, ApplicationPackageService

__all__ = [
    "DEFAULT_PACKAGES_ROOT",
    "AcquisitionProvenance",
    "ApplicationPackageContactError",
    "ApplicationPackageEligibilityError",
    "ApplicationPackageError",
    "ApplicationPackageIntegrityError",
    "ApplicationPackageManifest",
    "ApplicationPackageNotFoundError",
    "ApplicationPackageService",
    "ApplicationPackageStorageError",
    "ApplicationPackageValidationError",
    "DocumentArtefactRefs",
    "ErrorDetail",
    "EvidenceTrace",
]
