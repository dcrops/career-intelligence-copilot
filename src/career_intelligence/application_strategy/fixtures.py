"""Deterministic application-strategy fixtures for offline architecture tests.

Builders return untrusted strategy payloads (no ``job_analysis``, ``profile``,
``opportunity_assessment``, or ``portfolio_match``). ``ApplicationStrategyService``
binds caller-supplied trusted inputs after planning.

Scenarios key off shared FR-002 posting markers in ``job_analysis.posting.raw_text``
so journeys can chain:

    JobAnalysisService → OpportunityAssessmentService → PortfolioMatchingService
        → ApplicationStrategyService

without duplicating upstream domain structures. Strategy-only markers are added only
where FR-005 needs behaviour that existing shared markers cannot express.

These fixtures are contract scaffolding — not a second recommendation engine.
"""

from __future__ import annotations

from collections.abc import Callable

from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER,
    MARKER_AMBIGUOUS_SENIORITY,
    MARKER_APPLIED_AI,
    MARKER_CONTRACT,
    MARKER_DATA_ENGINEER,
    MARKER_MISSING_SALARY,
    MARKER_NO_TECHNOLOGIES,
    MARKER_WORKING_RIGHTS,
)
from career_intelligence.job_analysis.models import JobPosting

from .planner import ApplicationStrategyPayload

PayloadBuilder = Callable[[], ApplicationStrategyPayload]

# Strategy-only markers for scenarios not encoded by shared FR-002 markers.
MARKER_STRATEGY_SALARY_CONFLICT = "[CIC-FIXTURE:strategy-salary-conflict]"
MARKER_STRATEGY_WEAK_PORTFOLIO = "[CIC-FIXTURE:strategy-weak-portfolio]"
MARKER_STRATEGY_VOLUME = "[CIC-FIXTURE:strategy-volume]"

_LEAD_APPLIED = "operational-intelligence-copilot"
_LEAD_AI_ENGINEER = "governance-document-rag"


def _assessment(
    dimension: str,
    judgment: str,
) -> dict[str, object]:
    return {
        "origin": "opportunity_assessment",
        "assessment_dimension": dimension,
        "assessment_judgment": judgment,
    }


def _job(
    source: str,
    *,
    item_index: int | None = None,
    name: str | None = None,
    excerpt: str | None = None,
) -> dict[str, object]:
    job_evidence: dict[str, object] = {"source": source}
    if item_index is not None:
        job_evidence["item_index"] = item_index
    if name is not None:
        job_evidence["name"] = name
    if excerpt is not None:
        job_evidence["excerpt"] = excerpt
    return {"origin": "job_analysis", "job_evidence": job_evidence}


def _profile(source: str, ref: str) -> dict[str, object]:
    return {
        "origin": "career_profile",
        "profile_evidence": {"source": source, "ref": ref},
    }


def _portfolio(project_id: str) -> dict[str, object]:
    return {
        "origin": "portfolio_match",
        "portfolio_project_id": project_id,
    }


def _reason(
    kind: str,
    summary: str,
    evidence: list[dict[str, object]],
    *,
    importance: str = "material",
) -> dict[str, object]:
    return {
        "kind": kind,
        "summary": summary,
        "importance": importance,
        "evidence": evidence,
    }


def _risk(
    summary: str,
    evidence: list[dict[str, object]],
    *,
    importance: str = "material",
) -> dict[str, object]:
    return {
        "summary": summary,
        "importance": importance,
        "evidence": evidence,
    }


def _check(
    summary: str,
    why_it_matters: str,
    evidence: list[dict[str, object]],
    *,
    could_change_recommendation: bool = True,
) -> dict[str, object]:
    return {
        "summary": summary,
        "why_it_matters": why_it_matters,
        "could_change_recommendation": could_change_recommendation,
        "evidence": evidence,
    }


def _action(
    kind: str,
    summary: str,
    evidence: list[dict[str, object]],
    *,
    related_project_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": kind,
        "summary": summary,
        "evidence": evidence,
    }
    if related_project_id is not None:
        payload["related_project_id"] = related_project_id
    return payload


def _emphasis(
    project_id: str,
    *,
    source_rank: int,
    summary: str,
) -> dict[str, object]:
    return {
        "project_id": project_id,
        "source_rank": source_rank,
        "summary": summary,
        "evidence": [_portfolio(project_id)],
    }


