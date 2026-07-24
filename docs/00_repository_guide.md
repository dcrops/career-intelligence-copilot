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
| What is next? | **FR-006b CV Quality Improvement**, then FR-007 and job acquisition — [10_roadmap.md](10_roadmap.md). |
| Where should I start reading? | This guide → [AGENTS.md](../AGENTS.md) → [04_functional_specification.md](04_functional_specification.md) → [10_roadmap.md](10_roadmap.md). |

---

## Current Status

**Phase 2 Job Intelligence — Complete** (documentation frozen as baseline).

**Next milestone:** FR-006b CV Quality Improvement

**Thereafter:** FR-007 Cover Letter → automated job acquisition (Horizon 1)

Architecture decisions: `docs/adr/`. Release evidence:
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
| [eval/fr006_manual_validation.md](eval/fr006_manual_validation.md) | Supporting | FR-006 validation procedure |
| [eval/fr002_openai_manual_eval.md](eval/fr002_openai_manual_eval.md) | Supporting | FR-002 live eval record |
| [eval/fr003_openai_manual_eval.md](eval/fr003_openai_manual_eval.md) | Supporting | FR-003 live eval record |
| [01_executive_summary.md](01_executive_summary.md) | Supporting | Quick narrative overview |
| [02_problem_statement.md](02_problem_statement.md) | Supporting | Problem context |
| [11_changelog.md](11_changelog.md) | Historical | Why documentation changed |
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

## Repository Structure

| Path | Layer | Purpose |
|------|-------|---------|
| `docs/` | Specification | Product and engineering knowledge |
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
outcome logging (FR-013 subset) are the automated counterparts to manual tracking in
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
