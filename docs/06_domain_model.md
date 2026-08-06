# Domain Model

## Purpose

This document defines the conceptual domain model for Career Intelligence Copilot — the entities, relationships, and decision loop the system implements.

It is implementation-agnostic: no schema, storage, or technology choices. For requirements and acceptance criteria, see [04_functional_specification.md](04_functional_specification.md). For tier and fit semantics, see [04_functional_specification.md](04_functional_specification.md) § Assessment and Tier Semantics.

---

## Decision Loop

Phase 2 delivered a vertical slice through analysis → strategy → document generation.
Horizon 1A extends that into an end-to-end application workflow:

```
Job Acquisition (FR-008; adapters — not “scraping” by default)
      ↓
Validate → Normalise → Duplicate candidates (FR-009 — surfaced, never auto-merged)
      ↓
Career Profile + Job Posting
      ↓
Job Analysis (FR-002)
      ↓
      ├─→ Opportunity Assessment   (FR-003)
      └─→ Portfolio Matching       (FR-004)
      ↓
Application Strategy (FR-005)
      ↓
Persist Opportunity (FR-009 M1 — before any owner decision, decision = None)
      ↓
Owner Review / Approval Interrupt (FR-008) → apply | skip | defer recorded on that record
      ↓
Rank / Review Queue (Phase 2 M4 baseline + FR-009 derived projection)
      ↓
CV Generation (FR-006) + Cover Letter Generation (FR-007)
      ↓
Application Package (FR-010 / FR-011 — composition + preparation orchestration)
      ↓
Truth Validation (FR-014 — Markdown authoritative; fail-closed external-use gate;
[ADR-006](adr/006_recruiter_document_truth_validation.md))
      ↓
Bounded Opportunity Preparation Agent (FR-015 — readiness coordination; stops for owner;
[ADR-007](adr/007_bounded_agentic_workflow.md))
      ↓
Owner Review (mandatory) → Render (HTML/PDF) → Manual / Assisted Submission (FR-012 — never silent)
      ↓
Pipeline Tracking (FR-013; builds on Phase 2 M2)
      ↓
Reporting → Operational History (derived report / due / export + append-only events)
```

**Owner-facing production summary (post–FR-015):** Job Analysis → Opportunity
Assessment → Portfolio Match → Application Strategy → CV Generation → Cover Letter
Generation → Application Package → Truth Validation → Bounded Opportunity Preparation
Agent → Owner Review → Submission → Pipeline Tracking.

**FR-014 (complete and frozen):** Truth Validation gates recruiter-facing Markdown
(advisory after generate; authoritative after owner edit) before external use. It does
not replace owner review.

**FR-015 (complete and frozen):** BOPA coordinates post-acquisition package/truth
readiness and stops for owner review. It does not submit, advance pipeline, or waive
truth ([acceptance](eval/fr015_bounded_agentic_workflow.md)).

Opportunity Assessment and Portfolio Matching remain sibling consumers of Career Profile +
Job Analysis. Application Strategy consumes both. Document generation and submission are
separate stages under mandatory owner review. Recruiter Document Truth Validation (FR-014)
is the fail-closed factual trust boundary before recruiter-facing artefacts scale
toward automation ([ADR-006](adr/006_recruiter_document_truth_validation.md)). Workflow
orchestration (FR-008) coordinates acquisition/pre-decision nodes; preparation
orchestration (FR-011) coordinates package prep; BOPA (FR-015) coordinates readiness
for owner review without replacing those services.

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

### Job Acquisition Record

**Maps to:** FR-008 (complete); provenance feeds FR-009 duplicate detection

Canonical record of how a job entered the system via a **source adapter**. Indicative
fields: source type; source identifier; source URL; acquisition timestamp; raw and
normalised content; employer; title; location; work arrangement; employment type;
salary; posting/closing dates; provenance; acquisition status; extraction warnings.

