"""Deterministic portfolio-match fixtures for offline architecture tests.

Builders return untrusted match payloads (no ``job_analysis`` or ``profile``).
``PortfolioMatchingService`` binds caller-supplied trusted inputs after matching.

Scenarios key off shared FR-002 posting markers in ``job_analysis.posting.raw_text``
so journeys can chain JobAnalysisService → PortfolioMatchingService without
duplicating JobAnalysis structures in this package.

Canned rankings are aligned to ``tests/fixtures/golden/career_profile.yaml``
project ids and to the technology/responsibility indexes of the corresponding
FR-002 fixture analyses.
"""

from __future__ import annotations

from collections.abc import Callable

from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER,
    MARKER_APPLIED_AI,
    MARKER_DATA_ENGINEER,
    MARKER_NO_TECHNOLOGIES,
    MARKER_WORKING_RIGHTS,
)

from .matcher import PortfolioMatchPayload

PayloadBuilder = Callable[[], PortfolioMatchPayload]

# Portfolio-matching-only marker for an explicit tie-group service-contract scenario.
MARKER_PORTFOLIO_TIE = "[CIC-FIXTURE:portfolio-tie]"

_GOLDEN_PROJECT_IDS = (
    "operational-intelligence-copilot",
    "governance-document-rag",
    "payroll-diagnostics-engine",
    "public-holiday-entitlements",
)


def _job(
    source: str,
    *,
    item_index: int | None = None,
    name: str | None = None,
    excerpt: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"source": source}
    if item_index is not None:
        payload["item_index"] = item_index
    if name is not None:
        payload["name"] = name
    if excerpt is not None:
        payload["excerpt"] = excerpt
    return payload


def _project_ref(project_id: str, *, excerpt: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "source": "project",
        "ref": f"project:{project_id}",
    }
    if excerpt is not None:
        payload["excerpt"] = excerpt
    return payload


def _factor(
    kind: str,
    summary: str,
    *,
    job_evidence: list[dict[str, object]],
    project_id: str,
    excerpt: str | None = None,
) -> dict[str, object]:
    return {
        "kind": kind,
        "summary": summary,
        "job_evidence": job_evidence,
        "profile_evidence": [_project_ref(project_id, excerpt=excerpt)],
    }


def _ranked(
    rank: int,
    project_id: str,
    rationale: str,
    factors: list[dict[str, object]],
    *,
    tie_group: int | None = None,
    tie_break_reason: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "rank": rank,
        "project_id": project_id,
        "rationale": rationale,
        "factors": factors,
    }
    if tie_group is not None:
        payload["tie_group"] = tie_group
        payload["tie_break_reason"] = tie_break_reason
    return payload


def _match(
    ranked: list[dict[str, object]],
    *,
    summary: str,
    insufficient_evidence: bool = False,
) -> PortfolioMatchPayload:
    ranked_ids = {entry["project_id"] for entry in ranked}
    unranked = [project_id for project_id in _GOLDEN_PROJECT_IDS if project_id not in ranked_ids]
    return {
        "ranked_projects": ranked,
        "unranked_project_ids": unranked,
        "summary": summary,
        "insufficient_evidence": insufficient_evidence,
    }


