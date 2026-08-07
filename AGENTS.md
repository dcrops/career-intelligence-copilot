# Agent Instructions

## Purpose

Bootstrap instructions for Cursor agents working in this repository.

The repository — not conversation history — is the project's long-term memory. Read these instructions and the linked documents before proposing or implementing work.

---

## Start Here

1. [docs/00_repository_guide.md](docs/00_repository_guide.md) — documentation map and folder semantics
2. [docs/04_functional_specification.md](docs/04_functional_specification.md) — requirements
3. [docs/06_domain_model.md](docs/06_domain_model.md) — decision loop and entities
4. [docs/05_engineering_principles.md](docs/05_engineering_principles.md) — engineering tradeoffs
5. [docs/07_testing_strategy.md](docs/07_testing_strategy.md) — testing and regression conventions
6. [docs/10_roadmap.md](docs/10_roadmap.md) — completed vs current focus vs future
7. [docs/masterclass/README.md](docs/masterclass/README.md) — Engineering Learning Academy source (after freeze)

---

## Project Context

Career Intelligence Copilot is a decision-support system for job search — not an
unsupervised application-automation bot. Assisted submission (when built) still
requires explicit owner approval.

**Current phase:** Phase 2 Job Intelligence MVP is **complete** and documentation is
a **frozen baseline** (M5 GO —
[docs/eval/phase2_release_report.md](docs/eval/phase2_release_report.md);
[docs/12_phase_history.md](docs/12_phase_history.md)). FR-001–FR-007 (including
FR-006b/c) are closed. **FR-008** is **complete and frozen** —
[docs/eval/fr008_workflow_orchestration.md](docs/eval/fr008_workflow_orchestration.md);
[ADR-003](docs/adr/003_application_workflow_orchestration.md). **FR-009** (review queue /
duplicates / ranking) is **complete and frozen** —
[docs/eval/fr009_opportunity_review_queue.md](docs/eval/fr009_opportunity_review_queue.md);
[ADR-004](docs/adr/004_opportunity_review_boundary.md); milestones
[M0](docs/eval/fr009_m0_domain_contracts.md),
[M1](docs/eval/fr009_m1_persistence_boundary.md),
[M2](docs/eval/fr009_m2_owner_review_actions.md),
[M3](docs/eval/fr009_m3_duplicate_detection.md),
[M4](docs/eval/fr009_m4_recommendations.md). **FR-010** Application Package Preparation
is **complete and frozen** —
[docs/eval/fr010_application_package.md](docs/eval/fr010_application_package.md);
milestones [M0](docs/eval/fr010_m0_application_package.md),
[M1](docs/eval/fr010_m1_package_durability.md),
[M2](docs/eval/fr010_m2_owner_cli.md). **FR-011** Application Preparation Orchestration
is **complete and frozen** —
[docs/eval/fr011_application_preparation.md](docs/eval/fr011_application_preparation.md);
milestones [M0](docs/eval/fr011_m0_application_preparation.md),
[M1](docs/eval/fr011_m1_executable_preparation.md). **FR-012** Submission Assistance
is **complete and frozen** —
[docs/eval/fr012_submission_assistance.md](docs/eval/fr012_submission_assistance.md);
milestones [M0](docs/eval/fr012_m0_submission_contracts.md),
[M1](docs/eval/fr012_m1_submission_orchestration.md),
[M2](docs/eval/fr012_m2_owner_workflow.md). **FR-013** Application Pipeline Tracking
is **complete and frozen** —
[docs/eval/fr013_application_pipeline_tracking.md](docs/eval/fr013_application_pipeline_tracking.md);
[ADR-005](docs/adr/005_application_pipeline_lifecycle.md). **FR-014** Recruiter Document
Truth Validation is **complete and frozen** —
[acceptance](docs/eval/fr014_recruiter_document_truth_validation.md);
milestones [M0](docs/eval/fr014_m0_engineering_spike.md)–[M4](docs/eval/fr014_m4_claim_validation.md);
[ADR-006](docs/adr/006_recruiter_document_truth_validation.md). **Current focus — FR-019
Recruiter Intelligence** (on owner request). **FR-018** Opportunity Discovery &
Acquisition is **complete and frozen** —
[acceptance](docs/eval/fr018_opportunity_discovery_acquisition.md);
[ADR-010](docs/adr/010_opportunity_discovery_ingress.md);
[package](docs/masterclass/FR018/). Horizon 1B FR-019–FR-025.
**Horizon 1A (FR-008–FR-017) is complete and frozen.**
**FR-017** Agent Evaluation & Observability is **complete and frozen** (derive-only;
**must not block Horizon 1B**) —
[acceptance](docs/eval/fr017_agent_evaluation_observability.md);
[ADR-009](docs/adr/009_orchestration_evaluation_substrate.md);
[package](docs/masterclass/FR017/). **FR-016** Multi-Agent Orchestration is **complete and frozen** (learning proof —
**GO AS LEARNING PROOF ONLY**; prefer `cic agent run` for ordinary prep;
Engineering Learning Academy ready —
[acceptance](docs/eval/fr016_multi_agent_orchestration.md);
[ADR-008](docs/adr/008_multi_agent_orchestration.md)). **FR-015**
Bounded Agentic Workflow is **complete and frozen** —
[acceptance](docs/eval/fr015_bounded_agentic_workflow.md);
milestones [M0](docs/eval/fr015_m0_engineering_spike.md)–[M4](docs/eval/fr015_m4_evaluation.md);
[ADR-007](docs/adr/007_bounded_agentic_workflow.md).
Do not reopen Phase 2, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, or FR-018 exit criteria without
explicit owner request.
**Principle:** Job acquisition first. Recruiter outreach second (Horizon 1B —
**FR-018 complete**; recruiter work **FR-019+**; 1A application loop is usable). Remap:
[docs/11_changelog.md](docs/11_changelog.md) § 1.115; FR-018 freeze § 1.125.

