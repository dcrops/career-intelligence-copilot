"""Unit tests for DeterministicMatcher ranking behaviour."""

from __future__ import annotations

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.portfolio_matching.service import PortfolioMatchingService
from career_intelligence.profile.models import CareerProfile


def _project(
    project_id: str,
    *,
    technologies: list[str] | None = None,
    demonstrates: list[str] | None = None,
    summary: str = "Generic project summary.",
    outcomes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": project_id,
        "name": project_id.replace("-", " ").title(),
        "summary": summary,
        "technologies": technologies or [],
        "outcomes": outcomes or [],
        "url": None,
        "demonstrates": demonstrates or [],
    }


def _profile(*projects: dict[str, object]) -> CareerProfile:
    return CareerProfile.model_validate(
        {
            "schema_version": "1",
            "identity": {
                "full_name": "Test Candidate",
                "target_role": "AI Engineer",
            },
            "experience": [],
            "skills": {"technical": [{"name": "Python"}]},
            "projects": list(projects),
            "certifications": [],
            "goals": {"primary": "Secure an AI Engineering role."},
            "preferences": {"remote": "flexible"},
        }
    )


def _job_analysis(
    *,
    technologies: list[dict[str, object]] | None = None,
    responsibilities: list[dict[str, object]] | None = None,
) -> JobAnalysis:
    return JobAnalysis.model_validate(
        {
            "posting": {"raw_text": "Fixture posting for deterministic matcher tests."},
            "role_family": {"family": "unknown"},
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": technologies or [],
            "responsibilities": responsibilities or [],
            "compensation": {"clarity": "unstated"},
            "location": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
            "employment": {},
            "experience_requirements": [],
        }
    )


def _tech(name: str, level: str) -> dict[str, object]:
    return {
        "name": name,
        "level": level,
        "evidence": [{"excerpt": f"{name} {level}", "section": "requirements"}],
    }


def _responsibility(description: str) -> dict[str, object]:
    return {
        "description": description,
        "evidence": [{"excerpt": description, "section": "responsibilities"}],
    }


def _ranks(payload: dict[str, object]) -> list[str]:
    return [entry["project_id"] for entry in payload["ranked_projects"]]


def test_required_technology_outranks_preferred_only_match() -> None:
    profile = _profile(
        _project("preferred-only", technologies=["LangChain"]),
        _project("required-hit", technologies=["Python"]),
    )
    job = _job_analysis(
        technologies=[
            _tech("Python", "required"),
            _tech("LangChain", "preferred"),
        ]
    )

    payload = DeterministicMatcher().match(job, profile)

    assert _ranks(payload) == ["required-hit", "preferred-only"]
    assert payload["insufficient_evidence"] is False


def test_preferred_technology_outranks_unspecified_only_match() -> None:
    profile = _profile(
        _project("unspecified-only", technologies=["Docker"]),
        _project("preferred-hit", technologies=["FastAPI"]),
    )
    job = _job_analysis(
        technologies=[
            _tech("FastAPI", "preferred"),
            _tech("Docker", "unspecified"),
        ]
    )

    payload = DeterministicMatcher().match(job, profile)

    assert _ranks(payload) == ["preferred-hit", "unspecified-only"]


def test_responsibility_only_ranking() -> None:
    profile = _profile(
        _project(
            "weak-overlap",
            summary="Maintains batch reporting dashboards.",
            outcomes=["Produces weekly status packs."],
        ),
        _project(
            "strong-overlap",
            summary="Builds retrieval pipelines for enterprise knowledge.",
            outcomes=["Ships grounded document answers."],
            technologies=["Python"],
        ),
    )
    job = _job_analysis(
        responsibilities=[
            _responsibility("Build and maintain retrieval pipelines for documents")
        ]
    )

    payload = DeterministicMatcher().match(job, profile)

    assert payload["insufficient_evidence"] is False
    assert _ranks(payload)[0] == "strong-overlap"
    assert "weak-overlap" in payload["unranked_project_ids"] or _ranks(payload)[-1] == (
        "weak-overlap"
    )


def test_demonstrates_overlap() -> None:
    profile = _profile(
        _project(
            "demo-project",
            demonstrates=["Retrieval orchestration", "Grounding validation"],
            summary="Unrelated summary without retrieval wording.",
        ),
        _project(
            "no-demo",
            summary="Unrelated analytics workbook.",
            outcomes=["Exports spreadsheets."],
        ),
    )
    job = _job_analysis(
        responsibilities=[_responsibility("Own retrieval orchestration for documents")]
    )

    payload = DeterministicMatcher().match(job, profile)

    assert _ranks(payload) == ["demo-project"]
    assert payload["unranked_project_ids"] == ["no-demo"]
    kinds = [factor["kind"] for factor in payload["ranked_projects"][0]["factors"]]
    assert "demonstrates_overlap" in kinds


def test_zero_overlap_projects_become_unranked() -> None:
    profile = _profile(
        _project("python-project", technologies=["Python"]),
        _project("unrelated", technologies=["Cobol"], summary="Legacy mainframe tools."),
    )
    job = _job_analysis(technologies=[_tech("Python", "required")])

    payload = DeterministicMatcher().match(job, profile)

    assert _ranks(payload) == ["python-project"]
    assert payload["unranked_project_ids"] == ["unrelated"]


