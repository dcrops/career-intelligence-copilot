# Domain Model

## Purpose

This document defines the conceptual domain model for Career Intelligence Copilot — the entities, relationships, and decision loop the system implements.

It is implementation-agnostic: no schema, storage, or technology choices. For requirements and acceptance criteria, see [04_functional_specification.md](04_functional_specification.md). For tier and fit semantics, see [04_functional_specification.md](04_functional_specification.md) § Assessment and Tier Semantics.

---

## Decision Loop

Phase 2 implements a single vertical slice through this loop:

```
Career Profile
      ↓
Job Posting (input)
      ↓
Job Analysis
      ↓
      ├─→ Opportunity Assessment   (whether the role fits — FR-003)
      └─→ Portfolio Matching       (which projects to lead with — FR-004)
      ↓
Application Strategy (FR-005: posture + effort tier + advisory next actions)
      ↓
User Decision
      ↓
Outcome Logging
      ↓
Ranked Comparison (among open opportunities)
```

Opportunity Assessment and Portfolio Matching are sibling consumers of Career Profile +
Job Analysis. Neither feeds or modifies the other. Application Strategy is the downstream
consumer of **both** sibling artifacts (plus Career Profile). Each stage produces a durable
artifact that downstream stages and future assessments can reference. The loop repeats for
every new opportunity.

---

## Entities

### Career Profile

**Maps to:** FR-001

A structured representation of the candidate: experience, skills, projects, certifications, goals, and preferences. Available to every decision.

Experience is a broad professional-history facet, not an employment list. Each entry is
explicitly typed by `kind` — `employment`, `independent_engineering`, or
`professional_development` — so independent engineering work and structured professional
development are never misrepresented as employment. No separate career-phase ontology exists;
phases are derived from dated, typed entries when needed.

Certifications carry an explicit `status` (`active` or `expired`) and an optional expiry
date, so lapsed credentials remain part of the historical record without being surfaced as
current.

**Implementation:** The typed schema is defined in
`src/career_intelligence/profile/models.py`; the current structured instance is
`data/career_profile.yaml`. Downstream stages access it through the public profile service.

**Operational source:** `career-documents/` (Master CV) and owner-provided goals and preferences.

---

### Job Posting

The raw input for a single opportunity — typically a job description provided by the user. Phase 2 does not include automated job discovery.

**Implementation (Phase 2):** Callers supply a typed `JobPosting` (`raw_text` plus
optional `title`, `company`, `source_url`). The OpenAI extractor formats these as
tagged sections so analysis uses the complete posting, not only the body. When
caller provenance omits title/company, extraction may return grounded
`posting_identity` values; `JobAnalysisService` binds them into the trusted
`JobPosting` only when value and evidence appear in `raw_text` (M4a). Manual
paste is the current ingestion path; automated acquisition is future work — see
[10_roadmap.md](10_roadmap.md) § Automated Job Acquisition.

#### Future Evolution

Do not redesign the Phase 2 model here. Future ingestion may attach **structured
metadata already known at acquisition time** — for example location, employment,
salary, category, and platform metadata (job IDs, canonical URLs, application
status) — so Job Analysis need not rediscover facts that the platform already
stated. Platform UI noise and personalised match content remain acquisition concerns,
not employer job-description content. Duplicate recognition is FR-014.

---

### Job Analysis

**Maps to:** FR-002

Structured extraction from a job posting alone: technologies and experience requirements
(required / preferred / unspecified), responsibilities, role family, seniority, location,
work arrangement (with optional details), compensation, and employment as working hours plus
engagement type. Material positive claims require short source evidence from the posting;
unknown, unspecified, and unstated values may omit evidence.

FR-002 does not assess candidate fit. Ambiguous seniority keeps conflicting signals without
forcing a single level. Fit evaluation against the career profile begins at Opportunity
Assessment (FR-003).

**Implementation:** Typed domain models and `JobAnalysisService` live in
`src/career_intelligence/job_analysis/`. Extractors return untrusted structured payloads;
the service alone validates the result and binds the caller-supplied Job Posting.
`FixtureExtractor` is deterministic offline scaffolding for tests and must be passed
explicitly — it is not a public default. `OpenAIJobExtractor` is the live Responses API
path; first manual evaluation and prompt hardening (through v5) are recorded in
[eval/fr002_openai_manual_eval.md](eval/fr002_openai_manual_eval.md).

---

### Opportunity Assessment

**Maps to:** FR-003

**Status:** Implemented.

