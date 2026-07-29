# Functional Specification

## Purpose

The Career Intelligence Copilot shall provide intelligent decision support throughout the complete career lifecycle.

The immediate objective is to help the repository owner secure a suitable AI Engineering role sooner by improving opportunity selection and reducing repetitive job-search work.

The long-term objective is to evolve into a reusable Career Intelligence Platform supporting ongoing career progression.

Requirements are prioritised against two success horizons. Horizon 1 takes priority whenever horizons compete. Near-term capabilities should improve the likelihood of securing relevant interviews or offers, or reduce the manual effort required to run an effective job search.

The product is intelligence-first. Automation is in scope where it safely reduces repetitive administrative work. Important career decisions and externally visible actions must remain reviewable by the user.

The product does not guarantee employment, interviews, or recruiter engagement.

---

## Scope and Phasing

This specification describes the full platform capability set. Delivery is phased by roadmap.

**Phase 2 (Job Intelligence MVP)** is the first vertical slice. Its purpose is to improve opportunity selection and reduce repetitive job-analysis work. Phase 2 must not expand into the entire job-search platform.

### Phase 2 — In Scope

- FR-001 Career Profile
- FR-002 Job Analysis
- FR-003 Opportunity Assessment (scoped — see below)
- FR-004 Portfolio Matching
- FR-005 Application Strategy
- Job opportunity pipeline tracking
- Outcome logging for assessed opportunities
- Ranked comparison of open assessed opportunities

### Phase 2 — Out of Scope

- Cover letter generation (FR-007) and later job-search platform capabilities below
- FR-008 Recruiter Intelligence
- FR-009 Interview Preparation
- FR-010 Career Dashboard (full)
- FR-011 Market Intelligence
- FR-012 Daily Prioritisation (cross-domain)
- Automated job discovery or external platform integration
- Interview Probability and Recruiter Confidence scoring (insufficient data at launch)

**Note:** FR-006 CV Generation and FR-007 Cover Letter were originally deferred from
Phase 2 exit criteria and were later **completed** as owner-sequenced post–Phase 2
capabilities. They are not Phase 2 exit blockers. See FR-006 and FR-007 below.

**Phase 2 close-out:** **Complete** (M1–M4 + M4a + M5). Documentation is a frozen
baseline before FR-006b. See [10_roadmap.md](10_roadmap.md),
[12_phase_history.md](12_phase_history.md), and
[eval/phase2_release_report.md](eval/phase2_release_report.md).

### Post–Phase 2

Remaining functional requirements are scheduled per roadmap phases 3–8.

---

## Conceptual References

Domain entities and the decision loop: [06_domain_model.md](06_domain_model.md).

Engineering tradeoffs during implementation: [05_engineering_principles.md](05_engineering_principles.md).

Phase 2 completion criteria: [10_roadmap.md](10_roadmap.md) § Phase 2 Exit Criteria.

---

## Assessment and Tier Semantics

This section defines what Phase 2 fit dimensions and application tiers mean. It is the authoritative source for assessment vocabulary.

### Fit Dimensions (Phase 2)

**Technical Fit** — Alignment between the role's technical requirements and the candidate's demonstrated skills and experience. Evidence comes from the job description and career profile. Covers technologies, seniority expectations, domain knowledge, and production experience where stated.

**Commercial Fit** — Alignment between the role and the candidate's commercial goals and constraints. Evidence includes salary range, employment type, location, company stage, and role scope relative to stated preferences and career direction.

**Portfolio Fit** — Alignment between the role's requirements and the candidate's portfolio projects as a whole. Evidence comes from project descriptions and the specific technologies, domains, or problem types the role emphasises. Answers whether the portfolio supports the role. It does **not** rank which projects to lead with — that is FR-004 Portfolio Matching.

Where evidence is unavailable (e.g. salary not listed), the assessment must state assumptions explicitly rather than infer silently.

### Application Tier Semantics

Tiers translate fit analysis into **effort investment** guidance. They are not apply/skip
decisions. The system recommends; the user decides (FR-013).