**Implementation foundation:** Python 3.11+, Pydantic, YAML storage, and the public profile
service boundary are recorded in
[ADR-001](docs/adr/001_python_yaml_profile_foundation.md).

**Immediate priority (Horizon 1):** Help the repository owner secure a suitable AI Engineering role sooner while reducing job-search effort. Horizon 1 wins when objectives conflict. See [docs/03_product_vision.md](docs/03_product_vision.md).

**Single-user phase:** The repository owner is the user, builder, and product owner.

---

## Phase 2 Scope Boundaries

**In scope (delivered):** Career profile, job analysis, opportunity assessment (Technical, Commercial, Portfolio Fit), portfolio matching, application strategy (pursuit posture + effort tiers), pipeline tracking, outcome logging, ranked comparison of open opportunities, grounded opportunity identity.

**Out of scope for Phase 2 exit (unchanged historically):** Recruiter outreach, interview preparation, full dashboard, market intelligence, cross-domain daily prioritisation, automated job discovery, predictive scoring (Interview Probability, Recruiter Confidence).

**Delivered outside original Phase 2 exit criteria (owner-sequenced):** FR-006 CV Generation (complete, including FR-006b/c); **FR-007 Cover Letter** (complete — plan + deterministic narrative render; manual validation passed).

**Horizon 1A (complete / frozen):** FR-008 **complete** (acquisition adapters + orchestration;
ADR-003; persistence boundary since amended by FR-009 M1). **FR-009 complete and frozen**
(pre-review persistence, derived review queue, owner review actions, owner-confirmed
duplicates, calibrated quality-first ranking and derived recommendations; ADR-004
implemented with Decision 8 amended by the M4 calibration). **FR-010 complete and
frozen** (standalone package composition, durability/regeneration, owner CLI;
[acceptance](docs/eval/fr010_application_package.md)). **FR-011 complete and frozen**
(dedicated preparation orchestrator + owner CLI;
[acceptance](docs/eval/fr011_application_preparation.md)). **FR-012 complete and
frozen** (owner-assisted submission; append-only attempts; thin `cic submission`;
[acceptance](docs/eval/fr012_submission_assistance.md)). **FR-013 Application
Pipeline Tracking is complete and frozen**
([acceptance](docs/eval/fr013_application_pipeline_tracking.md)). **FR-014**
Recruiter Document Truth Validation is **complete and frozen**
([acceptance](docs/eval/fr014_recruiter_document_truth_validation.md)). **FR-015**
Bounded Agentic Workflow is **complete and frozen**
([acceptance](docs/eval/fr015_bounded_agentic_workflow.md);
[ADR-007](docs/adr/007_bounded_agentic_workflow.md)). **FR-016** is **complete and frozen**
(learning proof only). **FR-017** is **complete and frozen**
([docs/eval/fr017_agent_evaluation_observability.md](docs/eval/fr017_agent_evaluation_observability.md);
[ADR-009](docs/adr/009_orchestration_evaluation_substrate.md)).
Next: Horizon 1B on owner request — **FR-019 Recruiter Intelligence**.
**FR-018** is **complete and frozen**
([docs/eval/fr018_opportunity_discovery_acquisition.md](docs/eval/fr018_opportunity_discovery_acquisition.md)).
See [docs/10_roadmap.md](docs/10_roadmap.md).

