# FR-006 Manual Validation

## Purpose

Owner validation for FR-006 Tailoring Plan, Tailored CV render, and optional Phase C
summary rewrite.

The pipeline under test is:

```
Job advertisement
      ↓
Application Strategy (FR-005)   ← reuse saved artefacts for the FR-005 corpus
      ↓
Tailoring Plan (FR-006 Phase A)     ← Q1: is the plan correct?
      ↓
(optional owner review of the plan)
      ↓
Tailored CV (FR-006 Phase B)        ← Q2: does the CV render the plan?
      ↓
(optional Phase C summary rewrite)  ← Q3: is the rewritten summary faithful?
      ↓
mandatory owner review before use
```

This process deliberately separates **planning failures** from **rendering failures**
and from **summary-rewrite failures**.

Do **not** ask only “does the CV look good?”

---

## Prerequisites

- Package installed: `pip install -e ".[dev]"`
- Career profile available (`data/career_profile.yaml` or `--profile-path`)
- For the FR-005 manual validation corpus: matching JSON under
  `manual_validation/outputs/{job_stem}.json` (produced by
  `scripts/run_application_strategy_manual.py --output-json …`)
- For live upstream re-run of FR-002/003: `OPENAI_API_KEY` and `--live-upstream`
- For Phase C summary rewrite: `OPENAI_API_KEY`, `--rewrite-summary`, and (on
  Windows SSL environments) the same optional `truststore` package used by
  FR-002/003 live manuals — the FR-006 runner injects it automatically.
- For CIC-FIXTURE smoke only: a job text containing `[CIC-FIXTURE:…]` and
  `--offline-fixtures`

Phase A/B are deterministic. Phase C is **opt-in** (`rewrite_summary` defaults to false).

---

## Upstream resolution (important)

| Mode | When | Notes |
|------|------|--------|
| **Reused pipeline JSON** | `--strategy-json` **or** `--job-file` stem matches `manual_validation/outputs/{stem}.json` | Preferred for FR-005 corpus. Fully deterministic. |
| **Offline fixtures** | `--offline-fixtures` **and** job text contains `[CIC-FIXTURE:…]` | Smoke tests only. **Not** for real SEEK/LinkedIn ads. |
| **Live upstream** | `--live-upstream` (or no saved JSON) | OpenAI for FR-002/003. |

`--offline-fixtures` does **not** mean “offline validation of real job files.”
If you pass it with a real corpus job that already has a saved output JSON, the
runner **reuses that JSON** and notes that `--offline-fixtures` was ignored.

---

## Runner — preferred commands

### FR-005 corpus (deterministic reuse)

```bash
python scripts/run_cv_generation_manual.py \
  --job-file manual_validation/jobs/013_pay_com_au_ai_automation_engineer.txt
```

Job 013 is Silver without `consider_cv_tailoring`, so the material-benefit gate
refuses TailoringPlan unless you explicitly override:

```bash
python scripts/run_cv_generation_manual.py \
  --job-file manual_validation/jobs/013_pay_com_au_ai_automation_engineer.txt \
  --override-material-benefit
```

Platinum/Gold corpus example (no override needed):

```bash
python scripts/run_cv_generation_manual.py \
  --job-file manual_validation/jobs/002_bluefin_ai_systems_developer.txt
```

Equivalent explicit form:

```bash
python scripts/run_cv_generation_manual.py \
  --strategy-json manual_validation/outputs/013_pay_com_au_ai_automation_engineer.json
```

### CIC-FIXTURE smoke only

```bash
python scripts/run_cv_generation_manual.py \
  --job-file tmp_fixture_job.txt \
  --offline-fixtures \
  --title "Applied AI Engineer" \
  --company "Harbour Labs"
```

### Force live upstream (re-extract / re-assess)

```bash
python scripts/run_cv_generation_manual.py \
  --job-file manual_validation/jobs/013_pay_com_au_ai_automation_engineer.txt \
  --live-upstream
```

Useful flags:

| Flag | Effect |
|------|--------|
| `--strategy-json PATH` | Explicit FR-005 pipeline JSON reuse |
| `--live-upstream` | Ignore saved JSON; re-run FR-001→FR-005 live |
| `--offline-fixtures` | CIC-FIXTURE smoke only (not real corpus ads) |
| `--plan-only` | Write Tailoring Plan JSON only; skip CV render |
| `--not-tailoring-plan-approved` | Same as stopping after plan review |
| `--include-extended-history` | Opt in to temporary pre-Master-CV experience ids |
| `--override-material-benefit` | Explicit override of platinum/gold gate |
| `--rewrite-summary` | Opt into Phase C OpenAI summary rewrite (fail-soft) |
| `--output-dir PATH` | Override `career-documents/cv/generated/` |

