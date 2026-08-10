# Repository Guide

## Purpose

This document is the canonical entry point for understanding the Career Intelligence
Copilot repository.

It explains what the repository contains, which documents are authoritative, how
folders relate to the product, and where to read next. Every new engineer or AI agent
session should start here.

---

## What This Repository Is

Career Intelligence Copilot has three coexisting layers:

**Specification layer** — product intent, requirements, delivery phasing, and
engineering decision guidance in `docs/` and `AGENTS.md`.

**Operational layer** — the repository owner's live job search: application tracking,
network contacts, career artefacts, and placeholders for future workflows.

**Implementation layer** — the Python package, structured data, and tests in `src/`,
`data/`, and `tests/`. Phase 2 Job Intelligence is the frozen baseline.

The repository is simultaneously a career tool, a portfolio project, and a Cursor
learning laboratory. See [03_product_vision.md](03_product_vision.md) § Project
Objectives.

---

## Answers for new contributors

| Question | Answer |
|----------|--------|
| What is this project? | Decision-support for job search (Horizon 1), evolving toward a Career Intelligence Platform (Horizon 2). |
| What has been completed? | **Phase 1** and **Phase 2** — see [12_phase_history.md](12_phase_history.md) and [eval/phase2_release_report.md](eval/phase2_release_report.md). |
| What is next? | **FR-019 Recruiter Intelligence** on owner request. **FR-018 Complete / Frozen** ([eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md)). **Horizon 1A complete.** Changelog § 1.125 — [10_roadmap.md](10_roadmap.md). |
| Where should I start reading? | This guide → [AGENTS.md](../AGENTS.md) → [04_functional_specification.md](04_functional_specification.md) → [10_roadmap.md](10_roadmap.md). |

---

## Current Status

**Phase 2 Job Intelligence — Complete** (documentation frozen as baseline).

**Closed in Horizon 1A:** **FR-008** Job Acquisition & Workflow Orchestration
([eval/fr008_workflow_orchestration.md](eval/fr008_workflow_orchestration.md)),
**FR-009** Opportunity Review Queue & Ranking
([eval/fr009_opportunity_review_queue.md](eval/fr009_opportunity_review_queue.md);
milestones [M0](eval/fr009_m0_domain_contracts.md),
[M1](eval/fr009_m1_persistence_boundary.md),
[M2](eval/fr009_m2_owner_review_actions.md),
[M3](eval/fr009_m3_duplicate_detection.md),
[M4](eval/fr009_m4_recommendations.md)), and **FR-010** Application Package Preparation
([eval/fr010_application_package.md](eval/fr010_application_package.md);
milestones [M0](eval/fr010_m0_application_package.md),
[M1](eval/fr010_m1_package_durability.md),
[M2](eval/fr010_m2_owner_cli.md)), and **FR-011** Application Preparation Orchestration
([eval/fr011_application_preparation.md](eval/fr011_application_preparation.md);
milestones [M0](eval/fr011_m0_application_preparation.md),
[M1](eval/fr011_m1_executable_preparation.md)), and **FR-012** Submission Assistance
([eval/fr012_submission_assistance.md](eval/fr012_submission_assistance.md);
milestones [M0](eval/fr012_m0_submission_contracts.md),
[M1](eval/fr012_m1_submission_orchestration.md),
[M2](eval/fr012_m2_owner_workflow.md)), and **FR-013** Application Pipeline Tracking
([eval/fr013_application_pipeline_tracking.md](eval/fr013_application_pipeline_tracking.md);
[ADR-005](adr/005_application_pipeline_lifecycle.md)).