def _strategy(
    *,
    application_tier: str,
    pursuit_posture: str,
    practical_value: str,
    effort_level: str,
    summary: str,
    reasons: list[dict[str, object]],
    next_actions: list[dict[str, object]],
    risks_or_gaps: list[dict[str, object]] | None = None,
    manual_checks: list[dict[str, object]] | None = None,
    portfolio_emphasis: list[dict[str, object]] | None = None,
    assumptions: list[str] | None = None,
    decision_blockers: list[str] | None = None,
    insufficient_information: bool = False,
) -> ApplicationStrategyPayload:
    return {
        "application_tier": application_tier,
        "pursuit_posture": pursuit_posture,
        "practical_value": practical_value,
        "effort_level": effort_level,
        "summary": summary,
        "reasons": reasons,
        "risks_or_gaps": risks_or_gaps or [],
        "manual_checks": manual_checks or [],
        "next_actions": next_actions,
        "portfolio_emphasis": portfolio_emphasis or [],
        "assumptions": assumptions or [],
        "decision_blockers": decision_blockers or [],
        "owner_review_required": True,
        "insufficient_information": insufficient_information,
    }


def strategy_strong_applied_ai() -> ApplicationStrategyPayload:
    """MARKER_APPLIED_AI — strong AI opportunity with portfolio emphasis."""
    return _strategy(
        application_tier="platinum",
        pursuit_posture="prioritise",
        practical_value="career_priority",
        effort_level="full",
        summary=(
            "Recommend posture 'prioritise' with effort tier 'platinum' (full). "
            "Owner review is required before any application action."
        ),
        reasons=[
            _reason(
                "alignment",
                "Technical fit is strong and portfolio fit is strong for this applied AI role.",
                [
                    _assessment("technical", "strong"),
                    _assessment("portfolio", "strong"),
                ],
            ),
            _reason(
                "priority",
                "Pursuit posture prioritise with platinum effort reflects moderate commercial fit and AI alignment.",
                [
                    _assessment("commercial", "moderate"),
                    _job("role_family", excerpt="Applied AI Engineer"),
                ],
            ),
        ],
        risks_or_gaps=[
            _risk(
                "Sydney hybrid location is workable but not Melbourne-first.",
                [
                    _assessment("commercial", "moderate"),
                    _profile("preference", "preference:locations"),
                ],
                importance="minor",
            )
        ],
        next_actions=[
            _action(
                "consider_emphasising_portfolio_projects",
                "Consider emphasising the strongest matched portfolio project(s).",
                [_portfolio(_LEAD_APPLIED)],
                related_project_id=_LEAD_APPLIED,
            ),
            _action(
                "consider_cv_tailoring",
                "Consider whether CV tailoring is worth the effort for this opportunity.",
                [_assessment("technical", "strong")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "strong")],
            ),
        ],
        portfolio_emphasis=[
            _emphasis(
                _LEAD_APPLIED,
                source_rank=1,
                summary="Lead with operational-intelligence-copilot from PortfolioMatch.",
            ),
            _emphasis(
                _LEAD_AI_ENGINEER,
                source_rank=2,
                summary="Also consider governance-document-rag as supporting emphasis.",
            ),
        ],
    )


def strategy_seniority_stretch_ai_engineer() -> ApplicationStrategyPayload:
    """MARKER_AI_ENGINEER — production/seniority stretch with reduced posture."""
    return _strategy(
        application_tier="gold",
        pursuit_posture="pursue",
        practical_value="career_priority",
        effort_level="targeted",
        summary=(
            "Recommend posture 'pursue' with effort tier 'gold' (targeted). "
            "Seniority/production evidence is mixed; owner review is required."
        ),
        reasons=[
            _reason(
                "alignment",
                "Technical fit is mixed and portfolio fit is moderate for this AI Engineer role.",
                [
                    _assessment("technical", "mixed"),
                    _assessment("portfolio", "moderate"),
                ],
            ),
            _reason(
                "priority",
                "Pursue with gold effort: AI-aligned role with commercial compatibility, tempered by production-tenure gaps.",
                [
                    _assessment("commercial", "moderate"),
                    _job("role_family", excerpt="Senior AI Engineer"),
                ],
            ),
        ],
        risks_or_gaps=[
            _risk(
                "Stated seniority/production expectations may exceed currently supported commercial AI employment evidence.",
                [
                    _job("seniority", excerpt="Senior AI Engineer"),
                    _assessment("technical", "mixed"),
                ],
            )
        ],
        manual_checks=[
            _check(
                "Review seniority expectations against demonstrated experience.",
                "A seniority stretch can change whether significant effort is justified.",
                [_job("seniority", excerpt="Senior AI Engineer")],
            )
        ],
        next_actions=[
            _action(
                "consider_reviewing_seniority_expectations",
                "Consider reviewing seniority expectations against demonstrated experience.",
                [_job("seniority", excerpt="Senior AI Engineer")],
            ),
            _action(
                "consider_emphasising_portfolio_projects",
                "Consider emphasising the strongest matched portfolio project(s).",
                [_portfolio(_LEAD_AI_ENGINEER)],
                related_project_id=_LEAD_AI_ENGINEER,
            ),
            _action(
                "consider_cv_tailoring",
                "Consider whether CV tailoring is worth the effort for this opportunity.",
                [_assessment("technical", "mixed")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "mixed")],
            ),
        ],
        portfolio_emphasis=[
            _emphasis(
                _LEAD_AI_ENGINEER,
                source_rank=1,
                summary="Lead with governance-document-rag from PortfolioMatch.",
            )
        ],
    )


