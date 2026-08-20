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
    ApplicationPackageGenerationError,
    ApplicationPackageIntegrityError,
    ApplicationPackageNotFoundError,
    ApplicationPackageStorageError,
    ApplicationPackageValidationError,
    ErrorDetail,
)
from .external_upload import (
    MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN,
    ExternalUploadPaths,
    atomic_tmp_path,
    build_external_upload_filename,
    build_external_upload_filenames,
    materialize_external_upload_pdfs,
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
    "ApplicationPackageGenerationError",
    "ApplicationPackageIntegrityError",
    "ApplicationPackageManifest",
    "ApplicationPackageNotFoundError",
    "ApplicationPackageService",
    "ApplicationPackageStorageError",
    "ApplicationPackageValidationError",
    "DocumentArtefactRefs",
    "ErrorDetail",
    "EvidenceTrace",
    "ExternalUploadPaths",
    "MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN",
    "atomic_tmp_path",
    "build_external_upload_filename",
    "build_external_upload_filenames",
    "materialize_external_upload_pdfs",
]