---

## Outputs

Default directory: `career-documents/cv/generated/`

For a full run:

| File | Contents |
|------|----------|
| `{stem}.tailoring_plan.json` | Trusted Tailoring Plan |
| `{stem}.json` | Trusted TailoredCv (typed JSON) |
| `{stem}.md` | Human-reviewable Markdown draft |

No PDF. No DOCX. Drafts must not be submitted or emailed without owner review.

---

## Validation checklist

For each job:

### Question 1 — Was the Tailoring Plan correct?

1. Read the job advertisement.
2. Independently list the ~5 most important requirements.
3. Generate the Tailoring Plan (runner console + `.tailoring_plan.json`).
4. Confirm the plan identifies those priorities.
5. Confirm projects promoted match strategy portfolio emphasis / JD relevance.
6. Confirm skills promoted vs not-emphasised are sensible (skills are never deleted).
7. Confirm experience guidance (`master_cv_only` by default).

**If Q1 fails:** fix or challenge planning inputs/policy — do **not** blame the Markdown renderer.

### Question 2 — Did the Tailored CV faithfully render the plan?

1. Accept the plan (`tailoring_plan_approved`).
2. Generate the Tailored CV.
3. Confirm emphasised skills appear in plan order under Emphasised.
4. Confirm project section order matches `projects_to_emphasise`.
5. Confirm experience ids match plan inclusion list / kinds remain truthful.
6. Confirm certifications are baseline (active profile credentials) — not re-ordered by the plan.
7. Confirm Markdown and JSON agree with the structured TailoredCv.

**If Q2 fails:** treat as a rendering/fidelity defect — the plan may still be correct.

### Question 3 — Phase C summary rewrite (opt-in)

```bash
python scripts/run_cv_generation_manual.py \
  --job-file manual_validation/jobs/002_bluefin_ai_systems_developer.txt \
  --rewrite-summary
```

1. Confirm `summary_source` is `openai_rewrite` (or `fallback_profile_copy` if OpenAI failed).
2. Confirm the summary reads naturally and covers plan themes.
3. Confirm no unsupported JD technologies appear (e.g. Terraform / Rails / TypeScript when unsupported).
4. Confirm no invented employers, projects, certifications, or years.
5. Confirm Summary themes section remains under the summary for review.

**If Q3 fails with invented facts:** treat as prompt/validation defect — fall back should have blocked shipping bad prose when validation catches it.

---

## Architectural notes for reviewers

### Certifications (Option A)

Active certifications are a **fixed profile baseline**, not TailoringPlan content.
See `career_intelligence.cv_generation.baseline`.

### Extended history (temporary rule)

Pre-Master-CV experience ids live **only** in
`career_intelligence.cv_generation.experience_scope`.
Default excludes them; `--include-extended-history` opts in.
This is a temporary implementation detail — not an FR-001 schema change.

### Summary rewriting (Phase C)

Default remains profile summary copy (`rewrite_summary=False`).
With `--rewrite-summary`, `OpenAISummaryRewriter` rewrites prose from plan-derived
structured inputs only (prompt file
`src/career_intelligence/cv_generation/prompts/cv_summary_v2.md`; v1 retained).
Failures and allowlist violations fall back to the profile summary
(`summary_source=fallback_profile_copy`). Design record:
[eval/fr006_phase_c_design.md](fr006_phase_c_design.md).

---

## Finite exit criteria (deterministic validation)

1. At least three real jobs where Q1 and Q2 both pass (prefer Platinum/Gold), using
   reused `manual_validation/outputs/*.json` upstream.
2. At least one Silver/Bronze (or gated) case where tailoring is refused or override-only.
3. Console report reviewed for tier, gates, priorities, skills, projects, experience, filenames.
4. Phase C (optional): at least one live `--rewrite-summary` run with
   `summary_source=openai_rewrite` and no unsupported technologies in the summary.

---

## FR-006 completion status

**Status: Completed** (2026-07-23).

FR-006 delivers deterministic CV generation, evidence-based Tailoring Plan emphasis,
optional LLM summary enhancement (prompt v2), and mandatory owner review.

**Bluefin close-out (Prompt v2):** `summary_source=openai_rewrite`; employer-relevant
summary lead; no unsupported JD technologies in the rewritten summary; deterministic
planning unchanged.

Do **not** implement informal “Phase D” presentation work under FR-006. Next planned
FR: **FR-007 Cover Letter**. Remaining Phase 2 exit criteria are unchanged.
