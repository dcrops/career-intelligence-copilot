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
| **Horizon 1A** | End-to-end job application workflow | FR-008–FR-017 | **Current — complete first** |
| **Horizon 1B** | Recruiter and market engagement | FR-018–FR-024 | After FR-017 |

**Product progression:** Understand the candidate → Understand the opportunity →
Generate the application → Acquire jobs → Orchestrate applications → Track
pipeline → **Validate recruiter-document truth** → Introduce bounded agents →
Scale to multi-agent systems → Expand into recruiter and market intelligence.

---

## At a Glance

| Stage | Status |
|-------|--------|
| **Phase 1** — Product Definition | **Complete** |
| **Phase 2** — Job Intelligence MVP | **Complete** ([release report](eval/phase2_release_report.md)) |
| **Horizon 1A** — Job application workflow | **Current** (FR-008–FR-012 complete; FR-013 Pipeline Tracking next; FR-014 Truth Validation planned; FR-015–FR-017 planned) |
| **Horizon 1B** — Recruiter / market engagement | Not started (FR-018–FR-024; after 1A) |
| **Horizon 2** — Platform capabilities | Not started (FR-025+) |

Narrative history of completed phases: [12_phase_history.md](12_phase_history.md).

**FR remapping:** Future requirements after FR-007 were renumbered so numbering
follows implementation order — see [11_changelog.md](11_changelog.md) § 1.47,
§ 1.65, and **§ 1.84** (insert Recruiter Document Truth Validation as **FR-014**;
FR-013 Pipeline Tracking identifier unchanged).

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
| Decision & outcome logging | M2 | Historically “FR-013 subset”; foundation for **FR-013** |
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

## Current Focus — Horizon 1A Job Application Workflow (FR-008–FR-017)

**Objective:** Discover, assess, prepare, review, submit and track suitable
applications — before recruiter outreach or networking automation.

**Automation safety:** **FR-014 Recruiter Document Truth Validation** must be
accepted before any future work that increases application automation or reduces
owner review. FR-013 Application Pipeline Tracking keeps its established identifier.

**Learning objective:** Teach **agent orchestration** progressively and transparently
while building the workflow (deterministic first; bounded agents only when justified).
See [04_functional_specification.md](04_functional_specification.md) § Horizon 1A.

### Dependency order

```
FR-008 Job Acquisition & Workflow Orchestration  ✅ Complete (2026-07-29)
        ▼
FR-009 Opportunity Review Queue & Ranking  (duplicates + identity + rank)  ✅ Complete (2026-07-30)
        ▼
FR-010 Application Package Preparation  (FR-006 / FR-007)  ✅ Complete (2026-07-31)
        ▼
FR-011 Application Preparation Orchestration  ✅ Complete (2026-07-31)
        ▼
FR-012 Submission Assistance  ✅ Complete (2026-07-31)
        ▼
FR-013 Application Pipeline Tracking  ← Now
        ▼
FR-014 Recruiter Document Truth Validation  ← automation-safety gate
        ▼
FR-015 Bounded Agentic Workflow
        ▼
FR-016 Multi-Agent Orchestration
        ▼
FR-017 Agent Evaluation & Observability
        ▼
   Horizon 1B (FR-018+)
```

| Priority | Item | Intent |
|----------|------|--------|
| **Completed** | **FR-008** (2026-07-29) | Job acquisition + deterministic workflow orchestration — paste/export adapters; thin runner; owner review; checkpoint/resume; Opportunity persist on apply; bounded LLM retries; [ADR-003](adr/003_application_workflow_orchestration.md); [acceptance](eval/fr008_workflow_orchestration.md) |
| **Completed** | **FR-009** (2026-07-30) | Opportunity review queue, duplicate handling, quality-first ranking and explainable recommendations — [ADR-004](adr/004_opportunity_review_boundary.md); [acceptance](eval/fr009_opportunity_review_queue.md); milestones [M0](eval/fr009_m0_domain_contracts.md), [M1](eval/fr009_m1_persistence_boundary.md), [M2](eval/fr009_m2_owner_review_actions.md), [M3](eval/fr009_m3_duplicate_detection.md), [M4](eval/fr009_m4_recommendations.md) |
| **Completed** | **FR-010** (2026-07-31) | Application Package Preparation — standalone composition over FR-006/007, durability/regeneration, owner CLI — [acceptance](eval/fr010_application_package.md); milestones [M0](eval/fr010_m0_application_package.md), [M1](eval/fr010_m1_package_durability.md), [M2](eval/fr010_m2_owner_cli.md) |
| **Completed** | **FR-011** (2026-07-31) | Application Preparation Orchestration — dedicated orchestrator + owner CLI; [acceptance](eval/fr011_application_preparation.md); milestones [M0](eval/fr011_m0_application_preparation.md), [M1](eval/fr011_m1_executable_preparation.md) |
| **Completed** | **FR-012** (2026-07-31) | Submission Assistance — owner-assisted submit with append-only audit; [acceptance](eval/fr012_submission_assistance.md); milestones [M0](eval/fr012_m0_submission_contracts.md), [M1](eval/fr012_m1_submission_orchestration.md), [M2](eval/fr012_m2_owner_workflow.md) |
| **Now** | **FR-013** | Application pipeline tracking |
| **Next / gate** | **FR-014** | Recruiter document truth validation — fail-closed factual trust boundary before automation scales; [planning](eval/fr014_recruiter_document_truth_validation.md) |
| Later in 1A | **FR-015 → FR-017** | Bounded agents → multi-agent → evaluation |
| **After 1A** | **Horizon 1B (FR-018–FR-024)** | Recruiters, outreach, meetups, LinkedIn, market |