Preferred adapters (reliability / compliance order): APIs/feeds → job-alert email →
saved-search notifications → owner URLs → pasted descriptions → exports →
Playwright-assisted browser workflows as a **controlled fallback**. Do not assume
browser automation for every job. See [04_functional_specification.md](04_functional_specification.md)
§ FR-008 and [10_roadmap.md](10_roadmap.md) § Horizon 1A.

---

### Job Posting

Trusted employer-facing job description used by Job Analysis — typically derived from
an acquisition record’s normalised content, or still supplied by manual paste (Phase 2 path).

**Implementation (Phase 2 / current):** Callers supply a typed `JobPosting` (`raw_text`
plus optional `title`, `company`, `source_url`). The OpenAI extractor formats these as
tagged sections so analysis uses the complete posting, not only the body. When
caller provenance omits title/company, extraction may return grounded
`posting_identity` values; `JobAnalysisService` binds them into the trusted
`JobPosting` only when value and evidence appear in `raw_text` (M4a).

#### Horizon 1A evolution

Attach **structured metadata known at acquisition time** (location, employment,
salary, platform IDs, canonical URLs, platform application status) so Job Analysis
need not rediscover platform facts. Platform UI noise and personalised match content
remain acquisition concerns — not employer job-description content. Duplicate
recognition is FR-009.

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

Evidence-backed fit analysis comparing Career Profile with Job Analysis across
Technical, Commercial, and Portfolio Fit. Produces explainable findings with
evidence refs. Does **not** assign application tiers, apply/skip decisions, or
effort guidance — those belong to Application Strategy (FR-005).

**Implementation:** `OpportunityAssessmentService` in
`src/career_intelligence/opportunity_assessment/` is the trust boundary.
`OpenAIAssessor` (prompt v11) is the live path; `FixtureAssessor` is offline scaffolding.

---

### Portfolio Match

**Maps to:** FR-004

Ranked list of portfolio projects to lead with for a role, with evidence-backed
factors. Sibling of Opportunity Assessment — both consume Career Profile + Job
Analysis; neither feeds the other.

**Implementation:** `PortfolioMatchingService` with deterministic matching as the
production path.

---

### Application Strategy

**Maps to:** FR-005

Pursuit posture (primary recommendation), application tier (effort band), practical
value, evidence-backed reasons/risks, and advisory `next_actions`. Consumes
Opportunity Assessment + Portfolio Match (+ Job Analysis for provenance).

Owner apply / skip / defer is recorded separately (Phase 2 M2; Horizon 1A FR-013).

**Implementation:** `ApplicationStrategyService` with `DeterministicStrategyPlanner`.

---

### Tailored CV / Cover Letter

**Maps to:** FR-006 / FR-007 (complete)

Optional Horizon 1 document artefacts under mandatory owner review. Consumed by
Horizon 1A package preparation (FR-010).

---

### Opportunity (durable)

Durable record of a **successfully analysed job candidate that may require an owner
decision** — not only a job the owner decided to apply for
([ADR-004](adr/004_opportunity_review_boundary.md)). Produced by `OpportunityService`
after Application Strategy. Structured storage under `data/opportunities/` is the
system of record (ADR-002). CSV export and one-time legacy import are M3. Ranking is M4
(`OpportunityComparisonService`). Owner decision and outcome logging are M2
(historically “FR-013 subset”; extended by Horizon 1A **FR-013**).

The record carries five separate concerns that must not be collapsed: identity and
acquisition provenance; denormalised FR-003–FR-005 signals (`strategy_summary`); the
owner decision (apply / skip / defer); owner review metadata (FR-009); and pipeline
status plus outcome (M2 / FR-013). Since **FR-009 M1** the workflow creates the record
after Application Strategy and before owner review, with `decision=None`; apply, skip,
and defer then update that same record, so skipped and deferred jobs remain auditable.

**Implementation:** `src/career_intelligence/opportunities/`.

---

### Pipeline Entry

Historical domain name for the durable Opportunity aggregate above. Prefer
**Opportunity** / `OpportunityService` in implementation and new docs.