Full detail: [docs/04_functional_specification.md](docs/04_functional_specification.md) and [docs/10_roadmap.md](docs/10_roadmap.md).

Do not expand scope into Horizon 1B (FR-019+), Phase 3+, or Horizon 2 capabilities unless
explicitly requested by the owner.

---

## Engineering Invariants

Apply [docs/05_engineering_principles.md](docs/05_engineering_principles.md) for all tradeoffs. Non-negotiables:

- **Job acquisition first** — Horizon 1A application loop before Horizon 1B recruiter work (1A is complete; start 1B only on owner request). Within 1B, **FR-018 is complete**; Recruiter Intelligence is **FR-019+**
- **Intelligence before automation** — explain before acting; deterministic workflow before agents
- **Human review** — tiers, packages, and submission require owner judgment; never silent submit
- **Dual-value test** — every capability must improve interview/offer odds or reduce repetitive search effort
- **Explainability** — assessments must cite evidence from job description and profile
- **Outcome logging** — decisions and results must be recordable (Phase 2 M2 / FR-013)
- **Operational continuity** — the built system must connect to existing tracking in `applications/`, not run parallel to it
- **Public profile boundary** — downstream capabilities obtain the career profile through
 `career_intelligence.profile`, never through its YAML storage adapter
- **One system of record for opportunities** — `data/opportunities/` is the durable
 business record; the FR-009 review queue and duplicate groups are derived projections,
 and workflow checkpoints stay recovery data
 ([ADR-004](docs/adr/004_opportunity_review_boundary.md))
- **Duplicates are linked, never merged** — detection recommends, the owner confirms, and
 no discovered advertisement is deleted or collapsed
- **Ranking is deterministic and quality-first** — `pursuit_posture → fit_strength →
 practical_value → opportunity_id`; `application_tier` is effort context only; missing
 evidence cannot improve ranking and unavailable data is never invented. No composite
 score, no LLM ranking. Change the key only with explicit owner approval
- **Acquisition via adapters** — prefer APIs/feeds/alerts/URLs/paste/exports; Playwright is a controlled fallback, not crawlers
- **Recruiter-document truth is fail-closed (FR-014 — frozen)** — Markdown is authoritative;
 Career Profile authorizes Class A; JD/assessment/strategy/plans are context only;
 detection certainty ≠ evidence status; fresh content-hash TruthReports gate package
 external use and submission; never rewrite; owner review remains mandatory
 ([ADR-006](docs/adr/006_recruiter_document_truth_validation.md))
- **Bounded agent coordinates; services remain authoritative (FR-015 — frozen)** — BOPA proposes
 allow-listed actions; ToolPolicy validates; existing services execute; no FR-008 wrap,
 submit, pipeline mutation, discovery, or truth waive; deterministic proposer is the
 operational default
 ([ADR-007](docs/adr/007_bounded_agentic_workflow.md))
- **Orchestration evaluation is derive-only (FR-017 — frozen)** — metrics and R1–R12
 reconstructability are pure views over existing FR-016 audits (+ reused FR-015 child
 metrics); read-only CLI; no dashboards; must not block Horizon 1B
 ([ADR-009](docs/adr/009_orchestration_evaluation_substrate.md))
- **Constrained multi-agent substrate (FR-016 — frozen)** — DOS delegates only; BOPA mutating
  allow-list unchanged; OBS is strictly read-only; typed handoffs; DelegationPolicy +
  per-specialist ToolPolicy; Prep/Truth/Review persona split rejected as theatre;
  learning/substrate purpose only — not preferred daily replacement for `cic agent run`
  ([ADR-008](docs/adr/008_multi_agent_orchestration.md);
  [acceptance](docs/eval/fr016_multi_agent_orchestration.md))