**Active focus:** **FR-019 Recruiter Intelligence** on owner request.
**FR-018 Complete / Frozen**
([eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md);
[masterclass/FR018/](masterclass/FR018/)). **Horizon 1A complete.**
**FR-016** is **complete and frozen**
(learning proof — **GO AS LEARNING PROOF ONLY**; prefer `cic agent run`;
[acceptance](eval/fr016_multi_agent_orchestration.md);
[M0](eval/fr016_m0_engineering_spike.md)–[M4](eval/fr016_m4_evaluation.md);
[ADR-008](adr/008_multi_agent_orchestration.md)). **FR-015** Bounded Agentic Workflow is **complete and frozen**
([acceptance](eval/fr015_bounded_agentic_workflow.md);
[M0](eval/fr015_m0_engineering_spike.md)–[M4](eval/fr015_m4_evaluation.md);
[ADR-007](adr/007_bounded_agentic_workflow.md)). **FR-014** Recruiter Document Truth
Validation is **complete and frozen**
([acceptance](eval/fr014_recruiter_document_truth_validation.md);
[M0](eval/fr014_m0_engineering_spike.md)–[M4](eval/fr014_m4_claim_validation.md);
[ADR-006](adr/006_recruiter_document_truth_validation.md)).
**FR-013** Application Pipeline Tracking is **complete and frozen**
([acceptance](eval/fr013_application_pipeline_tracking.md);
[ADR-005](adr/005_application_pipeline_lifecycle.md)).

**Thereafter:** Horizon 1B when the owner requests it — **FR-019 Recruiter
Intelligence** (**FR-018 frozen** —
[eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md)).
Horizon 1A (FR-008–FR-017) is complete and frozen. Remap:
[11_changelog.md](11_changelog.md) § 1.115; FR-018 freeze § 1.125.

Architecture decisions: `docs/adr/` (ADR-001, ADR-002, **ADR-003** thin in-repo
workflow runner accepted — LangGraph not required for current FR-008 scope; **ADR-004**
Opportunity as pre-decision system of record with the review queue as a derived
projection; **ADR-005** application pipeline lifecycle — stored status + append-only
events; SubmissionAttempt never auto-advances status; **ADR-006** recruiter document
truth validation — detection certainty ≠ evidence validation; JD never authorizes
candidate capability). Release evidence:
[eval/phase2_release_report.md](eval/phase2_release_report.md).

---

## Documentation Index

| Document | Authority | Use when you need |
|----------|-----------|-------------------|
| [00_repository_guide.md](00_repository_guide.md) | Canonical entry point | Orientation, read order, folder semantics |
| [04_functional_specification.md](04_functional_specification.md) | **Authoritative — requirements** | What the system must do; tier and fit semantics |
| [10_roadmap.md](10_roadmap.md) | **Authoritative — delivery** | Completed vs current focus vs future |
| [03_product_vision.md](03_product_vision.md) | **Authoritative — product direction** | Vision, horizons, capability domains |
| [05_engineering_principles.md](05_engineering_principles.md) | **Authoritative — engineering tradeoffs** | How to make implementation decisions |
| [06_domain_model.md](06_domain_model.md) | **Authoritative — domain concepts** | Entities, decision loop, operational mapping |
| [07_testing_strategy.md](07_testing_strategy.md) | **Authoritative — testing** | Test layers and regression philosophy |
| [08_implementation_notes.md](08_implementation_notes.md) | Supporting | Implementation notes and manual runners |
| [12_phase_history.md](12_phase_history.md) | Supporting | Phase 1–2 outcomes and lessons |
| [eval/phase2_release_report.md](eval/phase2_release_report.md) | Supporting | Phase 2 M5 GO evidence |
| [adr/README.md](adr/README.md) | Supporting | ADR index (001–004) |
| [eval/fr008_workflow_orchestration.md](eval/fr008_workflow_orchestration.md) | Supporting | FR-008 acceptance and close-out |
| [eval/fr009_opportunity_review_queue.md](eval/fr009_opportunity_review_queue.md) | Supporting | FR-009 acceptance and close-out (milestone records: `eval/fr009_m0`–`m4`) |
| [eval/fr006_manual_validation.md](eval/fr006_manual_validation.md) | Supporting | FR-006 validation procedure |
| [eval/fr006b_cv_quality_golden_suite.md](eval/fr006b_cv_quality_golden_suite.md) | Supporting | FR-006b permanent CV quality benchmarks |
| [eval/fr006b_cv_quality_findings.md](eval/fr006b_cv_quality_findings.md) | Supporting | FR-006b quality review (pre-implementation) |
| [eval/fr006b_cv_quality_validation.md](eval/fr006b_cv_quality_validation.md) | Supporting | FR-006b P0 implementation + G1–G5 results |
| [eval/fr002_openai_manual_eval.md](eval/fr002_openai_manual_eval.md) | Supporting | FR-002 live eval record |
| [eval/fr003_openai_manual_eval.md](eval/fr003_openai_manual_eval.md) | Supporting | FR-003 live eval record |
| [01_executive_summary.md](01_executive_summary.md) | Supporting | Quick narrative overview |
| [02_problem_statement.md](02_problem_statement.md) | Supporting | Problem context |
| [11_changelog.md](11_changelog.md) | Historical | Why documentation changed |
| [masterclass/README.md](masterclass/README.md) | Educational source | Academy packages (`FRnnn/` + regenerable `sources/`) |
| [AGENTS.md](../AGENTS.md) | **Authoritative — agent behaviour** | Cursor agent bootstrap and invariants |

