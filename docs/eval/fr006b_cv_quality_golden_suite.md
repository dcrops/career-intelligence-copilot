# FR-006b CV Quality — Golden Validation Suite

## Purpose

Provide a **permanent, representative benchmark** for judging CV (and later cover-letter)
generation quality.

The suite does **not** freeze exact generated text. It freezes **which opportunities**
we re-run and **what good looks like** for each, so improvements and regressions can be
compared over time instead of using ad hoc examples.

Use this suite for:

- **FR-006b** — CV quality improvement
- **FR-007** — Cover letter generation (same jobs; letter-specific criteria added later)
- Prompt / planner / render regressions for application artefacts
- Owner preference reviews (“would I submit this?”)

## Success metric (human preference)

A generated CV succeeds only if:

1. It accurately represents the owner’s experience (no invention or exaggeration).
2. It preserves Master CV writing quality (tone, achievement impact, readability).
3. It tailors to the target role without dropping important achievements.
4. The owner would **genuinely prefer submitting it** over manually editing the Master CV.

Technical fidelity alone is insufficient.

## Benchmark jobs (initial set)

All jobs live under `manual_validation/jobs/`. Prefer reusing saved strategy JSON under
`manual_validation/outputs/{stem}.json` for deterministic FR-005→FR-006 runs.

| ID | File stem | Company | Role | Why selected | Expected emphasis |
|----|-----------|---------|------|--------------|-------------------|
| **G1** | `001_strong_ai_engineer` | Allura Partners (client) | AI Engineer | Strong applied AI Engineering match; production LLM/agents | Technical depth: Python, LLM apps, RAG/ops intel projects, stakeholder delivery |
| **G2** | `013_pay_com_au_ai_automation_engineer` | pay.com.au | AI Automation Engineer | Good automation / applied AI match | Automation + LLM tooling; production discipline; Python; portfolio order for ops/RAG |
| **G3** | `012_maincode_ai_infrastructure_engineer` | Maincode | AI Infrastructure Engineer | Platform / infra / GPU systems role | Systems & platform engineering signals; Linux/GPU/infra curiosity; careful not to invent infra employment |
| **G4** | `008_repurpose_it_ai_adoption_specialist` | Repurpose It | AI Adoption Specialist | AI solutions / adoption (less build-heavy) | Consulting-style communication; practical AI adoption; governance; lighter deep-infra claims |
| **G5** | `006_senior_ai_engineer_kogan` | Kogan.com | Senior AI Engineer | Aspirational / stretch senior role | Leadership + delivery stretch; honest gaps; still strong portfolio proof without inventing seniority |

### Expected tailoring characteristics (all jobs)

| Dimension | Expectation |
|-----------|-------------|
| Fidelity | No skills/employers/projects not in Career Profile |
| Summary | Role-aware, Master-CV-quality prose (not raw profile dump; not generic LLM marketing) |
| Skills | Compact emphasised set aligned to role + evidence; not a full inventory dump |
| Projects | Order and framing match role; outcomes remain evidence-backed |
| Experience | Master-CV scope by default; highlight selection/impact competitive with Master CV |
| Presentation | Submit-ready surface (minimal internal meta); owner-review gates may exist separately |
| Preference | Owner would submit with light or no rewrite |

Job-specific notes:

- **G1 / G2:** Lead with AI Engineering portfolio depth; de-emphasise pure QA history unless relevant.
- **G3:** Do not invent datacentre employment; emphasise transferable systems/engineering discipline and honest learning posture where needed.
- **G4:** Prefer adoption, enablement, and explainability over GPU/cluster claims.
- **G5:** Stretch narrative without claiming commercial senior AI employment the profile does not support.

## How to run a suite review

1. For each golden job, generate (or regenerate) a Tailored CV via
   `scripts/run_cv_generation_manual.py` (reuse strategy JSON where possible;
   `--override-material-benefit` when the strategy gate refuses Silver without
   `consider_cv_tailoring`).
2. Compare against:
   - Master CV (`career-documents/cv/master_ai_engineer_cv.pdf`; prior v3 archived)
   - Prior generated draft for the same stem (if any)
3. Score qualitatively (Pass / Partial / Fail) on: fidelity, writing quality,
   tailoring, section balance, submit preference.
4. Record notes under `manual_validation/reviews/` (or a dedicated FR-006b review
   log when introduced).
5. Prefer fixing the highest-impact root causes first (see findings report).

## Adding benchmark jobs later

1. Choose a real job already (or newly) under `manual_validation/jobs/`.
2. Prefer diversity of role family / seniority / emphasis, not near-duplicates.
3. Add a row to the table above: ID, stem, company, title, why, expected emphasis.
4. Persist a strategy JSON under `manual_validation/outputs/` for reproducible runs.
5. Do **not** remove existing golden jobs without owner approval (breaks trend comparison).

## Relationship to automated tests

- Unit/functional/golden **code** tests remain the regression net for contracts and
  fidelity (no invented facts).
- This suite is the **qualitative** regression net for human preference and writing
  quality. Automated snapshot equality of full CV prose is intentionally avoided.

## Related documents

- Findings (FR-006b quality review): [fr006b_cv_quality_findings.md](fr006b_cv_quality_findings.md)
- FR-006 procedure: [fr006_manual_validation.md](fr006_manual_validation.md)
- Owner Q1/Q2 notes: `manual_validation/reviews/tailored_cv_reviews.md`
- Functional requirement: [04_functional_specification.md](../04_functional_specification.md) § FR-006