Evidence-backed fit analysis across three Phase 2 dimensions: Technical Fit, Commercial Fit,
and Portfolio Fit. Produced by `OpportunityAssessmentService`, which binds a caller-owned
`JobAnalysis`, validates schema and evidence-reference integrity, and returns a trusted
`OpportunityAssessment`. Assessors (`FixtureAssessor`, package-private `OpenAIAssessor`)
return untrusted payloads only.

Judgments are qualitative (`strong`, `moderate`, `mixed`, `weak`, `misaligned`, `unknown`) —
not percentage scores. Findings cite `JobEvidenceRef` and `ProfileEvidenceRef` entries.
Independent engineering and portfolio projects demonstrate capability but are not treated as
commercial AI employment. Working rights are never inferred for the candidate.

FR-003 does **not** emit Apply/Skip/Defer, application tiers, effort guidance, or JobSeeker
quota fields — those belong to FR-005. Architecture and verification overview:
[08_implementation_notes.md](08_implementation_notes.md) § FR-003. Manual evaluation:
[eval/fr003_openai_manual_eval.md](eval/fr003_openai_manual_eval.md) (PARTIAL PASS;
assessment prompt v6).

Post–Phase 2 dimensions (Recruiter Confidence, Interview Probability, Strategic Value) remain
deferred.

---

### Portfolio Match

**Maps to:** FR-004

**Status:** Implemented.

A ranked list of the candidate's portfolio projects aligned to the opportunity, with
explained ordering and evidence-backed ranking factors. Produced by
`PortfolioMatchingService` from a trusted `CareerProfile` and `JobAnalysis`. Projects
with no matching factors remain unranked; jobs without usable technologies or
responsibilities report insufficient evidence.

Portfolio Match is independent of Opportunity Assessment. It does **not** feed or modify
Portfolio Fit. Portfolio Fit (FR-003) answers whether the portfolio supports the role;
Portfolio Match answers which projects should lead, in what order, and why.

**Implementation:** Typed domain models and `PortfolioMatchingService` live in
`src/career_intelligence/portfolio_matching/`. `DeterministicMatcher` is the production
ranking path; `FixtureMatcher` is offline scaffolding keyed to shared FR-002 fixture
markers. Neither is exported as a public default — callers inject a matcher explicitly.

---

### Application Strategy

**Maps to:** FR-005

**Status:** Implemented.

Evidence-backed application strategy for one opportunity. Produced by
`ApplicationStrategyService` from a trusted `CareerProfile`, `OpportunityAssessment`, and
`PortfolioMatch` (optional `SearchOperatingContext`). The service binds `JobAnalysis` from
the assessment after verifying posting identity against the portfolio match.

**PursuitPosture** is the primary recommendation. **ApplicationTier** (Platinum / Gold /
Silver / Bronze) is effort investment only — Bronze does not mean never apply. Advisory
`next_actions` use a closed `consider_*` taxonomy. Final apply / skip / defer is an owner
decision (FR-013).

**Implementation:** Typed domain models and `ApplicationStrategyService` live in
`src/career_intelligence/application_strategy/`. `DeterministicStrategyPlanner` is the
production path; `FixtureStrategyPlanner` is offline scaffolding. Neither is exported as a
public default — callers inject a planner explicitly. OpenAI is not required.

---

### Opportunity (durable record)

**Maps to:** Phase 2 pipeline tracking (M1 complete) + decision/outcome logging (M2 complete)

A persisted assessed opportunity with permanent id `opp_<ULID>`, lifecycle
`PipelineStatus`, optional owner decision, optional outcome record, strategy summary,
and immutable FR-002–FR-005 artifact snapshots.
Produced by `OpportunityService.create_from_strategy` after Application Strategy.
Structured storage under `data/opportunities/` is the system of record (ADR-002).
CSV export and one-time legacy import are M3 (derived / migration only). Ranking is M4
(`OpportunityComparisonService`).

**Implementation:** `src/career_intelligence/opportunities/`.

---

### Pipeline Entry

Historical domain name for the durable Opportunity aggregate above. Prefer
**Opportunity** / `OpportunityService` in implementation and new docs.

---

### Outcome Record

**Maps to:** FR-013 (Phase 2 subset delivered in M2)

Captures three distinct concepts on the durable Opportunity:

- **Decision** (`OwnerDecisionRecord`): apply / skip / defer
- **Status** (`PipelineStatus`): operational lifecycle stage
- **Outcome** (`OutcomeRecord.outcome`): pending / offer / accepted / rejected /
  withdrawn / unknown, plus interview stage, follow-up date, and notes

M2 supports record and retrieve only. Feeding outcome history into future FR-003
assessments is deferred beyond Phase 2 exit.

