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

After Horizon 1A, that means: **scale lawful opportunity inflow** into the finished
application loop, then recruiter / network / market engagement.

| Sub-horizon | Scope | FRs | When |
|-------------|--------|-----|------|
| **Horizon 1A** | End-to-end job application workflow | FR-008–FR-017 | **Complete / frozen** |
| **Horizon 1B** | Scaled acquisition and market engagement | FR-018–FR-025 | After usable 1A application loop (**not** gated on FR-017); **FR-018 first** |

**Product progression:** Understand the candidate → Understand the opportunity →
Generate the application → Acquire jobs → Orchestrate applications → Track
pipeline → **Validate recruiter-document truth** → Introduce bounded agents →
Scale to multi-agent systems → **Scale opportunity discovery/acquisition** →
Expand into recruiter and market intelligence.

**FR remapping (1.115):** Opportunity Discovery & Acquisition inserted as **FR-018**;
prior Horizon 1B recruiter/network/market FRs and Horizon 2 FRs shifted +1 — see
[11_changelog.md](11_changelog.md) § 1.115.

---

## At a Glance

| Stage | Status |
|-------|--------|
| **Phase 1** — Product Definition | **Complete** |
| **Phase 2** — Job Intelligence MVP | **Complete** ([release report](eval/phase2_release_report.md)) |
| **Horizon 1A** — Job application workflow | **Complete** (FR-008–FR-017 frozen; Horizon 1B next when owner chooses) |
| **Horizon 1B** — Scaled acquisition and market engagement | Not started (FR-018–FR-025; **FR-018** Opportunity Discovery & Acquisition first; **not blocked on FR-017**) |
| **Horizon 2** — Platform capabilities | Not started (FR-026+) |

Narrative history of completed phases: [12_phase_history.md](12_phase_history.md).

**FR remapping:** Future requirements after FR-007 were renumbered so numbering
follows implementation order — see [11_changelog.md](11_changelog.md) § 1.47,
§ 1.65, **§ 1.84** (insert Recruiter Document Truth Validation as **FR-014**;
FR-013 Pipeline Tracking identifier unchanged), and **§ 1.115** (Horizon 1B
reprioritisation — Opportunity Discovery & Acquisition as FR-018).

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

## Current Focus — Horizon 1A complete; Horizon 1B next (owner choice)

FR-008–FR-017 are **complete and frozen**. Next product focus is **Horizon 1B**
(FR-018+) when the owner requests it — gated on usable application loop
(FR-008–FR-015), **not** on FR-017.

**First Horizon 1B FR:** **FR-018 Opportunity Discovery & Acquisition** — scale
lawful inflow of suitable opportunities into the frozen FR-008/FR-009 path.
Recruiter Intelligence is **FR-019** (not first). See § 1.115 remapping.

**Objective:** Discover, assess, prepare, review, submit and track suitable
applications — then scale acquisition — before recruiter outreach or networking
automation.

**Automation safety:** **FR-014 Recruiter Document Truth Validation** is **accepted
and frozen** and must remain in force before any future work that increases
application automation or reduces owner review. FR-013 Application Pipeline Tracking
keeps its established identifier.

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
FR-013 Application Pipeline Tracking  ← Complete
        ▼
FR-014 Recruiter Document Truth Validation  ← Complete (automation-safety gate)
        ▼
FR-015 Bounded Agentic Workflow  ← Complete (frozen)
        ▼
FR-016 Multi-Agent Orchestration  ← Complete / Frozen / Accepted (learning proof; Academy ready)
        ▼
FR-017 Agent Evaluation & Observability  ← Complete / Frozen
        ▼
   Horizon 1B (FR-018+)  ← Not blocked on FR-017; gated on usable application loop