| Tier | Effort investment |
|------|-------------------|
| **Platinum** | Full investment — full tailoring where materially beneficial; portfolio-led application; interview preparation investment warranted |
| **Gold** | Targeted investment — Master CV with selective adjustments; moderate preparation |
| **Silver** | Minimal customisation — Master CV; apply when capacity allows. **Exception:** for a credible AI seniority stretch (`consider` posture, strong technical and portfolio fit, missing senior commercial AI employment evidence), Silver may use **targeted** effort without elevating pursuit to Gold. |
| **Bronze** | Do **not** invest significant effort — log rationale; may still submit as a low-effort/volume application if the owner chooses |

**Bronze does not mean “never apply.”** It means significant effort is not justified.
Final apply / skip / defer remains an owner decision.

For FR-005, **PursuitPosture** is the primary recommendation (attention / pursuit nuance).
**ApplicationTier** is the effort band. See FR-005.

Tier assignment must be explained by referencing fit dimensions and cited evidence (FR-003, FR-005).

### Legacy Terminology

Operational data predating v1.2 may use "Tier 1" language. **Tier 1 maps to Platinum** in product documentation. The former product tier name **Skip** is renamed **Bronze** (effort band only; not a never-apply decision). Reconcile operational files when the owner approves. See [00_repository_guide.md](00_repository_guide.md) § Operational Data Conventions.

---

# Functional Requirements

## FR-001 Career Profile

**Phase:** 2

The system shall maintain a structured representation of the user's:

- experience
- skills
- projects
- certifications
- goals
- preferences

Acceptance Criteria

✓ User profile can be updated.

✓ Profile is available to every decision.

---

## FR-002 Job Analysis

**Phase:** 2

The system shall analyse job descriptions and produce a structured **Job Analysis** of the
posting alone.

FR-002 extracts and organises what the job asks for. It does **not** evaluate candidate fit,
assign application tiers, recommend whether to apply, match portfolio projects, or generate
application content. Those behaviours belong to FR-003 and later requirements.

### Structured output

Analysis captures:

- technologies (each tagged required, preferred, or unspecified)
- responsibilities
- role family
- seniority
- location
- work arrangement (onsite, hybrid, remote, or unspecified), with optional details such as
  office days or geographic limits
- compensation (salary or rate where available)
- employment as two dimensions: working hours (full-time / part-time / unspecified) and
  engagement type (permanent / fixed-term / contract / casual / internship / unspecified)
- experience requirements as an evidence-backed list (each required, preferred, or
  unspecified), not a single aggregate years field

### Role-family taxonomy

- `ai_engineering`
- `ai_solutions`
- `data_engineering`
- `software_engineering`
- `ml_engineering`
- `network_engineering`
- `ai_adjacent`
- `other`
- `unknown`

### Seniority taxonomy

- `entry`
- `mid`
- `senior`
- `lead`
- `principal`
- `manager`
- `unknown`

### Requirements, evidence, and unknowns

- Technology and experience requirements must distinguish **required**, **preferred**, and
  **unspecified**. Unspecified means the posting does not make the obligation clear.
- Material positive claims require at least one **source evidence** item: a short excerpt from
  the posting and, optionally, the section it came from. Evidence may be empty only for
  explicitly unknown, unspecified, or unstated values. Evidence does not invent character
  offsets, confidence scores, or stable evidence identifiers.
- Unknown, unstated, or ambiguous information must be represented explicitly. The system must
  not guess missing salary, force a seniority when the posting conflicts, or invent a role
  family. Ambiguous seniority keeps `level` as `unknown`, retains at least one plausible
  candidate level, and cites conflicting evidence — without selecting a false single
  classification.
- Work arrangement is part of Job Analysis (not deferred to Commercial Fit). Commercial Fit
  later compares analysed arrangement and compensation against the career profile.

Acceptance Criteria

✓ Technologies identified with required / preferred / unspecified distinction.

✓ Role classified using the role-family taxonomy (including `unknown`).

✓ Salary or rate extracted where available; absence recorded without invention.

✓ Seniority and other ambiguous fields represented without forced classification.

✓ Positive extracted claims cite source evidence.

✓ Analysis reduces manual extraction effort compared to unassisted review.

### Service trust boundary (implementation)

Job Analysis is produced through `JobAnalysisService`, which is the public trust
boundary. An extractor returns untrusted structured data only; the service validates
that payload, binds the caller-supplied Job Posting, and returns a trusted Job
Analysis. Fixture extraction is deterministic test scaffolding and is never a public
default — production callers must supply an extractor explicitly. Live OpenAI extraction
completed its first manual evaluation with prompt hardening through v5; see
[eval/fr002_openai_manual_eval.md](eval/fr002_openai_manual_eval.md).

