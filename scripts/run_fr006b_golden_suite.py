"""Regenerate FR-006b Golden Suite (G1–G5) CVs for quality validation."""

from __future__ import annotations

import json
from pathlib import Path

from career_intelligence.application_strategy import ApplicationStrategy
from career_intelligence.cv_generation import (
    ContactDetails,
    CvGenerationOptions,
    CvGenerationService,
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanService,
    write_tailored_cv_drafts,
)
from career_intelligence.profile import CareerProfileService

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUTS = _ROOT / "tests" / "fixtures" / "application_strategy"
_GENERATED = _ROOT / "career-documents" / "cv" / "generated" / "fr006b_golden"

GOLDEN = (
    ("G1", "001_strong_ai_engineer.json"),
    ("G2", "013_pay_com_au_ai_automation_engineer.json"),
    ("G3", "012_maincode_ai_infrastructure_engineer.json"),
    ("G4", "008_repurpose_it_ai_adoption_specialist.json"),
    ("G5", "006_senior_ai_engineer_kogan.json"),
)

CONTACT = ContactDetails(
    email="djcropster@gmail.com",
    phone="0400 811 545",
    location="Melbourne, VIC",
    linkedin_url="https://www.linkedin.com/in/david-cropper/",
    portfolio_url="https://journey.chaseriskandcompliance.com.au/",
    github_url="https://github.com/dcrops",
)


def main() -> None:
    profile = CareerProfileService.from_path(_ROOT / "data" / "career_profile.yaml").load()
    _GENERATED.mkdir(parents=True, exist_ok=True)
    planner = TailoringPlanService(DeterministicTailoringPlanner())
    service = CvGenerationService()

    for suite_id, filename in GOLDEN:
        payload = json.loads((_OUTPUTS / filename).read_text(encoding="utf-8"))
        strategy = ApplicationStrategy.model_validate(payload["application_strategy"])
        override = strategy.application_tier not in {"platinum", "gold"} and not any(
            action.kind == "consider_cv_tailoring" for action in strategy.next_actions
        )
        plan = planner.plan(
            strategy,
            profile,
            options=TailoringOptions(
                owner_approved_to_tailor=True,
                override_material_benefit=override,
            ),
        )
        cv = service.generate(
            strategy,
            profile,
            plan,
            options=CvGenerationOptions(
                tailoring_plan_approved=True,
                contact=CONTACT,
            ),
        )
        stem = f"{suite_id}_{filename.removesuffix('.json')}"
        result = write_tailored_cv_drafts(cv, plan, output_dir=_GENERATED, stem=stem)
        print(
            suite_id,
            result.markdown_path.name,
            "themes=",
            [t.theme for t in plan.summary_themes],
            "promoted=",
            [s.skill_name for s in plan.skills_to_promote],
        )


if __name__ == "__main__":
    main()
