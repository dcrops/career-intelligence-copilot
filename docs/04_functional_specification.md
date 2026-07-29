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

### Phase 2 — Out of Scope (historical)

At Phase 2 exit these were out of scope (several are now renumbered under Horizon
1A/1B): cover letters (later completed as FR-007), recruiter intelligence, interview
prep, full dashboard, market intelligence, cross-domain daily prioritisation,
automated job discovery, predictive scoring.

**Note:** FR-006 CV Generation and FR-007 Cover Letter were originally deferred from
Phase 2 exit criteria and were later **completed** as owner-sequenced post–Phase 2
capabilities. They are not Phase 2 exit blockers. See FR-006 and FR-007 below.

**Phase 2 close-out:** **Complete** (M1–M4 + M4a + M5). Documentation is a frozen
baseline before FR-006b. See [10_roadmap.md](10_roadmap.md),
[12_phase_history.md](12_phase_history.md), and
[eval/phase2_release_report.md](eval/phase2_release_report.md).

**Historical Phase 2 FR labels (superseded numbering):** M4 ranked comparison was
tracked as “FR-012 partial”; M2 outcome logging as “FR-013 subset”. Those
*capabilities* remain complete. Identifiers FR-012 and FR-013 now mean Horizon 1A
pipeline tracking and bounded agents — see remapping in
[11_changelog.md](11_changelog.md) § 1.47.

### Post–Phase 2 / Horizon 1

- **Complete:** FR-001–FR-007 (through Cover Letter)
- **Current — Horizon 1A (Job application workflow):** FR-008–FR-015
- **Then — Horizon 1B (Recruiter and market engagement):** FR-016–FR-022
- **Later — Horizon 2:** FR-023+ (interview, dashboard, cross-domain prioritisation)

**Principle:** Job acquisition first. Recruiter outreach second.

**Product progression:** Understand the candidate → Understand the opportunity →
Generate the application → Acquire jobs → Orchestrate applications → Introduce
bounded agents → Scale to multi-agent systems → Expand into recruiter and market
intelligence.

See [10_roadmap.md](10_roadmap.md).

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
decisions. The system recommends; the user decides (owner decision / pipeline tracking — Phase 2 M2; Horizon 1A FR-012).

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
Phase 2 M2 outcome logging (historically FR-013 subset) and Horizon 1A FR-012.

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

## Horizon 1A — Job Application Workflow (FR-008–FR-015)

**Product rule:** Complete the discover → assess → prepare → review → submit → track
loop before Horizon 1B recruiter / meetup / LinkedIn engagement work.

**Agent orchestration learning:** Horizon 1A is a deliberate hands-on programme for
the owner — a production system *and* an AI Engineering learning platform. Do not
ship opaque “install a framework and wire agents” instructions. Each orchestration
feature must state: engineering reason; pattern chosen; alternatives considered;
why deterministic vs agentic; what concept is taught; how the owner validates it;
what constitutes mastery.

**Workflow fundamentals to teach:** workflow orchestration; state management; typed
state; nodes; edges; routing; conditional execution; checkpointing; retries;
resumability; observability; failure recovery; approval interrupts.

**Agent engineering to teach:** when to introduce agents; when deterministic services
are preferable; bounded reasoning; tool permissions; context boundaries; supervisor /
handoff / agents-as-tools architectures; evaluation; tracing; loop prevention; cost
optimisation; prompt-injection defence; testing agentic systems.

**Cursor modes (deliberate use):** Ask for conceptual explanation and codebase
orientation; Plan for architecture and dependency sequencing; Agent for bounded
implementation; Debug for runtime failures, state-flow issues, and browser automation
problems.

### Progressive stages

| Stage | Focus | FR |
|-------|--------|-----|
| 1–2 | Job acquisition + deterministic workflow orchestration | FR-008 |
| 3 | Opportunity review queue & ranking (incl. duplicates) | FR-009 |
| 4 | Application package preparation | FR-010 |
| 5 | Submission assistance | FR-011 |
| 6 | Application pipeline tracking | FR-012 |
| 7 | Bounded agentic workflow | FR-013 |
| 8 | Multi-agent orchestration | FR-014 |
| 9 | Agent evaluation & observability | FR-015 |