---

## FR-003 Opportunity Assessment

**Phase:** 2 (scoped)

**Status:** Implemented.

The system shall assess each opportunity and produce evidence-backed fit analysis comparing
a trusted Career Profile with a trusted Job Analysis.

Fit dimension definitions: see § Assessment and Tier Semantics.

Opportunity Assessment is produced through `OpportunityAssessmentService`, which is the
public trust boundary. An assessor returns untrusted structured data only; the service
validates that payload, binds the caller-supplied Job Analysis, checks evidence-reference
integrity, and returns a trusted Opportunity Assessment. Fixture assessment is deterministic
test scaffolding and is never a public default. Live OpenAI assessment completed manual
evaluation at **PARTIAL PASS** with prompt hardening through **v6**; see
[eval/fr003_openai_manual_eval.md](eval/fr003_openai_manual_eval.md) and
[08_implementation_notes.md](08_implementation_notes.md) § FR-003.

### Phase 2 dimensions

- Technical Fit
- Commercial Fit
- Portfolio Fit

### Phase 2 synthesis output

- Assessment summary with explainable, evidence-backed rationale (no tier assignment)

### Explicitly not produced by FR-003

Apply / Skip / Defer recommendations, application tiers, effort guidance, JobSeeker quota
logic, interview probabilities, or percentage fit scores (FR-005 and later).

### Post–Phase 2 dimensions (deferred)

- Recruiter Confidence
- Interview Probability
- Strategic Value

Acceptance Criteria (Phase 2)

✓ All three Phase 2 fit dimensions assessed.

✓ Explanation generated with cited evidence from the job analysis and user profile.

✓ Assessment supports tier recommendation (FR-005) without performing tiering itself.

---

## FR-004 Portfolio Matching

**Phase:** 2

**Status:** Implemented.

The system shall identify the portfolio projects that best align with each opportunity
and produce a separate ranked **Portfolio Match** artifact.

Given a trusted Career Profile and a trusted Job Analysis, Portfolio Matching answers:
which projects should be highlighted for this role, in what order, and why?

Portfolio Matching is produced through `PortfolioMatchingService`, which is the public
trust boundary. A matcher returns untrusted structured data only; the service validates
that payload, binds the caller-supplied Job Analysis, checks project coverage and
evidence-reference integrity, and returns a trusted Portfolio Match. Deterministic
matching is the production ranking path; fixture matching is offline test scaffolding
and is never a public default.

FR-004 is a **sibling** of FR-003 Opportunity Assessment. Both consume Career Profile +
Job Analysis. Portfolio Match does **not** feed, modify, or depend on
`OpportunityAssessment.portfolio_fit`. Portfolio Fit answers whether the portfolio
supports the role; Portfolio Match answers which projects should lead.

### Explicitly not produced by FR-004

Apply / Skip / Defer recommendations, application tiers, effort guidance, CV strategy,
outreach strategy, percentage match scores, or Opportunity Assessment fields.

Acceptance Criteria

✓ Projects ranked.

✓ Ranking explained with evidence-backed factors citing job analysis and
  `project:<id>` profile references.

✓ Zero-overlap projects are unranked; sparse jobs with no usable technologies or
  responsibilities report insufficient evidence rather than inventing rankings.

---


## FR-005 Application Strategy

**Phase:** 2

**Status:** Implemented. Formally closed after owner manual validation of the
FR-001→FR-005 pipeline (see
[manual_validation/jobs/manual_validation_notes.md](../manual_validation/jobs/manual_validation_notes.md)).

The system shall produce an evidence-backed **Application Strategy** for an opportunity by
consuming trusted upstream artifacts — Career Profile, Opportunity Assessment, and
Portfolio Match (with Job Analysis bound for provenance) — without redoing job extraction,
fit assessment, or portfolio ranking.

Application Strategy answers:

1. Why is this the recommendation? (`summary`, `reasons`, posture/tier/practical value)
2. Why might it not be the right recommendation? (`risks_or_gaps`, `decision_blockers`)
3. What should the owner do next? (`next_actions`)
4. What evidence supports the recommendation? (evidence refs on reasons, risks, checks, actions)
5. What information could change the recommendation? (`manual_checks`, `assumptions`)

### Recommendation semantics

