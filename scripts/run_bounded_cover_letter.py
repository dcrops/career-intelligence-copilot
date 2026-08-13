#!/usr/bin/env python3
"""Slice 2: bounded LLM cover letter for one Opportunity (experiment).

Writes beside existing generated drafts using stem
``{opportunity_id}.bounded_llm`` so live package Markdown is not overwritten.
Runs existing truth validation after persist. Does not call package prepare,
Playwright, or submission.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from career_intelligence.candidate_contact import load_candidate_contact
from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterPlanOptions,
    CoverLetterPlanService,
    DeterministicCoverLetterPlanner,
    default_generated_dir,
    write_cover_letter_drafts,
)
from career_intelligence.cover_letter.bounded_composer import OpenAICoverLetterComposer
from career_intelligence.cover_letter.bounded_generation import (
    BoundedCoverLetterService,
    EXPERIMENT_STEM_SUFFIX,
    experiment_stem,
    write_evidence_pack,
    write_truth_report,
)
from career_intelligence.cover_letter.errors import (
    CoverLetterError,
    CoverLetterGenerationValidationError,
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
    parser.add_argument(
        "--stem-suffix",
        default=EXPERIMENT_STEM_SUFFIX,
        help="Draft stem suffix. Use bounded_llm_retest to preserve the first experiment.",
    )
    args = parser.parse_args()

    live_stem = args.opportunity_id
    stem = experiment_stem(args.opportunity_id, args.stem_suffix)
    if stem == live_stem:
        print("Refusing to use the live package stem for the experiment.", file=sys.stderr)
        return 2

    _prepare_openai_runtime()

    opportunities = OpportunityService()
    artifacts = opportunities.load_artifacts(args.opportunity_id)
    profile = CareerProfileService().load()
    contact = load_candidate_contact()
    plan = CoverLetterPlanService(DeterministicCoverLetterPlanner()).plan(
        artifacts.strategy,
        profile,
        options=CoverLetterPlanOptions(
            owner_approved_to_plan=True,
            override_material_benefit=True,
        ),
    )
    service = BoundedCoverLetterService(OpenAICoverLetterComposer())
    try:
        composed = service.compose(
            artifacts.strategy,
            profile,
            plan,
            options=CoverLetterGenerationOptions(
                cover_letter_plan_approved=True,
                contact=contact,
            ),
        )
    except CoverLetterGenerationValidationError as error:
        print("Bounded composition failed closed on unsupported claims:", file=sys.stderr)
        for detail in error.errors:
            print(f"  - {detail.msg}", file=sys.stderr)
        return 1
    except CoverLetterError as error:
        print(f"Bounded composition failed: {error}", file=sys.stderr)
        return 1

    drafts = write_cover_letter_drafts(
        composed.letter,
        plan,
        output_dir=args.output_dir,
        stem=stem,
    )
    pack_path = args.output_dir / f"{stem}.evidence_pack.json"
    write_evidence_pack(pack_path, composed.pack)

    truth = service.assess_truth(
        markdown=composed.letter.rendered_markdown,
        profile=profile,
        artefact_path=str(drafts.markdown_path),
        opportunity_id=args.opportunity_id,
    )
    truth_path = args.output_dir / f"{stem}.truth.json"
    write_truth_report(truth_path, truth.report)
    _write_comparison_notes(
        output_dir=args.output_dir,
        live_stem=live_stem,
        experiment_stem_name=stem,
        markdown_path=drafts.markdown_path,
        pack_path=pack_path,
        truth_path=truth_path,
        external_use_allowed=truth.external_use_allowed,
        truth_messages=truth.messages,
        outcome=truth.report.outcome,
        projects=[item.name for item in composed.pack.projects],
    )

    print(f"composition_source={composed.letter.composition_source}")
    print(f"projects={[item.id for item in composed.pack.projects]}")
    print(f"markdown={drafts.markdown_path}")
    print(f"evidence_pack={pack_path}")
    print(f"truth={truth_path}")
    print(f"truth_outcome={truth.report.outcome}")
    print(f"external_use_allowed={truth.external_use_allowed}")
    for message in truth.messages:
        print(f"truth: {message}")
    if not truth.external_use_allowed:
        print(
            "Truth validation blocks external use. Experimental Markdown was "
            "persisted for owner review; no automatic LLM repair was attempted.",
            file=sys.stderr,
        )
        return 1
    return 0


def _prepare_openai_runtime() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Slice 2 bounded cover-letter composition "
            "requires OpenAI."
        )
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass


def _write_comparison_notes(
    *,
    output_dir: Path,
    live_stem: str,
    experiment_stem_name: str,
    markdown_path: Path,
    pack_path: Path,
    truth_path: Path,
    external_use_allowed: bool,
    truth_messages: tuple[str, ...],
    outcome: str,
    projects: list[str],
) -> None:
    live_path = output_dir / f"{live_stem}.md"
    first_attempt_path = output_dir / f"{live_stem}.{EXPERIMENT_STEM_SUFFIX}.md"
    notes_path = output_dir / f"{experiment_stem_name}.comparison.md"
    live_excerpt = (
        live_path.read_text(encoding="utf-8")[:2000]
        if live_path.is_file()
        else "(live deterministic cover letter not found at this stem)"
    )
    first_excerpt = (
        first_attempt_path.read_text(encoding="utf-8")[:2000]
        if first_attempt_path.is_file() and first_attempt_path != markdown_path
        else ""
    )
    experimental = markdown_path.read_text(encoding="utf-8")
    truth_lines = [f"- {message}" for message in truth_messages] or ["- (none)"]
    notes = "\n".join(
        [
            "# Slice 2 bounded-LLM cover letter comparison",
            "",
            f"- Live deterministic letter: `{live_path}`",
            f"- Slice 2 letter: `{markdown_path}`",
            f"- Evidence pack: `{pack_path}`",
            f"- Truth report: `{truth_path}`",
            f"- Truth outcome: `{outcome}`",
            f"- External use allowed: `{external_use_allowed}`",
            f"- Packed projects: {', '.join(projects) or '(none)'}",
            "",
            "The handcrafted benchmark is a quality reference, not expected-output text.",
            "Do not treat wording differences as automatic failure.",
            "",
            "## Truth messages",
            "",
            *truth_lines,
            "",
            "## A. Previous CIC deterministic letter (excerpt)",
            "",
            "```markdown",
            live_excerpt.rstrip(),
            "```",
            "",
            *(
                [
                    "## B. Slice 2 first bounded-LLM attempt (excerpt)",
                    "",
                    "```markdown",
                    first_excerpt.rstrip(),
                    "```",
                    "",
                    "## C. This run",
                    "",
                    "```markdown",
                    experimental.rstrip(),
                    "```",
                    "",
                ]
                if first_excerpt
                else [
                    "## B. Slice 2 bounded-LLM letter",
                    "",
                    "```markdown",
                    experimental.rstrip(),
                    "```",
                    "",
                ]
            ),
        ]
    )
    notes_path.write_text(notes + "\n", encoding="utf-8")
    print(f"comparison={notes_path}")


if __name__ == "__main__":
    raise SystemExit(main())