Near-term entry: **Agent Orchestration Learning Spike** under FR-008 (saved/manual
job only — no live acquisition, no real submission). Live source adapters follow
once the deterministic workflow path is proven.

**Phase 2 foundations reused (historical labels):** Ranked comparison (M4; was
“FR-012 partial”) feeds FR-009. Outcome logging (M2; was “FR-013 subset”) feeds FR-012.

---

## FR-008 Job Acquisition & Workflow Orchestration

**Phase:** Horizon 1A Stages 1–2  
**Status:** **Complete** (2026-07-29)  
**Acceptance:** [docs/eval/fr008_workflow_orchestration.md](eval/fr008_workflow_orchestration.md)  
**Architecture:** [ADR-003](adr/003_application_workflow_orchestration.md) (Accepted)

Acquire job opportunities through **source adapters** and coordinate existing
capabilities as an explicit deterministic workflow with shared typed state,
mandatory owner review, and controlled Opportunity persistence on apply.

### Delivered capabilities

- Source-adapter acquisition (paste; local export file) with explicit provenance
- Deterministic workflow orchestration (`ApplicationWorkflowRunner`)
- FR-002–FR-005 as typed workflow nodes
- JSON checkpoint / process-level resume
- Owner-review interrupt (`apply` / `skip` / `defer`)
- Apply → persist Opportunity + record decision (idempotent)
- Bounded recoverable retries for LLM-backed analyse/assess (fail-closed otherwise)
- Append-only execution event trace

**Supported acquisition today:** paste; local export file.  
**Deferred:** URL/API/email adapters; Playwright fallback; job-board integrations;
FR-009+ ranking/dedupe; submission; agents.

### Final delivered workflow

```
Acquire
  ↓
Validate / Normalise
  ↓
Analyse (FR-002)
  ↓
Assess (FR-003)
  ↓
Portfolio Match (FR-004)
  ↓
Application Strategy (FR-005)
  ↓
Owner Review  ← checkpoint / interrupt
  │
  ├─ Apply
  │    ↓
  │  Allocate opportunity_id → checkpoint
  │    ↓
  │  Persist Opportunity
  │    ↓
  │  Record Decision
  │    ↓
  │  Complete
  │
  ├─ Skip → Complete (no Opportunity)
  └─ Defer → Complete (no Opportunity)
```

The runner does not branch on acquisition source. Deduplicate / rank (FR-009),
document packages (FR-010), and submit (FR-011) are **out of scope** for FR-008.

### Preferred acquisition methods (reliability / compliance order)

1. Supported APIs or structured feeds where available *(future)*
2. Job-alert email ingestion *(future)*
3. Saved-search notifications *(future)*
4. User-supplied job URLs *(future)*
5. User-supplied pasted job descriptions ✅
6. Exported or downloaded job data ✅
7. Playwright-assisted browser workflows where necessary *(deferred)*

### Explicitly avoid as default design

- Uncontrolled crawlers or mass page collection
- Brittle HTML parsers / selector-heavy extraction tied to one layout
- Workflows intended to bypass authentication, rate limits, or access controls
- Traditional large-scale scraping as the primary acquisition strategy
- Describing this capability as “web scraping”

### Playwright positioning

Playwright remains a **deferred browser-automation adapter** — isolated behind
interfaces when built, **not** the architectural centre. Typical future uses:
owner-provided URLs; authenticated sessions; visible description extraction;
form assistance (FR-011); submission evidence.

### Canonical acquisition model (delivered fields)

`source_kind`; `source_identifier`; `source_url`; `acquired_at`; `raw_content`;
`normalised_content`; title/company provenance; `warnings`; linked `JobPosting`.

The domain model does **not** assume every job comes from browser automation.

### Definition of Done (FR-008) — met

✓ Jobs acquired from paste and local-export paths with explicit provenance  
✓ Acquisition metadata separate from Job Analysis content  
✓ Adapter boundary for future API / email / Playwright sources  
✓ No production dependency on uncontrolled crawling  
✓ End-to-end deterministic workflow with owner interrupt  
✓ Checkpoint / resume after approval demonstrated  
✓ Opportunity persist + decision record on apply (idempotent)  
✓ Skip / defer complete without Opportunity  
✓ Node execution trace recorded  
✓ Bounded failure recovery for eligible LLM nodes  
✓ ADR-003 documents architecture choice  
✓ Acceptance report and documentation freeze  

