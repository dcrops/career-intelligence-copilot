"""Deterministic extractor used to exercise the service without network access."""

from __future__ import annotations

from collections.abc import Callable

from .errors import JobAnalysisError
from .extractor import JobAnalysisPayload
from .fixtures import FIXTURE_BUILDERS
from .models import JobPosting

PayloadBuilder = Callable[[], JobAnalysisPayload]


class FixtureExtractor:
    """Return canned analysis payloads for a small set of representative postings.

    Matching is intentionally dumb: distinctive fixture markers in raw_text. This is
    architecture test scaffolding, not intelligence. It is never a public default —
    callers (including tests) must pass it explicitly to JobAnalysisService.
    """

    def extract(self, posting: JobPosting) -> JobAnalysisPayload:
        builder = self._match(posting)
        if builder is None:
            raise JobAnalysisError(
                "No fixture analysis is available for this posting. "
                "Provide a recognised fixture description or a real extractor."
            )
        return builder()

    def _match(self, posting: JobPosting) -> PayloadBuilder | None:
        for marker, builder in FIXTURE_BUILDERS.items():
            if marker in posting.raw_text:
                return builder
        return None