def match_ai_engineer() -> PortfolioMatchPayload:
    """AI Engineer fixture: LangChain-capable RAG project leads."""
    rag = "governance-document-rag"
    ops = "operational-intelligence-copilot"
    return _match(
        [
            _ranked(
                1,
                rag,
                "Strongest required Python plus preferred LangChain overlap.",
                [
                    _factor(
                        "required_technology",
                        "Project evidence supports required technology 'Python'.",
                        job_evidence=[
                            _job(
                                "technology",
                                item_index=0,
                                name="Python",
                                excerpt="Strong Python required",
                            )
                        ],
                        project_id=rag,
                        excerpt="Python",
                    ),
                    _factor(
                        "preferred_technology",
                        "Project evidence supports preferred technology 'LangChain'.",
                        job_evidence=[
                            _job(
                                "technology",
                                item_index=1,
                                name="LangChain",
                                excerpt="LangChain experience preferred",
                            )
                        ],
                        project_id=rag,
                        excerpt="LangChain",
                    ),
                    _factor(
                        "responsibility_overlap",
                        "Project technologies overlap LLM application responsibilities.",
                        job_evidence=[
                            _job(
                                "responsibility",
                                item_index=0,
                                excerpt=(
                                    "Build and maintain LLM applications using "
                                    "Python and LangChain"
                                ),
                            )
                        ],
                        project_id=rag,
                        excerpt="LangChain",
                    ),
                ],
            ),
            _ranked(
                2,
                ops,
                "Required Python and LLM responsibility overlap without LangChain.",
                [
                    _factor(
                        "required_technology",
                        "Project evidence supports required technology 'Python'.",
                        job_evidence=[
                            _job(
                                "technology",
                                item_index=0,
                                name="Python",
                                excerpt="Strong Python required",
                            )
                        ],
                        project_id=ops,
                        excerpt="Python",
                    ),
                    _factor(
                        "responsibility_overlap",
                        "Project technologies overlap LLM application responsibilities.",
                        job_evidence=[
                            _job(
                                "responsibility",
                                item_index=0,
                                excerpt=(
                                    "Build and maintain LLM applications using "
                                    "Python and LangChain"
                                ),
                            )
                        ],
                        project_id=ops,
                        excerpt="Python",
                    ),
                ],
            ),
        ],
        summary=(
            "Ranked AI-engineering portfolio matches; lead with "
            "governance-document-rag."
        ),
    )


def match_applied_ai() -> PortfolioMatchPayload:
    """Applied AI fixture: FastAPI/OpenAI operational project leads with RAG close behind."""
    ops = "operational-intelligence-copilot"
    rag = "governance-document-rag"
    return _match(
        [
            _ranked(
                1,
                ops,
                "Required Python and FastAPI with applied-AI demonstrates overlap.",
                [
                    _factor(
                        "required_technology",
                        "Project evidence supports required technology 'Python'.",
                        job_evidence=[
                            _job(
                                "technology",
                                item_index=0,
                                name="Python",
                                excerpt="Python and FastAPI required",
                            )
                        ],
                        project_id=ops,
                        excerpt="Python",
                    ),
                    _factor(
                        "required_technology",
                        "Project evidence supports required technology 'FastAPI'.",
                        job_evidence=[
                            _job(
                                "technology",
                                item_index=1,
                                name="FastAPI",
                                excerpt="Python and FastAPI required",
                            )
                        ],
                        project_id=ops,
                        excerpt="FastAPI",
                    ),
                    _factor(
                        "demonstrates_overlap",
                        "Demonstrates explainable AI recommendations for applied delivery.",
                        job_evidence=[
                            _job(
                                "responsibility",
                                item_index=0,
                                excerpt=(
                                    "Deliver applied AI prototypes into production services"
                                ),
                            )
                        ],
                        project_id=ops,
                        excerpt="Explainable AI recommendations",
                    ),
                ],
            ),
            _ranked(
                2,
                rag,
                "Required Python and FastAPI with production-service responsibility overlap.",
                [
                    _factor(
                        "required_technology",
                        "Project evidence supports required technology 'Python'.",
                        job_evidence=[
                            _job(
                                "technology",
                                item_index=0,
                                name="Python",
                                excerpt="Python and FastAPI required",
                            )
                        ],
                        project_id=rag,
                        excerpt="Python",
                    ),
                    _factor(
                        "required_technology",
                        "Project evidence supports required technology 'FastAPI'.",
                        job_evidence=[
                            _job(
                                "technology",
                                item_index=1,
                                name="FastAPI",
                                excerpt="Python and FastAPI required",
                            )
                        ],
                        project_id=rag,
                        excerpt="FastAPI",
                    ),
                    _factor(
                        "responsibility_overlap",
                        "Project summary overlaps production-service delivery language.",
                        job_evidence=[
                            _job(
                                "responsibility",
                                item_index=0,
                                excerpt=(
                                    "Deliver applied AI prototypes into production services"
                                ),
                            )
                        ],
                        project_id=rag,
                        excerpt="Enterprise retrieval-augmented generation platform",
                    ),
                ],
            ),
        ],
        summary=(
            "Ranked applied-AI portfolio matches; lead with "
            "operational-intelligence-copilot."
        ),
    )