---

### Outcome Record

**Maps to:** Phase 2 M2 (historically “FR-013 subset”); extended by FR-013

Captures three distinct concepts on the durable Opportunity:

- **Decision** (`OwnerDecisionRecord`): apply / skip / defer
- **Status** (`PipelineStatus`): operational lifecycle stage
- **Outcome** (`OutcomeRecord.outcome`): pending / offer / accepted / rejected /
  withdrawn / unknown, plus interview stage, follow-up date, and notes

M2 supports record and retrieve only. Feeding outcome history into future FR-003
assessments remains deferred.

---

### Owner Review Metadata

**Maps to:** FR-009 (M0 contracts; M2 owner actions and M3 duplicate review complete)

Owner-authored annotations on a durable Opportunity that control **review visibility and
attention**, held as independent fields rather than one lifecycle enum: `reviewed_at`,
`pinned`, `defer_until`, `archived_at`.

Distinct from the owner decision (apply / skip / defer records *what the owner chose*),
from `PipelineStatus` (application progress — FR-013), and from workflow status (a run's
runtime state — FR-008). Archiving hides a record from active review; it never means
employer rejection or a closed recruitment process.

Queue eligibility, rank position, age, and staleness are **derived** from these fields —
not stored. See [ADR-004](adr/004_opportunity_review_boundary.md).

**Service:** `OpportunityReviewService` (`mark_reviewed`, `pin`, `unpin`, `defer_until`,
`clear_defer`, `archive`, `reopen`). Append-only audit evidence lives on
`Opportunity.review_actions` and is never used for eligibility.

---

### Review Queue (derived)

**Maps to:** FR-009 M1 (complete; pin ordering extended in M2)

Not an entity with its own storage: a **projection** computed on demand from persisted
Opportunities plus an explicit reference date. Two scopes exist — *awaiting review*
(no owner decision yet; `reviewed_at` alone does not remove a record) and *active*
(still live, including applied-for records).

A record is excluded when it is archived, a confirmed duplicate, skipped, currently
deferred, or closed by a terminal `PipelineStatus`; every omission carries a reason so
ordering is explainable. Eligible records are ordered **pinned first**, then by the
unchanged M4 sort key.

**Implementation:** `src/career_intelligence/review_queue/` (`ReviewQueueService`).

---

### Duplicate Relation

**Maps to:** FR-009 (M0 contract; M3 detection and confirmation complete)

An owner-confirmed link from a duplicate Opportunity to its canonical record
(`duplicate_of`), with confirmation timestamp and the evidence kinds that justified it
(platform job ID, canonical URL, identity facets, content fingerprint, owner judgment).

Non-destructive by contract: both records keep their own identity, provenance, and
artefacts, and remain auditable. Detection proposes candidates; only the owner confirms.
A shared content fingerprint alone is not proof — the live store already contains
fingerprint collision groups.

A **rejected** suggestion is equally durable: `duplicate_rejections` records the pair on
both records so the same question is never asked twice.

**Implementation:** `opportunities.DuplicateReviewService` (`confirm_duplicate`,
`reject_duplicate`, `confirm_canonical`).

---

### Duplicate Group (derived)

**Maps to:** FR-009 M3 (complete)

The set of advertisements the owner has confirmed describe **one real-world vacancy**.
Not a stored aggregate: it is derived by scanning `duplicate_of` links, the same way the
review queue is derived. Star-shaped and one hop deep — the canonical record carries no
relation, every member points at it, and chains are rejected.

Grouping never merges or deletes: each advertisement keeps its own identity, provenance,
and FR-002–FR-005 artefacts, because a false merge would permanently hide a real
vacancy while a visible duplicate only costs a glance. Group membership is not a workflow
state; `reviewed_at`, `pinned`, `defer_until`, `archived_at`, and the owner decision stay
independent of it.

Canonical selection is **recommended deterministically and confirmed by the owner**:
artefact evidence present → not a recruiter repost → platform rank → metadata
completeness → earliest discovery → `opportunity_id`.

