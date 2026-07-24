# Career Intelligence Copilot Roadmap

## Prioritisation Context

**Horizon 1 — Immediate:** Help the repository owner secure a suitable AI Engineering
role sooner while reducing job-search effort.

**Horizon 2 — Long term:** Evolve into a reusable Career Intelligence Platform for
ongoing career progression (networking, learning, role changes, multi-domain
intelligence).

Horizon 1 takes priority whenever the two horizons compete.

Near-term work should satisfy at least one of:

- improve the likelihood of securing relevant interviews or job offers
- reduce the manual effort required to run an effective job search

---

## At a Glance

| Stage | Status |
|-------|--------|
| **Phase 1** — Product Definition | **Complete** |
| **Phase 2** — Job Intelligence MVP | **Complete** ([release report](eval/phase2_release_report.md)) |
| **Current focus** — Horizon 1 operational follow-ons | **FR-006b** (next), then FR-007, then job acquisition |
| **Future** — Horizon 2 capability phases | Not started |

Narrative history of completed phases: [12_phase_history.md](12_phase_history.md).

---

## Completed

### Phase 1 — Product Definition

**Status:** Complete.

Delivered product vision, Phase 2 MVP scope, repository structure, and the first
implementation ADR ([ADR-001](adr/001_python_yaml_profile_foundation.md)).

---

### Phase 2 — Job Intelligence (MVP)

**Status:** **Complete** (M5 GO — 2026-07-24 —
[eval/phase2_release_report.md](eval/phase2_release_report.md)).

**Purpose:** Improve opportunity selection and reduce repetitive job-analysis work.

**Primary outcome:** Prioritise which roles deserve effort — and how much — while
reducing manual job-description analysis and tracking.

**Delivered:**

| Capability | ID | Notes |
|------------|-----|--------|
| Career Profile | FR-001 | Evidence-based YAML profile |
| Job Analysis | FR-002 | OpenAI extraction; prompt v8 |
| Opportunity Assessment | FR-003 | Technical / Commercial / Portfolio Fit; prompt v11 |
| Portfolio Matching | FR-004 | Deterministic ranking |
| Application Strategy | FR-005 | Posture + tier + next actions |
| CV Generation | FR-006 | Owner-sequenced; plan + optional summary rewrite |
| Opportunity persistence | M1 | Structured SoT; `opp_<ULID>` |
| Decision & outcome logging | M2 | FR-013 Phase 2 subset |
| CSV operational bridge | M3 | Export + one-time import; no two-way sync |
| Ranked comparison | M4 | Open opportunities; explainable |
| Opportunity identity | M4a | Grounded title/company |
| Close-out validation | M5 | Formal GO |

**Explicitly out of scope for Phase 2 (unchanged):** Cover letter (FR-007+), recruiter
outreach, interview prep, full dashboard, market intelligence, cross-domain daily
prioritisation, automated job discovery, predictive scoring.

**Exit criteria (met):** See historical checklist below and the
[release report](eval/phase2_release_report.md). Detail:
[12_phase_history.md](12_phase_history.md) § Phase 2.

#### Phase 2 Exit Criteria (historical record)

Phase 2 is complete when the decision loop in [06_domain_model.md](06_domain_model.md)
is usable on real job postings during the owner's active search.

**Engineering exit criteria:** ✓ Career profile (FR-001); ✓ Job analysis (FR-002);
✓ Three-dimension assessment (FR-003); ✓ Portfolio ranking (FR-004); ✓ Strategy with
posture/tier/actions (FR-005); ✓ Outcomes recordable (FR-013 subset); ✓ Open
opportunities ranked.

**Adoption criteria:** ✓ Owner uses the loop on real postings; ✓ Structured store +
CSV bridge connect to `applications/`; outcome logging available for assessed
opportunities.

**Explicit non-criteria:** CV/cover-letter quality polish, recruiter/interview/
dashboard/market modules, automated discovery, predictive scores, multi-user
production.

---

## Current Focus — Horizon 1 Operational MVP

Work that improves interview/offer odds or reduces search effort **on top of** the
frozen Phase 2 baseline. Do not reopen Phase 2 architecture or exit criteria.

| Priority | Item | Intent |
|----------|------|--------|
| **Next** | **FR-006b — CV Quality Improvement** | Better tailored CVs from the existing FR-006 pipeline |
| Then | **FR-007 — Cover Letter Generation** | Company-specific letters under human review |
| Then | **Automated Job Discovery / Acquisition** | Reduce copy/paste; keep analysis separate from acquisition (see below) |

Phase 2 documentation is a **stable baseline**. Prefer additive changes; update
authoritative docs when behaviour or scope changes.

---

## Future — Horizon 2 and Beyond

Capability phases below are **not** current work. They organise Horizon 2 domains
after Horizon 1 priorities are met.

| Phase | Domain |
|-------|--------|
| Phase 3 | Recruiter Intelligence |
| Phase 4 | Portfolio Intelligence |
| Phase 5 | Networking Intelligence |
| Phase 6 | Learning Intelligence |
| Phase 7 | Interview Intelligence |
| Phase 8 | Career Dashboard |

### Future ideas (Horizon 2)

Deferred unless they directly support Horizon 1 during the active search:

- Gmail / Calendar / LinkedIn / Meetup / GitHub integrations
- Salary benchmarking, recruiter scoring, interview analytics
- Commercial SaaS / multi-user (often framed as a later horizon beyond H2 platform
  reuse — not a numbered delivery phase today)

### Automated Job Acquisition (design note)

**Status:** Planned after FR-006b / FR-007 under Horizon 1 operational work — **not**
a Phase 2 reopen. Manual paste into `JobPosting` remains valid for evaluation.

```
Job Discovery → Acquisition → Metadata Normalisation → Duplicate Detection (FR-014)
      → Job Extraction (FR-002) → Candidate Fit (FR-003+)
```

| Concern | Responsibility |
|---------|----------------|
| **Job Acquisition** | Raw listing + platform metadata |
| **Job Analysis** | Structured `JobAnalysis` from trusted `JobPosting` only |

Acquisition must not live inside extractors. See
[04_functional_specification.md](04_functional_specification.md) FR-014 and
[06_domain_model.md](06_domain_model.md) § Job Posting — Future Evolution.

### Parking Lot

Ideas that may be valuable but are deferred. Promote only via the dual-value test.
