# FR-007 — Cover Letter Generation

**Status:** Implemented (narrative rendering + HTML)  
**Date:** 2026-07-29

## Purpose

Produce company-specific, recruiter-ready cover letters that feel authentic to an
experienced AI Engineer — using the same evidence-first plan → render pattern as
FR-006.

**Planner thinks like an engineer. Renderer writes like a human.**

## Architecture

| Phase | Artifact | Owner |
|-------|----------|-------|
| A | `CoverLetterPlan` | `CoverLetterPlanService` + `DeterministicCoverLetterPlanner` |
| B | `CoverLetter` | `CoverLetterGenerationService` + narrative `composer` |

Package: `src/career_intelligence/cover_letter/`

## CoverLetterPlan fields

- `company_alignment` — company + grounded attraction hook (JD excerpt / responsibility)
- `role_motivation` — role title + compact engineering theme
- `relevant_evidence` — Career Profile claims (summary / highlights)
- `strongest_projects` — portfolio emphasis projects (profile-backed)
- `closing_strategy` — conversation vs contribution close from pursuit posture

Plan vocabulary is **never** copied into the finished letter.

## Narrative composition rules

- Open with why this role’s engineering challenge attracted the candidate —
  not marketing slogans (“shaping the future”) or JD paraphrase
- Motivation: credibility + independent portfolio breadth + architecture-first /
  deterministic / evidence / human-in-the-loop philosophy + collaboration
- Stakeholder/adoption sentence when the JD mentions stakeholders, UAT,
  requirements translation, or similar
- Portfolio URL referenced in the body (encourages recruiters to visit)
- **Evidence-based project selection:** rank profile projects by employer
  concerns (trust, production, LLM/agents, documents, rules, ops) plus JD/tech
  fit and moderated strategy emphasis
- Projects explained as products in plain English: what it does, engineering
  capability, and why it matters, with **varied** paragraph structures (no
  repeated “This demonstrates…” / “The business value is…” templates)
- Domain context is secondary to engineering principles demonstrated
- Closing invites working software, architecture decisions, trade-offs, and
  live demos (curiosity, not a full catalogue)
- No em/en dashes or AI-template markers (“I am excited…”, “Furthermore…”)
- Signature block still includes LinkedIn / Portfolio / GitHub
- Deterministic; no LLM rewrite in the default path
- `owner_review_required` always true
- Target length: approximately one page

## Outputs

Each draft stem under `career-documents/cover-letters/generated/`:

| File | Purpose |
|------|---------|
| `{stem}.md` | Submit-ready Markdown |
| `{stem}.html` | Print-friendly HTML (shared CV print CSS) |
| `{stem}.json` | Typed `CoverLetter` |
| `{stem}.cover_letter_plan.json` | Typed `CoverLetterPlan` |

**Visual regression:** review Markdown and HTML together against the tailored CV
for the same role — typography, spacing, and signature should feel like one suite.

## Manual validation set (2026-07-29 narrative pass)

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

| Role | Distinctive opening signal | Projects emphasised |
|------|---------------------------|---------------------|
| Bluefin — AI Systems Developer | Fintech AI systems build/operate | Operational Intelligence + Governance RAG |
| Maincode — AI Infrastructure Engineer | Learn/design AI infrastructure backbone | Operational Intelligence + Governance RAG |
| Allura — AI Engineer | Design/build/deploy LLM + agentic workflows | Public Holiday Entitlements + Operational Intelligence |
| Forever New — Senior AI Automation | Agents/tools/pipelines across the business | Operational Intelligence + Public Holiday Entitlements |

Governance-focused portfolio evidence surfaces most clearly on Bluefin/Maincode
(Governance-Aware Document Intelligence RAG). Forever New exercises agent/automation
emphasis as the fourth genuinely different commercial role.

## Unit tests

`tests/unit/cover_letter/` — gates, narrative bans, signature, Markdown+HTML drafts.