**Implementation:** `src/career_intelligence/duplicates/` (`DuplicateDetectionService`).

---

### Opportunity Recommendation (derived)

**Maps to:** FR-009 M4 (complete)

A prioritised, explainable suggestion for owner attention — not an autonomous decision.
Derived from the review-queue eligibility projection plus the calibrated comparison sort
key (`pursuit_posture → fit_strength → practical_value → opportunity_id`). Effort tier is
context only. Each recommendation carries a priority band, urgency, a recommended next
action, and structured positives / negatives / missing / trade-offs. Urgency comes only
from genuine workflow state (follow-up date, interview or offer status) — closing dates
and salary do not exist on the record and are never invented. Recommendations never
persist rank, band, or urgency.

**Implementation:** `src/career_intelligence/recommendations/`
(`OpportunityRecommendationService`).

---

### Ranked Comparison

A prioritised ordering of open assessed opportunities. Phase 2 M4 delivered job-scoped
ranking (historically “FR-012 partial”). Horizon 1A **FR-009** extended it into the
acquisition workflow (duplicates, owner-review queue, recommendations) as a **derived
projection** over persisted Opportunities, and calibrated the sort key for quality:
`pursuit_posture → fit_strength → practical_value → opportunity_id`, with
`application_tier` retained as effort context only.

**Implementation (M4):** `OpportunityComparisonService.compare_open` ranks open
Opportunity aggregates with a deterministic sort key:

1. Pursuit posture (FR-005 primary attention signal)
2. Fit strength (sum of technical + commercial + portfolio judgments)
3. Application tier (effort band)
4. `opportunity_id` (stable ascending tie-break)

Open filter: status ∈ {assessed, deferred, preparing, submitted, interviewing, offer}
and decision ≠ skip. Each ranked item includes explainable `reasons`. Owner review
required — ranking does not apply, skip, or mutate opportunities.

Cross-domain daily prioritisation is Horizon 2 **FR-027**.

---

### Application Workflow State (planned)

**Maps to:** FR-008

Shared typed state coordinating acquisition through tracking. Nodes wrap existing
services; conditional edges follow strategy and owner decisions; checkpoints support
owner-review interrupts and resumability. Production orchestration for the current
FR-008 spike is the thin in-repository runner (**ADR-003 accepted**). LangGraph remains
out unless ADR-003 reconsideration conditions are met.

### Application Package

**Maps to:** FR-010 (uses FR-006, FR-007) — complete and frozen
([acceptance](eval/fr010_application_package.md))

Grouped artefacts (tailoring plan, CV, cover letter, HTML) under one application
identity equal to the Opportunity id. The durable record is an
``ApplicationPackageManifest`` of deterministic references to generated drafts and
immutable Opportunity evidence (job analysis, assessment, portfolio match,
strategy, acquisition provenance). Regeneration replaces the previous package;
draft paths persist as relative filenames and resolve through the service.
Failed regeneration leaves the prior package current until a full prepare
succeeds. Only owner decision ``apply`` is eligible. Owner review remains
mandatory before external use. Owner operations use the thin ``cic package``
CLI adapter over ``ApplicationPackageService``. Coordinated preparation of this
package is **FR-011** (standalone orchestrator — does not amend FR-010 rules).

### Preparation Orchestration

**Maps to:** FR-011 — complete and frozen
([acceptance](eval/fr011_application_preparation.md))

Dedicated coordinator (`ApplicationPreparationOrchestrator`) that verifies
Opportunity preconditions (FR-002–FR-005 artefacts + owner decision ``apply``) then
invokes ``ApplicationPackageService.prepare``. Owner operations use thin
``cic preparation``. Does **not** extend the FR-008 runner, does not re-run
analysis/assessment/strategy, and does not own package business rules. Preparation
runs under ``data/preparation_runs/`` are recovery/audit only — not Opportunity SoT.

### Submission Attempt (FR-012 — complete and frozen)

