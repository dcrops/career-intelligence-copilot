"""Seniority-aware FR-005 policy regressions."""

from __future__ import annotations

from datetime import date
from typing import Any

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.profile.models import CareerProfile, ExperienceEntry

from .helpers import job_analysis, minimal_profile, portfolio_match
from .test_deterministic_planner import (
    _assessment_for,
    _dimension,
    _finding,
    _plan,
)


def _profile_with_experience(*entries: ExperienceEntry) -> CareerProfile:
    profile = minimal_profile()
    return profile.model_copy(update={"experience": list(entries)})


def _employment_ai_senior() -> ExperienceEntry:
    return ExperienceEntry.model_validate(
        {
            "id": "acme-senior-ai-engineer",
            "kind": "employment",
            "organisation": "Acme AI",
            "title": "Senior AI Engineer",
            "start_date": date(2022, 1, 1),
            "end_date": date(2025, 1, 1),
            "location": "Melbourne",
            "highlights": [
                "Led production AI system ownership and deployment lifecycle.",
                "Partnered with executives on AI delivery initiatives.",
            ],
            "technologies": ["Python", "LLM", "Docker"],
        }
    )


def _employment_ai_mid() -> ExperienceEntry:
    return ExperienceEntry.model_validate(
        {
            "id": "acme-ai-engineer",
            "kind": "employment",
            "organisation": "Acme AI",
            "title": "AI Engineer",
            "start_date": date(2023, 1, 1),
            "end_date": date(2025, 1, 1),
            "location": "Melbourne",
            "highlights": ["Built internal LLM prototypes."],
            "technologies": ["Python", "LLM"],
        }
    )


def _independent_ai_only() -> ExperienceEntry:
    return ExperienceEntry.model_validate(
        {
            "id": "independent-ai-rd",
            "kind": "independent_engineering",
            "organisation": "Independent",
            "title": "AI Engineer - Independent Research & Development",
            "start_date": date(2025, 1, 1),
            "end_date": None,
            "location": "Melbourne",
            "highlights": [
                "Independently develops production-minded AI Engineering projects."
            ],
            "technologies": ["Python", "LLM", "Docker"],
        }
    )