```

| Priority | Item | Intent |
|----------|------|--------|
| **Completed** | **FR-008** (2026-07-29) | Job acquisition + deterministic workflow orchestration — paste/export adapters; thin runner; owner review; checkpoint/resume; Opportunity persist on apply; bounded LLM retries; [ADR-003](adr/003_application_workflow_orchestration.md); [acceptance](eval/fr008_workflow_orchestration.md) |
| **Completed** | **FR-009** (2026-07-30) | Opportunity review queue, duplicate handling, quality-first ranking and explainable recommendations — [ADR-004](adr/004_opportunity_review_boundary.md); [acceptance](eval/fr009_opportunity_review_queue.md); milestones [M0](eval/fr009_m0_domain_contracts.md), [M1](eval/fr009_m1_persistence_boundary.md), [M2](eval/fr009_m2_owner_review_actions.md), [M3](eval/fr009_m3_duplicate_detection.md), [M4](eval/fr009_m4_recommendations.md) |
| **Completed** | **FR-010** (2026-07-31) | Application Package Preparation — standalone composition over FR-006/007, durability/regeneration, owner CLI — [acceptance](eval/fr010_application_package.md); milestones [M0](eval/fr010_m0_application_package.md), [M1](eval/fr010_m1_package_durability.md), [M2](eval/fr010_m2_owner_cli.md) |
| **Completed** | **FR-011** (2026-07-31) | Application Preparation Orchestration — dedicated orchestrator + owner CLI; [acceptance](eval/fr011_application_preparation.md); milestones [M0](eval/fr011_m0_application_preparation.md), [M1](eval/fr011_m1_executable_preparation.md) |
| **Completed** | **FR-012** (2026-07-31) | Submission Assistance — owner-assisted submit with append-only audit; [acceptance](eval/fr012_submission_assistance.md); milestones [M0](eval/fr012_m0_submission_contracts.md), [M1](eval/fr012_m1_submission_orchestration.md), [M2](eval/fr012_m2_owner_workflow.md) |
| **Completed** | **FR-013** (2026-08-05) | Application pipeline tracking — Opportunity SoT + append-only events + owner CLI + reporting; [ADR-005](adr/005_application_pipeline_lifecycle.md); [acceptance](eval/fr013_application_pipeline_tracking.md); milestones [M0](eval/fr013_m0_engineering_spike.md)–[M4](eval/fr013_m4_reporting_acceptance.md) |
| **Completed** | **FR-014** (2026-08-05) | Recruiter document truth validation — **complete and frozen**; [acceptance](eval/fr014_recruiter_document_truth_validation.md); [M0](eval/fr014_m0_engineering_spike.md)–[M4](eval/fr014_m4_claim_validation.md); [ADR-006](adr/006_recruiter_document_truth_validation.md) |
| **Completed** | **FR-015** (2026-08-05) | Bounded Agentic Workflow — **complete and frozen**; BOPA; [acceptance](eval/fr015_bounded_agentic_workflow.md); [M0](eval/fr015_m0_engineering_spike.md)–[M4](eval/fr015_m4_evaluation.md); [ADR-007](adr/007_bounded_agentic_workflow.md) |
| **Done** | **FR-016** | Multi-Agent Orchestration — **Complete / Frozen / Accepted** (learning proof; prefer `cic agent run`; Academy package — [acceptance](eval/fr016_multi_agent_orchestration.md); [package](masterclass/FR016/); [M4](eval/fr016_m4_evaluation.md); [ADR-008](adr/008_multi_agent_orchestration.md) |
| **Now** | **Horizon 1B / FR-018** | Opportunity Discovery & Acquisition — owner request required; **not blocked on FR-017** |
| Just completed | **FR-017** | Agent Evaluation & Observability — **Complete / Frozen** ([acceptance](eval/fr017_agent_evaluation_observability.md); [ADR-009](adr/009_orchestration_evaluation_substrate.md); [package](masterclass/FR017/)) |
| **After FR-018** | **Horizon 1B (FR-019–FR-025)** | Recruiters, outreach, meetups, LinkedIn, market |

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

### FR-013 completion summary

**Complete — documentation frozen (2026-08-05).**
[acceptance](eval/fr013_application_pipeline_tracking.md);
[ADR-005](adr/005_application_pipeline_lifecycle.md).

| Milestone | Intent | Status |
|-----------|--------|--------|
| M0 | Engineering spike (hybrid architecture) | **Complete** |
| M1 | Contracts, event store, ADR-005 | **Complete** |
| M2 | `PipelineTrackingService` event-first dual-write | **Complete** |
| M3 | Owner-operable workflow (`cic pipeline`) | **Complete** |
| M4 | Reporting, CSV continuity, acceptance | **Complete** |
| Close-out | Owner manual validation + documentation freeze | **Complete** |

Canonical flow: Owner → `cic pipeline` → `PipelineTrackingService` → append
`PipelineEvent` → project Opportunity current state → derived report / due / export.
CLI is thin; Opportunity remains SoT; SubmissionAttempt success never auto-advances
status; corrections are new events only. Legacy Phase 2 M2 `update_outcome` rows may
show status without event history — expected accepted debt.

**Do not reopen without explicit owner request:** Opportunity current-state SoT,
append-only PipelineEvents, event-first dual-write, SubmissionAttempt non-auto-advance,
or divergence/repair without projection watermark.

Not in FR-013: adaptive scoring, dashboards, email, recruiter messaging, silent
automation, Application aggregate, FR-014 truth validation.

### Job acquisition (not “web scraping”)

Acquire via **source adapters**. Supported today (FR-008 frozen): **paste** and
**local export file**. Further discovery/acquisition channels are planned under
**FR-018 Opportunity Discovery & Acquisition** (Horizon 1B lead). Preferred
investigation order for FR-018: official APIs → structured feeds → email alerts →
exports → manual URLs → supported integrations → browser automation last.

Playwright is a **controlled fallback adapter** — intentionally deferred; isolated
when built; not the sole strategy. Avoid uncontrolled crawlers, mass collection,
and bypass of access controls. Do not describe FR-018 as “web scraping.”

### Agent Orchestration Learning Spike (complete under FR-008)

Completed before FR-008 closure: typed state; service nodes; owner interrupt;
checkpoint/resume; recoverable failure drill; ADR-003 (thin in-repo runner).

**Still must not without explicit request:** live scrape; real submission; many
autonomous agents; replace validated FR-002–FR-007 services.

Phase 2 documentation remains a **stable baseline**. Prefer additive changes.

---

## Horizon 1B — Scaled Acquisition and Market Engagement (FR-018–FR-025)

**Status:** Not started (documentation remapped 2026-08-07 — changelog § 1.115).
Gated on usable Horizon 1A **application loop** (FR-008–FR-015). **Not blocked on
FR-017** ([eval/fr017_m0_engineering_spike.md](eval/fr017_m0_engineering_spike.md) §9).

**Lead FR:** Opportunity Discovery & Acquisition — feed the frozen Horizon 1A
pipeline. Recruiter / network / content / market work follows. Owner approval
required before FR-018 planning/M0 or implementation. No scrape-first design.

| FR | Capability |
|----|------------|
| FR-018 | Opportunity Discovery & Acquisition |
| FR-019 | Recruiter Intelligence |
| FR-020 | Recruiter Outreach |
| FR-021 | Existing Connection Outreach |
| FR-022 | LinkedIn Network Intelligence |
| FR-023 | Meetup Intelligence |
| FR-024 | LinkedIn Content Planning |
| FR-025 | Market Intelligence |

---

## Future — Horizon 2 (FR-026+)

| FR | Capability |
|----|------------|
| FR-026 | Interview Preparation |
| FR-027 | Career Dashboard |
| FR-028 | Daily Prioritisation (cross-domain) |

Capability phases below organise Horizon 2 domains after Horizon 1 priorities are met.

| Phase | Domain |
|-------|--------|
| Phase 3+ | Recruiter / network (also Horizon 1B FR-019–FR-024) |
| Phase 4 | Portfolio Intelligence |
| Phase 5 | Networking Intelligence |
| Phase 6 | Learning Intelligence |
| Phase 7 | Interview Intelligence (FR-026) |
| Phase 8 | Career Dashboard (FR-027) |

### Parking Lot

Ideas that may be valuable but are deferred. Promote only via the dual-value test.