- **PursuitPosture** (primary recommendation): `prioritise`, `pursue`, `consider`,
  `low_effort_submit`, `do_not_prioritise`, `insufficient_information`
- **ApplicationTier** (effort band only): Platinum, Gold, Silver, Bronze — see
  § Application Tier Semantics
- **EffortLevel**: `full` / `targeted` / `minimal` / `none` (must align with tier)
- **PracticalValue**: `career_priority`, `acceptable_opportunity`, `volume_obligation`,
  `deferred_pending_information`

There is no system-owned binary Apply/Skip field. Owner apply / skip / defer belongs to
FR-013.

### SearchOperatingContext

Optional caller-supplied search posture for strategy planning:

- `volume_applications_enabled` defaults to `False`
- optional `notes`
- no quotas, counters, or JobSeeker numeric state in FR-005 v1

When volume mode is enabled, lower strategic fit may still yield `low_effort_submit` with
Silver / minimal effort and `practical_value=volume_obligation`. The owner still decides.

### Seniority-aware stretch (AI target families)

For primary AI target families (`ai_engineering`, `ai_solutions`, `ml_engineering`), FR-005
may cap priority when the job is explicitly senior (or lead/principal/manager) and the
profile lacks **direct senior commercial AI employment** evidence:

- Independent engineering / professional development support technical and portfolio fit
  but do **not** count as senior commercial AI employment.
- Commercial `mixed`/`weak` caused only by salary uncertainty does **not** trigger the cap.
- Material assessment findings about seniority, leadership, commercial ownership, executive
  partnership, or production-leadership gaps are required for explicit `senior` level.
- Cap outcome: `consider` / Silver / `acceptable_opportunity`, with targeted effort when
  technical and portfolio fits remain strong (credible stretch, not rejection).
- Commercial fit need not be labelled `mixed` if material senior/leadership gap findings
  are present and commercial is not `strong`; salary-only uncertainty still does not cap.
- This is **not** a blanket “senior = silver” rule: matching commercial AI employment with
  senior ownership markers keeps Gold/Platinum possible.

### next_actions

Advisory follow-ups only (`consider_*` taxonomy). They must not generate CV/cover-letter
content, contact recruiters, or submit applications.

### Service trust boundary (implementation)

`ApplicationStrategyService` is the public trust boundary. A planner returns untrusted
structured data only; the service validates the payload, binds caller-owned `JobAnalysis`
(from Opportunity Assessment after posting-identity checks against Portfolio Match),
validates evidence references, and returns a trusted Application Strategy.
`DeterministicStrategyPlanner` is the production path; `FixtureStrategyPlanner` is offline
scaffolding. Neither is a public default — callers inject a planner explicitly. OpenAI is
not required for FR-005.

### Explicitly not produced by FR-005

CV or cover-letter content, recruiter outreach, application submission, browser automation,
percentage scores, autonomous apply/skip commitment, or modification of Career Profile /
Job Analysis / Opportunity Assessment / Portfolio Match.

Acceptance Criteria

✓ PursuitPosture assigned as the primary recommendation.

✓ ApplicationTier and EffortLevel assigned as effort guidance (Bronze ≠ never apply).

✓ Practical value distinguished (including optional volume obligation).

✓ Rationale is evidence-backed (reasons, risks/gaps, assumptions, blockers as applicable).

✓ Portfolio emphasis drawn from Portfolio Match without reranking.

✓ Advisory next_actions present (closed `consider_*` kinds; max five).

✓ Manual checks and assumptions surface information that could change the recommendation.

✓ owner_review_required is always true.

✓ Strategy answers the five conceptual questions above using existing fields.

---

## FR-006 CV Generation

**Phase:** Post–Phase 2  
**Status:** Completed (FR-006); FR-006b ready for daily use; **FR-006c Summary Intelligence** improves Phase B summary composition

The system shall generate tailored CVs when tailoring is materially beneficial and approved by the user.

### FR-006b — CV Quality Improvement

**Status:** Ready for daily Markdown use (owner preference vs Master CV v3).

FR-006b improves the integrated loop: Master CV content accuracy → Career Profile
source fidelity → Tailoring Plan emphasis → submit-ready Markdown render.

Additional FR-006b behaviours (additive to FR-006):

- Deterministic theme-aware Professional Summary when Phase C is off
- Submit-ready Markdown presentation (default); optional `presentation=review`
- Relevance-based selection of experience highlights and project demonstrates/outcomes
  from Career Profile text only (no invention)