def match_data_engineer() -> PortfolioMatchPayload:
    """Data Engineer fixture: Python-only ties; RAG does not uniquely lead."""
    reason = "equal primary ranking signals; ordered by stable project_id ascending"

    def python_factor(project_id: str) -> dict[str, object]:
        return _factor(
            "required_technology",
            "Project evidence supports required technology 'Python'.",
            job_evidence=[
                _job(
                    "technology",
                    item_index=0,
                    name="Python",
                    excerpt="Python and SQL required",
                )
            ],
            project_id=project_id,
            excerpt="Python",
        )

    ordered = sorted(_GOLDEN_PROJECT_IDS)
    ranked = [
        _ranked(
            index + 1,
            project_id,
            "Shared required Python overlap without stronger data-stack differentiation.",
            [python_factor(project_id)],
            tie_group=1,
            tie_break_reason=reason,
        )
        for index, project_id in enumerate(ordered)
    ]
    return _match(
        ranked,
        summary=(
            "Data-engineering signals currently differentiate poorly across portfolio "
            "projects; ordering uses stable project_id ties."
        ),
    )


def match_no_technologies() -> PortfolioMatchPayload:
    """No-technologies fixture: responsibility-only ranking remains possible."""
    ops = "operational-intelligence-copilot"
    return _match(
        [
            _ranked(
                1,
                ops,
                "Responsibility overlap with operational AI workflow evidence.",
                [
                    _factor(
                        "demonstrates_overlap",
                        "Demonstrates overlap with AI-assisted operational workflows.",
                        job_evidence=[
                            _job(
                                "responsibility",
                                item_index=0,
                                excerpt=(
                                    "Improve operational workflows with AI-assisted tooling"
                                ),
                            )
                        ],
                        project_id=ops,
                        excerpt="Explainable AI recommendations",
                    )
                ],
            )
        ],
        summary=(
            "Responsibility-only ranking; lead with operational-intelligence-copilot."
        ),
    )


def match_working_rights_insufficient() -> PortfolioMatchPayload:
    """Working-rights fixture: no usable technologies or responsibilities."""
    return {
        "ranked_projects": [],
        "unranked_project_ids": list(_GOLDEN_PROJECT_IDS),
        "summary": (
            "Insufficient job evidence for portfolio ranking: the analysis has no "
            "usable technologies or responsibilities."
        ),
        "insufficient_evidence": True,
    }


def match_portfolio_tie() -> PortfolioMatchPayload:
    """Explicit tie-group contract scenario for two equally evidenced projects."""
    reason = "equal primary ranking signals; ordered by stable project_id ascending"
    first = "governance-document-rag"
    second = "operational-intelligence-copilot"

    def shared_factor(project_id: str) -> dict[str, object]:
        return _factor(
            "required_technology",
            "Project evidence supports required technology 'Python'.",
            job_evidence=[
                _job(
                    "technology",
                    item_index=0,
                    name="Python",
                    excerpt="Python required",
                )
            ],
            project_id=project_id,
            excerpt="Python",
        )

    return _match(
        [
            _ranked(
                1,
                first,
                "Tied required Python overlap; ordered by project_id.",
                [shared_factor(first)],
                tie_group=1,
                tie_break_reason=reason,
            ),
            _ranked(
                2,
                second,
                "Tied required Python overlap; ordered by project_id.",
                [shared_factor(second)],
                tie_group=1,
                tie_break_reason=reason,
            ),
        ],
        summary="Tied portfolio matches resolved by stable project_id ordering.",
    )


MATCH_FIXTURE_BUILDERS: dict[str, PayloadBuilder] = {
    MARKER_AI_ENGINEER: match_ai_engineer,
    MARKER_APPLIED_AI: match_applied_ai,
    MARKER_DATA_ENGINEER: match_data_engineer,
    MARKER_NO_TECHNOLOGIES: match_no_technologies,
    MARKER_WORKING_RIGHTS: match_working_rights_insufficient,
    MARKER_PORTFOLIO_TIE: match_portfolio_tie,
}
