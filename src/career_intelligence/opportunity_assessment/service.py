"""Public service layer for opportunity-assessment consumers."""

from __future__ import annotations

from pydantic import ValidationError

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

from .assessor import Assessor, OpportunityAssessmentPayload
from .errors import ErrorDetail, OpportunityAssessmentValidationError
from .models import OpportunityAssessment
from .refs import validate_references

_FORBIDDEN_PAYLOAD_KEYS = frozenset({"job_analysis", "profile", "career_profile"})


class OpportunityAssessmentService:
    """Stable interface used by future decision stages.

    The service is the public trust boundary: it accepts validated JobAnalysis and
    CareerProfile inputs, obtains an untrusted payload from an explicitly supplied
    assessor, binds the original job analysis, validates profile evidence
    references, and returns a trusted OpportunityAssessment.

    The service contains no LLM logic. Callers must supply an assessor — there is
    no production default.
    """

    def __init__(self, assessor: Assessor) -> None:
        self._assessor = assessor

    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessment:
        payload = dict(self._assessor.assess(job_analysis, profile))
        self._reject_embedded_inputs(payload)
        payload["job_analysis"] = job_analysis
        assessment = self._validate(payload)
        validate_references(assessment, profile)
        return assessment

    def _reject_embedded_inputs(self, payload: dict[str, object]) -> None:
        """Assessor payloads must exclude caller-owned trusted inputs."""
        errors: list[ErrorDetail] = []
        for key in _FORBIDDEN_PAYLOAD_KEYS:
            if key in payload:
                errors.append(
                    ErrorDetail(
                        loc=(key,),
                        msg=(
                            f"assessor payload must not include '{key}'; "
                            "the service binds caller-supplied trusted inputs"
                        ),
                        type="value_error",
                    )
                )
        if errors:
            raise OpportunityAssessmentValidationError(errors)

    def _validate(self, payload: OpportunityAssessmentPayload) -> OpportunityAssessment:
        try:
            return OpportunityAssessment.model_validate(payload)
        except ValidationError as error:
            raise OpportunityAssessmentValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