- Portfolio project relevance reordering within ApplicationStrategy emphasis; optional
  Career Profile project append for AI-family roles when evidenced
- Profile baselines: `selected_engineering_highlights`, `engineering_methodology`
- Success metric: owner would prefer submitting the generated CV over manually
  editing the Master CV for the target role

Golden validation: [eval/fr006b_cv_quality_golden_suite.md](eval/fr006b_cv_quality_golden_suite.md),
[eval/fr006b_cv_quality_validation.md](eval/fr006b_cv_quality_validation.md).

### FR-006c — Summary Intelligence

**Status:** Implemented (Phase B default path); final polish complete — owner close pending.

Improves Professional Summary *composition* quality while preserving evidence gates:

- Credibility-first opening (stable personal brand across roles)
- Later paragraphs carry job-specific tech and a single promoted theme
- Multi-paragraph story (who / what / how / value); Master-length readability
- Natural engineering verbs; no “Background:” / “strengths in…” bridges
- Grounded visual emphasis for recruiter skimming (no over-bolding)
- Engineering Highlights keep curated impact lead; remaining bullets relevance-ordered
- No invented experience, technologies, employers, or years
- Optional Phase C OpenAI rewrite remains unchanged and opt-in

Eval: [eval/fr006c_summary_intelligence.md](eval/fr006c_summary_intelligence.md).

### Architecture

```
Career Profile (FR-001)
        ↓
Job Analysis (FR-002)
        ↓
Opportunity Assessment (FR-003)  +  Portfolio Matching (FR-004)
        ↓
Application Strategy (FR-005)
        ↓
Deterministic Tailoring Plan (FR-006 Phase A)
        ↓
CV Generation / Markdown render (FR-006 Phase B)
        ↓
Optional OpenAI Summary Rewrite (FR-006 Phase C)
        ↓
Owner Review (mandatory before external use)
```

**Invariants**

- The deterministic Tailoring Plan is authoritative for emphasis (skills, projects,
  themes, experience scope).
- The LLM (when enabled) rewrites Professional Summary **presentation only** from
  plan-derived structured inputs. It must not analyse the raw job description, rank
  projects, select technologies, or invent unsupported evidence.
- Fail-soft: if OpenAI rewrite fails or fails validation, the CV is still produced
  using the Career Profile summary; `summary_source` records
  `fallback_profile_copy`.

### Delivery slices

1. **Phase A** — Deterministic `TailoringPlan` (emphasis decisions only).
2. **Phase B** — Deterministic `TailoredCv` render of an approved plan.
3. **Phase C** — Optional OpenAI rewrite of the Professional Summary
   (`rewrite_summary=True`; default off). Prompt files are versioned on disk
   (`cv_summary_v1.md` historical; **`cv_summary_v2.md` current**).

### Prompt versioning

| Version | File | Role |
|---------|------|------|
| v1 | `src/career_intelligence/cv_generation/prompts/cv_summary_v1.md` | Historical baseline |
| v2 | `src/career_intelligence/cv_generation/prompts/cv_summary_v2.md` | Current — employer-relevant lead, capabilities before chronology/project names |

Bump `SUMMARY_PROMPT_VERSION` and add a new `cv_summary_vN.md` file for future prompt
changes. Do not embed production prompts in Python source. Keep prior versions for diff
and regression comparison.

### Out of scope for FR-006 (do not implement as “Phase D”)

Dynamic layouts, recruiter-focused section reordering, adaptive rendering, engineering
highlight blocks, and richer document presentation formats are **not** part of FR-006.
FR-006 decides **what** content belongs on the CV. If real-world usage later justifies
smarter presentation, consider a **new** functional requirement (for example a future
Intelligent Document Presentation FR) rather than extending FR-006. Do not create that
FR unless the owner explicitly requests it.

Acceptance Criteria

✓ Summary rewritten (Phase C, opt-in; otherwise profile summary is copied).

✓ Skills reordered.

✓ Projects prioritised.

✓ Truthfulness maintained.

✓ Output requires user review before use.

Manual validation: [eval/fr006_manual_validation.md](eval/fr006_manual_validation.md).
Design: [eval/fr006_phase_c_design.md](eval/fr006_phase_c_design.md).

---

## FR-007 Cover Letter