def _kogan_like_assessment(
    *,
    seniority_level: str = "senior",
    role_family: str = "ai_engineering",
    technical: str = "strong",
    commercial: str = "mixed",
    portfolio: str = "strong",
    commercial_findings: list[dict[str, Any]] | None = None,
    technical_findings: list[dict[str, Any]] | None = None,
    title: str = "Senior AI Engineer",
) -> tuple[JobAnalysis, OpportunityAssessment]:
    analysis = job_analysis(
        posting={
            "raw_text": f"{title}. Python required. Melbourne.",
            "title": title,
        },
        role_family={
            "family": role_family,
            "evidence": [{"excerpt": title, "section": "title"}],
        },
        seniority={
            "level": seniority_level,
            "ambiguous": seniority_level == "unknown",
            "evidence": (
                [{"excerpt": title, "section": "title"}]
                if seniority_level != "unknown"
                else []
            ),
        },
    )
    default_commercial = [
        _finding(
            kind="gap",
            summary=(
                "No direct evidence of senior commercial AI ownership or "
                "executive partnership on AI initiatives."
            ),
            job_evidence=[{"source": "seniority", "excerpt": title}],
            profile_evidence=[],
        ),
        _finding(
            kind="partial_alignment",
            summary=(
                "Independent AI delivery supports capability but not senior "
                "commercial AI employment ownership."
            ),
            job_evidence=[
                {
                    "source": "responsibility",
                    "item_index": 0,
                    "name": "Build LLM applications",
                }
            ],
            profile_evidence=[
                {"source": "experience", "ref": "experience:example-role"}
            ],
        ),
    ]
    default_technical = [
        _finding(summary="Required Python aligns with profile skills."),
    ]
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            technical,
            "Technical alignment is strong.",
            technical_findings or default_technical,
        ),
        commercial=_dimension(
            "commercial",
            commercial,
            "Commercial fit is mixed.",
            commercial_findings
            if commercial_findings is not None
            else default_commercial,
        ),
        portfolio=_dimension(
            "portfolio",
            portfolio,
            "Portfolio alignment is strong.",
            [
                _finding(
                    summary="Portfolio supports production-minded AI work.",
                    profile_evidence=[
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Senior AI stretch assessment.",
    )
    return analysis, assessment


def test_senior_ai_without_commercial_evidence_caps_at_consider_silver() -> None:
    analysis, assessment = _kogan_like_assessment()
    strategy = _plan(
        assessment,
        portfolio_match(analysis),
        _profile_with_experience(_independent_ai_only()),
    )

    assert strategy.pursuit_posture == "consider"
    assert strategy.application_tier == "silver"
    assert strategy.effort_level == "targeted"
    assert strategy.practical_value == "acceptable_opportunity"
    assert any("senior" in reason.summary.casefold() for reason in strategy.reasons)
    assert any(
        "seniority" in risk.summary.casefold()
        or "commercial ai" in risk.summary.casefold()
        for risk in strategy.risks_or_gaps
    )


def test_senior_ai_with_direct_commercial_evidence_allows_gold() -> None:
    analysis, assessment = _kogan_like_assessment(
        commercial="moderate",
        commercial_findings=[
            _finding(
                summary="Location and employment type align with preferences.",
                job_evidence=[{"source": "location"}],
                profile_evidence=[
                    {"source": "preference", "ref": "preference:locations"}
                ],
            )
        ],
    )
    strategy = _plan(
        assessment,
        portfolio_match(analysis),
        _profile_with_experience(_employment_ai_senior()),
    )

    assert strategy.pursuit_posture in {"prioritise", "pursue"}
    assert strategy.application_tier in {"platinum", "gold"}
    assert strategy.effort_level in {"full", "targeted"}
    assert strategy.practical_value == "career_priority"
    assert not any(
        reason.kind == "constraint" and "senior commercial" in reason.summary.casefold()
        for reason in strategy.reasons
    )


def test_mid_level_ai_strong_path_remains_gold_capable() -> None:
    analysis, assessment = _kogan_like_assessment(
        seniority_level="mid",
        title="AI Engineer",
        commercial="moderate",
        commercial_findings=[
            _finding(
                summary="Commercial preferences align.",
                job_evidence=[{"source": "location"}],
                profile_evidence=[
                    {"source": "preference", "ref": "preference:locations"}
                ],
            )
        ],
    )
    strategy = _plan(assessment, portfolio_match(analysis), minimal_profile())

    assert strategy.pursuit_posture in {"prioritise", "pursue"}
    assert strategy.application_tier in {"platinum", "gold"}


def test_junior_ai_does_not_apply_seniority_cap() -> None:
    analysis, assessment = _kogan_like_assessment(
        seniority_level="entry",
        title="Junior AI Engineer",
        commercial="mixed",
        commercial_findings=[
            _finding(
                kind="uncertainty",
                summary="Compensation is unstated.",
                job_evidence=[{"source": "compensation"}],
                profile_evidence=[],
            )
        ],
    )
    strategy = _plan(assessment, portfolio_match(analysis), minimal_profile())

    assert strategy.pursuit_posture == "pursue"
    assert strategy.application_tier == "gold"
    assert not any(
        "senior commercial" in reason.summary.casefold() for reason in strategy.reasons
    )


def test_senior_ai_job_side_executive_signal_caps_without_oa_gap() -> None:
    """JobAnalysis CEO/CTO language can trigger stretch when OA under-reports gaps."""
    analysis = job_analysis(
        posting={
            "raw_text": (
                "Senior AI Engineer. Work one-on-one with the CEO and CTO on "
                "high-impact AI initiatives. Python required. Melbourne."
            ),
            "title": "Senior AI Engineer",
        },
        responsibilities=[
            {
                "description": (
                    "Working one-on-one with the CEO/CTO on high-impact special projects."
                ),
                "evidence": [
                    {
                        "excerpt": "Working one-on-one with the CEO/CTO",
                        "section": "responsibilities",
                    }
                ],
            }
        ],
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Technical alignment is strong.",
            [_finding(summary="Required Python aligns with profile skills.")],
        ),
        commercial=_dimension(
            "commercial",
            "moderate",
            "Commercial fit is moderate.",
            [
                _finding(
                    kind="uncertainty",
                    summary="Compensation is unstated.",
                    job_evidence=[{"source": "compensation"}],
                    profile_evidence=[],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio alignment is strong.",
            [
                _finding(
                    summary="Portfolio supports production-minded AI work.",
                    profile_evidence=[
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Executive partnership role with understated OA gaps.",
    )
    strategy = _plan(
        assessment,
        portfolio_match(analysis),
        _profile_with_experience(_independent_ai_only()),
    )

    assert strategy.pursuit_posture == "consider"
    assert strategy.application_tier == "silver"
    assert strategy.effort_level == "targeted"


def test_senior_ai_moderate_commercial_with_material_gap_still_caps() -> None:
    """Findings-driven: moderate commercial + executive gap still caps (not labels alone)."""
    analysis, assessment = _kogan_like_assessment(
        commercial="moderate",
        commercial_findings=[
            _finding(
                kind="gap",
                summary=(
                    "Role requires partnership with CEO/CTO on high-impact AI "
                    "initiatives; profile lacks executive partnership evidence."
                ),
                job_evidence=[{"source": "seniority", "excerpt": "Senior AI Engineer"}],
                profile_evidence=[],
            )
        ],
    )
    strategy = _plan(
        assessment,
        portfolio_match(analysis),
        _profile_with_experience(_independent_ai_only()),
    )

    assert strategy.pursuit_posture == "consider"
    assert strategy.application_tier == "silver"
    assert strategy.effort_level == "targeted"
    assert strategy.practical_value == "acceptable_opportunity"


def test_senior_ai_salary_uncertainty_alone_does_not_cap() -> None:
    analysis, assessment = _kogan_like_assessment(
        commercial="mixed",
        commercial_findings=[
            _finding(
                kind="uncertainty",
                summary="Compensation is unstated and cannot be scored.",
                job_evidence=[{"source": "compensation"}],
                profile_evidence=[],
            )
        ],
    )
    strategy = _plan(assessment, portfolio_match(analysis), minimal_profile())

    assert strategy.pursuit_posture == "pursue"
    assert strategy.application_tier == "gold"
    assert strategy.practical_value == "career_priority"


def test_unknown_seniority_does_not_invent_mismatch() -> None:
    analysis = job_analysis(
        posting={
            "raw_text": "AI Engineer. Python required. Melbourne.",
            "title": "AI Engineer",
        },
        seniority={
            "level": "unknown",
            "ambiguous": False,
            "evidence": [],
        },
    )
    assessment = _assessment_for(
        analysis,
        technical=_dimension(
            "technical",
            "strong",
            "Technical alignment is strong.",
            [_finding(summary="Required Python aligns with profile skills.")],
        ),
        commercial=_dimension(
            "commercial",
            "mixed",
            "Commercial fit is mixed.",
            [
                _finding(
                    kind="gap",
                    summary=(
                        "No direct evidence of senior commercial AI ownership or "
                        "executive partnership on AI initiatives."
                    ),
                    job_evidence=[{"source": "experience_requirement", "item_index": 0}],
                    profile_evidence=[],
                )
            ],
        ),
        portfolio=_dimension(
            "portfolio",
            "strong",
            "Portfolio alignment is strong.",
            [
                _finding(
                    summary="Portfolio supports production-minded AI work.",
                    profile_evidence=[
                        {"source": "project", "ref": "project:example-project"}
                    ],
                )
            ],
        ),
        summary="Unknown seniority assessment.",
    )
    strategy = _plan(assessment, portfolio_match(analysis), minimal_profile())

    assert strategy.pursuit_posture == "pursue"
    assert strategy.application_tier == "gold"
    assert not any(
        reason.kind == "constraint" and "senior" in reason.summary.casefold()
        for reason in strategy.reasons
    )


def test_senior_non_ai_role_is_not_promoted_by_seniority_rule() -> None:
    analysis, assessment = _kogan_like_assessment(
        role_family="network_engineering",
        title="Senior Network Engineer",
        technical="moderate",
        commercial="moderate",
        portfolio="moderate",
        commercial_findings=[
            _finding(
                summary="Location aligns.",
                job_evidence=[{"source": "location"}],
                profile_evidence=[
                    {"source": "preference", "ref": "preference:locations"}
                ],
            )
        ],
        technical_findings=[
            _finding(summary="Some transferable networking skills."),
        ],
    )
    strategy = _plan(assessment, portfolio_match(analysis), minimal_profile())

    assert strategy.pursuit_posture == "do_not_prioritise"
    assert strategy.application_tier == "bronze"


def test_independent_engineering_is_not_senior_commercial_evidence() -> None:
    analysis, assessment = _kogan_like_assessment()
    strategy = _plan(
        assessment,
        portfolio_match(analysis),
        _profile_with_experience(_independent_ai_only()),
    )

    assert strategy.pursuit_posture == "consider"
    assert strategy.application_tier == "silver"


def test_commercial_ai_employment_with_senior_ownership_unlocks_gold() -> None:
    analysis, assessment = _kogan_like_assessment(
        commercial="moderate",
        commercial_findings=[
            _finding(
                summary="Commercial constraints are acceptable.",
                job_evidence=[{"source": "location"}],
                profile_evidence=[
                    {"source": "preference", "ref": "preference:locations"}
                ],
            )
        ],
    )
    # Mid title but production ownership markers in employment highlights.
    mid_with_ownership = _employment_ai_mid().model_copy(
        update={
            "highlights": [
                "Owned production AI deployment and lifecycle governance.",
            ]
        }
    )
    strategy = _plan(
        assessment,
        portfolio_match(analysis),
        _profile_with_experience(mid_with_ownership),
    )

    assert strategy.application_tier in {"platinum", "gold"}
    assert strategy.pursuit_posture in {"prioritise", "pursue"}
