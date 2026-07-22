"""Public service layer for application-strategy consumers."""

from __future__ import annotations

from pydantic import ValidationError

from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile.models import CareerProfile

from .context import SearchOperatingContext
from .errors import ApplicationStrategyValidationError, ErrorDetail
from .models import ApplicationStrategy
from .planner import ApplicationStrategyPayload, StrategyPlanner
from .refs import validate_references

_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "job_analysis",
        "profile",
        "career_profile",
        "opportunity_assessment",
        "portfolio_match",
        "operating_context",
        "search_operating_context",
    }
)


class ApplicationStrategyService:
    """Stable interface used by future decision stages.

    The service is the public trust boundary: it accepts validated
    OpportunityAssessment, PortfolioMatch, and CareerProfile inputs, obtains an
    untrusted payload from an explicitly supplied planner, binds the original
    JobAnalysis, validates evidence references, and returns a trusted
    ApplicationStrategy.

    The service contains no recommendation policy. Callers must supply a planner
    — there is no production default.
    """

    def __init__(self, planner: StrategyPlanner) -> None:
        self._planner = planner

    def plan(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        profile: CareerProfile,
        *,
        operating_context: SearchOperatingContext | None = None,
    ) -> ApplicationStrategy:
        context = operating_context or SearchOperatingContext()
        self._reject_mismatched_postings(assessment, portfolio_match)

        payload = dict(
            self._planner.plan(assessment, portfolio_match, profile, context)
        )
        self._reject_embedded_inputs(payload)
        payload["job_analysis"] = assessment.job_analysis
        strategy = self._validate(payload)
        validate_references(strategy, assessment, portfolio_match, profile)
        return strategy

    def _reject_mismatched_postings(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
    ) -> None:
        if _same_posting(
            assessment.job_analysis.posting,
            portfolio_match.job_analysis.posting,
        ):
            return
        raise ApplicationStrategyValidationError(
            [
                ErrorDetail(
                    loc=("portfolio_match", "job_analysis", "posting"),
                    msg=(
                        "OpportunityAssessment and PortfolioMatch must refer to "
                        "the same JobPosting identity"
                    ),
                    type="value_error",
                )
            ]
        )

    def _reject_embedded_inputs(self, payload: dict[str, object]) -> None:
        """Planner payloads must exclude caller-owned trusted inputs."""
        errors: list[ErrorDetail] = []
        for key in _FORBIDDEN_PAYLOAD_KEYS:
            if key in payload:
                errors.append(
                    ErrorDetail(
                        loc=(key,),
                        msg=(
                            f"planner payload must not include '{key}'; "
                            "the service binds caller-supplied trusted inputs"
                        ),
                        type="value_error",
                    )
                )
        if errors:
            raise ApplicationStrategyValidationError(errors)

    def _validate(self, payload: ApplicationStrategyPayload) -> ApplicationStrategy:
        try:
            return ApplicationStrategy.model_validate(payload)
        except ValidationError as error:
            raise ApplicationStrategyValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error


def _same_posting(left: JobPosting, right: JobPosting) -> bool:
    return (
        left.raw_text == right.raw_text
        and left.title == right.title
        and left.company == right.company
        and left.source_url == right.source_url
    )