def strategy_outside_data_engineer() -> ApplicationStrategyPayload:
    """MARKER_DATA_ENGINEER — outside AI priority; bronze effort guidance."""
    return _strategy(
        application_tier="bronze",
        pursuit_posture="do_not_prioritise",
        practical_value="acceptable_opportunity",
        effort_level="none",
        summary=(
            "Do not prioritise significant effort for this Data Engineer opportunity "
            "(tier bronze, effort none). Bronze means low effort investment guidance, "
            "not an automatic never-apply decision."
        ),
        reasons=[
            _reason(
                "priority",
                "Role family 'data_engineering' is outside the owner's current AI Engineering target set.",
                [_job("role_family", excerpt="Data Engineer")],
            )
        ],
        risks_or_gaps=[
            _risk(
                "Portfolio emphasises AI engineering more than classic data-platform delivery.",
                [_assessment("portfolio", "weak")],
            )
        ],
        next_actions=[
            _action(
                "consider_logging_and_deprioritising",
                "Consider logging the rationale and not investing significant effort.",
                [_assessment("technical", "mixed")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "mixed")],
            ),
        ],
        portfolio_emphasis=[
            _emphasis(
                "governance-document-rag",
                source_rank=1,
                summary="If submitting anyway, PortfolioMatch still ranks projects by shared Python overlap.",
            )
        ],
    )


def strategy_volume_low_fit() -> ApplicationStrategyPayload:
    """Volume-enabled low strategic fit (DATA_ENGINEER or STRATEGY_VOLUME)."""
    return _strategy(
        application_tier="silver",
        pursuit_posture="low_effort_submit",
        practical_value="volume_obligation",
        effort_level="minimal",
        summary=(
            "Strategic fit is limited. If volume applications are desired, consider a "
            "low-effort submission (tier silver, effort minimal). This is a "
            "recommendation only; the owner decides whether to apply."
        ),
        reasons=[
            _reason(
                "practical_value",
                "Strategic fit is limited, but volume applications are enabled.",
                [
                    _assessment("technical", "mixed"),
                    _assessment("commercial", "moderate"),
                ],
            ),
            _reason(
                "priority",
                "Role family is outside the current AI Engineering priority set for significant effort.",
                [_job("role_family")],
            ),
        ],
        assumptions=[
            "Volume applications are enabled; low strategic fit may still justify "
            "minimal-effort submission by owner choice."
        ],
        next_actions=[
            _action(
                "consider_low_effort_application",
                "Consider a low-effort application if you choose to submit for volume reasons.",
                [_assessment("technical", "mixed")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "mixed")],
            ),
        ],
    )