### Historical note — learning spike

The first orchestration implementation used manually supplied / fixture jobs and
produced ADR-003 before broader adapters. That spike is **complete**; FR-008 is
closed. Do not reopen spike criteria without explicit owner request.

## FR-009 Opportunity Review Queue & Ranking

**Phase:** Horizon 1A Stage 3  
**Status:** **In progress — M0 complete** (domain contracts; 2026-07-29). The queue,
ranking extensions, owner actions, and duplicate detection are **not implemented**.  
**M0 acceptance:** [docs/eval/fr009_m0_domain_contracts.md](eval/fr009_m0_domain_contracts.md)  
**Architecture:** [ADR-004](adr/004_opportunity_review_boundary.md) (Accepted)

Compare multiple acquired opportunities for owner attention — not only process each
job in isolation. Include duplicate detection, opportunity identity, ranking,
prioritisation, explanation, and an owner review queue.

Builds on Phase 2 **M4 ranked comparison** (`OpportunityComparisonService`;
historically labelled “FR-012 partial”). Extends into the acquisition workflow with
explainable ranking inputs such as:

- suitability / fit signals from FR-003–FR-005
- application tier and effort
- commercial and portfolio fit
- evidence strength and material gaps
- freshness, location fit
- duplicate or repost handling (platform ID, canonical URL, company/title/location,
  optional description fingerprints)
- opportunity identity continuity (builds on Phase 2 M4a)

When a platform exposes application status (for example “Applied”), store it as
**acquisition metadata** — not as Job Analysis content. Duplicate detection belongs
with acquisition and pipeline continuity.

Produce an owner-review queue with clear explanations. Optimise for the human
reader’s concerns, not ATS keyword frequency alone.

### Domain boundary (M0 — ADR-004)

An **Opportunity** is the durable record of a *successfully analysed job candidate that
may require an owner decision* — no longer only a job the owner decided to apply for.
Persistence belongs after FR-005 Application Strategy and **before** owner review, so
skip and defer stay auditable instead of disappearing. FR-008 currently persists on
`apply` only; **FR-009 M1** moves that node.

- `data/opportunities/` remains the single business system of record.
- The review queue is a **derived projection / query** over persisted Opportunities —
  not a second persisted aggregate. Rank position is computed, never stored.
- Workflow checkpoints (`data/workflow_runs/`) remain recovery infrastructure; no
  listing or catalogue features are added to them.
- Owner review metadata is persisted as orthogonal fields (`reviewed_at`, `pinned`,
  `defer_until`, `archived_at`) rather than one lifecycle enum, and stays distinct from
  owner decision, `PipelineStatus`, workflow status, and duplicate state.
- Confirmed duplicates are recorded as `duplicate_of` a canonical record with evidence,
  and are never merged or deleted. A shared content fingerprint alone is not proof.
- **Archive means review visibility only** — hide from active review. Employer
  rejection, withdrawal, and process completion are FR-012 pipeline concepts.
- Phase 2 M4 ranking (`pursuit_posture → fit strength → application_tier →
  opportunity_id`) is the frozen fit baseline. FR-009 adds eligibility and explicit
  owner overrides around it — no composite score, no LLM ranking.
- FR-009 does not write `PipelineStatus` and does not mutate FR-002–FR-005 artefacts.

### Milestones

| Milestone | Scope | Status |
|-----------|-------|--------|
| M0 | Domain contracts, persistence-boundary specification, ADR-004 | **Complete** |
| M1 | Deterministic review projection + workflow persistence-boundary move | Planned |
| M2 | Owner queue actions (mark reviewed, pin, defer until, archive, reopen) | Planned |
| M3 | Duplicate candidate detection + owner confirmation | Planned |
| M4 | Manual validation and ranking calibration | Planned |
| Close-out | Acceptance and documentation freeze | Planned |

Acceptance Criteria

✓ Previously seen opportunities can be matched by platform ID and/or canonical URL.

