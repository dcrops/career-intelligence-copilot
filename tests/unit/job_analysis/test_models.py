"""Unit tests for the FR-002 job-analysis domain contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.job_analysis import (
    Compensation,
    EmploymentInfo,
    ExperienceRequirement,
    JobAnalysis,
    LocationInfo,
    Responsibility,
    RoleFamilyAssessment,
    SeniorityAssessment,
    SourceEvidence,
    TechnologyRequirement,
    WorkArrangement,
)


def _posting(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "raw_text": (
            "Senior AI Engineer. Build LLM applications with Python and LangChain. "
            "Hybrid Melbourne, 3 days in office. Full-time permanent. "
            "Salary $150,000–$180,000 AUD. 5+ years software engineering required."
        ),
        "title": "Senior AI Engineer",
        "company": "Example AI Co",
    }
    payload.update(overrides)
    return payload


def _evidence(excerpt: str, section: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"excerpt": excerpt}
    if section is not None:
        payload["section"] = section
    return payload


def _valid_analysis(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "posting": _posting(),
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_evidence("Senior AI Engineer", "title")],
        },
        "seniority": {
            "level": "senior",
            "ambiguous": False,
            "evidence": [_evidence("Senior AI Engineer", "title")],
        },
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [_evidence("Build LLM applications with Python", "description")],
            },
            {
                "name": "LangChain",
                "level": "preferred",
                "evidence": [_evidence("with Python and LangChain", "description")],
            },
        ],
        "responsibilities": [
            {
                "description": "Build LLM applications",
                "evidence": [_evidence("Build LLM applications with Python", "description")],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 150_000,
            "maximum": 180_000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "Salary $150,000–$180,000 AUD",
            "evidence": [_evidence("Salary $150,000–$180,000 AUD", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [_evidence("Hybrid Melbourne", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "details": "3 days in office",
            "evidence": [_evidence("Hybrid Melbourne, 3 days in office", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_evidence("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "5+ years of software engineering experience",
                "level": "required",
                "minimum_years": 5,
                "evidence": [
                    _evidence("5+ years software engineering required", "requirements")
                ],
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_valid_clear_ai_engineering_analysis() -> None:
    analysis = JobAnalysis.model_validate(_valid_analysis())

    assert analysis.role_family.family == "ai_engineering"
    assert analysis.seniority.level == "senior"
    assert analysis.seniority.ambiguous is False
    assert analysis.work_arrangement.arrangement == "hybrid"
    assert analysis.work_arrangement.details == "3 days in office"
    assert analysis.compensation.clarity == "stated"
    assert analysis.employment.working_hours == "full_time"
    assert analysis.employment.engagement_type == "permanent"
    assert [tech.name for tech in analysis.technologies] == ["Python", "LangChain"]


def test_required_versus_preferred_technologies() -> None:
    analysis = JobAnalysis.model_validate(_valid_analysis())

    by_name = {tech.name: tech.level for tech in analysis.technologies}

    assert by_name["Python"] == "required"
    assert by_name["LangChain"] == "preferred"


def test_required_technology_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        TechnologyRequirement.model_validate({"name": "Python", "level": "required"})


def test_responsibility_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        Responsibility.model_validate({"description": "Build LLM applications"})


def test_known_role_family_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        RoleFamilyAssessment.model_validate({"family": "ai_engineering"})


def test_other_role_family_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        RoleFamilyAssessment.model_validate({"family": "other", "evidence": []})


def test_network_engineering_role_family_accepts_evidence() -> None:
    assessment = RoleFamilyAssessment.model_validate(
        {
            "family": "network_engineering",
            "evidence": [
                {
                    "excerpt": "6+ years in Layer 2 & 3 network engineering",
                    "section": "profile",
                }
            ],
        }
    )
    assert assessment.family == "network_engineering"
    assert assessment.evidence


def test_known_seniority_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        SeniorityAssessment.model_validate({"level": "senior", "ambiguous": False})


def test_unknown_seniority_without_evidence_is_valid() -> None:
    seniority = SeniorityAssessment.model_validate(
        {"level": "unknown", "ambiguous": False}
    )

    assert seniority.level == "unknown"
    assert seniority.evidence == []


def test_unknown_seniority_must_not_be_marked_ambiguous_without_candidates() -> None:
    """Live smoke regression: missing seniority is unknown, not empty-ambiguous."""
    with pytest.raises(ValidationError, match="non-unknown candidate level"):
        SeniorityAssessment.model_validate(
            {
                "level": "unknown",
                "ambiguous": True,
                "candidate_levels": [],
                "evidence": [],
            }
        )

    with pytest.raises(ValidationError, match="non-unknown candidate level"):
        SeniorityAssessment.model_validate(
            {
                "level": "unknown",
                "ambiguous": True,
                "candidate_levels": ["unknown"],
                "evidence": [_evidence("no level stated", "about")],
            }
        )

    seniority = SeniorityAssessment.model_validate(
        {
            "level": "unknown",
            "ambiguous": False,
            "candidate_levels": [],
            "evidence": [],
        }
    )
    assert seniority.ambiguous is False
    assert seniority.candidate_levels == []


def test_ambiguous_seniority_with_one_candidate_and_evidence_is_valid() -> None:
    analysis = JobAnalysis.model_validate(
        _valid_analysis(
            seniority={
                "level": "unknown",
                "ambiguous": True,
                "candidate_levels": ["senior"],
                "evidence": [
                    _evidence("Senior / Lead AI Engineer", "title"),
                    _evidence("reports to Head of Engineering", "organisation"),
                ],
            }
        )
    )

    assert analysis.seniority.ambiguous is True
    assert analysis.seniority.level == "unknown"
    assert analysis.seniority.candidate_levels == ["senior"]
    assert len(analysis.seniority.evidence) == 2


def test_ambiguous_seniority_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        SeniorityAssessment.model_validate(
            {
                "level": "unknown",
                "ambiguous": True,
                "candidate_levels": ["senior", "lead"],
            }
        )


def test_ambiguous_seniority_rejects_forced_level() -> None:
    with pytest.raises(ValidationError, match="level to 'unknown'"):
        SeniorityAssessment.model_validate(
            {
                "level": "senior",
                "ambiguous": True,
                "candidate_levels": ["senior"],
                "evidence": [_evidence("senior or lead", "title")],
            }
        )


def test_missing_salary_represented_without_invention() -> None:
    analysis = JobAnalysis.model_validate(
        _valid_analysis(compensation={"clarity": "unstated"})
    )

    assert analysis.compensation.clarity == "unstated"
    assert analysis.compensation.minimum is None
    assert analysis.compensation.evidence == []


def test_unstated_compensation_accepts_explicit_nulls_and_empty_evidence() -> None:
    """OpenAI strict structured output emits nulls; they must equal omission."""
    compensation = Compensation.model_validate(
        {
            "clarity": "unstated",
            "minimum": None,
            "maximum": None,
            "currency": None,
            "period": None,
            "raw_text": None,
            "evidence": [],
        }
    )

    assert compensation.clarity == "unstated"
    assert compensation.minimum is None
    assert compensation.maximum is None
    assert compensation.currency is None
    assert compensation.period is None
    assert compensation.raw_text is None
    assert compensation.evidence == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"minimum": 120_000},
        {"maximum": 150_000},
        {"currency": "AUD"},
        {"period": "year"},
        {"raw_text": "Competitive salary"},
        {"evidence": [{"excerpt": "Competitive salary package", "section": "compensation"}]},
    ],
)
def test_unstated_compensation_rejects_invented_content(overrides: dict[str, object]) -> None:
    payload: dict[str, object] = {
        "clarity": "unstated",
        "minimum": None,
        "maximum": None,
        "currency": None,
        "period": None,
        "raw_text": None,
        "evidence": [],
    }
    payload.update(overrides)

    with pytest.raises(ValidationError, match="unstated compensation"):
        Compensation.model_validate(payload)


def test_stated_compensation_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        Compensation.model_validate(
            {
                "clarity": "stated",
                "minimum": 150_000,
                "currency": "AUD",
                "period": "year",
                "raw_text": "$150,000 AUD",
            }
        )


def test_unstated_compensation_rejects_invented_amount() -> None:
    with pytest.raises(ValidationError, match="unstated compensation"):
        Compensation.model_validate(
            {
                "clarity": "unstated",
                "minimum": 120_000,
                "currency": "AUD",
                "period": "year",
            }
        )

def test_stated_location_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        LocationInfo.model_validate({"clarity": "stated", "summary": "Melbourne"})


def test_hybrid_work_arrangement_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        WorkArrangement.model_validate({"arrangement": "hybrid"})


def test_unspecified_arrangement_with_no_evidence_is_valid() -> None:
    arrangement = WorkArrangement.model_validate({"arrangement": "unspecified"})

    assert arrangement.arrangement == "unspecified"
    assert arrangement.details is None
    assert arrangement.evidence == []


def test_unspecified_arrangement_rejects_details() -> None:
    with pytest.raises(ValidationError, match="must omit details"):
        WorkArrangement.model_validate(
            {
                "arrangement": "unspecified",
                "details": "3 days in office",
            }
        )


def test_remote_work_arrangement_with_details() -> None:
    analysis = JobAnalysis.model_validate(
        _valid_analysis(
            work_arrangement={
                "arrangement": "remote",
                "details": "remote within Australia only",
                "evidence": [_evidence("Fully remote within Australia", "location")],
            },
            location={
                "clarity": "stated",
                "summary": "Remote Australia",
                "evidence": [_evidence("Fully remote within Australia", "location")],
            },
        )
    )

    assert analysis.work_arrangement.arrangement == "remote"
    assert analysis.work_arrangement.details == "remote within Australia only"


def test_full_time_permanent_can_be_represented() -> None:
    analysis = JobAnalysis.model_validate(_valid_analysis())

    assert analysis.employment.working_hours == "full_time"
    assert analysis.employment.engagement_type == "permanent"


def test_full_time_contract_can_be_represented() -> None:
    analysis = JobAnalysis.model_validate(
        _valid_analysis(
            employment={
                "working_hours": "full_time",
                "engagement_type": "contract",
                "evidence": [_evidence("Full-time contract", "employment")],
            },
            compensation={
                "clarity": "stated",
                "minimum": 850,
                "maximum": 950,
                "currency": "AUD",
                "period": "day",
                "raw_text": "$850–$950 per day",
                "evidence": [_evidence("$850–$950 per day", "compensation")],
            },
        )
    )

    assert analysis.employment.working_hours == "full_time"
    assert analysis.employment.engagement_type == "contract"
    assert analysis.compensation.period == "day"


def test_part_time_fixed_term_can_be_represented() -> None:
    employment = EmploymentInfo.model_validate(
        {
            "working_hours": "part_time",
            "engagement_type": "fixed_term",
            "evidence": [_evidence("Part-time fixed-term, 12 months", "employment")],
        }
    )

    assert employment.working_hours == "part_time"
    assert employment.engagement_type == "fixed_term"


def test_known_employment_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        EmploymentInfo.model_validate(
            {
                "working_hours": "full_time",
                "engagement_type": "permanent",
            }
        )


def test_unspecified_employment_allows_empty_evidence() -> None:
    employment = EmploymentInfo.model_validate({})

    assert employment.working_hours == "unspecified"
    assert employment.engagement_type == "unspecified"
    assert employment.evidence == []


def test_explicit_full_time_permanent_employment_with_evidence() -> None:
    employment = EmploymentInfo.model_validate(
        {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_evidence("Full-time permanent role", "employment")],
        }
    )

    assert employment.working_hours == "full_time"
    assert employment.engagement_type == "permanent"
    assert employment.evidence[0].excerpt == "Full-time permanent role"


def test_explicit_contract_engagement_with_evidence() -> None:
    employment = EmploymentInfo.model_validate(
        {
            "working_hours": "unspecified",
            "engagement_type": "contract",
            "evidence": [_evidence("6 month contract", "employment")],
        }
    )

    assert employment.working_hours == "unspecified"
    assert employment.engagement_type == "contract"
    assert employment.evidence


def test_explicit_part_time_working_hours_with_evidence() -> None:
    employment = EmploymentInfo.model_validate(
        {
            "working_hours": "part_time",
            "engagement_type": "unspecified",
            "evidence": [_evidence("Part-time", "employment")],
        }
    )

    assert employment.working_hours == "part_time"
    assert employment.engagement_type == "unspecified"


def test_inferred_employment_language_must_remain_unspecified() -> None:
    """Recruiter/office/seniority wording is not employment evidence."""
    employment = EmploymentInfo.model_validate(
        {
            "working_hours": "unspecified",
            "engagement_type": "unspecified",
            "evidence": [],
        }
    )

    assert employment.working_hours == "unspecified"
    assert employment.engagement_type == "unspecified"
    assert employment.evidence == []

    with pytest.raises(ValidationError, match="at least one evidence item"):
        EmploymentInfo.model_validate(
            {
                "working_hours": "full_time",
                "engagement_type": "permanent",
                "evidence": [],
            }
        )


def test_multiple_experience_requirements_can_coexist() -> None:
    analysis = JobAnalysis.model_validate(
        _valid_analysis(
            experience_requirements=[
                {
                    "description": "5+ years of software engineering experience",
                    "level": "required",
                    "minimum_years": 5,
                    "evidence": [
                        _evidence("5+ years software engineering required", "requirements")
                    ],
                },
                {
                    "description": "production LLM experience",
                    "level": "required",
                    "evidence": [_evidence("production LLM experience", "requirements")],
                },
                {
                    "description": "stakeholder-facing consulting experience",
                    "level": "preferred",
                    "evidence": [
                        _evidence("consulting experience preferred", "requirements")
                    ],
                },
                {
                    "description": "LangChain experience",
                    "level": "preferred",
                    "evidence": [_evidence("LangChain experience preferred", "requirements")],
                },
            ]
        )
    )

    assert len(analysis.experience_requirements) == 4
    levels = {item.description: item.level for item in analysis.experience_requirements}
    assert levels["production LLM experience"] == "required"
    assert levels["LangChain experience"] == "preferred"


def test_required_and_preferred_experience_are_distinguished() -> None:
    analysis = JobAnalysis.model_validate(
        _valid_analysis(
            experience_requirements=[
                {
                    "description": "5+ years of software engineering experience",
                    "level": "required",
                    "minimum_years": 5,
                    "evidence": [_evidence("5+ years required", "requirements")],
                },
                {
                    "description": "stakeholder-facing consulting experience",
                    "level": "preferred",
                    "evidence": [_evidence("consulting preferred", "requirements")],
                },
            ]
        )
    )

    by_level = {item.level for item in analysis.experience_requirements}
    assert by_level == {"required", "preferred"}


def test_experience_requirement_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one evidence item"):
        ExperienceRequirement.model_validate(
            {
                "description": "5+ years of software engineering experience",
                "level": "required",
                "minimum_years": 5,
            }
        )


def test_invalid_experience_year_ranges_are_rejected() -> None:
    with pytest.raises(ValidationError, match="maximum_years"):
        ExperienceRequirement.model_validate(
            {
                "description": "3–5 years experience",
                "level": "required",
                "minimum_years": 5,
                "maximum_years": 3,
                "evidence": [_evidence("3–5 years experience", "requirements")],
            }
        )


def test_uppercase_three_letter_currency_codes_are_accepted() -> None:
    for currency in ("AUD", "USD", "GBP", "EUR", "SGD"):
        compensation = Compensation.model_validate(
            {
                "clarity": "stated",
                "minimum": 100_000,
                "currency": currency,
                "period": "year",
                "raw_text": f"100000 {currency}",
                "evidence": [_evidence(f"100000 {currency}", "compensation")],
            }
        )
        assert compensation.currency == currency


@pytest.mark.parametrize("currency", ["aud", "AU", "DOLLARS", ""])
def test_invalid_currency_formats_are_rejected(currency: str) -> None:
    with pytest.raises(ValidationError):
        Compensation.model_validate(
            {
                "clarity": "stated",
                "minimum": 100_000,
                "currency": currency,
                "period": "year",
                "raw_text": "100000",
                "evidence": [_evidence("100000", "compensation")],
            }
        )


def test_unknown_role_family_allows_empty_evidence() -> None:
    analysis = JobAnalysis.model_validate(
        _valid_analysis(role_family={"family": "unknown"})
    )

    assert analysis.role_family.family == "unknown"
    assert analysis.role_family.evidence == []


def test_evidence_excerpt_rejects_blank() -> None:
    with pytest.raises(ValidationError, match="at least 1 character"):
        SourceEvidence.model_validate({"excerpt": "   ", "section": "title"})


def test_evidence_section_is_optional() -> None:
    evidence = SourceEvidence.model_validate({"excerpt": "Python required"})

    assert evidence.excerpt == "Python required"
    assert evidence.section is None


def test_extra_fields_rejected_on_job_analysis() -> None:
    payload = _valid_analysis()
    payload["technical_fit"] = "strong"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        JobAnalysis.model_validate(payload)


def test_extra_fields_rejected_on_nested_models() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SourceEvidence.model_validate({"excerpt": "Python", "confidence": 0.9})


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("role_family", {"family": "prompt_engineer"}),
        ("seniority", {"level": "staff", "ambiguous": False}),
        ("technologies", [{"name": "Python", "level": "nice_to_have"}]),
        ("work_arrangement", {"arrangement": "flexible"}),
        (
            "employment",
            {
                "working_hours": "full_time",
                "engagement_type": "temp",
                "evidence": [_evidence("temp", "employment")],
            },
        ),
    ],
)
def test_invalid_enum_values_rejected(field: str, invalid_value: object) -> None:
    payload = _valid_analysis(**{field: invalid_value})

    with pytest.raises(ValidationError):
        JobAnalysis.model_validate(payload)


def test_representative_model_dump_is_human_readable() -> None:
    analysis = JobAnalysis.model_validate(_valid_analysis())
    dumped = analysis.model_dump(mode="json")

    assert set(dumped) >= {
        "posting",
        "role_family",
        "seniority",
        "technologies",
        "responsibilities",
        "compensation",
        "location",
        "work_arrangement",
        "employment",
        "experience_requirements",
    }
    assert "employment_type" not in dumped
    assert "employment_type" not in dumped["employment"]
    assert dumped["employment"] == {
        "working_hours": "full_time",
        "engagement_type": "permanent",
        "evidence": [
            {"excerpt": "Full-time permanent", "section": "employment"},
        ],
    }
    assert dumped["work_arrangement"]["details"] == "3 days in office"
    assert dumped["experience_requirements"][0]["level"] == "required"
    assert dumped["compensation"]["currency"] == "AUD"


def test_fr002_models_contain_no_candidate_fit_fields() -> None:
    forbidden = {
        "technical_fit",
        "commercial_fit",
        "portfolio_fit",
        "fit",
        "tier",
        "recommendation",
        "apply",
        "skip",
        "candidate_fit",
        "profile",
        "career_profile",
        "match_score",
        "interview_probability",
    }

    field_names = set(JobAnalysis.model_fields)

    assert field_names.isdisjoint(forbidden)
    for name in JobAnalysis.model_fields:
        annotation = str(JobAnalysis.model_fields[name].annotation).lower()
        assert "fit" not in annotation
        assert "tier" not in annotation
        assert "profile" not in annotation