When documents overlap, prefer the authoritative source for that concern. Do not treat
supporting documents as requirements sources.

---

## Recommended Read Order

**Engineers and agents starting cold:**

1. This guide
2. [AGENTS.md](../AGENTS.md)
3. [10_roadmap.md](10_roadmap.md) — what is done vs next
4. [04_functional_specification.md](04_functional_specification.md) — requirements
5. [06_domain_model.md](06_domain_model.md) — decision loop
6. [05_engineering_principles.md](05_engineering_principles.md) — invariants
7. [07_testing_strategy.md](07_testing_strategy.md) — how we test
8. [03_product_vision.md](03_product_vision.md) — when product context is needed
9. [12_phase_history.md](12_phase_history.md) — optional Phase 1–2 narrative

Supporting documents (01, 02) are optional for onboarding.

---

## Engineering Learning Academy workflow

Frozen engineering becomes interview-ready learning material through a fixed
pipeline. The repository owns packaging through **Masterclass Source Package**.
Deep learning and rapid interview revision follow Academy standards.

```text
Engineering → Validation → Acceptance → Freeze
    → Masterclass Source Package (docs/masterclass/FRnnn/)
    → Lean Engineering Masterclass (Markdown)
    → Masterclass PDF (official study edition)
    → Gamma Learning Presentation (~15–20 slides)
    → Interview Brief (~1 page)
    → Interview Deck (~3–5 slides)
    → Interview Revision / Coaching
```

| Step | Where |
|------|--------|
| Freeze / acceptance | `docs/eval/`, `docs/adr/` (authoritative) |
| Package | `docs/masterclass/FRnnn/` — `README.md`, `MANIFEST.md`, regenerable `sources/` |
| Lean Masterclass standard | [masterclass/LEAN_MASTERCLASS_STANDARD.md](masterclass/LEAN_MASTERCLASS_STANDARD.md) |
| Generator prompt | [masterclass/MASTERCLASS_GENERATOR_LEAN.md](masterclass/MASTERCLASS_GENERATOR_LEAN.md) |
| Masterclass PDF | `scripts/render_masterclass_pdf.py --package FRnnn` (Lean + `sources/` + optional); also automatic from `build_masterclass_package.py` |
| Interview Brief | [masterclass/INTERVIEW_BRIEF_STANDARD.md](masterclass/INTERVIEW_BRIEF_STANDARD.md) |
| Interview Deck | [masterclass/INTERVIEW_DECK_STANDARD.md](masterclass/INTERVIEW_DECK_STANDARD.md) |
| First packaged FRs | [masterclass/FR016/](masterclass/FR016/), [masterclass/FR017/](masterclass/FR017/), [masterclass/FR018/](masterclass/FR018/) |
| Regenerate snapshots + PDFs | `python scripts/build_masterclass_package.py FRnnn` |
| Academy index | [masterclass/README.md](masterclass/README.md) |

**Deep learning** = Masterclass + PDF + Gamma Learning Presentation.  
**Rapid interview revision** = Interview Brief + Interview Deck.

