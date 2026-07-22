# Repository Guide

## Purpose

This document is the canonical entry point for understanding the Career Intelligence Copilot repository.

It explains what the repository contains, which documents are authoritative, how folders relate to the product, and where to read next. Every new engineer or AI agent session should start here.

---

## What This Repository Is

Career Intelligence Copilot has three coexisting layers:

**Specification layer** — product intent, requirements, delivery phasing, and engineering decision guidance in `docs/` and `AGENTS.md`.

**Operational layer** — the repository owner's live job search: application tracking, network contacts, career artifacts, and placeholders for future workflows.

**Implementation layer** — the Phase 2 Python package, structured data, and tests in `src/`,
`data/`, and `tests/`.

The repository is simultaneously a career tool, a portfolio project, and a Cursor learning laboratory. See [03_product_vision.md](03_product_vision.md) § Project Objectives.

Phase 2 implementation has started. FR-001 Career Profile, FR-002 Job Analysis, and
FR-003 Opportunity Assessment are implemented; later decision-loop stages (FR-004+) remain
to be built. Architecture decisions are recorded under `docs/adr/`.

---

## Documentation Index

| Document | Authority | Use when you need |
|----------|-----------|-------------------|
| [00_repository_guide.md](00_repository_guide.md) | Canonical entry point | Orientation, read order, folder semantics |
| [04_functional_specification.md](04_functional_specification.md) | **Authoritative — requirements** | What the system must do, acceptance criteria, tier and fit semantics |
| [10_roadmap.md](10_roadmap.md) | **Authoritative — delivery** | Phase status, scope boundaries, Phase 2 exit criteria |
| [03_product_vision.md](03_product_vision.md) | **Authoritative — product direction** | Vision, principles, horizons, capability domains |
| [05_engineering_principles.md](05_engineering_principles.md) | **Authoritative — engineering tradeoffs** | How to make implementation decisions |
| [06_domain_model.md](06_domain_model.md) | **Authoritative — domain concepts** | Entities, decision loop, operational mapping |
| [07_testing_strategy.md](07_testing_strategy.md) | **Authoritative — testing** | Test layers, regression philosophy, future suite growth |
| [08_implementation_notes.md](08_implementation_notes.md) | Supporting | Implementation architecture notes, provenance, deviations, FR-002/FR-003 verification |
| [eval/fr002_openai_manual_eval.md](eval/fr002_openai_manual_eval.md) | Supporting | FR-002 live OpenAI evaluation record |
| [eval/fr003_openai_manual_eval.md](eval/fr003_openai_manual_eval.md) | Supporting | FR-003 live OpenAI evaluation record (PARTIAL PASS) |
| [01_executive_summary.md](01_executive_summary.md) | Supporting | Quick narrative overview |
| [02_problem_statement.md](02_problem_statement.md) | Supporting | Problem context and rationale |
| [11_changelog.md](11_changelog.md) | Historical | Why documentation changed across versions |
| [AGENTS.md](../AGENTS.md) | **Authoritative — agent behaviour** | Cursor agent bootstrap and invariants |

When documents overlap, prefer the authoritative source for that concern. Do not treat supporting documents as requirements sources.

---

## Recommended Read Order

**Engineers and agents starting cold:**

1. This guide
2. [AGENTS.md](../AGENTS.md)
3. [04_functional_specification.md](04_functional_specification.md) — Phase 2 scope and requirements
4. [06_domain_model.md](06_domain_model.md) — conceptual model
5. [05_engineering_principles.md](05_engineering_principles.md) — decision invariants
6. [07_testing_strategy.md](07_testing_strategy.md) — test and regression conventions
7. [10_roadmap.md](10_roadmap.md) — current phase and exit criteria
8. [03_product_vision.md](03_product_vision.md) — when product context is needed

Supporting documents (01, 02) are optional for onboarding.

---

## Repository Structure

| Path | Layer | Purpose |
|------|-------|---------|
| `docs/` | Specification | Product and engineering knowledge |
| `docs/assets/` | Specification | Diagrams and verification overview images |
| `src/` | Implementation | Python package and public capability boundaries |
| `tests/` | Implementation | Unit, functional, and golden journey regression tests |
| `data/` | Operational | Structured career profile consumed by the system |
| `applications/` | Operational | Live application pipeline, company notes, network tracking |
| `career-documents/` | Operational | Career artifacts (e.g. Master CV) |
| `templates/` | Operational | Message and document templates — intentional placeholders, currently empty |
| `metrics/` | Operational | Review and analytics placeholders — intentional placeholders, currently empty |
| `career-log.md` | Operational | Dated log of career milestones and actions |
| `tools/` | Implementation | Engineering evaluation harnesses (not product CLIs) |
| `images/` | Reserved | Listed in README; not yet populated |

The operational layer is the domain the future system must serve. Phase 2 pipeline and outcome logging (FR-013) are the automated counterparts to manual tracking in `applications/`.

---

## Operational Data Conventions

**Application tracker** (`applications/application_tracker.csv`) — records pursued opportunities: company, role, status, outcome, notes.

**Network tracker** (`applications/network/network_tracker.csv`) — records recruiter and professional contacts. Contains personal data; do not copy into engineering or agent configuration documents.

**Company notes** (`applications/company_notes/`) — per-company pursuit notes and interview records.

**Terminology reconciliation:** Operational data may use legacy tier language (e.g. "Tier 1"). Product documentation standardises on **Platinum, Gold, Silver, Skip**. See [04_functional_specification.md](04_functional_specification.md) § Application Tier Semantics. Operational files will be reconciled when the owner approves.

**External reference:** Application notes may reference systems outside this repository (e.g. "Career Platform v1.0"). Those systems are not documented here. This repository is the authoritative home for the Career Intelligence Copilot platform under definition.

---

## Current Status

**Phase:** Phase 2 — Job Intelligence implementation

**Approved:** Phase 2 Job Intelligence MVP scope

**Implemented:** FR-001 Career Profile → FR-002 Job Analysis → FR-003 Opportunity Assessment
(**Complete**; FR-003 live eval **PARTIAL PASS**, assessment prompt v6)

**In progress:** Remaining Phase 2 decision loop, beginning with FR-004 Portfolio Matching

See [10_roadmap.md](10_roadmap.md) for phase detail and Phase 2 exit criteria.

---

## What Belongs in This Repository

- Product requirements and delivery phasing
- Engineering principles and domain concepts
- Operational job-search data and career artifacts
- Decision history (changelog)
- Implementation decisions — recorded in changelog and, when code exists, commit history

## What Does Not Belong Here

- API keys, credentials, or secrets
- Duplicated recruiter contact details in docs or agent rules
- Unrecorded or speculative architecture choices
- Speculative features not approved in the functional specification or roadmap

---

## Knowledge Accumulation

Engineering and product decisions made during development should be recorded in the repository — not left in conversation history.

- **Product strategy changes** → [11_changelog.md](11_changelog.md)
- **Engineering invariant changes** → [05_engineering_principles.md](05_engineering_principles.md) and changelog
- **Requirement or semantic changes** → [04_functional_specification.md](04_functional_specification.md) and changelog
- **Phase or scope changes** → [10_roadmap.md](10_roadmap.md) and changelog

Architecture Decision Records live under `docs/adr/`. See
[ADR-001](adr/001_python_yaml_profile_foundation.md) for the Phase 2 profile foundation.