**Maps to:** FR-012 — [acceptance](eval/fr012_submission_assistance.md);
milestones [M0](eval/fr012_m0_submission_contracts.md),
[M1](eval/fr012_m1_submission_orchestration.md),
[M2](eval/fr012_m2_owner_workflow.md)

One append-only attempt to submit (or record that the owner submitted) an already
prepared Application Package. Opportunity remains the business system of record;
attempts under ``data/submission_attempts/`` are audit only.

| Field group | Role |
|-------------|------|
| Identity | ``sub_<ULID>``; references ``opportunity_id`` + package ``prepared_at`` |
| Channel / mode | ``manual_assisted`` / ``fake``; ``assist_only`` / ``adapter_action`` |
| Status | ``ready`` → ``in_progress`` → terminal or ``manual_action_required`` |
| Evidence | Owner Approval flag, adapter result_code / message, failure_reason when needed |

**Delivered:** ``SubmissionOrchestrator`` enforces gates and policy;
``SubmissionAdapter`` implements channels offline-first; ``cic submission`` is a
thin owner interface (`check` / `run` / `record-manual` / `show` / `list`).
Submission Readiness never creates attempts. Assisted Submission and Manual
Completion are distinct operations. Live browser / board automation is deferred.
No ``PipelineStatus`` writes (FR-013).

### Pipeline Event (FR-013 M1)

**Maps to:** FR-013 — [spike](eval/fr013_m0_engineering_spike.md) (Accepted);
[M1 contracts](eval/fr013_m1_pipeline_contracts.md); [ADR-005](adr/005_application_pipeline_lifecycle.md)

One immutable audit event for application lifecycle progress on an Opportunity.
Opportunity remains the business system of record for **current**
`PipelineStatus` / `OutcomeRecord`. Events under ``data/pipeline_events/`` are
append-only audit only.

| Field group | Role |
|-------------|------|
| Identity | ``ple_<ULID>``; references ``opportunity_id`` |
| Kind | status_transition / interview_stage_change / outcome_change / evidence_added / follow_up_set / correction / note |
| Status delta | optional ``from_status`` / ``to_status`` (coarse ``PipelineStatus``) |
| Evidence | optional package ref, ``submission_attempt_id``, channel, submitted_at, notes |
| Actor | ``owner`` (default) or future ``agent:<id>`` |

**Invariant:** FR-012 ``SubmissionAttempt`` success never automatically appends a
pipeline event or advances ``Opportunity.status``. Citing an attempt id is
evidence for an **explicit owner** pipeline action (M2+).

**M1 delivered:** typed contracts, transition/correction policy, evidence rules,
append-only store.  
**M2 delivered:** ``PipelineTrackingService`` — event-first dual-write onto
Opportunity via ``apply_pipeline_projection``; divergence detection; reconcile;
terminal corrections.  
**M3 delivered:** thin ``cic pipeline`` owner workflow.  
**M4 delivered:** derived ``summary_report`` / ``due`` / ``export``; acceptance freeze.
SubmissionAttempt ids remain optional evidence citations. No projection watermark.
No FR-014 work in this FR.

### Truth Validation (FR-014 — complete)

**Maps to:** FR-014 — [acceptance](eval/fr014_recruiter_document_truth_validation.md)
(frozen); [ADR-006](adr/006_recruiter_document_truth_validation.md);
milestones [M0](eval/fr014_m0_engineering_spike.md)–[M4](eval/fr014_m4_claim_validation.md)

Deterministic fail-closed trust boundary for recruiter-facing documents.
Validates; does not generate or rewrite.

| Concept | Role |
|---------|------|
| Candidate Evidence Catalogue | Normalised candidate facts; Class A support requires ``candidate_authoritative`` provenance |
| Claim (classes A–D) | Structured factual assertion with strength |
| TruthFinding | **Detection certainty** and **evidence status** are distinct dimensions |
| TruthReport | Coverage + performed flags + findings + overall outcome |

