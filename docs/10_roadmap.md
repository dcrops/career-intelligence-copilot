# Career Intelligence Copilot Roadmap

## Prioritisation Context

**Horizon 1 — Immediate:** Help the repository owner secure a suitable AI Engineering
role sooner while reducing job-search effort — by automating as much of the
application workflow as possible while preserving owner approval and evidence-based
decision making.

**Horizon 2 — Long term:** Evolve into a reusable Career Intelligence Platform for
ongoing career progression (networking, learning, role changes, multi-domain
intelligence).

Horizon 1 takes priority whenever the two horizons compete.

Near-term work should satisfy at least one of:

- improve the likelihood of securing relevant interviews or job offers
- reduce the manual effort required to run an effective job search

### Horizon 1 sequencing principle

**Job acquisition first. Recruiter outreach second.**

| Sub-horizon | Scope | FRs | When |
|-------------|--------|-----|------|
| **Horizon 1A** | End-to-end job application workflow | FR-008–FR-015 | **Current — complete first** |
| **Horizon 1B** | Recruiter and market engagement | FR-016–FR-022 | After FR-015 |

**Product progression:** Understand the candidate → Understand the opportunity →
Generate the application → Acquire jobs → Orchestrate applications → Introduce
bounded agents → Scale to multi-agent systems → Expand into recruiter and market
intelligence.

---

## At a Glance

| Stage | Status |
|-------|--------|
| **Phase 1** — Product Definition | **Complete** |
| **Phase 2** — Job Intelligence MVP | **Complete** ([release report](eval/phase2_release_report.md)) |
| **Horizon 1A** — Job application workflow | **Current** (FR-008–FR-015 planned; FR-001–007 complete) |
| **Horizon 1B** — Recruiter / market engagement | Not started (FR-016–FR-022; after 1A) |
| **Horizon 2** — Platform capabilities | Not started (FR-023+) |

Narrative history of completed phases: [12_phase_history.md](12_phase_history.md).

**FR remapping (v1.47):** Future requirements after FR-007 were renumbered so numbering
follows implementation order. See [11_changelog.md](11_changelog.md) § 1.47.

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
| Decision & outcome logging | M2 | Historically “FR-013 subset”; foundation for **FR-012** |
| CSV operational bridge | M3 | Export + one-time import; no two-way sync |
| Ranked comparison | M4 | Historically “FR-012 partial”; foundation for **FR-009** |
| Opportunity identity | M4a | Grounded title/company |
| Close-out validation | M5 | Formal GO |

**Explicitly out of scope for Phase 2 (historical):** Cover letter (later completed as
FR-007), recruiter outreach, interview prep, full dashboard, market intelligence,
cross-domain daily prioritisation, automated job discovery, predictive scoring.

#### Phase 2 Exit Criteria (historical record)

**Engineering exit criteria:** ✓ FR-001–FR-005; ✓ Outcomes recordable (M2); ✓ Open
opportunities ranked (M4).

**Adoption criteria:** ✓ Owner uses the loop on real postings; ✓ Structured store +
CSV bridge connect to `applications/`.

---

### Owner-sequenced document generation (complete)

| Capability | ID | Status |
|------------|-----|--------|
| CV Generation (+ FR-006b/c) | FR-006 | Complete |
| Cover Letter Generation | FR-007 | Complete — [eval/fr007_cover_letter.md](eval/fr007_cover_letter.md) |

---

## Current Focus — Horizon 1A Job Application Workflow (FR-008–FR-015)

**Objective:** Discover, assess, prepare, review, submit and track suitable
applications — before recruiter outreach or networking automation.

**Learning objective:** Teach **agent orchestration** progressively and transparently
while building the workflow (deterministic first; bounded agents only when justified).
See [04_functional_specification.md](04_functional_specification.md) § Horizon 1A.

### Dependency order

```
FR-008 Job Acquisition & Workflow Orchestration
        │  (learning spike on saved/manual job first; then live adapters)
        ▼
FR-009 Opportunity Review Queue & Ranking  (duplicates + identity + rank)
        ▼
FR-010 Application Package Preparation  (FR-006 / FR-007)
        ▼
FR-011 Submission Assistance
        ▼
FR-012 Application Pipeline Tracking  (extends Phase 2 M2)
        ▼
FR-013 Bounded Agentic Workflow
        ▼
FR-014 Multi-Agent Orchestration
        ▼
FR-015 Agent Evaluation & Observability
        ▼
   Horizon 1B (FR-016+)
```

| Priority | Item | Intent |
|----------|------|--------|
| **Now** | **FR-008 learning spike** | Deterministic workflow on a *saved/manual* job; owner interrupt; ADR-003 |
| Then | **FR-008 live adapters** | Source adapters (not “scraping”) after spike |
| Then | **FR-009 → FR-012** | Queue, packages, submission, tracking |
| Later in 1A | **FR-013 → FR-015** | Bounded agents → multi-agent → evaluation |
| **After 1A** | **Horizon 1B (FR-016–FR-022)** | Recruiters, outreach, meetups, LinkedIn, market |

### Job acquisition (not “web scraping”)

Acquire via **source adapters**. Preferred order: APIs/feeds → job-alert email →
saved-search notifications → owner URLs → pasted descriptions → exports →
Playwright-assisted browser workflows where necessary.

Playwright is a **controlled fallback adapter** — isolated, tested, not the sole
strategy. Avoid uncontrolled crawlers, mass collection, and bypass of access controls.

### Agent Orchestration Learning Spike (near-term)

Under **FR-008**, before live acquisition:

1. One manually supplied or existing validation job
2. Typed shared state; existing services as nodes
3. Route on real ApplicationStrategy outputs
4. Mandatory owner-review interrupt; checkpoint; resume
5. One recoverable failure; execution trace
6. Label deterministic vs LLM-backed vs agentic nodes
7. **ADR-003** — orchestration architecture (evaluate LangGraph vs existing approach)

**Must not:** live scrape; real submission; many autonomous agents; replace validated
services.

Phase 2 documentation remains a **stable baseline**. Prefer additive changes.

---

## Horizon 1B — Recruiter and Market Engagement (FR-016–FR-022)

**Status:** Not started. Blocked until Horizon 1A (through FR-015) is usable end to end.

| FR | Capability |
|----|------------|
| FR-016 | Recruiter Intelligence |
| FR-017 | Recruiter Outreach |
| FR-018 | Existing Connection Outreach |
| FR-019 | LinkedIn Network Intelligence |
| FR-020 | Meetup Intelligence |
| FR-021 | LinkedIn Content Planning |
| FR-022 | Market Intelligence |

Do not implement Horizon 1B in the current phase.

---

## Future — Horizon 2 (FR-023+)

| FR | Capability |
|----|------------|
| FR-023 | Interview Preparation |
| FR-024 | Career Dashboard |
| FR-025 | Daily Prioritisation (cross-domain) |

Capability phases below organise Horizon 2 domains after Horizon 1 priorities are met.

| Phase | Domain |
|-------|--------|
| Phase 3+ | Recruiter / network (also Horizon 1B FR-016–FR-021) |
| Phase 4 | Portfolio Intelligence |
| Phase 5 | Networking Intelligence |
| Phase 6 | Learning Intelligence |
| Phase 7 | Interview Intelligence (FR-023) |
| Phase 8 | Career Dashboard (FR-024) |

### Parking Lot

Ideas that may be valuable but are deferred. Promote only via the dual-value test.
