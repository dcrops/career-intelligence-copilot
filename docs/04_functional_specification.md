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
*capabilities* remain complete. Current Horizon 1A ids: Submission **FR-012**,
pipeline tracking **FR-013**, Recruiter Document Truth Validation **FR-014**,
bounded agents **FR-015** — see remapping in [11_changelog.md](11_changelog.md)
§ 1.47, § 1.65, and § 1.84.

### Post–Phase 2 / Horizon 1

- **Complete:** FR-001–FR-007 (through Cover Letter)
- **Current — Horizon 1A (Job application workflow):** FR-008–FR-017
- **Then — Horizon 1B (Recruiter and market engagement):** FR-018–FR-024
- **Later — Horizon 2:** FR-025+ (interview, dashboard, cross-domain prioritisation)

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
decisions. The system recommends; the user decides (owner decision / pipeline tracking — Phase 2 M2; Horizon 1A FR-013).

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
Phase 2 M2 outcome logging (historically FR-013 subset) and Horizon 1A FR-013.

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

## Horizon 1A — Job Application Workflow (FR-008–FR-017)

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
| 5 | Application preparation orchestration | FR-011 |
| 6 | Submission assistance | FR-012 |
| 7 | Application pipeline tracking | FR-013 |
| 8 | Recruiter document truth validation | FR-014 |
| 9 | Bounded agentic workflow | FR-015 |
| 10 | Multi-agent orchestration | FR-016 |
| 11 | Agent evaluation & observability | FR-017 |

Near-term entry: **Agent Orchestration Learning Spike** under FR-008 (saved/manual
job only — no live acquisition, no real submission). Live source adapters follow
once the deterministic workflow path is proven.

**Phase 2 foundations reused (historical labels):** Ranked comparison (M4; was
“FR-012 partial”) feeds FR-009. Outcome logging (M2; was “FR-013 subset”) feeds FR-013.

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