✓ Company / title / location matching supports review when IDs are absent.

✓ Optional description fingerprinting reduces false novelty on near-identical ads.

✓ Multiple opportunities can be ranked with explainable reasons.

✓ Queue surfaces items awaiting owner review with provenance links.

✓ Duplicate/repost handling is visible to the owner.

---

## FR-010 Application Package Preparation

**Phase:** Horizon 1A Stage 4  
**Status:** Planned

Connect approved opportunities to existing document generation:

- Tailoring Plan + Tailored CV (FR-006)
- Cover Letter (FR-007)
- HTML outputs where applicable
- Owner approval gates

Group artefacts by **application package identity** and trace them back to original
job evidence and acquisition provenance.

Acceptance Criteria

✓ Approved opportunities can produce a packaged CV + cover letter set.

✓ Artefacts are grouped and traceable to job evidence.

✓ Owner approval remains mandatory before external use.

---

## FR-011 Submission Assistance

**Phase:** Horizon 1A Stage 5  
**Status:** Planned

Submission is a **separate capability** from document generation.

### Progressive automation levels

1. Manual submission with generated materials
2. Playwright-assisted form completion
3. Owner-reviewed pre-submission state
4. Explicit owner approval
5. Final submission only where technically safe, permitted, and reliable

**The system must never silently submit an application.** Owner review and explicit
approval remain mandatory.

Handle unsupported forms, custom / salary / work-rights questions, file uploads,
authentication, CAPTCHA or anti-bot controls, failed submission evidence, duplicate
submissions, and confirmation capture.

**Fail closed** where any required answer is unknown or materially uncertain.
Do not fabricate answers.

Acceptance Criteria

✓ No submission without explicit owner approval.

✓ Fail-closed behaviour for unknown required answers.

✓ Submission evidence / failure artefacts can be retained for audit.

---

## FR-012 Application Pipeline Tracking

**Phase:** Horizon 1A Stage 6  
**Status:** Planned

Track application lifecycle with timestamps, evidence, and full audit history.
Builds on Phase 2 **M2 outcome logging** (`OpportunityService.record_decision` /
`update_outcome`; historically labelled “FR-013 subset”).

Indicative states: discovery; assessment; review; preparation; submission;
employer response; recruiter screen; interview; rejection; offer — plus supporting
states such as awaiting owner review, approved, rejected by owner, submission
failed, withdrawn.

Decision, pipeline status, and outcome kind remain distinct concepts. Automatic
feedback of outcome history into FR-003 assessments remains deferred unless later
scoped under Horizon 2.

Acceptance Criteria

✓ State transitions are auditable with timestamps.

✓ Owner can see current pipeline status per application identity.

✓ Failed submission and recovery attempts are recordable.

✓ Outcomes can be recorded against assessed opportunities (Phase 2 M2 retained).

---

## FR-013 Bounded Agentic Workflow

**Phase:** Horizon 1A Stage 7  
**Status:** Planned — **first introduction of bounded agentic reasoning**

Only after the deterministic workflow (FR-008) is functioning may selected nodes
become agentic.

Potential bounded agents (examples): search-query refinement; company-context
research; application-question drafting; submission recovery; quality review;
incomplete-job investigation.

Each agent must have: bounded scope; explicit tools; typed inputs; typed outputs;
maximum iterations; stop conditions; traceable reasoning; owner escalation where
necessary; validation before state updates.

Document why each selected capability benefits from agentic reasoning rather than
deterministic logic.

Acceptance Criteria

✓ No agent ships without typed I/O, tool allowlist, and iteration caps.

✓ Agent decisions are traceable; unsafe tool calls are blocked.

✓ Deterministic alternatives were considered and documented for each agent.

---

## FR-014 Multi-Agent Orchestration

**Phase:** Horizon 1A Stage 8  
**Status:** Planned — **introduces multi-agent orchestration**

Only after bounded agents (FR-013) are reliable.

Evaluate: supervisor pattern; agents as tools; handoffs; context isolation; shared
state; orchestration trade-offs; centralised vs distributed control.

Avoid role-playing agents. Each specialist must represent a genuine engineering
boundary (acquisition, job intelligence, evidence matching, preparation, submission,
compliance/approval).

