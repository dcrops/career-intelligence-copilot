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

---

## Project Context

Career Intelligence Copilot is a decision-support system for job search — not an application automation tool.

**Current phase:** Phase 2 Job Intelligence MVP is **complete** and documentation is
a **frozen baseline** (M5 GO —
[docs/eval/phase2_release_report.md](docs/eval/phase2_release_report.md);
[docs/12_phase_history.md](docs/12_phase_history.md)). FR-001–FR-006, M1–M4, and
corrective M4a are closed. **Next milestone:** **FR-006b CV Quality Improvement**
(Horizon 1). Do not reopen Phase 2 exit criteria or architecture without explicit
owner request. FR-007 Cover Letter remains planned thereafter.

**Implementation foundation:** Python 3.11+, Pydantic, YAML storage, and the public profile
service boundary are recorded in
[ADR-001](docs/adr/001_python_yaml_profile_foundation.md).

**Immediate priority (Horizon 1):** Help the repository owner secure a suitable AI Engineering role sooner while reducing job-search effort. Horizon 1 wins when objectives conflict. See [docs/03_product_vision.md](docs/03_product_vision.md).

**Single-user phase:** The repository owner is the user, builder, and product owner.

---

## Phase 2 Scope Boundaries

**In scope (delivered):** Career profile, job analysis, opportunity assessment (Technical, Commercial, Portfolio Fit), portfolio matching, application strategy (pursuit posture + effort tiers), pipeline tracking, outcome logging, ranked comparison of open opportunities, grounded opportunity identity.

**Out of scope for Phase 2 (unchanged):** Cover letter generation, recruiter outreach, interview preparation, full dashboard, market intelligence, cross-domain daily prioritisation, automated job discovery, predictive scoring (Interview Probability, Recruiter Confidence).

**Delivered outside original Phase 2 exit criteria (owner-sequenced):** FR-006 CV Generation — complete; do not reopen as informal “Phase D” presentation work. Quality iteration is **FR-006b**.

Full detail: [docs/04_functional_specification.md](docs/04_functional_specification.md) and [docs/10_roadmap.md](docs/10_roadmap.md).

Do not expand scope into Phase 3+ / Horizon 2 capabilities unless explicitly requested by the owner.

---

## Engineering Invariants

Apply [docs/05_engineering_principles.md](docs/05_engineering_principles.md) for all tradeoffs. Non-negotiables:

- **Intelligence before automation** — explain before acting
- **Human review** — tier recommendations and effort allocation require user judgment; no automated external communications
- **Dual-value test** — every capability must improve interview/offer odds or reduce repetitive search effort
- **Explainability** — assessments must cite evidence from job description and profile
- **Outcome logging** — decisions and results must be recordable (FR-013)
- **Operational continuity** — the built system must connect to existing tracking in `applications/`, not run parallel to it
- **Public profile boundary** — downstream capabilities obtain the career profile through
  `career_intelligence.profile`, never through its YAML storage adapter

---

## Do Not

- Propose architecture or choose technologies unless explicitly asked
- Add Phase 3+ / Horizon 2 features unless explicitly requested
- Copy recruiter PII from `applications/network/` into rules, skills, or documentation
- Treat executive summary or problem statement as requirements sources
- Duplicate content that already exists in authoritative docs — cross-reference instead
- Guarantee employment, interviews, or recruiter engagement in any output

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

Do not leave important knowledge only in chat history.