def strategy_insufficient_information() -> ApplicationStrategyPayload:
    """MARKER_WORKING_RIGHTS — sparse assessability + working-rights manual check.

    Shared working-rights OA fixture uses unknown technical and commercial judgments,
    so the canned strategy uses insufficient_information while still surfacing the
    working-rights verification recommendation.
    """
    return _strategy(
        application_tier="bronze",
        pursuit_posture="insufficient_information",
        practical_value="deferred_pending_information",
        effort_level="none",
        summary=(
            "Insufficient information for a confident strategy; gather missing details "
            "and verify working-rights wording before investing significant effort."
        ),
        reasons=[
            _reason(
                "uncertainty",
                "Available job and fit evidence is insufficient for a confident application strategy.",
                [_assessment("technical", "unknown")],
            )
        ],
        manual_checks=[
            _check(
                "Gather missing job requirements and commercial details.",
                "Additional posting detail could change pursuit posture and effort.",
                [_assessment("technical", "unknown")],
            ),
            _check(
                "Verify working-rights wording against your own eligibility.",
                "The posting states a working-rights requirement; the system does not infer eligibility.",
                [_assessment("commercial", "unknown")],
            ),
        ],
        assumptions=[
            "Owner working-rights eligibility is unknown to the system and was not inferred."
        ],
        next_actions=[
            _action(
                "consider_gathering_missing_job_information",
                "Consider gathering missing job information before deciding effort.",
                [_assessment("technical", "unknown")],
            ),
            _action(
                "consider_verifying_working_rights",
                "Consider verifying working-rights wording against your eligibility.",
                [_assessment("commercial", "unknown")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "unknown")],
            ),
        ],
        portfolio_emphasis=[],
        insufficient_information=True,
    )


def strategy_no_technologies_limited() -> ApplicationStrategyPayload:
    """MARKER_NO_TECHNOLOGIES — limited technical assessability; portfolio emphasis available."""
    return _strategy(
        application_tier="silver",
        pursuit_posture="consider",
        practical_value="acceptable_opportunity",
        effort_level="minimal",
        summary=(
            "Recommend posture 'consider' with effort tier 'silver' (minimal). "
            "Technical assessability is limited because technologies are unnamed."
        ),
        reasons=[
            _reason(
                "uncertainty",
                "Technical fit is unknown because the advert names no specific technologies.",
                [_assessment("technical", "unknown")],
            ),
            _reason(
                "priority",
                "Commercial and portfolio signals remain usable enough to consider minimal effort.",
                [
                    _assessment("commercial", "moderate"),
                    _assessment("portfolio", "moderate"),
                ],
            ),
        ],
        next_actions=[
            _action(
                "consider_gathering_missing_job_information",
                "Consider gathering missing technology requirements before investing more effort.",
                [_assessment("technical", "unknown")],
            ),
            _action(
                "consider_emphasising_portfolio_projects",
                "Consider emphasising the responsibility-matched portfolio project.",
                [_portfolio(_LEAD_APPLIED)],
                related_project_id=_LEAD_APPLIED,
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "unknown")],
            ),
        ],
        portfolio_emphasis=[
            _emphasis(
                _LEAD_APPLIED,
                source_rank=1,
                summary="PortfolioMatch ranks operational-intelligence-copilot on responsibility overlap.",
            )
        ],
    )


def strategy_salary_unknown() -> ApplicationStrategyPayload:
    """MARKER_MISSING_SALARY — no invented salary conflict."""
    return _strategy(
        application_tier="gold",
        pursuit_posture="pursue",
        practical_value="career_priority",
        effort_level="targeted",
        summary=(
            "Recommend posture 'pursue' with effort tier 'gold' (targeted). "
            "Compensation is unstated; no salary conflict was invented."
        ),
        reasons=[
            _reason(
                "alignment",
                "Technical fit is moderate and portfolio fit remains usable.",
                [
                    _assessment("technical", "moderate"),
                    _assessment("portfolio", "moderate"),
                ],
            )
        ],
        manual_checks=[
            _check(
                "Review compensation once salary or rate information is available.",
                "Compensation clarity can change commercial priority.",
                [_job("compensation")],
            )
        ],
        assumptions=[
            "Compensation fit is not scored because salary/rate evidence is missing or ambiguous.",
            "No candidate salary minimum is configured, so compensation was not treated as a hard threshold conflict.",
        ],
        next_actions=[
            _action(
                "consider_reviewing_compensation",
                "Consider reviewing compensation before investing significant effort.",
                [_job("compensation")],
            ),
            _action(
                "consider_cv_tailoring",
                "Consider whether CV tailoring is worth the effort for this opportunity.",
                [_assessment("technical", "moderate")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "moderate")],
            ),
        ],
    )