- **Opportunity discovery ingress is thin (FR-018 — frozen)** —
  URL + email job-alert adapters + `ThinDiscoveryIngress` only; SEEK URL production;
  LinkedIn/Indeed URL attempt/fail-closed; email digests via `cic opportunity discover-email`
  with optional **URL enrich** when alerts are card-only; Horizon 1A runner/SoT unchanged
  ([ADR-010](docs/adr/010_opportunity_discovery_ingress.md);
  [acceptance](docs/eval/fr018_opportunity_discovery_acquisition.md))

---

## Do Not

- Propose architecture or choose technologies unless explicitly asked
- Add Phase 3+ / Horizon 2 features unless explicitly requested
- Copy recruiter PII from `applications/network/` into rules, skills, or documentation
- Treat executive summary or problem statement as requirements sources
- Duplicate content that already exists in authoritative docs — cross-reference instead
- Guarantee employment, interviews, or recruiter engagement in any output
- Generate Engineering Learning Academy presentations/decks unless explicitly asked;
  build Masterclass Source Packages under `docs/masterclass/FRnnn/` only after freeze
  (acceptance remains canonical; regenerate `sources/` — do not hand-edit snapshots).
  When a Masterclass is requested, follow
  [docs/masterclass/LEAN_MASTERCLASS_STANDARD.md](docs/masterclass/LEAN_MASTERCLASS_STANDARD.md).
  Interview Brief / Deck follow
  [docs/masterclass/INTERVIEW_BRIEF_STANDARD.md](docs/masterclass/INTERVIEW_BRIEF_STANDARD.md) and
  [docs/masterclass/INTERVIEW_DECK_STANDARD.md](docs/masterclass/INTERVIEW_DECK_STANDARD.md)
  — do not regenerate FR-016/FR-017 interview artefacts unless asked.

---

## Operational Data

`applications/`, `career-documents/`, `career-log.md`, `templates/`, and `metrics/` contain live or placeholder operational data.

- Respect existing tracker formats and terminology during transition
- Legacy "Tier 1" in operational data maps to **Platinum** in product docs; legacy product
  tier name Skip is now **Bronze** (effort only) — see functional specification
- Empty template and metrics files are intentional placeholders

---

## Recording Decisions

When a session produces a durable decision or invariant, update the appropriate repository document:

| Decision type | Update |
|---------------|--------|
| Product strategy | [docs/11_changelog.md](docs/11_changelog.md) |
| Requirements or tier semantics | [docs/04_functional_specification.md](docs/04_functional_specification.md) |
| Engineering tradeoffs | [docs/05_engineering_principles.md](docs/05_engineering_principles.md) |
| Phase or scope | [docs/10_roadmap.md](docs/10_roadmap.md) |
| Frozen FR → Academy Masterclass package | [docs/masterclass/](docs/masterclass/README.md) + `scripts/build_masterclass_package.py` |

Do not leave important knowledge only in chat history.

**Engineering Learning Academy pipeline:** Engineering → Validation → Acceptance →
Freeze → Masterclass Source Package (`docs/masterclass/FRnnn/`) →
Lean Masterclass (Markdown) → **Masterclass PDF** → Gamma Learning Presentation
(~15–20) → **Interview Brief** (~1 page) → **Interview Deck** (~3–5) →
Interview Revision / Coaching.
Regenerate `sources/` snapshots after SoT doc changes; do not hand-edit snapshots.
Do not generate Masterclass presentations in-repo during FR close-out.
When generating a Masterclass, follow
[docs/masterclass/LEAN_MASTERCLASS_STANDARD.md](docs/masterclass/LEAN_MASTERCLASS_STANDARD.md)
and [docs/masterclass/MASTERCLASS_GENERATOR_LEAN.md](docs/masterclass/MASTERCLASS_GENERATOR_LEAN.md),
then render the PDF with `python scripts/render_masterclass_pdf.py <masterclass.md>`.
Interview Brief / Deck standards:
[docs/masterclass/INTERVIEW_BRIEF_STANDARD.md](docs/masterclass/INTERVIEW_BRIEF_STANDARD.md),
[docs/masterclass/INTERVIEW_DECK_STANDARD.md](docs/masterclass/INTERVIEW_DECK_STANDARD.md).
Do not regenerate FR-016/FR-017 interview artefacts unless explicitly requested.
