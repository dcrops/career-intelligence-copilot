"""Public service layer for job-analysis consumers."""

from __future__ import annotations

from pydantic import ValidationError

from .errors import ErrorDetail, JobAnalysisValidationError
from .extractor import JobAnalysisPayload, JobExtractor
from .models import JobAnalysis, JobPosting


class JobAnalysisService:
    """Stable interface used by future decision stages.

    The service is the public trust boundary: it accepts a validated JobPosting,
    obtains an untrusted payload from an explicitly supplied extractor, binds the
    original posting, and validates the result into a trusted JobAnalysis.

    The service contains no LLM logic. Callers must supply an extractor — there is
    no default (FixtureExtractor is test scaffolding, not a production default).
    """

    def __init__(self, extractor: JobExtractor) -> None:
        self._extractor = extractor

    def analyse(self, posting: JobPosting) -> JobAnalysis:
        payload = dict(self._extractor.extract(posting))
        self._reject_embedded_posting(payload)
        payload["posting"] = posting
        return self._validate(payload)

    def _reject_embedded_posting(self, payload: dict[str, object]) -> None:
        """Extractor payloads must exclude top-level ``posting``.

        Silently overwriting would hide extractor bugs. Reject instead.
        """
        if "posting" in payload:
            raise JobAnalysisValidationError(
                [
                    ErrorDetail(
                        loc=("posting",),
                        msg=(
                            "extractor payload must not include 'posting'; "
                            "the service binds the caller-supplied JobPosting"
                        ),
                        type="value_error",
                    )
                ]
            )

    def _validate(self, payload: JobAnalysisPayload) -> JobAnalysis:
        try:
            return JobAnalysis.model_validate(payload)
        except ValidationError as error:
            raise JobAnalysisValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