def strategy_employment_and_location_conflict() -> ApplicationStrategyPayload:
    """MARKER_CONTRACT — employment blocker with location friction."""
    return _strategy(
        application_tier="bronze",
        pursuit_posture="do_not_prioritise",
        practical_value="acceptable_opportunity",
        effort_level="none",
        summary=(
            "Do not prioritise significant effort (tier bronze, effort none) because "
            "contract engagement conflicts with the confirmed full-time preference."
        ),
        reasons=[
            _reason(
                "constraint",
                "Job engagement type is contract, but the profile preference is full-time only.",
                [
                    _job("employment", excerpt="Full-time contract (initial 6 months)"),
                    _profile("preference", "preference:employment_types"),
                ],
            )
        ],
        risks_or_gaps=[
            _risk(
                "Sydney hybrid on-site expectations add commercial friction.",
                [_assessment("commercial", "mixed")],
                importance="minor",
            )
        ],
        decision_blockers=[
            "Job engagement type is contract, but the profile preference is full-time only."
        ],
        manual_checks=[
            _check(
                "Review location and work-arrangement expectations.",
                "Soft location mismatches should be accepted consciously by the owner.",
                [_job("work_arrangement", excerpt="Hybrid Sydney, 3 days on-site")],
            )
        ],
        next_actions=[
            _action(
                "consider_logging_and_deprioritising",
                "Consider logging the rationale and not investing significant effort.",
                [_assessment("technical", "moderate")],
            ),
            _action(
                "consider_reviewing_location_or_arrangement",
                "Consider reviewing location or work-arrangement expectations.",
                [_job("work_arrangement", excerpt="Hybrid Sydney, 3 days on-site")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "moderate")],
            ),
        ],
    )


def strategy_ambiguous_seniority() -> ApplicationStrategyPayload:
    """MARKER_AMBIGUOUS_SENIORITY — seniority uncertainty reduces confidence."""
    return _strategy(
        application_tier="silver",
        pursuit_posture="consider",
        practical_value="acceptable_opportunity",
        effort_level="minimal",
        summary=(
            "Recommend posture 'consider' with effort tier 'silver' (minimal). "
            "Seniority expectations are ambiguous."
        ),
        reasons=[
            _reason(
                "uncertainty",
                "Seniority is ambiguous, so pursuit confidence is limited.",
                [_assessment("technical", "mixed")],
            )
        ],
        risks_or_gaps=[
            _risk(
                "Ambiguous senior/lead expectations could change the right effort level.",
                [_job("seniority")],
            )
        ],
        manual_checks=[
            _check(
                "Review seniority expectations against demonstrated experience.",
                "Ambiguous seniority can change whether significant effort is justified.",
                [_job("seniority")],
            )
        ],
        next_actions=[
            _action(
                "consider_reviewing_seniority_expectations",
                "Consider reviewing seniority expectations against demonstrated experience.",
                [_job("seniority")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "mixed")],
            ),
        ],
    )


def strategy_salary_conflict() -> ApplicationStrategyPayload:
    """MARKER_STRATEGY_SALARY_CONFLICT — confirmed salary below minimum."""
    return _strategy(
        application_tier="silver",
        pursuit_posture="consider",
        practical_value="acceptable_opportunity",
        effort_level="minimal",
        summary=(
            "Recommend posture 'consider' with effort tier 'silver' (minimal) because "
            "stated compensation appears below the confirmed salary minimum."
        ),
        reasons=[
            _reason(
                "constraint",
                "Stated compensation appears below the confirmed salary minimum.",
                [
                    _job("compensation"),
                    _profile("preference", "preference:salary_min"),
                ],
            )
        ],
        risks_or_gaps=[
            _risk(
                "Stated compensation appears below the confirmed salary minimum.",
                [
                    _job("compensation"),
                    _profile("preference", "preference:salary_min"),
                ],
            )
        ],
        manual_checks=[
            _check(
                "Confirm whether the stated compensation is acceptable.",
                "A confirmed salary minimum conflict may justify deprioritising significant effort.",
                [
                    _job("compensation"),
                    _profile("preference", "preference:salary_min"),
                ],
            )
        ],
        next_actions=[
            _action(
                "consider_reviewing_compensation",
                "Consider reviewing compensation before investing significant effort.",
                [_job("compensation")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "strong")],
            ),
        ],
    )