def test_empty_signal_job_produces_insufficient_evidence() -> None:
    profile = _profile(
        _project("alpha", technologies=["Python"]),
        _project("beta", technologies=["FastAPI"]),
    )
    job = _job_analysis(technologies=[], responsibilities=[])

    payload = DeterministicMatcher().match(job, profile)

    assert payload["ranked_projects"] == []
    assert payload["insufficient_evidence"] is True
    assert payload["unranked_project_ids"] == ["alpha", "beta"]
    assert "Insufficient job evidence" in payload["summary"]


def test_ties_produce_tie_group_and_deterministic_ordering() -> None:
    profile = _profile(
        _project("zeta-project", technologies=["Python"]),
        _project("alpha-project", technologies=["Python"]),
    )
    job = _job_analysis(technologies=[_tech("Python", "required")])

    payload = DeterministicMatcher().match(job, profile)

    assert _ranks(payload) == ["alpha-project", "zeta-project"]
    ranked = payload["ranked_projects"]
    assert ranked[0]["tie_group"] == ranked[1]["tie_group"] == 1
    assert ranked[0]["tie_break_reason"] is not None
    assert "project_id" in ranked[0]["tie_break_reason"]


def test_repeated_runs_produce_identical_output() -> None:
    profile = _profile(
        _project("governance-document-rag", technologies=["Python", "LangChain"]),
        _project("payroll-diagnostics-engine", technologies=["Python", "Pandas"]),
        _project(
            "operational-intelligence-copilot",
            technologies=["Python", "FastAPI", "OpenAI"],
            demonstrates=["Explainable AI recommendations"],
        ),
    )
    job = _job_analysis(
        technologies=[
            _tech("Python", "required"),
            _tech("LangChain", "preferred"),
        ],
        responsibilities=[
            _responsibility("Deliver explainable AI recommendations for executives")
        ],
    )
    matcher = DeterministicMatcher()

    first = matcher.match(job, profile)
    second = matcher.match(job, profile)

    assert first == second


def test_every_emitted_factor_has_valid_job_and_profile_evidence() -> None:
    profile = _profile(
        _project(
            "rich-project",
            technologies=["Python", "LangChain"],
            demonstrates=["Retrieval orchestration"],
            summary="Builds retrieval pipelines with Python.",
            outcomes=["Grounded answers over documents."],
        )
    )
    job = _job_analysis(
        technologies=[
            _tech("Python", "required"),
            _tech("LangChain", "preferred"),
            _tech("Docker", "unspecified"),
        ],
        responsibilities=[
            _responsibility("Own retrieval orchestration and grounded answers")
        ],
    )

    payload = DeterministicMatcher().match(job, profile)
    factors = payload["ranked_projects"][0]["factors"]

    assert factors
    for factor in factors:
        assert factor["job_evidence"]
        assert factor["profile_evidence"]
        for profile_ref in factor["profile_evidence"]:
            assert profile_ref["source"] == "project"
            assert profile_ref["ref"] == "project:rich-project"
        for job_ref in factor["job_evidence"]:
            assert "source" in job_ref
            if job_ref["source"] in {"technology", "responsibility"}:
                assert isinstance(job_ref["item_index"], int)


def test_service_successfully_validates_matcher_output() -> None:
    profile = _profile(
        _project("lead-project", technologies=["Python"]),
        _project("other-project", technologies=["Excel"]),
    )
    job = _job_analysis(technologies=[_tech("Python", "required")])
    service = PortfolioMatchingService(DeterministicMatcher())

    match = service.match(job, profile)

    assert match.ranked_projects[0].project_id == "lead-project"
    assert match.unranked_project_ids == ["other-project"]
    assert match.job_analysis is job
    assert match.insufficient_evidence is False
    for ranked in match.ranked_projects:
        assert ranked.factors
        for factor in ranked.factors:
            assert factor.job_evidence
            assert any(
                ref.ref == f"project:{ranked.project_id}"
                for ref in factor.profile_evidence
            )


def test_technology_match_in_summary_and_outcomes() -> None:
    profile = _profile(
        _project(
            "summary-hit",
            summary="Production system built around FastAPI services.",
        ),
        _project(
            "outcome-hit",
            outcomes=["Delivered LangChain evaluation harness."],
        ),
    )
    job = _job_analysis(
        technologies=[
            _tech("FastAPI", "required"),
            _tech("LangChain", "preferred"),
        ]
    )

    payload = DeterministicMatcher().match(job, profile)

    assert set(_ranks(payload)) == {"summary-hit", "outcome-hit"}
    assert _ranks(payload)[0] == "summary-hit"


def test_no_percentage_or_score_fields() -> None:
    profile = _profile(_project("python-project", technologies=["Python"]))
    job = _job_analysis(technologies=[_tech("Python", "required")])

    payload = DeterministicMatcher().match(job, profile)

    serialized = str(payload).casefold()
    assert "percentage" not in serialized
    assert "match_score" not in serialized
    assert "confidence" not in serialized