### FR-008 completion summary

Delivered a source-adapter acquisition boundary and a thin deterministic runner that
coordinates FR-002–FR-005, pauses for owner approval, resumes from JSON checkpoints,
and records the owner decision idempotently. **Historical FR-008 behaviour:** only
`apply` persisted an Opportunity; skip/defer completed without a durable record.
**Current behaviour (FR-009 M1):** the workflow persists after Application Strategy
and before owner review; apply, skip, and defer all update the same Opportunity.
Playwright, URL/API adapters, ranking, and submission remain out of scope.

### FR-009 completion summary

**Complete — documentation frozen (2026-07-30).** Owner reviewed and approved;
[acceptance](eval/fr009_opportunity_review_queue.md). M0 resolved the
source-of-truth question: the Opportunity is the durable record of a successfully
analysed job candidate, the review queue is a **derived projection** over it, and
workflow checkpoints remain recovery infrastructure. M1 implemented that boundary — the
workflow now persists the record after Application Strategy and before owner review, and
apply, skip, and defer all update the same record — plus a minimal read-only review
projection. M2 adds reversible owner review actions (mark reviewed, pin, defer until,
archive, reopen) with lightweight audit history. M3 adds deterministic multi-evidence
duplicate detection with owner confirmation, rejection, and canonical selection —
duplicates are **linked, never merged**, so every discovered advertisement survives.
M4 calibrates ranking for **quality over effort**
(`pursuit_posture → fit_strength → practical_value → opportunity_id`, with
`application_tier` as effort context only) and adds derived explainable recommendations —
priority band, urgency, next action, and structured positives / negatives / missing /
trade-offs. Missing evidence cannot improve ranking, and unavailable data is never
invented. Pin remains a presentation override only.

| Milestone | Scope | Status |
|-----------|-------|--------|
| M0 | Domain contracts, persistence boundary, ADR-004 | **Complete** |
| M1 | Workflow persistence-boundary move + derived review projection | **Complete** |
| M2 | Owner review actions, reversibility, and audit | **Complete** |
| M3 | Duplicate detection, owner confirmation, canonical selection (non-destructive) | **Complete** |
| M4 | Prioritisation and explainable recommendations | **Complete** |
| Close-out | Acceptance and documentation freeze | **Complete** |

Not in FR-009: application pipeline status (FR-012), document packages (FR-010),
submission (FR-011), UI, LLM ranking.
*(Remap after FR-011 M0: preparation orchestration is FR-011; submission is FR-012;
pipeline tracking is FR-013.)*



**Do not reopen without explicit owner request:** the persistence boundary, the derived
queue projection, link-never-merge duplicate policy, or the calibrated sort key.

### FR-010 completion summary

**Complete — documentation frozen (2026-07-31).** Owner close-out;
[acceptance](eval/fr010_application_package.md). M0 delivers a standalone
`ApplicationPackageService` that composes FR-006 Tailoring Plan / Tailored CV and
FR-007 Cover Letter for Opportunities with owner decision `apply`. One Opportunity
maps to one current package; regeneration replaces; the durable record is a
**manifest of references** only. M1 hardens durability: relative draft paths,
manifest commit-point semantics, idempotent prepare, and fail-closed integrity
checks. M2 adds a thin `cic package` CLI (`prepare` / `show` / `verify`) with
explicit `--approve` so FR-006/007 gates are never silently defaulted.

| Milestone | Scope | Status |
|-----------|-------|--------|
| M0 | Vertical slice — composition, eligibility, manifest, evidence | **Complete** |
| M1 | Durability, regeneration, relative paths, integrity | **Complete** |
| M2 | Owner CLI adapter | **Complete** |
| Close-out | Acceptance and documentation freeze | **Complete** |