---

### Ranked Comparison

A prioritised ordering of open assessed opportunities to support effort allocation
among concurrent options. Phase 2 scope is job opportunities only — not cross-domain
daily prioritisation (FR-012 deferred).

**Implementation (M4):** `OpportunityComparisonService.compare_open` ranks open
Opportunity aggregates with a deterministic sort key:

1. Pursuit posture (FR-005 primary attention signal)
2. Fit strength (sum of technical + commercial + portfolio judgments)
3. Application tier (effort band)
4. `opportunity_id` (stable ascending tie-break)

Open filter: status ∈ {assessed, deferred, preparing, submitted, interviewing, offer}
and decision ≠ skip. Each ranked item includes explainable `reasons`. Owner review
required — ranking does not apply, skip, or mutate opportunities.

**Future consideration (not implemented):** Strategy summary and fit judgments are
job-application-centric. Generalising ranking to recruiters, networking, or meetups
would need a shared “rankable signals” view (or adapter) over heterogeneous opportunity
types; Phase 2 comparison remains deliberately job-scoped so that redesign is not
forced now.

---

## Entity Relationships

| From | To | Relationship |
|------|-----|--------------|
| Career Profile | Opportunity Assessment | Profile evidence cited in fit analysis |
| Career Profile | Portfolio Match | Projects ranked with `project:<id>` evidence |
| Career Profile | Application Strategy | Preferences and goals inform policy; profile evidence cited |
| Job Posting | Job Analysis | Analysis extracts structure from posting |
| Job Analysis | Opportunity Assessment | Extracted requirements inform fit dimensions |
| Job Analysis | Portfolio Match | Technologies and responsibilities drive ranking |
| Job Analysis | Application Strategy | Bound for provenance; facts cited in strategy evidence |
| Opportunity Assessment | Application Strategy | Fit judgments and findings drive posture/tier |
| Portfolio Match | Application Strategy | Ranked projects inform portfolio emphasis (no rerank) |
| Application Strategy | Opportunity | Trusted artifacts may be persisted (M1) |
| Application Strategy | User Decision | User accepts, overrides, or defers the recommendation |
| User Decision | Outcome Record | Decision and subsequent events logged (M2) |
| Outcome Record | Opportunity | Outcomes attach to durable opportunities |
| Opportunity | OpportunityComparison | Open opportunities compared for prioritisation (M4) |

Portfolio Match and Opportunity Assessment are siblings. Both feed Application Strategy.
There is no Portfolio Match → Opportunity Assessment dependency.

---

## User Actions vs System Outputs

| User provides | System produces |
|---------------|-----------------|
| Job description | Job Analysis |
| Profile updates | Updated Career Profile |
| Pursuit decisions | Outcome Records |
| — | Opportunity Assessment with evidence |
| — | Portfolio Match ranking |
| — | Application Strategy (posture + effort tier + next actions) |
| — | Ranked Comparison of open opportunities |

The system advises. The user commits. Important decisions remain reviewable.

---

## Operational Layer Mapping

The operational layer is the manual precursor to the automated domain model.

| Domain entity | Operational counterpart |
|---------------|------------------------|
| Career Profile | `career-documents/cv/`, owner knowledge |
| Opportunity (durable) | `data/opportunities/` (SoT); CSV under `data/exports/` is derived (M3) |
| Outcome Record | Status / notes on Opportunity (M2); tracker Outcome column is import/export projection |
| Network contacts | `applications/network/network_tracker.csv` (Phase 3+ domain) |
| Company context | `applications/company_notes/` |
| Career milestones | `career-log.md` |
| Future templates | `templates/` (placeholders) |
| Future analytics | `metrics/` (placeholders) |

Phase 2 engineering must respect this mapping. The future system should absorb or replace manual tracking — not ignore it.

---

## Functional Requirement Index

| Entity / capability | FR ID |
|---------------------|-------|
| Career Profile | FR-001 |
| Job Analysis | FR-002 |
| Opportunity Assessment | FR-003 |
| Portfolio Match | FR-004 |
| Application Strategy | FR-005 |
| Opportunity (durable persistence) | Phase 2 M1 (complete) |
| Outcome Record | FR-013 Phase 2 subset (M2 complete); full “inform assessments” deferred |
| CSV operational bridge | Phase 2 M3 (complete) |
| Duplicate Application Detection | FR-014 (future) |
| Ranked Comparison | FR-012 (partial — job opportunities only; M4 complete) |
| Pipeline tracking | Phase 2 M1–M5 complete |
| Opportunity identity (title/company) | Phase 2 M4a complete |
