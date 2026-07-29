# FR-007 — Cover Letter Generation

**Status:** Complete (passed manual validation)  
**Date closed:** 2026-07-29  
**Package:** `career_intelligence.cover_letter`

## Purpose

Produce company-specific, approximately one-page cover letters that feel authentic
to an experienced AI Engineer. Evidence-first plan → deterministic narrative render
(same pattern as FR-006). Owner review is mandatory before external use.

**Planner thinks like an engineer. Renderer writes like a human.**

## Inputs / outputs

| Stage | Artefact |
|-------|----------|
| In | `ApplicationStrategy` + `CareerProfile` + gates / optional `ContactDetails` |
| Phase A | `CoverLetterPlan` |
| Phase B | `CoverLetter` (Markdown); HTML via `write_cover_letter_drafts` |
| Out dir | `career-documents/cover-letters/generated/` (gitignored drafts) |

## Pipeline

```
ApplicationStrategy + CareerProfile
        ↓
CoverLetterPlanService + DeterministicCoverLetterPlanner
        ↓
CoverLetterGenerationService + composer (+ project_selection / project narratives)
        ↓
Markdown + HTML + JSON + plan JSON
        ↓
Owner review
```

## CoverLetterPlan fields

- `company_alignment` — company + grounded attraction hook
- `role_motivation` — role title + compact engineering theme
- `relevant_evidence` — profile-backed credibility claims
- `strongest_projects` — evidence-ranked projects with `selection_reason`,
  `business_outcome`, `fit_focus`
- `closing_strategy` — conversation vs contribution close from pursuit posture

Plan vocabulary is never copied into the finished letter.

## Project selection strategy

Rank profile projects for **interview value**, not popularity:

- employer concern clusters (trust/explainability, production, LLM/agents,
  documents, deterministic rules, ops insights)
- JD technology and responsibility overlap
- production maturity
- moderated ApplicationStrategy portfolio-emphasis boost (no circular injection
  of emphasis project IDs into JD tokens)

Different roles should surface different projects.

## Writing principles

- Concrete opening (engineering challenge), not marketing slogans or JD dumps
- Credibility, portfolio breadth, engineering philosophy, collaboration;
  stakeholder language when the JD asks for it
- Portfolio URL in the body
- Projects as products: what it does → engineering capability → practical outcome;
  domain secondary; varied paragraph shapes
- Closing invites working software, trade-offs, and demos
- No AI-template markers, em/en dashes, or planner jargon
- Deterministic; no LLM rewrite on the default path

## Validation

```bash
python scripts/run_cover_letter_manual.py \
  --job-file manual_validation/jobs/002_bluefin_ai_systems_developer.txt

python scripts/run_cover_letter_manual.py \
  --job-file manual_validation/jobs/012_maincode_ai_infrastructure_engineer.txt \
  --override-material-benefit

python scripts/run_cover_letter_manual.py \
  --job-file manual_validation/jobs/001_strong_ai_engineer.txt \
  --override-material-benefit

python scripts/run_cover_letter_manual.py \
  --job-file manual_validation/jobs/009_forever_new_senior_ai_automation_engineer_digital.txt
```

Review Markdown and HTML together against the tailored CV for the same role.

Unit tests: `tests/unit/cover_letter/`.

## Known limitations

- Catalogued project narratives are curated; unknown projects use summary fallbacks.
- Quality tracks JobAnalysis and Career Profile richness.
- System never submits or emails letters.

## Closure

FR-007 is **complete**. Manual validation passed. Do not reopen as informal
presentation polish unless the owner requests a scoped change. Next Horizon 1
focus: automated job acquisition / discovery (see roadmap).