**Phase:** Post–Phase 2 (Horizon 1 operational)  
**Status:** **Complete** — passed owner manual validation (2026-07-29)

Generate company-specific, approximately one-page cover letters that read as if
written by an experienced AI Engineer. Same evidence-first architecture as FR-006:
a structured intermediate plan, then deterministic narrative composition
(Markdown + HTML). Owner review is mandatory before any external use.

### Objective

Maximise interview likelihood by selecting the strongest portfolio evidence for
the employer’s priorities and writing in a genuine human voice — not by listing
technologies or polishing AI-sounding prose.

### Inputs

- Trusted `ApplicationStrategy` (FR-005), including bound `JobAnalysis`
- Trusted `CareerProfile` (FR-001) via the public profile boundary
- Caller options: `owner_approved_to_plan`, optional `override_material_benefit`,
  `cover_letter_plan_approved`, optional `ContactDetails` (signature / body portfolio URL)

### Outputs

- `CoverLetterPlan` (Phase A) — composition decisions only
- `CoverLetter` (Phase B) — paragraphs + rendered Markdown; HTML via draft writer
- Draft artefacts under `career-documents/cover-letters/generated/` (gitignored):
  `.md`, `.html`, `.json`, `.cover_letter_plan.json`

### Architecture

```
Career Profile (FR-001)
        ↓
Job Analysis → Assessment → Portfolio → Application Strategy (FR-002–005)
        ↓
CoverLetterPlan (FR-007 Phase A)
  company alignment, role motivation, relevant evidence,
  evidence-ranked strongest projects, closing strategy
        ↓
CoverLetter (FR-007 Phase B) — narrative Markdown + HTML
        ↓
Owner Review (mandatory before external use)
```

Package: `career_intelligence.cover_letter`  
Manual runner: `scripts/run_cover_letter_manual.py`  
Eval / closure: [eval/fr007_cover_letter.md](eval/fr007_cover_letter.md)

### Decision making (Phase A)

- **Material-benefit gate:** platinum/gold **or** `consider_cover_letter` next
  action (else explicit `override_material_benefit`).
- **Attraction hook:** grounded JD excerpt / responsibility; marketing slogans
  (e.g. “shaping the future”) scrubbed or rejected.
- **Project selection:** ranks Career Profile projects for interview value using
  employer concern clusters (trust/explainability, production, LLM/agents,
  documents, deterministic rules, ops insights), JD/tech overlap, production
  maturity, and a *moderated* ApplicationStrategy portfolio-emphasis boost.
  Selection is role-specific; popularity or recency alone is not sufficient.
- Each selected project carries `selection_reason`, `business_outcome`, and
  `fit_focus` for explainable planning (not copied as planner jargon into prose).

### Writing principles (Phase B)

- Planner thinks like an engineer; renderer writes like a human.
- Open on why this role’s engineering challenge attracted the candidate.
- Credibility + portfolio breadth + architecture-first / deterministic /
  evidence / human-in-the-loop philosophy + collaboration; stakeholder/adoption
  sentence when the JD signals it.
- Portfolio URL introduced in the body (not only the signature).
- Projects explained as products in plain English: what it does, engineering
  capability demonstrated (domain secondary), practical outcome — with **varied**
  paragraph structures (no repeated “This demonstrates…” templates).
- Closing invites curiosity: working software, architecture trade-offs, live demos.
- No planner vocabulary in the letter; no generic apply boilerplate; no em/en
  dashes or common AI-template markers.
- Deterministic composition (no LLM rewrite on the default path).

### Invariants

- `CoverLetterPlan` is authoritative for composition decisions.
- Prose uses only plan fields and Career Profile text already selected — no
  invented employers, technologies, metrics, or achievements.
- Two-stage owner approval: `owner_approved_to_plan` → `cover_letter_plan_approved`
  → final `owner_review_required=True`.

### Validation

- Unit tests: `tests/unit/cover_letter/` (gates, selection, narrative bans,
  signature, Markdown+HTML drafts).
- Owner manual validation across genuinely different roles (e.g. Bluefin,
  Maincode, Allura, Forever New) with MD+HTML visual review alongside CVs.

### Known limitations

- Narratives for catalogued projects are curated; unknown profile projects fall
  back to summary-derived clauses.
- Selection quality depends on JobAnalysis completeness and Career Profile
  project metadata.