**Superseded by FR-009 M1:** persistence now runs *before* owner review and all three
decisions update that same record — see
[FR-009 delivered workflow](#delivered-workflow-m1). FR-008's other guarantees
(routing, checkpoints, retry, failure classification) are unchanged.

The runner does not branch on acquisition source. Deduplicate / rank (FR-009),
document packages (FR-010), preparation orchestration (FR-011), and submit (FR-012)
are **out of scope** for FR-008.

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
form assistance (FR-012); submission evidence.

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
**Status:** **Complete** — documentation frozen (2026-07-30). Owner reviewed and
approved; M0–M4 delivered and closed out.  
**Acceptance:** [docs/eval/fr009_opportunity_review_queue.md](eval/fr009_opportunity_review_queue.md)  
**M0 acceptance:** [docs/eval/fr009_m0_domain_contracts.md](eval/fr009_m0_domain_contracts.md)  
**M1 acceptance:** [docs/eval/fr009_m1_persistence_boundary.md](eval/fr009_m1_persistence_boundary.md)  
**M2 acceptance:** [docs/eval/fr009_m2_owner_review_actions.md](eval/fr009_m2_owner_review_actions.md)  
**M3 acceptance:** [docs/eval/fr009_m3_duplicate_detection.md](eval/fr009_m3_duplicate_detection.md)  
**M4 acceptance:** [docs/eval/fr009_m4_recommendations.md](eval/fr009_m4_recommendations.md)  
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
skip and defer stay auditable instead of disappearing. **M1 delivered that move** (see
below).

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
  **M3 implemented this** (see below): detection is derived, confirmation is the owner's.
- **Archive means review visibility only** — hide from active review. Employer
  rejection, withdrawal, and process completion are FR-013 pipeline concepts.
- Phase 2 M4 ranking is the **calibrated** fit baseline (FR-009 M4):
  `pursuit_posture → fit strength → practical_value → opportunity_id`.
  `application_tier` is effort context only — not a ranking factor. No composite score,
  no LLM ranking.
- FR-009 does not write `PipelineStatus` and does not mutate FR-002–FR-005 artefacts.

### Delivered workflow (M1)

```
Acquire → Validate → Analyse → Assess → Match → Strategy
  ↓
Allocate opportunity_id → checkpoint
  ↓
Persist Opportunity (decision = None)
  ↓
Owner Review  ← checkpoint / interrupt
  ↓
Apply | Skip | Defer
  ↓
Record Decision on that same Opportunity
  ↓
Complete
```

The interrupt is unreachable until the durable record exists: a persistence failure
pauses the run as resumable and never advances to owner review. No decision deletes or
duplicates a record, and `PipelineStatus` stays `assessed` for all three decisions.

### Review projection (M1)

`career_intelligence.review_queue.ReviewQueueService` is a read-only query over
`OpportunityService` — the queue is computed on every call, never stored.

| Query | Includes |
|-------|----------|
| `list_awaiting_review(reference_date=…)` | eligible records with no owner decision yet |
| `list_active_opportunities(reference_date=…)` | eligible records, including applied-for ones |

Exclusion reasons are explicit and deterministic: `archived`, `confirmed_duplicate`,
`skipped`, `deferred`, `closed` (terminal `PipelineStatus`), and — for the awaiting
scope only — `decided`. A record is deferred while `review.defer_until` is later than the
explicit reference date; where no date is set, a `defer` decision holds until the owner
clears it. Ordering is **pinned first**, then the unmodified M4 comparison, then stable
`opportunity_id`. Pinned items prepend the reason `"Pinned by owner"` so presentation
override is distinct from fit. Eligibility and rank position are never persisted.
`reviewed_at` does not remove a record from awaiting review — that scope means “no owner
decision yet”.

### Owner review actions (M2)

`OpportunityReviewService` writes owner review metadata against the existing Opportunity.
`ReviewQueueService` stays read-only. Supported actions:

| Action | Effect |
|--------|--------|
| `mark_reviewed` | set `reviewed_at` (preserve original on repeat); no owner decision |
| `pin` / `unpin` | toggle presentation prominence; pin rejected while archived |
| `defer_until(date)` | set `decision=defer` + `defer_until`; reject past dates vs reference date |
| `clear_defer` | clear `defer_until` and the defer decision → undecided |
| `archive` | set `archived_at` (preserve original); auto-clears pin |
| `reopen` | clear `archived_at` only — does not reset decision/defer/duplicate |

Each successful mutating action appends one `ReviewActionRecord` to
`Opportunity.review_actions` (audit evidence; never used for eligibility). Harmless
repeats are idempotent and do not append again. FR-009 still does not write
`PipelineStatus`.

### Duplicate review (M3)

**Philosophy: link, never merge.** A false merge hides a real vacancy permanently, while
a duplicate suggestion costs the owner one glance. So the system detects and explains;
the owner decides. No Opportunity is ever deleted, collapsed, or overwritten — every
discovered advertisement stays readable for provenance, audit, and recovery.

`career_intelligence.duplicates.DuplicateDetectionService` is read-only and derives
candidates on every call. Confidence is deterministic and multi-evidence:

| Confidence | Requires |
|------------|----------|
| `definite` | same canonical URL, same source URL, or same platform **and** platform job id |
| `probable` | same company and title plus a corroborating facet (location or identical description text), or same company plus identical description text |
| `possible` | same company and title only, or identical description text only |

A facet missing on either side is `unknown`, never a match. A shared
`content_fingerprint` alone never rises above `possible` — the live store already
contains fingerprint collision groups. Nothing is auto-confirmed at any confidence.

Owner actions live on `DuplicateReviewService` (writes) and mirror the M2 split:

| Action | Effect |
|--------|--------|
| `confirm_duplicate(duplicate_id, canonical_id)` | record `DuplicateRelation` on the duplicate record; both records survive |
| `reject_duplicate(a, b)` | persist a `DuplicateRejection` on **both** records so the pair never reappears |
| `confirm_canonical(canonical_id)` | re-point every group member at the chosen record; nothing is deleted |

**Duplicate groups are derived, star-shaped, and one hop deep.** The canonical record
carries no relation; every confirmed member points at it, so a group is
`canonical + members` reconstructed by one scan. Chains are rejected. Group membership
is not a workflow state: `reviewed_at`, `pinned`, `defer_until`, and `archived_at` stay
independent, and confirming a duplicate never changes an owner decision.

Canonical selection is **recommended, never applied automatically**:
artefact snapshots present → not a recruiter repost → platform rank → identity metadata
completeness → earliest discovery → `opportunity_id`. The owner confirms.

Unresolved candidates keep both records in the review queue. A confirmed member is
excluded with reason `confirmed_duplicate`; the canonical stays.

### Prioritisation and recommendations (M4)

**Philosophy: recommend attention; never decide.** Recommendations answer “what should I
work on next?” with a deterministic, explainable ordering. The owner still records
apply / skip / defer, confirms duplicates, and chooses a canonical.

`OpportunityComparisonService` uses the calibrated sort key:

`pursuit_posture → fit strength → practical_value → opportunity_id`

`application_tier` is shown as effort context only. Fit judgment `unknown` contributes 0
so missing evidence cannot raise priority. Closing dates and salary are **not** ranking
inputs — they are not fields on the Opportunity aggregate today and must not be invented.

`career_intelligence.recommendations.OpportunityRecommendationService` is read-only. It
reuses review-queue eligibility and pin ordering, then adds:

| Field | Meaning |
|-------|---------|
| `priority_band` | Coarse label: immediate / high / standard / low |
| `urgency` | From follow-up dates or interview/offer status only |
| `recommended_next_action` | Deterministic next step from decision/review/status |
| `positives` / `negatives` / `missing` / `trade_offs` | Structured explanation |
| `duplicate_group_size` | Presentation annotation when the canonical represents a group |

Recommendations are never persisted. Pin, archive, defer, and duplicate confirmation
continue to behave exactly as in M2/M3.

### Milestones

| Milestone | Scope | Status |
|-----------|-------|--------|
| M0 | Domain contracts, persistence-boundary specification, ADR-004 | **Complete** |
| M1 | Workflow persistence-boundary move + minimal derived review projection | **Complete** |
| M2 | Owner review actions, reversibility, and audit history | **Complete** |
| M3 | Duplicate candidate detection, owner confirmation, canonical selection | **Complete** |
| M4 | Prioritisation and explainable recommendations (quality over effort) | **Complete** |
| Close-out | Acceptance and documentation freeze | **Complete** |

Acceptance Criteria

✓ Previously seen opportunities can be matched by platform ID and/or canonical URL.

✓ Company / title / location matching supports review when IDs are absent.

✓ Optional description fingerprinting reduces false novelty on near-identical ads.

✓ Multiple opportunities can be ranked with explainable reasons.

✓ Queue surfaces items awaiting owner review with provenance links.

✓ Duplicate/repost handling is visible to the owner.

### Definition of Done (FR-009) — met

✓ Every successfully strategised job persists as a durable Opportunity before owner review  
✓ Review queue, duplicate groups, and recommendations are derived, never persisted  
✓ Owner review actions are reversible, idempotent on harmless repeats, and audited  
✓ Duplicates are linked and owner-confirmed — never merged, collapsed, or deleted  
✓ Recommendations are deterministic and explainable, with priority band, urgency, and
next action  
✓ Ranking is calibrated for quality (`pursuit_posture → fit_strength → practical_value →
opportunity_id`); `application_tier` is effort context only  
✓ Missing evidence cannot improve ranking; unavailable data is never invented  
✓ Unit, functional, and manual validation complete (1019 tests passing at freeze)  
✓ No `PipelineStatus` writes, no artefact mutation, no migration  
✓ Owner review complete; acceptance recorded in
[docs/eval/fr009_opportunity_review_queue.md](eval/fr009_opportunity_review_queue.md)

---

## FR-010 Application Package Preparation

**Phase:** Horizon 1A Stage 4  
**Status:** **Complete and frozen** (2026-07-31) —
[eval/fr010_application_package.md](eval/fr010_application_package.md); milestones
[M0](eval/fr010_m0_application_package.md),
[M1](eval/fr010_m1_package_durability.md),
[M2](eval/fr010_m2_owner_cli.md)

Connect approved opportunities to existing document generation:

- Tailoring Plan + Tailored CV (FR-006)
- Cover Letter (FR-007)
- HTML outputs where applicable
- Owner approval gates

Group artefacts by **application package identity** and trace them back to original
job evidence and acquisition provenance.

### M0 decisions (owner-approved)

| Decision | Rule |
|----------|------|
| Eligibility | Only Opportunities with owner decision **`apply`** may produce a package |
| Identity | One Opportunity → one current package (`opportunity_id`); regeneration **replaces** |
| Architecture | Standalone composition service — does **not** extend FR-008 orchestration |
| Persistence | Persist only the package **manifest** of artefact references; do not duplicate CV/cover-letter content into Opportunity storage |
| Gates | Compose existing FR-006 / FR-007 owner-approval gates; invent no new approval concepts |

### M1 durability and regeneration

| Guarantee | Behaviour |
|-----------|-----------|
| Load | `get` / `exists` reload the current package; draft paths resolve against service output dirs |
| Persist format | Draft refs stored as **relative filenames**; absolute M0 paths remain loadable |
| Write order | In-memory generation → CV drafts → cover-letter drafts → manifest (commit point) |
| Failure | Prior manifest remains current until a full `prepare` succeeds through manifest save |
| Idempotency | Same inputs + same `prepared_at` → identical manifest and draft bytes |
| Integrity | `get(verify=True)` fails closed if referenced drafts are missing |

### M2 owner operations (CLI)

Thin `cic package` adapter over `ApplicationPackageService` (no new business rules):

| Command | Behaviour |
|---------|-----------|
| `cic package prepare <opp_id> --approve` | Prepare/regenerate; `--approve` sets FR-006/FR-007 gates explicitly |
| `cic package show <opp_id>` | Display current package (optional `--yaml`, `--no-verify`) |
| `cic package verify <opp_id>` | Fail closed if manifest or drafts are missing/incomplete |

Optional: `--override-material-benefit`, `--dir`, `--packages-dir`, `--profile`, `--cv-dir`,
`--cover-letter-dir`.

### Acceptance Criteria

✓ Approved opportunities can produce a packaged CV + cover letter set.

✓ Artefacts are grouped and traceable to job evidence.

✓ Owner approval remains mandatory before external use.

✓ Packages reload, regenerate, and overwrite safely with deterministic manifests (M1).

✓ Owner can prepare, show, and verify packages via CLI without duplicating service logic (M2).

### Out of scope for FR-010 (frozen)

Submission (FR-012), pipeline lifecycle writes (FR-013), FR-008 runner integration,
package versioning, PDF/DOCX export, adaptive layouts, ranking or duplicate changes,
and recruiter workflows. Contact-overlay CLI flags, interactive plan-review UX, and
transactional draft staging remain documented future enhancements / deliberate deferrals
— not FR-010 reopen criteria. Preparation *coordination* after package composition is
**FR-011** (standalone orchestrator; does not amend this freeze).

---

## FR-011 Application Preparation Orchestration

**Phase:** Horizon 1A Stage 5  
**Status:** **Complete and frozen** (2026-07-31) —
[eval/fr011_application_preparation.md](eval/fr011_application_preparation.md);
milestones [M0](eval/fr011_m0_application_preparation.md),
[M1](eval/fr011_m1_executable_preparation.md)

Coordinate application package preparation as a single deterministic process by
invoking existing services — without moving business logic into the orchestrator and
without extending the FR-008 `ApplicationWorkflowRunner`.

### Final capability

```
Owner → cic preparation → ApplicationPreparationOrchestrator
  → validate_preconditions → ApplicationPackageService.prepare
```

| Component | Responsibility |
|-----------|----------------|
| CLI (`cic preparation`) | Thin interface only |
| `ApplicationPreparationOrchestrator` | Sequencing, coordination, run state |
| `ApplicationPackageService` | Package construction, validation, preparation rules |

### Milestone sequence

| Milestone | Intent | Status |
|-----------|--------|--------|
| M0 | Contracts + dedicated orchestrator | **Complete** |
| M1 | Owner-executable preparation workflow (thin CLI) | **Complete** |
| Close-out | Documentation freeze; begin FR-012 | **Complete** |

No M2–M4. Resume, FR-008 node wiring, submission, and PipelineStatus remain out of
FR-011 (not reopen criteria).

### M0 decisions

| Decision | Rule |
|----------|------|
| Architecture | Dedicated `ApplicationPreparationOrchestrator` — **not** an FR-008 graph extension |
| Preconditions | FR-002–FR-005 artefacts and owner decision ``apply`` must already exist; they are verified, not re-produced |
| Sequence | Inline fixed order: ``validate_preconditions`` → ``prepare_package`` |
| Package rules | Remain in ``ApplicationPackageService`` (FR-010); gates pass through unchanged |
| Persistence | Preparation runs under ``data/preparation_runs/`` are recovery/audit only — not Opportunity SoT |

### Acceptance Criteria (M0)

✓ Orchestrator coordinates package preparation via existing services only.

✓ Non-apply and missing artefacts fail closed at ``validate_preconditions``.

✓ FR-006/007 gate failures fail closed at ``prepare_package`` without inventing success.

✓ FR-008 runner and FR-010 package business rules remain unchanged.

### Out of scope for FR-011 M0

Submission (FR-012), PipelineStatus writes (FR-013), FR-008 ``prepare_package`` node
wiring, CLI, resume/branching routing module, package versioning, PDF/DOCX.

### M1 — Executable preparation workflow

**Business objective:** The owner can invoke preparation orchestration during the
normal apply → prepare loop, rather than only via library/manual script or by
bypassing the orchestrator with direct ``ApplicationPackageService`` calls.

**Engineering intent:** Thin ``cic preparation`` Typer adapter over
``ApplicationPreparationOrchestrator``. Sequencing stays in the orchestrator;
package rules stay in FR-010. FR-006/007 gates pass through unchanged
(``--approve`` required).

| Command | Behaviour |
|---------|-----------|
| ``cic preparation run <opp_id> --approve`` | Run orchestration; print ``PreparationRunState`` |
| ``cic preparation show <run_id>`` | Reload and display a preparation run |

``cic package`` remains supported as a direct package pathway — M1 adds an
orchestration pathway, not a replacement.

**Acceptance Criteria (M1)**

✓ Owner can execute preparation orchestration through the CLI.

✓ Successful orchestration produces a completed ``PreparationRunState``.

✓ Resulting Application Package remains verifiable via FR-010 integrity checks.

✓ Failed preconditions or gate failures result in deterministic failed runs.

✓ CLI invokes the orchestrator only — does not call ``ApplicationPackageService``
directly.

✓ FR-008 and FR-010 behaviour unchanged.

*(M1 delivered 2026-07-31 — [eval](eval/fr011_m1_executable_preparation.md))*

### Out of scope for FR-011 (frozen)

Submission (FR-012), PipelineStatus (FR-013), resume/retry, routing abstraction,
FR-008 workflow integration, versioning, package history, interactive workflows,
PDF/DOCX, additional approval logic — not FR-011 reopen criteria.

**Next planned FR:** **FR-012** Submission Assistance.

---

## FR-012 Submission Assistance

**Phase:** Horizon 1A Stage 6  
**Status:** **Complete** — documentation frozen (2026-07-31)  
**Acceptance:** [docs/eval/fr012_submission_assistance.md](eval/fr012_submission_assistance.md)

Submission is a **separate capability** from document generation and from preparation
orchestration (FR-011). It assists the owner in submitting an already-prepared
application package with explicit Owner Approval, fail-closed behaviour, and durable
SubmissionAttempt / SubmissionEvidence. It does **not** extend the FR-008 acquisition
workflow graph and does **not** advance `PipelineStatus` (that remains FR-013).

**Meaning (Horizon 1A):** Submission Readiness + Assisted Submission (manual-assisted
first) + Manual Completion + append-only audit. Live browser automation and
board-specific adapters remain deferred until a real owner need appears.

**Coordinating component name:** `SubmissionOrchestrator` (not `SubmissionService`).

| Role | Component | Responsibility |
|------|-----------|----------------|
| Coordinate | `SubmissionOrchestrator` | Sequences gates → adapter → attempt store; does not own package rules |
| Package integrity | `ApplicationPackageService` | Validates / prepares packages (FR-010); unchanged |
| Channel behaviour | `SubmissionAdapter` | Execute a channel action; no business policy |
| Persistence | `SubmissionAttemptStore` | Append-only attempt identity; validated status advances |
| Interface | `cic submission` (CLI) | Thin owner interface only |

**Why Orchestrator (consistent with FR-011):** In this repository, `*Service` owns
business rules for a domain entity (`OpportunityService`,
`ApplicationPackageService`). `ApplicationPreparationOrchestrator` sequences
existing services without absorbing their rules. FR-012's coordinator has the
same primary responsibility — sequence preconditions, adapter call, and evidence
persistence while delegating package integrity to `ApplicationPackageService` and
channel mechanics to adapters. Naming it `SubmissionService` would blur that
boundary and diverge from FR-011. Avoiding the word "Orchestrator" is unnecessary:
FR-011 already established that orchestration here means **capability
coordination**, not FR-008 workflow-graph expansion.

**The system must never silently submit an application.** Owner review and explicit
approval remain mandatory. All uncertain outcomes fail closed
(`failed` / `outcome_unknown` / `manual_action_required`) — never invent success.

### Progressive automation levels

1. Manual / Assisted Submission with generated materials (**delivered** — Horizon 1A)
2. Playwright-assisted form completion (deferred — only if owner need justifies)
3. Owner-reviewed pre-submission state
4. Explicit Owner Approval
5. Final submission only where technically safe, permitted, and reliable

Handle unsupported forms, custom / salary / work-rights questions, file uploads,
authentication, CAPTCHA or anti-bot controls, failed submission evidence, duplicate
submissions, and confirmation capture as later need arises — not as FR-012 exit scope.

Acceptance Criteria

✓ No submission without explicit Owner Approval.

✓ Fail-closed behaviour for unknown required answers / uncertain outcomes.

✓ SubmissionEvidence / failure artefacts retained for audit (append-only attempts).

✓ Package integrity remains in `ApplicationPackageService` (FR-010/FR-011).

✓ No silent `PipelineStatus` advance from FR-012 (FR-013 owns pipeline reporting).

✓ Owner-operable workflow via thin `cic submission` (check / run / record-manual /
show / list).

### Milestones

| Milestone | Delivers | Exit |
|-----------|----------|------|
| **M0** | Submission domain contracts, attempt state machine, evidence model, append-only JSON attempt store. No adapters, no orchestrator behaviour, no CLI, no network. | **Complete** ([eval](eval/fr012_m0_submission_contracts.md)) |
| **M1** | `SubmissionOrchestrator` + fake and manual-assisted adapters; gates; durable attempts for success / fail-closed / manual-action paths. No live boards, no Playwright, no PipelineStatus. | **Complete** ([eval](eval/fr012_m1_submission_orchestration.md)) |
| **M2** | Owner-operable Assisted Submission workflow — CLI is the **interface only**. | **Complete** ([eval](eval/fr012_m2_owner_workflow.md)) |
| **Close-out** | Freeze assisted-manual submission foundation; live automation remains deferred | **Complete** ([acceptance](eval/fr012_submission_assistance.md)) |

**Do not reopen without explicit owner request:** `SubmissionOrchestrator` boundary,
append-only attempt identity, distinct Owner Approval gate, offline-first adapters,
or the FR-013 PipelineStatus separation.

### Owner workflow

```
cic submission check <opp_id>
cic submission run <opp_id> --channel fake|manual_assisted --approve-submit --destination …
cic submission record-manual <opp_id> --approve-submit --attestation "…" [--destination …]
cic submission show <attempt_id>
cic submission list [--opportunity-id …]
```

All behaviour remains in `SubmissionOrchestrator`. The CLI parses flags, formats
output, and maps outcomes to exit codes only.

---

## FR-013 Application Pipeline Tracking

**Phase:** Horizon 1A Stage 7  
**Status:** **Complete and frozen**  
**Acceptance:** [eval/fr013_application_pipeline_tracking.md](eval/fr013_application_pipeline_tracking.md)  
**Architecture:** [ADR-005](adr/005_application_pipeline_lifecycle.md)  
**Milestones:** [M0](eval/fr013_m0_engineering_spike.md),
[M1](eval/fr013_m1_pipeline_contracts.md),
[M2](eval/fr013_m2_pipeline_tracking.md),
[M3](eval/fr013_m3_owner_workflow.md),
[M4](eval/fr013_m4_reporting_acceptance.md)

Track application lifecycle with timestamps, evidence, and full audit history.
Builds on Phase 2 **M2 outcome logging** (`OpportunityService.record_decision` /
`update_outcome`; historically labelled “FR-013 subset”).

**Architecture (accepted):** Opportunity remains the aggregate and stored
current-state source of truth (`PipelineStatus` + `OutcomeRecord`). Append-only
`PipelineEvent` records provide the audit trail. Coarse status plus separate
`InterviewStage` — no mega-enum. **SubmissionAttempt success does not
automatically advance `Opportunity.status`**; pipeline advancement is an explicit
owner action. Corrections are new events (never mutate or delete prior events).

Decision, pipeline status, and outcome kind remain distinct concepts. Automatic
feedback of outcome history into FR-003 assessments remains deferred unless later
scoped under Horizon 2.

| Milestone | Intent | Status |
|-----------|--------|--------|
| **M0** | Engineering spike | **Accepted** ([eval](eval/fr013_m0_engineering_spike.md)) |
| **M1** | Domain contracts, event store, ADR-005 | **Complete** ([eval](eval/fr013_m1_pipeline_contracts.md)) |
| **M2** | `PipelineTrackingService` (event + Opportunity dual-write) | **Complete** ([eval](eval/fr013_m2_pipeline_tracking.md)) |
| **M3** | Owner workflow; thin CLI | **Complete** ([eval](eval/fr013_m3_owner_workflow.md)) |
| **M4** | Reporting, CSV continuity, acceptance | **Complete** ([eval](eval/fr013_m4_reporting_acceptance.md)) |
| **Close-out** | Freeze | **Complete** ([acceptance](eval/fr013_application_pipeline_tracking.md)) |

Owner CLI:

```
cic pipeline list|show|history|preparing|submit|acknowledge|interview
cic pipeline reject|offer|accept|withdraw|follow-up|note|evidence|correct
cic pipeline check|repair|report|due|export
```

Acceptance Criteria

✓ State transitions are auditable with timestamps.

✓ Owner can see current pipeline status per application identity.

✓ Failed submission and recovery attempts are recordable.

✓ Outcomes can be recorded against assessed opportunities (Phase 2 M2 retained).

✓ SubmissionAttempt success never silently advances pipeline status (ADR-005).

✓ Derived reporting and owner-controlled pipeline CSV export available.

---

## FR-014 Recruiter Document Truth Validation

**Phase:** Horizon 1A Stage 8  
**Status:** **Complete and frozen** — M0–M4  
**Acceptance:** [eval/fr014_recruiter_document_truth_validation.md](eval/fr014_recruiter_document_truth_validation.md)  
**M0 spike:** [eval/fr014_m0_engineering_spike.md](eval/fr014_m0_engineering_spike.md) (**Accepted**)  
**M1 contracts:** [eval/fr014_m1_truth_validation_contracts.md](eval/fr014_m1_truth_validation_contracts.md)  
**M2 technology validation:** [eval/fr014_m2_technology_validation.md](eval/fr014_m2_technology_validation.md)  
**M3 owner CLI / gates:** [eval/fr014_m3_owner_workflow.md](eval/fr014_m3_owner_workflow.md)  
**M4 expanded claims:** [eval/fr014_m4_claim_validation.md](eval/fr014_m4_claim_validation.md)  
**Architecture:** [ADR-006](adr/006_recruiter_document_truth_validation.md) (Accepted)

Prevent unsupported, misleading, or incorrectly framed **candidate** claims from
reaching recruiter-facing CVs, cover letters, application answers, or future
semi-automated / automated submissions.

**Core principle:** Every material first-person candidate claim must be supported by
approved profile, employment, certification, project, or application evidence.

This is a **deterministic factual trust boundary**, not grammar checking, writing
improvement, or prompt optimisation. Motivating defect: a Redwolf cover letter
framed JD stack terms (TypeScript, Vue) as candidate capability (“…where I do my
best engineering work”) without profile evidence — an employer-evidence →
candidate-evidence boundary failure.

Preferred conceptual order: Planner → Composer → **Truth Validation** → Markdown →
HTML → PDF → Owner Review → Submission. Exact insertion points are decided by the
engineering spike
([eval/fr014_m0_engineering_spike.md](eval/fr014_m0_engineering_spike.md))
(**Accepted**): **Markdown is the primary validation surface**; dual gates after
generate (advisory) and after owner edit (authoritative before submit). Owner review
remains mandatory. Truth validation does not replace owner review.

**M1 (complete):** typed contracts in `career_intelligence.truth_validation` —
Claim, CandidateEvidenceCatalogue, TruthFinding, TruthReport; detection certainty
distinct from evidence status; PASS requires complete coverage + performed
detection/validation ([ADR-006](adr/006_recruiter_document_truth_validation.md);
[eval](eval/fr014_m1_truth_validation_contracts.md)).

**M2 (complete):** catalogue population from Career Profile;
`TruthValidationService.validate_markdown` for technology/framework claims;
Redwolf TypeScript/Vue FAIL; Python/FastAPI PASS; employer-context Class B
([eval](eval/fr014_m2_technology_validation.md)).

**M3 (complete):** thin `cic truth` CLI; sidecar TruthReport persistence with
Markdown content hashing; package external-use readiness; fail-closed FR-012
submission protection; owner correction via edit → revalidate (no rewrite)
([eval](eval/fr014_m3_owner_workflow.md)).

**M4 (complete):** employment honesty (commercial AI / software / independent),
certifications, years of experience (fail-closed or review_required when not
computable), project delivery, and domain claims — profile-authorised only
([eval](eval/fr014_m4_claim_validation.md)). Soft skills and subjective claims excluded.

**Frozen:** [acceptance](eval/fr014_recruiter_document_truth_validation.md).

**Roadmap dependency:** **FR-014 is accepted and frozen** and must remain in force
before any future work that increases application automation or reduces owner review.
FR-013 Application Pipeline Tracking is **complete and frozen** and keeps its
established identifier. **FR-015** Bounded Agentic Workflow is **complete and frozen**.
**FR-016** Multi-Agent Orchestration is **complete and frozen** (learning proof —
[acceptance](eval/fr016_multi_agent_orchestration.md)).
Next active FR: **FR-017** Agent Evaluation & Observability (owner request required;
do not auto-start).

Distinguish: (A) candidate claims (require candidate evidence); (B) employer-context
statements (JD evidence OK; must not become candidate capability); (C) aspirational /
transition statements (must not imply existing expertise); (D) judgement / motivation
(must not misrepresent facts).

Initial delivered scope (frozen): technology/framework claims, experience-duration
claims (computable tenure only), employment honesty (never equate independent work
with commercial employment without evidence), certifications, domain claims, and
project/delivery claims. Education and identity/contact crawling remain out of scope.

Behaviour: deterministic where possible; evidence-backed; explainable; **fail-closed**
for material unsupported candidate claims; traceable findings (claim, type, source,
evidence found/missing, severity, recommended owner action). Indicative results:
PASS / WARNING / FAIL. Must not silently delete claims, invent evidence, treat JD
requirements as candidate evidence, or use an LLM as the sole truth authority.

Acceptance Criteria

✓ Engineering spike completed and architecture accepted before broad implementation.

✓ Material unsupported candidate technology claims (e.g. TypeScript/Vue without
  profile evidence) fail closed and block submission.

✓ Supported candidate claims (e.g. Python/FastAPI with profile evidence) pass.

✓ Employer technology mentions are not converted into candidate capability claims.

✓ Independent engineering is not represented as commercial AI employment without
  evidence; historical proficiency is not overstated as current expertise.

✓ Generated and owner-edited Markdown can both be validated; findings are explainable.

✓ Owner review remains mandatory; truth validation does not replace it.

---

## FR-015 Bounded Agentic Workflow

**Phase:** Horizon 1A Stage 9  
**Status:** **Complete and frozen** —
[acceptance](eval/fr015_bounded_agentic_workflow.md);
[ADR-007](adr/007_bounded_agentic_workflow.md)  
*(Originally planned as FR-014; renumbered to FR-015 after insertion of FR-014
Recruiter Document Truth Validation — 2026-08-05.)*  
**M0:** [eval/fr015_m0_engineering_spike.md](eval/fr015_m0_engineering_spike.md) (Accepted)  
**M1:** [eval/fr015_m1_agent_contracts.md](eval/fr015_m1_agent_contracts.md)  
**M2:** [eval/fr015_m2_agent_runtime.md](eval/fr015_m2_agent_runtime.md)  
**M3:** [eval/fr015_m3_owner_cli.md](eval/fr015_m3_owner_cli.md)  
**M4:** [eval/fr015_m4_evaluation.md](eval/fr015_m4_evaluation.md)

Delivers Bounded Opportunity Preparation Agent (BOPA): one agent, one Opportunity,
post-acquisition. ActionProposer suggests; ToolPolicy authorises; CIC services
execute. Closed allow-list; no submit / pipeline / discovery / truth waiver /
multi-agent. Deterministic proposer is the operational default (`--llm` optional).
Thin `cic agent` CLI. Additive audit under `data/agent_runs/`.

Do not reopen FR-015 exit criteria without explicit owner request. Do not begin
FR-016 without explicit owner request.

Acceptance Criteria

✓ No agent ships without typed I/O, tool allowlist, and iteration caps.

✓ Agent decisions are traceable; unsafe tool calls are blocked.

✓ Deterministic alternatives were considered and documented for each agent.

✓ Evaluation / observability / owner manual validation complete (M4).

---

## FR-016 Multi-Agent Orchestration

**Phase:** Horizon 1A Stage 10  
**Status:** **Complete / Frozen / Accepted** — learning proof only (**GO AS LEARNING
PROOF ONLY**); prefer `cic agent run` for ordinary preparation; Engineering
Learning Academy ready
([acceptance](eval/fr016_multi_agent_orchestration.md);
[eval/fr016_m4_evaluation.md](eval/fr016_m4_evaluation.md);
[ADR-008](adr/008_multi_agent_orchestration.md)).  
*(Originally planned as FR-015; renumbered 2026-08-05.)*

Only after bounded agents (FR-015) are reliable — **FR-015 is complete and frozen**.

**Approved purpose (owner):** constrained learning milestone in production
multi-agent engineering, and architectural substrate for future
permission-separated capabilities (e.g. Job Discovery). Do **not** claim strong
near-term commercial value.

**Topology:** Deterministic Orchestration Supervisor (DOS) + frozen BOPA +
read-only Operational Briefing Specialist (OBS); typed handoffs; DelegationPolicy
+ per-specialist ToolPolicy; deterministic default; optional LLM propose only
behind policy. Prep/Truth/Review persona splitting is **rejected as multi-agent
theatre**.

Package: `career_intelligence.multi_agent` (distinct from FR-008
`orchestration` and FR-015 `agent`).

Acceptance Criteria

✓ Pattern choice is justified in an ADR or engineering note.
  → [ADR-008](adr/008_multi_agent_orchestration.md); [M0](eval/fr016_m0_engineering_spike.md).

✓ Specialists have distinct tools/context boundaries.
  → M1 registry + OBS vs BOPA allow-lists
  ([eval/fr016_m1_orchestration_contracts.md](eval/fr016_m1_orchestration_contracts.md)).

○ Loop detection and stop conditions remain enforced across agents.
  → Contracted in M1; **enforced in M2 runtime** (corpus I/J + limits).

✓ M2 go/no-go evidence (DOS/OBS value, complexity, continue vs defer).
  → **GO AS LEARNING PROOF ONLY**
  ([eval/fr016_m2_supervisor_runtime.md](eval/fr016_m2_supervisor_runtime.md)).

○ M3–M4 minimal owner surface / freeze only if owner requests learning close-out.
  → **M3 complete**; **M4 complete** — FR-016 **Complete / Frozen**
  ([acceptance](eval/fr016_multi_agent_orchestration.md);
  [eval/fr016_m4_evaluation.md](eval/fr016_m4_evaluation.md)).

---

## FR-017 Agent Evaluation & Observability

**Phase:** Horizon 1A Stage 11  
**Status:** Planned — **only after FR-016 freeze**; **owner request required**
(do not auto-start; FR-016 learning-proof result does not compel FR-017)  
*(Originally planned as FR-016; renumbered 2026-08-05.)*

Explicit evaluation for the orchestration layer:

traces; checkpoints; retries; replay; latency; token usage; cost; approval
interrupts; deterministic replay where possible; fault injection; orchestration
testing; browser journey evidence; golden workflow tests; loop prevention;
unsupported-claim checks (complementary to FR-014 truth validation — not a
substitute).

Acceptance Criteria

✓ Workflow runs produce inspectable traces.

✓ Golden workflow tests cover happy path and at least one failure/recovery path.

✓ Token/latency/cost are measurable for LLM/agent nodes.

---

## Horizon 1B — Recruiter and Market Engagement (FR-018–FR-024)

**Status:** Planned — **only after FR-017** (Horizon 1A complete and usable).  
*(Previously numbered FR-017–FR-023; renumbered 2026-08-05.)*

Recruiter outreach is an *additional acquisition channel* after the owner can
discover, assess, prepare, review, submit and track applications end to end.
Do not displace Horizon 1A work.

All externally visible outreach must require user review before sending.

---

## FR-018 Recruiter Intelligence

**Phase:** Horizon 1B  
**Status:** Planned  
*(Originally FR-017; renumbered 2026-08-05.)*

Discover and prioritise suitable recruiters. Track recruiter history. Recommend
follow-ups. Surface relationship context for outreach decisions.

---

## FR-019 Recruiter Outreach

**Phase:** Horizon 1B  
**Status:** Planned  
*(Originally FR-018; renumbered 2026-08-05.)*

Generate tailored recruiter outreach messages under mandatory owner review. No
autonomous sending.

---

## FR-020 Existing Connection Outreach

**Phase:** Horizon 1B  
**Status:** Planned  
*(Originally FR-019; renumbered 2026-08-05.)*

Support outreach to existing LinkedIn connections (and similar) with review gates,
prioritisation, and follow-up tracking.

---

## FR-021 LinkedIn Network Intelligence

**Phase:** Horizon 1B  
**Status:** Planned  
*(Originally FR-020; renumbered 2026-08-05.)*

Analyse and develop the owner’s professional network strategically — without
displacing job-application throughput.

---

## FR-022 Meetup Intelligence

**Phase:** Horizon 1B  
**Status:** Planned  
*(Originally FR-021; renumbered 2026-08-05.)*

Discover and recommend relevant Melbourne AI (and related) meetups as a networking
and learning channel.

---

## FR-023 LinkedIn Content Planning

**Phase:** Horizon 1B  
**Status:** Planned  
*(Originally FR-022; renumbered 2026-08-05.)*

Plan LinkedIn articles and related content to improve visibility — owner-approved
publishing only.

---

## FR-024 Market Intelligence

**Phase:** Horizon 1B / Horizon 2 boundary  
**Status:** Planned  
*(Originally FR-023; renumbered 2026-08-05.)*

Track recurring technologies, salary trends, and learning priorities that inform
search strategy. May begin late in 1B if it directly improves application targeting.

---

## Horizon 2 — Platform Capabilities (FR-025+)

Deferred unless they directly accelerate Horizon 1 during the active search.
*(Previously labelled FR-024+ / FR-023+ in older drafts; renumbered 2026-08-05.)*

---

## FR-025 Interview Preparation

**Phase:** Horizon 2  
**Status:** Planned  
*(Originally FR-024; renumbered 2026-08-05.)*

Generate recruiter, technical, and behavioural interview prep; project walkthroughs;
and questions to ask.

---

## FR-026 Career Dashboard

**Phase:** Horizon 2  
**Status:** Planned  
*(Originally FR-025; renumbered 2026-08-05.)*

Provide a live dashboard showing applications, recruiters, visibility, portfolio,
market trends, and priority actions. Phase 2 already provides a simple opportunity
list / CLI comparison — the full dashboard remains out of early scope.

---

## FR-027 Daily Prioritisation (cross-domain)

**Phase:** Horizon 2  
**Status:** Planned  
*(Originally FR-026; renumbered 2026-08-05.)*

Recommend the highest-value activities for the day across jobs, recruiters,
networking, and learning. Phase 2 M4 ranked comparison of *open job opportunities*
remains complete and is the job-scoped foundation (now extended by FR-009).

Acceptance Criteria (future)

○ Cross-domain daily prioritisation (recruiters, networking, meetups) — deferred.

---

## Prioritisation Guidance

When scoping or implementing requirements, apply the dual-value test:

1. Does this capability improve the likelihood of securing relevant interviews or job offers?
2. Does this capability reduce the manual effort required to run an effective job search?

If neither applies, defer unless it is required infrastructure for a Phase 2 in-scope requirement.
