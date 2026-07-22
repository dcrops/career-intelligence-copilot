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

- FR-006 CV Generation (deferred; tailor-yes/no guidance may be added as decision support)
- FR-007 Cover Letter
- FR-008 Recruiter Intelligence
- FR-009 Interview Preparation
- FR-010 Career Dashboard (full)
- FR-011 Market Intelligence
- FR-012 Daily Prioritisation (cross-domain)
- Automated job discovery or external platform integration
- Interview Probability and Recruiter Confidence scoring (insufficient data at launch)

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

Tiers translate fit analysis into effort allocation guidance. The system recommends; the user decides.

| Tier | Pursuit posture | Effort investment |
|------|-----------------|-------------------|
| **Platinum** | Strong candidate — pursue actively | Full tailoring where materially beneficial; portfolio-led application; interview preparation investment warranted |
| **Gold** | Good candidate — pursue with confidence | Master CV with targeted adjustments; selective tailoring; moderate preparation |
| **Silver** | Viable but not ideal — pursue selectively | Master CV; minimal customisation; apply when capacity allows |
| **Skip** | Poor return on effort — do not pursue | No application effort; log rationale for future reference |

Tier assignment must be explained by referencing fit dimensions and cited evidence (FR-003, FR-005).

### Legacy Terminology

Operational data predating v1.2 may use "Tier 1" language. **Tier 1 maps to Platinum** in product documentation. Reconcile operational files when the owner approves. See [00_repository_guide.md](00_repository_guide.md) § Operational Data Conventions.

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

The system shall recommend an application tier and effort investment.

Tier definitions and effort guidance: see § Assessment and Tier Semantics.

Tiers:

- Platinum
- Gold
- Silver
- Skip

Acceptance Criteria

✓ Tier assigned.

✓ Time investment recommended.

✓ Rationale explains why the tier was assigned.

---

## FR-006 CV Generation

**Phase:** Post–Phase 2

The system shall generate tailored CVs when tailoring is materially beneficial and approved by the user.

Acceptance Criteria

✓ Summary rewritten.

✓ Skills reordered.

✓ Projects prioritised.

✓ Truthfulness maintained.

✓ Output requires user review before use.

---

## FR-007 Cover Letter

**Phase:** Post–Phase 2

Generate company-specific cover letters.

Acceptance Criteria

✓ References company.

✓ References role.

✓ References portfolio.

✓ Output requires user review before use.

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

Phase 2 supports ranked comparison of open assessed job opportunities only. Cross-domain daily prioritisation is deferred.

---

## FR-013 Outcome Logging

**Phase:** 2

The system shall allow the user to record outcomes for assessed and pursued opportunities.

Capture:

- user decision (apply / skip / defer)
- application status
- interview stage
- outcome (where known)

Acceptance Criteria

✓ Outcomes can be recorded against assessed opportunities.

✓ Outcome history is available to inform future assessments.

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
