"""OpenAI Responses API assessor for FR-003 Opportunity Assessment.

Returns an untrusted ``OpportunityAssessmentPayload`` only. ``OpportunityAssessmentService``
binds the caller-supplied ``JobAnalysis`` and validates profile evidence references.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

from .assessment_prompt import ASSESSMENT_INSTRUCTIONS_V1
from .assessor import OpportunityAssessmentPayload
from .errors import ErrorDetail, OpportunityAssessmentError, OpportunityAssessmentValidationError
from .extraction import OpportunityAssessmentExtraction

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 60.0

_VALID_PREFERENCE_FIELDS = (
    "locations",
    "employment_types",
    "salary_min",
    "salary_currency",
    "remote",
    "company_stages",
    "must_haves",
    "deal_breakers",
)

_VALID_GOAL_FIELDS = ("primary", "secondary", "horizon_notes")


class _ResponsesParseAPI(Protocol):
    def parse(self, **kwargs: Any) -> Any: ...


class _OpenAIClient(Protocol):
    responses: _ResponsesParseAPI


class OpenAIAssessor:
    """Concrete ``Assessor`` backed by the OpenAI Responses API.

    Satisfies ``Assessor`` by structural typing. Configuration is intentionally
    minimal: API key (via SDK / override), model, and timeout.
    """

    def __init__(
        self,
        *,
        client: _OpenAIClient | None = None,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            kwargs: dict[str, object] = {"timeout": timeout}
            if api_key is not None:
                kwargs["api_key"] = api_key
            self._client = OpenAI(**kwargs)
        self._model = model

    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessmentPayload:
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=ASSESSMENT_INSTRUCTIONS_V1,
                input=format_assessment_input(job_analysis, profile),
                text_format=OpportunityAssessmentExtraction,
            )
        except ValidationError as error:
            raise OpportunityAssessmentValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        except OpenAIError as error:
            raise OpportunityAssessmentError(f"OpenAI assessment failed: {error}") from error

        refusal = _find_refusal(response)
        if refusal is not None:
            raise OpportunityAssessmentError(f"OpenAI refused the assessment request: {refusal}")

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise OpportunityAssessmentError("OpenAI returned an empty structured assessment response")

        extraction = _coerce_extraction(parsed)
        return extraction.model_dump(mode="python")


def format_assessment_input(job_analysis: JobAnalysis, profile: CareerProfile) -> str:
    """Render trusted inputs and reference catalogues for the assessor prompt."""
    catalogue = _profile_reference_tokens(profile)
    parts = [
        _tagged("JobAnalysis", _serialise(job_analysis.model_dump(mode="json"))),
        _tagged("ValidProfileReferences", "\n".join(catalogue)),
        _tagged("CareerProfile", _serialise(_assessment_profile_payload(profile, catalogue))),
        _tagged("JobEvidenceIndexes", _build_job_evidence_index_guide(job_analysis)),
    ]
    return "\n\n".join(parts)


def _serialise(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _tagged(name: str, content: str) -> str:
    return f"<{name}>\n{content}\n</{name}>"


def _profile_reference_tokens(profile: CareerProfile) -> list[str]:
    """Complete namespace:id tokens only — the sole selectable ProfileEvidenceRef.ref values."""
    tokens: list[str] = []
    for entry in profile.experience:
        tokens.append(f"experience:{entry.id}")
    for project in profile.projects:
        tokens.append(f"project:{project.id}")
    for certification in profile.certifications:
        tokens.append(f"certification:{certification.id}")
    for skills in (
        profile.skills.technical,
        profile.skills.domain,
        profile.skills.soft,
    ):
        for skill in skills:
            tokens.append(f"skill:{skill.name}")
    tokens.append("goal:primary")
    if profile.goals.secondary:
        tokens.append("goal:secondary")
    if profile.goals.horizon_notes is not None:
        tokens.append("goal:horizon_notes")
    tokens.append("identity:full_name")
    tokens.append("identity:target_role")
    if profile.identity.summary is not None:
        tokens.append("identity:summary")
    for field_name in _VALID_PREFERENCE_FIELDS:
        tokens.append(f"preference:{field_name}")
    return tokens


def _assessment_profile_payload(
    profile: CareerProfile,
    catalogue: list[str],
) -> dict[str, object]:
    """Assessor-facing profile dump: entity pointers use complete namespace:id refs only.

    Bare ``id`` fields and preference/goal/identity JSON keys are rewritten so the model
    cannot copy raw identifiers into ProfileEvidenceRef.ref. Validation still uses the
    real CareerProfile object, not this dump.
    """
    _ = catalogue  # documents that refs must match the catalogue contract
    experience: list[dict[str, object]] = []
    for entry in profile.experience:
        item = entry.model_dump(mode="json")
        item.pop("id", None)
        item["ref"] = f"experience:{entry.id}"
        experience.append(item)

    projects: list[dict[str, object]] = []
    for project in profile.projects:
        item = project.model_dump(mode="json")
        item.pop("id", None)
        item["ref"] = f"project:{project.id}"
        projects.append(item)

    certifications: list[dict[str, object]] = []
    for certification in profile.certifications:
        item = certification.model_dump(mode="json")
        item.pop("id", None)
        item["ref"] = f"certification:{certification.id}"
        certifications.append(item)

    def _skill_bucket(skills: list[object]) -> list[dict[str, object]]:
        bucket: list[dict[str, object]] = []
        for skill in skills:
            item = skill.model_dump(mode="json")  # type: ignore[attr-defined]
            name = item.get("name")
            item["ref"] = f"skill:{name}"
            bucket.append(item)
        return bucket

    prefs = profile.preferences.model_dump(mode="json")
    preferences = [
        {"ref": f"preference:{field_name}", "value": prefs.get(field_name)}
        for field_name in _VALID_PREFERENCE_FIELDS
    ]

    goals: list[dict[str, object]] = [
        {"ref": "goal:primary", "value": profile.goals.primary},
    ]
    if profile.goals.secondary:
        goals.append({"ref": "goal:secondary", "value": profile.goals.secondary})
    if profile.goals.horizon_notes is not None:
        goals.append({"ref": "goal:horizon_notes", "value": profile.goals.horizon_notes})

    identity: list[dict[str, object]] = [
        {"ref": "identity:full_name", "value": profile.identity.full_name},
        {"ref": "identity:target_role", "value": profile.identity.target_role},
    ]
    if profile.identity.summary is not None:
        identity.append({"ref": "identity:summary", "value": profile.identity.summary})

    return {
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
        "skills": {
            "technical": _skill_bucket(list(profile.skills.technical)),
            "domain": _skill_bucket(list(profile.skills.domain)),
            "soft": _skill_bucket(list(profile.skills.soft)),
        },
        "goals": goals,
        "identity": identity,
        "preferences": preferences,
    }


def _build_job_evidence_index_guide(job_analysis: JobAnalysis) -> str:
    lines: list[str] = [
        "Use cite-as JSON when populating job_evidence on every evidence-bearing finding.",
    ]
    for index, technology in enumerate(job_analysis.technologies):
        cite = {
            "source": "technology",
            "item_index": index,
            "name": technology.name,
        }
        excerpt = _first_evidence_excerpt(technology.evidence)
        if excerpt:
            cite["excerpt"] = excerpt
        lines.append(
            f"technology[{index}]: {technology.name} ({technology.level})"
            f" → cite: {json.dumps(cite, ensure_ascii=False)}"
        )
    for index, responsibility in enumerate(job_analysis.responsibilities):
        cite = {"source": "responsibility", "item_index": index}
        excerpt = _first_evidence_excerpt(responsibility.evidence)
        if excerpt:
            cite["excerpt"] = excerpt
        lines.append(
            f"responsibility[{index}]: {responsibility.description}"
            f" → cite: {json.dumps(cite, ensure_ascii=False)}"
        )
    for index, requirement in enumerate(job_analysis.experience_requirements):
        cite = {"source": "experience_requirement", "item_index": index}
        excerpt = _first_evidence_excerpt(requirement.evidence)
        if excerpt:
            cite["excerpt"] = excerpt
        lines.append(
            f"experience_requirement[{index}]: {requirement.description}"
            f" → cite: {json.dumps(cite, ensure_ascii=False)}"
        )
    role_family = job_analysis.role_family.family
    lines.append(
        f"role_family: {role_family}"
        f' → cite: {json.dumps({"source": "role_family", "excerpt": role_family}, ensure_ascii=False)}'
    )
    seniority = job_analysis.seniority.level
    lines.append(
        f"seniority: {seniority}"
        f' → cite: {json.dumps({"source": "seniority", "excerpt": seniority}, ensure_ascii=False)}'
    )
    compensation = job_analysis.compensation.clarity
    lines.append(
        f"compensation: {compensation}"
        f' → cite: {json.dumps({"source": "compensation", "excerpt": compensation}, ensure_ascii=False)}'
    )
    location = job_analysis.location.summary or job_analysis.location.clarity
    lines.append(
        f"location: {location}"
        f' → cite: {json.dumps({"source": "location", "excerpt": location}, ensure_ascii=False)}'
    )
    work_arrangement = job_analysis.work_arrangement.arrangement
    lines.append(
        f"work_arrangement: {work_arrangement}"
        f' → cite: {json.dumps({"source": "work_arrangement", "excerpt": work_arrangement}, ensure_ascii=False)}'
    )
    employment = (
        f"{job_analysis.employment.working_hours}/"
        f"{job_analysis.employment.engagement_type}"
    )
    lines.append(
        f"employment: {employment}"
        f' → cite: {json.dumps({"source": "employment", "excerpt": employment}, ensure_ascii=False)}'
    )
    return "\n".join(lines)


def _first_evidence_excerpt(evidence: list[object]) -> str | None:
    if not evidence:
        return None
    first = evidence[0]
    excerpt = getattr(first, "excerpt", None)
    if excerpt is None and isinstance(first, dict):
        excerpt = first.get("excerpt")
    if excerpt is None:
        return None
    text = str(excerpt).strip()
    return text[:120] if text else None


def _find_refusal(response: object) -> str | None:
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) == "refusal":
                refusal = getattr(content, "refusal", None)
                return str(refusal) if refusal else "Model refused the request"
    return None


def _coerce_extraction(parsed: object) -> OpportunityAssessmentExtraction:
    if isinstance(parsed, OpportunityAssessmentExtraction):
        return parsed
    try:
        return OpportunityAssessmentExtraction.model_validate(parsed)
    except ValidationError as error:
        raise OpportunityAssessmentValidationError(
            [ErrorDetail.from_pydantic(item) for item in error.errors()]
        ) from error
