#!/usr/bin/env python3
"""Generate a Master-adaptive tailored CV for one Opportunity (Slice 1).

Writes beside existing generated drafts using stem ``{opportunity_id}.master_adapt``
so live package Markdown is not overwritten.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from career_intelligence.candidate_contact import load_candidate_contact
from career_intelligence.cv_generation import (
    CvGenerationOptions,
    CvGenerationService,
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanService,
    default_generated_dir,
    write_tailored_cv_drafts,
)
from career_intelligence.opportunities import OpportunityService
from career_intelligence.profile import CareerProfileService

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OPP = "opp_01KZQJY6AX3EGX7TGYTHR3ABG1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity-id", default=_DEFAULT_OPP)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_generated_dir(_REPO_ROOT),
    )
    args = parser.parse_args()

    opportunities = OpportunityService()
    artifacts = opportunities.load_artifacts(args.opportunity_id)
    profile = CareerProfileService().load()
    contact = load_candidate_contact()
    plan = TailoringPlanService(DeterministicTailoringPlanner()).plan(
        artifacts.strategy,
        profile,
        options=TailoringOptions(
            owner_approved_to_tailor=True,
            override_material_benefit=True,
        ),
    )
    cv = CvGenerationService().generate(
        artifacts.strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            adapt_from_master=True,
            contact=contact,
        ),
    )
    stem = f"{args.opportunity_id}.master_adapt"
    drafts = write_tailored_cv_drafts(
        cv,
        plan,
        output_dir=args.output_dir,
        stem=stem,
    )
    print(f"summary_source={cv.summary_source}")
    print(f"projects={[item.project_id for item in plan.projects_to_emphasise]}")
    print(f"promoted={[item.skill_name for item in plan.skills_to_promote]}")
    print(f"themes={[item.theme for item in plan.summary_themes]}")
    print(f"markdown={drafts.markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