def strategy_weak_portfolio() -> ApplicationStrategyPayload:
    """MARKER_STRATEGY_WEAK_PORTFOLIO — strong technical path without portfolio emphasis."""
    return _strategy(
        application_tier="gold",
        pursuit_posture="pursue",
        practical_value="career_priority",
        effort_level="targeted",
        summary=(
            "Recommend posture 'pursue' with effort tier 'gold' (targeted). "
            "Technical fit remains usable despite weak portfolio evidence."
        ),
        reasons=[
            _reason(
                "alignment",
                "Technical fit is strong even though portfolio evidence is weak.",
                [
                    _assessment("technical", "strong"),
                    _assessment("portfolio", "weak"),
                ],
            )
        ],
        risks_or_gaps=[
            _risk(
                "Portfolio evidence is weak or insufficient for ranked emphasis.",
                [_assessment("portfolio", "weak")],
            )
        ],
        next_actions=[
            _action(
                "consider_cv_tailoring",
                "Consider whether CV tailoring is worth the effort for this opportunity.",
                [_assessment("technical", "strong")],
            ),
            _action(
                "consider_owner_review",
                "Consider reviewing this full strategy before taking any external action.",
                [_assessment("technical", "strong")],
            ),
        ],
        portfolio_emphasis=[],
    )


def posting_strategy_salary_conflict() -> JobPosting:
    """Minimal posting carrying the strategy-only salary-conflict marker."""
    return JobPosting(
        title="AI Engineer",
        company="Fixture Co",
        raw_text=(
            f"{MARKER_STRATEGY_SALARY_CONFLICT}\n"
            "AI Engineer. Python required. Salary $90,000-$110,000 AUD."
        ),
    )


def posting_strategy_weak_portfolio() -> JobPosting:
    """Minimal posting carrying the strategy-only weak-portfolio marker."""
    return JobPosting(
        title="AI Engineer",
        company="Fixture Co",
        raw_text=(
            f"{MARKER_STRATEGY_WEAK_PORTFOLIO}\n"
            "AI Engineer. Python required. Hybrid Melbourne."
        ),
    )


def posting_strategy_volume() -> JobPosting:
    """Minimal posting carrying the strategy-only volume marker."""
    return JobPosting(
        title="Data Engineer",
        company="Fixture Co",
        raw_text=(
            f"{MARKER_STRATEGY_VOLUME}\n"
            "Data Engineer. Python required. Hybrid Melbourne."
        ),
    )


STRATEGY_FIXTURE_BUILDERS: dict[str, PayloadBuilder] = {
    MARKER_APPLIED_AI: strategy_strong_applied_ai,
    MARKER_AI_ENGINEER: strategy_seniority_stretch_ai_engineer,
    MARKER_DATA_ENGINEER: strategy_outside_data_engineer,
    MARKER_WORKING_RIGHTS: strategy_insufficient_information,
    MARKER_NO_TECHNOLOGIES: strategy_no_technologies_limited,
    MARKER_MISSING_SALARY: strategy_salary_unknown,
    MARKER_CONTRACT: strategy_employment_and_location_conflict,
    MARKER_AMBIGUOUS_SENIORITY: strategy_ambiguous_seniority,
    MARKER_STRATEGY_SALARY_CONFLICT: strategy_salary_conflict,
    MARKER_STRATEGY_WEAK_PORTFOLIO: strategy_weak_portfolio,
    MARKER_STRATEGY_VOLUME: strategy_outside_data_engineer,
}

VOLUME_OVERRIDE_MARKERS: frozenset[str] = frozenset(
    {
        MARKER_DATA_ENGINEER,
        MARKER_STRATEGY_VOLUME,
    }
)

# Re-export shared markers for tests that compose FR-005 fixtures.
__all__ = [
    "MARKER_STRATEGY_SALARY_CONFLICT",
    "MARKER_STRATEGY_VOLUME",
    "MARKER_STRATEGY_WEAK_PORTFOLIO",
    "STRATEGY_FIXTURE_BUILDERS",
    "VOLUME_OVERRIDE_MARKERS",
    "posting_strategy_salary_conflict",
    "posting_strategy_volume",
    "posting_strategy_weak_portfolio",
    "strategy_ambiguous_seniority",
    "strategy_employment_and_location_conflict",
    "strategy_insufficient_information",
    "strategy_no_technologies_limited",
    "strategy_outside_data_engineer",
    "strategy_salary_conflict",
    "strategy_salary_unknown",
    "strategy_seniority_stretch_ai_engineer",
    "strategy_strong_applied_ai",
    "strategy_volume_low_fit",
    "strategy_weak_portfolio",
]