**Invariants (ADR-006):** JD / assessment / strategy / plans are context-only and
never authorize candidate capability. ``outcome=pass`` requires complete coverage
and performed detection + validation — empty findings alone are not proof of truth.
Ambiguous Class A detection is review-required or blocking by severity.

**M1 delivered:** typed contracts only.  
**M2 delivered:** catalogue population from Career Profile; deterministic technology
detection/validation via ``TruthValidationService``; Redwolf leakage blocked.  
**M3 delivered:** ``cic truth`` CLI; sidecar TruthReports + content hashing;
package/submission fail-closed external-use gates
([eval/fr014_m3_owner_workflow.md](eval/fr014_m3_owner_workflow.md)).  
**M4 delivered:** employment honesty, certifications, duration, project delivery,
domain ([eval/fr014_m4_claim_validation.md](eval/fr014_m4_claim_validation.md)).  
**Frozen:** [acceptance](eval/fr014_recruiter_document_truth_validation.md).
Education / identity / soft claims remain excluded.

### Bounded Agentic Workflow (FR-015 — complete / frozen)

**Maps to:** FR-015 — [acceptance](eval/fr015_bounded_agentic_workflow.md);
[M0](eval/fr015_m0_engineering_spike.md)–[M4](eval/fr015_m4_evaluation.md);
[ADR-007](adr/007_bounded_agentic_workflow.md)

Bounded Opportunity Preparation Agent (BOPA): one agent, one Opportunity,
post-acquisition. ActionProposer suggests allow-listed actions; deterministic
ToolPolicy validates; existing CIC services execute. Does not wrap FR-008.
Deterministic proposer is the operational default.

| Concept | Role |
|---------|------|
| AgentGoal | Bounded owner goal (`prepare_for_owner_review`) |
| ReadinessSnapshot | Derived observation of artefacts / package / truth |
| ReadinessStateClass | Priority classification of where BOPA adds value beyond FR-008 |
| AgentAction / AgentActionProposal | Closed allow-list + structured proposal |
| ToolPolicy | Deterministic allow/deny (`evaluate_action_policy`) |
| AgentRun / AgentAuditEvent | Additive audit/recovery — not Opportunity SoT |
| AgentStopReason | Fail-closed terminal reasons |
| AgentRunMetrics | M4 observability derived from audit |

**M1 delivered:** typed contracts + state-class matrix + ToolPolicy + unit tests.  
**M2 delivered:** AgentRuntime, proposers, thin adapters, audit store, checkpoint/resume.  
**M3 delivered:** thin `cic agent` CLI + owner presentation.  
**M4 delivered:** corpus evaluation, observability, owner validation, freeze.  
**Frozen:** [acceptance](eval/fr015_bounded_agentic_workflow.md).

### Multi-Agent Orchestration (FR-016)

**ADR:** [ADR-008](adr/008_multi_agent_orchestration.md)  
**Spike:** [eval/fr016_m0_engineering_spike.md](eval/fr016_m0_engineering_spike.md)
(Accepted with revisions)  
**M1:** [eval/fr016_m1_orchestration_contracts.md](eval/fr016_m1_orchestration_contracts.md)

Constrained multi-agent substrate (learning + future permission separation). Not
strong near-term commercial automation. Prep/Truth/Review persona split rejected.

| Concept | Role |
|---------|------|
| OrchestrationGoal / OrchestrationRun | Parent DOS run (audit/recovery; not Opportunity SoT) |
| OrchestrationObservation | Derived cross-surface observation for routing |
| DelegationPolicy | Sole admission for specialist invocation |
| Handoff | Typed, append-only, idempotent specialist handoff |
| OBS / OperationalBrief | Read-only briefing specialist + derived brief |
| BOPA (child) | Frozen FR-015 specialist; mutating allow-list unchanged |
| Specialist registry | Static OBS + BOPA boundaries |

