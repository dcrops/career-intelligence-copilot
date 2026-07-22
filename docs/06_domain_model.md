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
Opportunity Assessment ← Portfolio Matching
      ↓
Application Strategy (tier + effort)
      ↓
User Decision
      ↓
Outcome Logging
      ↓
Ranked Comparison (among open opportunities)
```

Each stage produces a durable artifact that downstream stages and future assessments can reference. The loop repeats for every new opportunity.

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
tagged sections so analysis uses the complete posting, not only the body. Manual
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

A ranked list of the candidate's portfolio projects aligned to the opportunity, with explained ordering. Feeds Portfolio Fit within the assessment.

---

### Application Strategy

**Maps to:** FR-005

A tier recommendation (Platinum, Gold, Silver, Skip) with effort investment guidance and rationale linking fit dimensions to the tier.

The tier is a recommendation. The user decides whether to act on it.

---

### Pipeline Entry

An assessed opportunity tracked through its lifecycle — from evaluation through pursuit to resolution. Phase 2 provides job opportunity pipeline tracking as the automated counterpart to `applications/application_tracker.csv`.

---

### Outcome Record

**Maps to:** FR-013

Captures what happened after assessment: user decision (apply / skip / defer), application status, interview stage, outcome where known. Enables future assessments to improve and eventually supports deferred predictive dimensions.

---

### Ranked Comparison

A prioritised ordering of open assessed opportunities to support effort allocation among concurrent options. Phase 2 scope is job opportunities only — not cross-domain daily prioritisation (FR-012 deferred).

---

## Entity Relationships

| From | To | Relationship |
|------|-----|--------------|
| Career Profile | Opportunity Assessment | Profile evidence cited in fit analysis |
| Job Posting | Job Analysis | Analysis extracts structure from posting |
| Job Analysis | Opportunity Assessment | Extracted requirements inform fit dimensions |
| Portfolio Match | Opportunity Assessment | Ranking informs Portfolio Fit |
| Opportunity Assessment | Application Strategy | Fit dimensions drive tier recommendation |
| Application Strategy | User Decision | User accepts, overrides, or defers tier |
| User Decision | Outcome Record | Decision and subsequent events logged |
| Outcome Record | Opportunity Assessment | History informs future assessments (over time) |
| Pipeline Entry | Ranked Comparison | Open entries compared for prioritisation |

---

## User Actions vs System Outputs

| User provides | System produces |
|---------------|-----------------|
| Job description | Job Analysis |
| Profile updates | Updated Career Profile |
| Pursuit decisions | Outcome Records |
| — | Opportunity Assessment with evidence |
| — | Portfolio Match ranking |
| — | Application Strategy (tier + effort) |
| — | Ranked Comparison of open opportunities |

The system advises. The user commits. Important decisions remain reviewable.

---

## Operational Layer Mapping

The operational layer is the manual precursor to the automated domain model.

| Domain entity | Operational counterpart |
|---------------|------------------------|
| Career Profile | `career-documents/cv/`, owner knowledge |
| Pipeline Entry | `applications/application_tracker.csv` |
| Outcome Record | Status, Outcome, Notes columns in application tracker |
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
| Outcome Record | FR-013 |
| Duplicate Application Detection | FR-014 (future) |
| Ranked Comparison | FR-012 (partial — job opportunities only) |
| Pipeline tracking | Phase 2 in-scope (see roadmap) |