Do **not** generate presentations in this repository as part of FR close-out.
Do **not** hand-edit `sources/` snapshots or their sibling PDFs — regenerate from SoT
(`build_masterclass_package.py`).
Do **not** replace deep-learning artefacts with interview-only materials.
FR-019+ inherits Brief/Deck structure automatically — no rediscovery.
(FR-018 Academy package: [masterclass/FR018/](masterclass/FR018/); packages still
follow freeze → package → Lean Masterclass → PDF → Gamma → Brief/Deck.)

---

## Repository Structure

| Path | Layer | Purpose |
|------|-------|---------|
| `docs/` | Specification | Product and engineering knowledge |
| `docs/masterclass/` | Educational source | Attachable Masterclass Source Packages (after freeze) |
| `docs/assets/` | Specification | Diagrams and verification images |
| `docs/adr/` | Specification | Architecture decision records |
| `docs/eval/` | Specification | Manual eval and release reports |
| `src/` | Implementation | Python package and public capability boundaries |
| `tests/` | Implementation | Unit, functional, and golden journey tests |
| `scripts/` | Implementation | Owner/developer manual validation runners |
| `data/` | Operational | Career profile and opportunities store (SoT) |
| `applications/` | Operational | Live application pipeline, company notes, network tracking |
| `career-documents/` | Operational | Career artefacts (e.g. Master CV, generated CVs) |
| `manual_validation/` | Operational | Real job texts, outputs, owner notes |
| `templates/` | Operational | Placeholders — intentionally empty |
| `metrics/` | Operational | Placeholders — intentionally empty |
| `career-log.md` | Operational | Dated career milestones |
| `tools/` | Implementation | Engineering evaluation harnesses (not product CLIs) |
| `images/` | Reserved | Listed historically; not yet populated |

The operational layer is the domain the system must serve. Phase 2 pipeline and
outcome logging (Phase 2 M2; historically FR-013 subset) are the automated counterparts to manual tracking in
`applications/`.

---

## Operational Data Conventions

**Application tracker** (`applications/application_tracker.csv`) — pursued
opportunities: company, role, status, outcome, notes. Structured opportunities under
`data/opportunities/` are the system of record for assessed jobs; CSV export is
derived (M3).

**Network tracker** (`applications/network/network_tracker.csv`) — recruiter and
professional contacts. Contains personal data; do not copy into engineering or agent
configuration documents.

**Company notes** (`applications/company_notes/`) — per-company pursuit notes.

**Terminology reconciliation:** Operational data may use legacy tier language (e.g.
"Tier 1"). Product documentation standardises on **Platinum, Gold, Silver, Bronze**.
The former product tier name Skip is renamed Bronze (effort band only). See
[04_functional_specification.md](04_functional_specification.md) § Application Tier
Semantics.

**External reference:** Application notes may reference systems outside this
repository. This repository is authoritative for Career Intelligence Copilot.

---

## What Belongs in This Repository

- Product requirements and delivery phasing
- Engineering principles and domain concepts
- Operational job-search data and career artefacts
- Decision history (changelog)
- Implementation decisions — changelog and, when code exists, commit history

## What Does Not Belong Here

- API keys, credentials, or secrets
- Duplicated recruiter contact details in docs or agent rules
- Unrecorded or speculative architecture choices
- Speculative features not approved in the functional specification or roadmap

---

## Knowledge Accumulation

Engineering and product decisions made during development should be recorded in the
repository — not left in conversation history.

- **Product strategy changes** → [11_changelog.md](11_changelog.md)
- **Engineering invariant changes** → [05_engineering_principles.md](05_engineering_principles.md) and changelog
- **Requirement or semantic changes** → [04_functional_specification.md](04_functional_specification.md) and changelog
- **Phase or sequencing changes** → [10_roadmap.md](10_roadmap.md) and changelog
- **Frozen FR → Academy package** → `docs/masterclass/FRnnn/` + regenerate
  `sources/` via `scripts/build_masterclass_package.py`