**M1 delivered:** contracts + DelegationPolicy + OBS ToolPolicy + unit tests.  
**M2 delivered:** DOS runtime, OBS, BOPA adapter, corpus A–O, go/no-go
**GO AS LEARNING PROOF ONLY**
([eval/fr016_m2_supervisor_runtime.md](eval/fr016_m2_supervisor_runtime.md)).  
**M3 delivered:** `cic agent orchestrate` owner CLI
([eval/fr016_m3_owner_cli.md](eval/fr016_m3_owner_cli.md)).  
**M4 delivered:** final corpus 20/20, safety/product review, study-aid source, freeze
([eval/fr016_m4_evaluation.md](eval/fr016_m4_evaluation.md)).  
**Frozen:** [acceptance](eval/fr016_multi_agent_orchestration.md).

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
| Opportunity | Application Package | Apply decision enables FR-010 package preparation (M0) |
| Opportunity | Preparation Orchestration | FR-011 coordinates package prep for apply Opportunities |
| Opportunity | Submission Attempt | FR-012 records append-only submit attempts (audit; not pipeline SoT) |
| Opportunity | Pipeline Event | FR-013 append-only lifecycle audit (not a second SoT; current status stays on Opportunity) |
| Opportunity | AgentRun | FR-015 BOPA observes one Opportunity; audit only (ADR-007) |
| Opportunity | OrchestrationRun | FR-016 DOS parent run cites Opportunity; audit only (ADR-008) |
| OrchestrationRun | Handoff | Append-only typed specialist handoffs |
| OrchestrationRun | AgentRun | BOPA child runs under DOS |
| OrchestrationRun | OperationalBrief | OBS briefing output (derived) |
| Application Package | Submission Attempt | Attempt references package prepared_at / optional hash |
| Application Package | Pipeline Event | Event may cite package prepared_at / hash as submit evidence |
| Application Package | AgentRun | BOPA may request prepare/verify via thin adapters (M2) |
| Submission Attempt | Pipeline Event | Event may cite attempt id; never auto-creates events (ADR-005) |
| Career Profile | Truth Validation | Authoritative candidate evidence for Class A claims (ADR-006) |
| Job Analysis | Truth Validation | Context-only; leakage detection; never authorizes capability |
| CV / Cover Letter Markdown | Truth Validation | Primary validation surface (artefact under test) |
| Truth Validation | AgentRun | BOPA may request validate / stop on block; never waives (ADR-007) |
| TruthReport | Submission / Package gates | Consumed by M3 external-use readiness; does not own submit or package rules |
| Application Strategy | User Decision | User accepts, overrides, or defers the recommendation |
| User Decision | Outcome Record | Decision and subsequent events logged (M2 / FR-013) |
| Outcome Record | Opportunity | Outcomes attach to durable opportunities |
| Opportunity | OpportunityComparison | Open opportunities compared for prioritisation (M4 / FR-009) |

Portfolio Match and Opportunity Assessment are siblings. Both feed Application Strategy.
There is no Portfolio Match → Opportunity Assessment dependency.

---

## User Actions vs System Outputs

| User provides | System produces |
|---------------|-----------------|
| Job description / URL / alert / export | Job Acquisition Record + Job Posting |
| Profile updates | Updated Career Profile |
| Pursuit / package / submission approvals | Outcome Records; workflow resume |
| — | Opportunity Assessment with evidence |
| — | Portfolio Match ranking |
| — | Application Strategy (posture + effort tier + next actions) |
| — | Ranked Comparison / review queue |
| — | Application package (CV + cover letter) under review |
| — | Submission assistance (never silent) |

The system advises. The user commits. Important decisions — especially submission — remain reviewable.

---

## Operational Layer Mapping

The operational layer is the manual precursor to the automated domain model.