- Default path does not LLM-rewrite prose; authenticity comes from deterministic
  narrative rules, not generative variation.
- Generated drafts are operational artefacts (gitignored under
  `career-documents/**/generated/`); they are not submitted or emailed by the system.

### Acceptance Criteria

✓ References company, role, and portfolio.  
✓ Output requires user review before use.  
✓ Grounded in ApplicationStrategy + Career Profile (no hallucinated claims).  
✓ Reads as a letter (not an assessment dump); Markdown and HTML both generated.  
✓ Project selection differs across roles based on employer priorities.  
✓ Owner manual validation passed for closure.

---

## FR-008 Recruiter Intelligence

**Phase:** 3

Generate recruiter outreach.

Track recruiter history.

Recommend follow-ups.

All externally visible outreach must require user review before sending.

---

## FR-009 Interview Preparation

**Phase:** 7

Generate:

Recruiter interview.

Technical interview.

Behavioural interview.

Project walkthrough.

Questions to ask.

---

## FR-010 Career Dashboard

**Phase:** 8

Provide a live dashboard showing:

Applications.

Recruiters.

Visibility.

Portfolio.

Market trends.

Priority actions.

Phase 2 may provide a simple job opportunity list only; the full dashboard is out of scope for Phase 2.

---

## FR-011 Market Intelligence

**Phase:** 6

Track recurring technologies.

Recommend learning priorities.

Monitor salary trends.

---

## FR-012 Daily Prioritisation

**Phase:** 8 (full); partial in Phase 2

Recommend the highest-value activities for the day based on:

Career goals.

Outstanding tasks.

Interview opportunities.

Expected ROI.

Phase 2 supports ranked comparison of open assessed job opportunities only
(`OpportunityComparisonService`; FR-012 partial / M4). Cross-domain daily
prioritisation is deferred.

Acceptance Criteria (Phase 2 subset)

✓ Open opportunities (non-terminal status; decision ≠ skip) can be ranked
  deterministically with explainable reasons.

✓ Ranking consumes persisted Opportunity records only — no re-analysis or OpenAI.

○ Cross-domain daily prioritisation (recruiters, networking, meetups) — deferred.

---

## FR-013 Outcome Logging

**Phase:** 2

The system shall allow the user to record outcomes for assessed and pursued opportunities.

Capture:

- user decision (apply / skip / defer)
- application status
- interview stage
- outcome (where known)

**Implementation status:** Phase 2 **subset** delivered in M2 via
`OpportunityService.record_decision` / `update_outcome`. Decision, pipeline status, and
outcome kind are modelled as separate fields. Acceptance criterion “outcome history is
available to inform future assessments” (automatic feedback into FR-003) remains
**deferred** beyond Phase 2 exit.

Acceptance Criteria

✓ Outcomes can be recorded against assessed opportunities.

○ Outcome history is available to inform future assessments. *(deferred — not required for Phase 2 exit)*

---

## FR-014 Duplicate Application Detection

**Phase:** Post–Phase 2 (future)

The system shall recognise opportunities the user has already considered or applied to,
so effort is not wasted on repeats and pipeline history stays coherent.

Career Copilot should:

- recognise previously applied or assessed jobs
- store platform job IDs when available
- compare canonical URLs
- compare company / title / location
- optionally compare description fingerprints (stable digests of employer description
  text, not UI chrome)

When a platform exposes application status (for example “Applied”), that status should
be captured as **acquisition metadata** — not analysed as part of the employer’s job
description. Duplicate detection belongs with acquisition and pipeline continuity; it
must not be embedded in Job Analysis extractors.

See [10_roadmap.md](10_roadmap.md) § Automated Job Acquisition and
[06_domain_model.md](06_domain_model.md) § Job Posting — Future Evolution.

Acceptance Criteria

✓ Previously seen opportunities can be matched by platform ID and/or canonical URL.

✓ Company / title / location matching supports review when IDs are absent.

✓ Optional description fingerprinting reduces false novelty on near-identical ads.

✓ Platform application status is stored as acquisition metadata, separate from Job Analysis.

---

## Prioritisation Guidance

When scoping or implementing requirements, apply the dual-value test:

1. Does this capability improve the likelihood of securing relevant interviews or job offers?
2. Does this capability reduce the manual effort required to run an effective job search?

If neither applies, defer unless it is required infrastructure for a Phase 2 in-scope requirement.
