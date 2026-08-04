"""Rematch + replan preferred strategy packages after FR-004 calibration.

Keeps stored JobAnalysis + OpportunityAssessment (no OpenAI).
Rewrites PortfolioMatch + ApplicationStrategy with calibrated DeterministicMatcher
and DeterministicStrategyPlanner. Writes to manual_validation/outputs/live/.

Usage:
  conda run -n ai311 python scripts/rematch_replan_calibrated.py
  conda run -n ai311 python scripts/rematch_replan_calibrated.py --stems 001_strong_ai_engineer,017_mars_recruitment_AI_Engineer
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from career_intelligence.application_strategy import (
    ApplicationStrategyService,
    SearchOperatingContext,
)
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.portfolio_matching.service import PortfolioMatchingService
from career_intelligence.profile import CareerProfileService

REPO = Path(__file__).resolve().parents[1]
OUTS = REPO / "manual_validation" / "outputs"
LIVE = OUTS / "live"
FIXTURES = REPO / "tests" / "fixtures" / "application_strategy"


def preferred_path(stem: str) -> Path | None:
    """Prefer regression fixtures, then root baselines, then live owner runs."""
    for candidate in (
        FIXTURES / f"{stem}.json",
        OUTS / f"{stem}.json",
        LIVE / f"{stem}.json",
    ):
        if candidate.is_file():
            return candidate
    return None


# Ranking-affected preferred packages from post-calibration corpus compare.
DEFAULT_STEMS = [
    "001_strong_ai_engineer",
    "002_bluefin_ai_systems_developer",
    "006_senior_ai_engineer_kogan",
    "008_repurpose_it_ai_adoption_specialist",
    "010_pisell_ai_quality_systems_reliability_engineer",
    "013_pay_com_au_ai_automation_engineer",
    "014_anton_ai_automation_engineer",
    "015_expedient_software_junior_full_stack_developer",
    "017_mars_recruitment_AI_Engineer",
    "job",
]


def preferred_path(stem: str) -> Path | None:
    """Prefer immutable root baselines when present; else live owner runs."""
    root = OUTS / f"{stem}.json"
    if root.is_file():
        return root
    live = LIVE / f"{stem}.json"
    if live.is_file():
        return live
    return None


def rematch_replan(stem: str) -> dict:
    path = preferred_path(stem)
    if path is None:
        raise FileNotFoundError(stem)
    payload = json.loads(path.read_text(encoding="utf-8"))
    before = [
        e["project_id"]
        for e in (payload.get("portfolio_match") or {}).get("ranked_projects") or []
    ]
    before_emphasis = (
        payload.get("application_strategy") or payload.get("strategy") or {}
    ).get("portfolio_emphasis") or []
    before_ids = [
        item.get("project_id") if isinstance(item, dict) else None
        for item in before_emphasis
    ]

    profile = CareerProfileService.from_path(REPO / "data" / "career_profile.yaml").load()
    job_analysis = JobAnalysis.model_validate(payload["job_analysis"])
    match = PortfolioMatchingService(DeterministicMatcher()).match(job_analysis, profile)
    volume = bool(payload.get("volume_applications_enabled", False))

    assessment_raw = payload.get("opportunity_assessment") or payload.get("assessment")
    strategy_raw = payload.get("application_strategy") or payload.get("strategy")
    mode = "rematch_replan"
    try:
        if assessment_raw is None:
            raise ValueError(f"{stem}: missing opportunity_assessment")
        assessment = OpportunityAssessment.model_validate(assessment_raw)
        strategy = ApplicationStrategyService(DeterministicStrategyPlanner()).plan(
            assessment,
            match,
            profile,
            operating_context=SearchOperatingContext(volume_applications_enabled=volume),
        )
        assessment_out = assessment.model_dump(mode="json")
        strategy_out = strategy.model_dump(mode="json")
        after_ids = [p.project_id for p in strategy.portfolio_emphasis]
        tier = strategy.application_tier
        posture = strategy.pursuit_posture
    except Exception as exc:  # noqa: BLE001 - fall back to rematch-only
        mode = f"rematch_only ({type(exc).__name__})"
        if strategy_raw is None:
            raise
        strategy_out = dict(strategy_raw)
        # Refresh portfolio emphasis from calibrated match order (cap 3).
        emphasis = []
        for entry in match.ranked_projects[:3]:
            emphasis.append(
                {
                    "project_id": entry.project_id,
                    "source_rank": entry.rank,
                    "summary": (
                        f"Emphasise portfolio project '{entry.project_id}' "
                        f"(calibrated match rank {entry.rank})."
                    ),
                    "evidence": [
                        {
                            "origin": "portfolio_match",
                            "portfolio_project_id": entry.project_id,
                            "excerpt": entry.rationale,
                        }
                    ],
                }
            )
        strategy_out["portfolio_emphasis"] = emphasis
        assessment_out = assessment_raw
        after_ids = [e["project_id"] for e in emphasis]
        tier = strategy_out.get("application_tier")
        posture = strategy_out.get("pursuit_posture")

    out = {
        "components": payload.get("components")
        or [
            {
                "name": "portfolio_matching",
                "implementation": "DeterministicMatcher",
                "mode": "deterministic_production",
            },
            {
                "name": "application_strategy",
                "implementation": "DeterministicStrategyPlanner",
                "mode": "deterministic_production",
            },
        ],
        "volume_applications_enabled": volume,
        "profile_identity": payload.get("profile_identity")
        or {
            "full_name": profile.identity.full_name,
            "target_role": profile.identity.target_role,
        },
        "posting": payload.get("posting") or job_analysis.posting.model_dump(mode="json"),
        "job_analysis": job_analysis.model_dump(mode="json"),
        "opportunity_assessment": assessment_out,
        "portfolio_match": match.model_dump(mode="json"),
        "application_strategy": strategy_out,
        "calibration_rematch": True,
        "calibration_rematch_mode": mode,
    }
    LIVE.mkdir(parents=True, exist_ok=True)
    dest = LIVE / f"{stem}.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    after = [e.project_id for e in match.ranked_projects]
    return {
        "stem": stem,
        "source": str(path),
        "dest": str(dest),
        "mode": mode,
        "before_top3": before[:3],
        "after_top3": after[:3],
        "before_emphasis": before_ids,
        "after_emphasis": after_ids,
        "tier": tier,
        "posture": posture,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stems",
        default=",".join(DEFAULT_STEMS),
        help="Comma-separated strategy JSON stems",
    )
    args = parser.parse_args()
    stems = [s.strip() for s in args.stems.split(",") if s.strip()]
    print("Rematch + replan (calibrated FR-004 / FR-005 planner)")
    for stem in stems:
        try:
            row = rematch_replan(stem)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {stem}: {exc}")
            continue
        print(
            f"{row['stem']}: {row['before_top3']} -> {row['after_top3']} | "
            f"emphasis {row['before_emphasis']} -> {row['after_emphasis']} | "
            f"{row['posture']}/{row['tier']} | {row['mode']}"
        )


if __name__ == "__main__":
    main()
