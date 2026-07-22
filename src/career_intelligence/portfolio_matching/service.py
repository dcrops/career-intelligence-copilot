"""Public service layer for portfolio-matching consumers."""

from __future__ import annotations

from pydantic import ValidationError

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

from .errors import ErrorDetail, PortfolioMatchingValidationError
from .matcher import PortfolioMatchPayload, PortfolioMatcher
from .models import PortfolioMatch
from .refs import validate_references

_FORBIDDEN_PAYLOAD_KEYS = frozenset({"job_analysis", "profile", "career_profile"})


class PortfolioMatchingService:
    """Stable interface used by future decision stages.

    The service is the public trust boundary: it accepts validated JobAnalysis and
    CareerProfile inputs, obtains an untrusted payload from an explicitly supplied
    matcher, binds the original job analysis, validates project evidence
    references, and returns a trusted PortfolioMatch.

    The service contains no ranking logic. Callers must supply a matcher — there is
    no production default.
    """

    def __init__(self, matcher: PortfolioMatcher) -> None:
        self._matcher = matcher

    def match(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> PortfolioMatch:
        payload = dict(self._matcher.match(job_analysis, profile))
        self._reject_embedded_inputs(payload)
        payload["job_analysis"] = job_analysis
        portfolio_match = self._validate(payload)
        validate_references(portfolio_match, profile)
        return portfolio_match

    def _reject_embedded_inputs(self, payload: dict[str, object]) -> None:
        """Matcher payloads must exclude caller-owned trusted inputs."""
        errors: list[ErrorDetail] = []
        for key in _FORBIDDEN_PAYLOAD_KEYS:
            if key in payload:
                errors.append(
                    ErrorDetail(
                        loc=(key,),
                        msg=(
                            f"matcher payload must not include '{key}'; "
                            "the service binds caller-supplied trusted inputs"
                        ),
                        type="value_error",
                    )
                )
        if errors:
            raise PortfolioMatchingValidationError(errors)

    def _validate(self, payload: PortfolioMatchPayload) -> PortfolioMatch:
        try:
            return PortfolioMatch.model_validate(payload)
        except ValidationError as error:
            raise PortfolioMatchingValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
