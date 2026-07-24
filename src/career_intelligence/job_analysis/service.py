"""Public service layer for job-analysis consumers."""

from __future__ import annotations

from pydantic import ValidationError

from .errors import ErrorDetail, JobAnalysisValidationError
from .extraction import ExtractedPostingIdentity
from .extractor import JobAnalysisPayload, JobExtractor
from .models import JobAnalysis, JobPosting, SourceEvidence


class JobAnalysisService:
    """Stable interface used by future decision stages.

    The service is the public trust boundary: it accepts a validated JobPosting,
    obtains an untrusted payload from an explicitly supplied extractor, binds the
    original posting (enriching missing title/company from grounded extraction when
    present), and validates the result into a trusted JobAnalysis.

    The service contains no LLM logic. Callers must supply an extractor — there is
    no default (FixtureExtractor is test scaffolding, not a production default).
    """

    def __init__(self, extractor: JobExtractor) -> None:
        self._extractor = extractor

    def analyse(self, posting: JobPosting) -> JobAnalysis:
        payload = dict(self._extractor.extract(posting))
        self._reject_embedded_posting(payload)
        identity = _parse_posting_identity(payload.pop("posting_identity", None))
        bound_posting = enrich_posting_identity(posting, identity)
        payload["posting"] = bound_posting
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


def enrich_posting_identity(
    posting: JobPosting,
    identity: ExtractedPostingIdentity | None,
) -> JobPosting:
    """Fill missing JobPosting title/company from grounded extraction only.

    Caller-supplied title/company are never overwritten. Ungrounded extracted
    values are dropped (left unset) — never invented into the trusted posting.
    """
    if identity is None:
        return posting

    updates: dict[str, str] = {}
    if posting.title is None and identity.title is not None:
        if _is_grounded(identity.title, identity.title_evidence, posting.raw_text):
            updates["title"] = identity.title
    if posting.company is None and identity.company is not None:
        if _is_grounded(identity.company, identity.company_evidence, posting.raw_text):
            updates["company"] = identity.company

    if not updates:
        return posting
    return posting.model_copy(update=updates)


def _parse_posting_identity(raw: object) -> ExtractedPostingIdentity | None:
    if raw is None:
        return None
    try:
        if isinstance(raw, ExtractedPostingIdentity):
            return raw
        return ExtractedPostingIdentity.model_validate(raw)
    except ValidationError as error:
        raise JobAnalysisValidationError(
            [ErrorDetail.from_pydantic(item) for item in error.errors()]
        ) from error


def _is_grounded(value: str, evidence: list[SourceEvidence], raw_text: str) -> bool:
    """Require value and at least one evidence excerpt to appear in the posting body."""
    if not evidence:
        return False
    if value not in raw_text:
        return False
    return any(item.excerpt in raw_text for item in evidence)