| Domain entity | Operational counterpart |
|---------------|------------------------|
| Career Profile | `career-documents/cv/`, owner knowledge |
| Opportunity (durable) | `data/opportunities/` (SoT); CSV under `data/exports/` is derived (M3) |
| Outcome Record | Status / notes on Opportunity (M2); tracker Outcome column is import/export projection |
| Network contacts | `applications/network/network_tracker.csv` (Horizon 1B / FR-018+) |
| Company context | `applications/company_notes/` |
| Career milestones | `career-log.md` |
| Future templates | `templates/` (placeholders) |
| Future analytics | `metrics/` (placeholders) |

Phase 2 engineering must respect this mapping. Horizon 1A tracking (FR-013) should
continue to connect to this layer rather than invent a parallel tracker.

---

## Functional Requirement Index

| Entity / capability | FR ID |
|---------------------|-------|
| Career Profile | FR-001 (complete) |
| Job Analysis | FR-002 (complete) |
| Opportunity Assessment | FR-003 (complete) |
| Portfolio Match | FR-004 (complete) |
| Application Strategy | FR-005 (complete) |
| Tailored CV / Tailoring Plan | FR-006 (complete) |
| Cover Letter | FR-007 (complete) |
| Opportunity (durable persistence) | Phase 2 M1 (complete) |
| Outcome Record | Phase 2 M2 (complete; hist. FR-013 subset); extended by **FR-013** |
| CSV operational bridge | Phase 2 M3 (complete) |
| Ranked Comparison | Phase 2 M4 (complete; hist. FR-012 partial); extended by **FR-009** |
| Opportunity identity (title/company) | Phase 2 M4a (complete) |
| Job Acquisition & Workflow Orchestration | **FR-008** (Horizon 1A; complete) |
| Opportunity Review Queue & Ranking | **FR-009** (Horizon 1A; complete — [acceptance](eval/fr009_opportunity_review_queue.md)) |
| Owner Review Metadata | **FR-009** M0–M2 ([ADR-004](adr/004_opportunity_review_boundary.md)) |
| Review Queue (derived projection) | **FR-009** M1 (complete; pin ordering in M2) |
| Duplicate Relation | **FR-009** M0 contract; M3 detection and confirmation complete |
| Duplicate Group (derived) | **FR-009** M3 (complete) |
| Opportunity Recommendations (derived) | **FR-009** M4 (complete) |
| Application Package Preparation | **FR-010** (Horizon 1A; complete — [acceptance](eval/fr010_application_package.md)) |
| Application Preparation Orchestration | **FR-011** (Horizon 1A; complete — [acceptance](eval/fr011_application_preparation.md)) |
| Submission Assistance | **FR-012** (Horizon 1A; complete — [acceptance](eval/fr012_submission_assistance.md)) |
| Application Pipeline Tracking | **FR-013** (Horizon 1A; complete — [acceptance](eval/fr013_application_pipeline_tracking.md); [ADR-005](adr/005_application_pipeline_lifecycle.md)) |
| Recruiter Document Truth Validation | **FR-014** (Horizon 1A; **complete and frozen** — [acceptance](eval/fr014_recruiter_document_truth_validation.md); [ADR-006](adr/006_recruiter_document_truth_validation.md)) |
| Bounded Agentic Workflow | **FR-015** (Horizon 1A; **complete / frozen** — ADR-007) |
| Multi-Agent Orchestration | **FR-016** (Horizon 1A — **complete / frozen**; learning proof) |
| Agent Evaluation & Observability | **FR-017** (Horizon 1A) |
| Recruiter Intelligence | **FR-018** (Horizon 1B) |
| Recruiter Outreach | **FR-019** (Horizon 1B) |
| Existing Connection Outreach | **FR-020** (Horizon 1B) |
| LinkedIn Network Intelligence | **FR-021** (Horizon 1B) |
| Meetup Intelligence | **FR-022** (Horizon 1B) |
| LinkedIn Content Planning | **FR-023** (Horizon 1B) |
| Market Intelligence | **FR-024** (Horizon 1B) |
| Interview Preparation | **FR-025** (Horizon 2) |
| Career Dashboard | **FR-026** (Horizon 2) |
| Daily Prioritisation (cross-domain) | **FR-027** (Horizon 2) |
