"""Internal extraction boundary for FR-002.

Kept package-private: consumers obtain analysis only through JobAnalysisService.

Extractor output is an untrusted structured payload. The service alone validates and
binds the caller-supplied JobPosting into a trusted JobAnalysis.
"""

from collections.abc import Mapping
from typing import Any, Protocol, TypeAlias

from .models import JobPosting

JobAnalysisPayload: TypeAlias = Mapping[str, Any]


class JobExtractor(Protocol):
    """Single-responsibility seam: turn a posting into untrusted structured data.

    The payload must describe extracted interpretations only. It must not include a
    top-level ``posting`` field — the service binds the caller-supplied JobPosting.
    """

    def extract(self, posting: JobPosting) -> JobAnalysisPayload:
        """Return untrusted analysis fields for the given posting."""
