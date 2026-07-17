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

**Operational precursor:** `career-documents/` (Master CV) and implicit owner knowledge not yet structured in the repository.

---

### Job Posting

The raw input for a single opportunity — typically a job description provided by the user. Phase 2 does not include automated job discovery.

---

### Job Analysis

**Maps to:** FR-002

Structured extraction from a job posting: technologies, responsibilities, seniority, location, salary, employment type, required experience. Reduces manual reading and extraction effort.

---

### Opportunity Assessment

**Maps to:** FR-003

Evidence-backed fit analysis across three Phase 2 dimensions: Technical Fit, Commercial Fit, and Portfolio Fit. Produces an explainable summary with cited evidence from the job posting and career profile.

Post–Phase 2 dimensions (Recruiter Confidence, Interview Probability, Strategic Value) are deferred.

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
| Ranked Comparison | FR-012 (partial — job opportunities only) |
| Pipeline tracking | Phase 2 in-scope (see roadmap) |
