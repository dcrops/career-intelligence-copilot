# Phase History

Brief narrative of completed delivery phases. For day-to-day status and sequencing,
see [10_roadmap.md](10_roadmap.md). For chronological product decisions, see
[11_changelog.md](11_changelog.md). For Phase 2 release evidence, see
[eval/phase2_release_report.md](eval/phase2_release_report.md).

This document does **not** list every changelog entry. It freezes high-level outcomes
and lessons so later work (starting with FR-006b) does not reopen settled Phase 2
questions without explicit owner intent.

---

## Phase 1 — Product Definition

**Objective:** Align vision, Phase 2 MVP scope, and repository structure before writing
product code.

**Major milestones:**

- Product vision, problem statement, and functional specification for Phase 2
- Engineering principles and domain model (decision loop)
- Repository layout (docs, operational folders, placeholders)
- ADR-001 — Python / YAML / public profile service foundation

**Outcome:** Phase 2 Job Intelligence MVP scope approved; implementation unblocked.

**Lessons learned:**

- Keep authoritative docs few and cross-linked; avoid duplicating requirements into
  chat or informal notes.
- Horizon 1 urgency must be explicit in prioritisation, or portfolio/learning goals
  will expand Phase 2 prematurely.
- Defer stack choices until a validated need exists (ADR-001 earned the foundation).

---

## Phase 2 — Job Intelligence (MVP)

**Objective:** Ship a usable vertical slice: analyse a job, assess fit, match
portfolio, recommend effort, optionally tailor a CV, persist the opportunity, record
owner decisions, and rank open opportunities — on real SEEK/LinkedIn ads.

**Major milestones:**

| Track | Delivered |
|-------|-----------|
| Intelligence | FR-001 → FR-005 (profile, analysis, assessment, portfolio, strategy) |
| Documents | FR-006 CV generation (owner-sequenced; not originally a Phase 2 exit blocker) |
| Close-out loop | M1 persistence, M2 decisions/outcomes, M3 CSV bridge, M4 ranking, M4a identity, M5 GO |

**Outcome:** Phase 2 **Complete** with formal **GO**
([eval/phase2_release_report.md](eval/phase2_release_report.md)). The decision loop is
the operational foundation for Horizon 1.

**Lessons learned:**

- Persist trusted artefacts early; ranking and list UX fail without identity and a
  durable Opportunity record (M4a was a corrective milestone, not a nice-to-have).
- Keep CSV as a derived view; structured store as system of record avoids parallel
  trackers (M3).
- Separate ranking from `OpportunityService`; keep comparison deterministic and
  explainable (M4).
- Human review and material-benefit gates (e.g. CV) are product behaviour — document
  override paths rather than weakening gates for convenience.
- Live OpenAI eval on real ads surfaces evidence-contract failures fixtures miss;
  prompt versions (FR-002 v8, FR-003 v11) are part of the baseline.

**Do not reopen without explicit owner request:** Phase 2 exit criteria, Opportunity
SoT shape, ranking sort key, or Horizon 2 domains (recruiters, networking, meetups).

---

## Next

**Current focus:** FR-006b — CV Quality Improvement  
**Then:** FR-007 Cover Letter; automated job acquisition under Horizon 1  
**Later:** Horizon 2 capability phases (see roadmap)