Acceptance Criteria

✓ Pattern choice is justified in an ADR or engineering note.

✓ Specialists have distinct tools/context boundaries.

✓ Loop detection and stop conditions remain enforced across agents.

---

## FR-015 Agent Evaluation & Observability

**Phase:** Horizon 1A Stage 9  
**Status:** Planned

Explicit evaluation for the orchestration layer:

traces; checkpoints; retries; replay; latency; token usage; cost; approval
interrupts; deterministic replay where possible; fault injection; orchestration
testing; browser journey evidence; golden workflow tests; loop prevention;
unsupported-claim checks.

Acceptance Criteria

✓ Workflow runs produce inspectable traces.

✓ Golden workflow tests cover happy path and at least one failure/recovery path.

✓ Token/latency/cost are measurable for LLM/agent nodes.

---

## Horizon 1B — Recruiter and Market Engagement (FR-016–FR-022)

**Status:** Planned — **only after FR-015** (Horizon 1A complete and usable).

Recruiter outreach is an *additional acquisition channel* after the owner can
discover, assess, prepare, review, submit and track applications end to end.
Do not displace Horizon 1A work.

All externally visible outreach must require user review before sending.

---

## FR-016 Recruiter Intelligence

**Phase:** Horizon 1B  
**Status:** Planned

Discover and prioritise suitable recruiters. Track recruiter history. Recommend
follow-ups. Surface relationship context for outreach decisions.

---

## FR-017 Recruiter Outreach

**Phase:** Horizon 1B  
**Status:** Planned

Generate tailored recruiter outreach messages under mandatory owner review. No
autonomous sending.

---

## FR-018 Existing Connection Outreach

**Phase:** Horizon 1B  
**Status:** Planned

Support outreach to existing LinkedIn connections (and similar) with review gates,
prioritisation, and follow-up tracking.

---

## FR-019 LinkedIn Network Intelligence

**Phase:** Horizon 1B  
**Status:** Planned

Analyse and develop the owner’s professional network strategically — without
displacing job-application throughput.

---

## FR-020 Meetup Intelligence

**Phase:** Horizon 1B  
**Status:** Planned

Discover and recommend relevant Melbourne AI (and related) meetups as a networking
and learning channel.

---

## FR-021 LinkedIn Content Planning

**Phase:** Horizon 1B  
**Status:** Planned

Plan LinkedIn articles and related content to improve visibility — owner-approved
publishing only.

---

## FR-022 Market Intelligence

**Phase:** Horizon 1B / Horizon 2 boundary  
**Status:** Planned

Track recurring technologies, salary trends, and learning priorities that inform
search strategy. May begin late in 1B if it directly improves application targeting.

---

## Horizon 2 — Platform Capabilities (FR-023+)

Deferred unless they directly accelerate Horizon 1 during the active search.

---

## FR-023 Interview Preparation

**Phase:** Horizon 2  
**Status:** Planned

Generate recruiter, technical, and behavioural interview prep; project walkthroughs;
and questions to ask.

---

## FR-024 Career Dashboard

**Phase:** Horizon 2  
**Status:** Planned

Provide a live dashboard showing applications, recruiters, visibility, portfolio,
market trends, and priority actions. Phase 2 already provides a simple opportunity
list / CLI comparison — the full dashboard remains out of early scope.

---

## FR-025 Daily Prioritisation (cross-domain)

**Phase:** Horizon 2  
**Status:** Planned

Recommend the highest-value activities for the day across jobs, recruiters,
networking, and learning. Phase 2 M4 ranked comparison of *open job opportunities*
remains complete and is the job-scoped foundation (now extended by FR-009).

Acceptance Criteria (future)

○ Cross-domain daily prioritisation (recruiters, networking, meetups) — deferred.

---

 path.

✓ Token/latency/cost are measurable for LLM/agent nodes.

---

## Prioritisation Guidance

When scoping or implementing requirements, apply the dual-value test:

1. Does this capability improve the likelihood of securing relevant interviews or job offers?
2. Does this capability reduce the manual effort required to run an effective job search?

If neither applies, defer unless it is required infrastructure for a Phase 2 in-scope requirement.