Not in FR-010: submission (FR-011), PipelineStatus (FR-012), orchestration package
node, package versioning, PDF/DOCX, ranking or duplicate changes.
*(Remap after FR-011 M0: preparation orchestration is FR-011; submission is FR-012;
pipeline tracking is FR-013.)*



**Do not reopen without explicit owner request:** standalone composition (not
orchestration), manifest-only persistence, replace-on-regenerate cardinality, or
FR-006/007 gate preservation.

### FR-011 completion summary

**Complete — documentation frozen (2026-07-31).**
[acceptance](eval/fr011_application_preparation.md).

| Milestone | Intent | Status |
|-----------|--------|--------|
| M0 | Contracts + dedicated orchestrator | **Complete** |
| M1 | Owner-executable preparation workflow (`cic preparation`) | **Complete** |
| Close-out | Freeze FR-011; begin FR-012 | **Complete** |

Canonical flow: Owner → `cic preparation` → `ApplicationPreparationOrchestrator` →
`ApplicationPackageService`. CLI is thin; package rules stay in FR-010; FR-008
runner untouched. No M2–M4. Deferred: resume/retry, FR-008 node wiring, submission
(FR-012), PipelineStatus (FR-013).

**Do not reopen without explicit owner request:** dedicated orchestrator (not FR-008
extension), precondition-only upstream artefacts, thin CLI, or FR-006/007 gate
pass-through.

### FR-012 completion summary

**Complete — documentation frozen (2026-07-31).**
[acceptance](eval/fr012_submission_assistance.md).

| Milestone | Intent | Status |
|-----------|--------|--------|
| M0 | Contracts, evidence, state machine, append-only attempt store | **Complete** |
| M1 | `SubmissionOrchestrator` + fake / manual-assisted adapters | **Complete** |
| M2 | Owner-operable Assisted Submission workflow (`cic submission`) | **Complete** |
| Close-out | Freeze assisted-manual foundation; live automation deferred | **Complete** |

Canonical flow: Owner → `cic submission` → `SubmissionOrchestrator` →
`ApplicationPackageService` + `SubmissionAdapter` → `SubmissionAttemptStore`.
CLI is thin; package rules stay in FR-010; FR-008 runner untouched; no
PipelineStatus writes (FR-013).

**Do not reopen without explicit owner request:** `SubmissionOrchestrator`
boundary, append-only attempt identity, distinct Owner Approval,
offline-first adapters, or FR-013 PipelineStatus separation.

Not in FR-012: live board automation, Playwright, PipelineStatus lifecycle
(FR-013), FR-008 `submit` node wiring, credentials, CAPTCHA, multi-agent submit.

### Job acquisition (not “web scraping”)

Acquire via **source adapters**. Supported today: **paste** and **local export
file**. Preferred later order: APIs/feeds → job-alert email → saved-search
notifications → owner URLs → Playwright-assisted browser workflows where necessary.

Playwright is a **controlled fallback adapter** — intentionally deferred; isolated
when built; not the sole strategy. Avoid uncontrolled crawlers, mass collection,
and bypass of access controls.

### Agent Orchestration Learning Spike (complete under FR-008)

Completed before FR-008 closure: typed state; service nodes; owner interrupt;
checkpoint/resume; recoverable failure drill; ADR-003 (thin in-repo runner).

**Still must not without explicit request:** live scrape; real submission; many
autonomous agents; replace validated FR-002–FR-007 services.

Phase 2 documentation remains a **stable baseline**. Prefer additive changes.

---

## Horizon 1B — Recruiter and Market Engagement (FR-018–FR-024)

**Status:** Not started. Blocked until Horizon 1A (through FR-017) is usable end to end.

| FR | Capability |
|----|------------|
| FR-018 | Recruiter Intelligence |
| FR-019 | Recruiter Outreach |
| FR-020 | Existing Connection Outreach |
| FR-021 | LinkedIn Network Intelligence |
| FR-022 | Meetup Intelligence |
| FR-023 | LinkedIn Content Planning |
| FR-024 | Market Intelligence |

Do not implement Horizon 1B in the current phase.

---

## Future — Horizon 2 (FR-025+)

| FR | Capability |
|----|------------|
| FR-025 | Interview Preparation |
| FR-026 | Career Dashboard |
| FR-027 | Daily Prioritisation (cross-domain) |

Capability phases below organise Horizon 2 domains after Horizon 1 priorities are met.

| Phase | Domain |
|-------|--------|
| Phase 3+ | Recruiter / network (also Horizon 1B FR-018–FR-023) |
| Phase 4 | Portfolio Intelligence |
| Phase 5 | Networking Intelligence |
| Phase 6 | Learning Intelligence |
| Phase 7 | Interview Intelligence (FR-025) |
| Phase 8 | Career Dashboard (FR-026) |

### Parking Lot

Ideas that may be valuable but are deferred. Promote only via the dual-value test.
