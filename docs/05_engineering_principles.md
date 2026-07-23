# Engineering Principles

## Purpose

This document defines how engineering decisions should be made throughout Phase 2 and beyond.

It complements [03_product_vision.md](03_product_vision.md) (what the product believes) and [04_functional_specification.md](04_functional_specification.md) (what the system must do). It does not choose technologies, propose architecture, or describe implementation.

For agent bootstrap instructions, see [AGENTS.md](../AGENTS.md).

---

## Decision Context

Every engineering tradeoff in this repository is made under constraints that do not apply to typical product teams:

- **Horizon 1 urgency** — the owner is running an active job search with real deadlines
- **Single builder** — the user, product owner, and engineer are the same person
- **Three objectives** — career outcome, portfolio demonstration, and Cursor workflow learning compete for time; Horizon 1 wins on conflict
- **Pre-implementation** — no code, stack, or architecture exists yet; choices must be earned by validated need

---

## Invariants

These are non-negotiable during Phase 2 unless the owner explicitly revises them and the changelog is updated.

### Intelligence before automation

Decision quality is the product. Automation serves intelligence — it does not replace it. Automate structured extraction and comparison; do not automate tier commitment or externally visible actions.

### Human review on consequential outputs

Tier recommendations, ranked comparisons that drive daily effort, and any future externally visible content require user review and override capability. Application tiers are effort guidance only — they are not autonomous apply/skip decisions.

### Dual-value gate

Every capability must satisfy at least one criterion from [04_functional_specification.md](04_functional_specification.md) § Prioritisation Guidance. If neither applies, defer.

### Explainability and evidence

Assessments must be explainable with cited evidence. Do not ship confident-sounding outputs without grounding. Do not invent precision (scores, percentages) where evidence is insufficient.

### Outcome logging

FR-013 is infrastructure, not a backlog item. A system that assesses but does not remember is a calculator, not a copilot.

### Operational continuity

The built system must connect to the owner's existing workflow in `applications/` and related operational folders. A parallel tool that the owner must maintain alongside manual trackers has failed regardless of technical quality.

---

## Tradeoff Principles

### Scope control

Phase 2 is one vertical slice through the decision loop. Resist adjacent features —
cover letters, recruiter modules, dashboards, and unofficial “Phase D” CV presentation
extensions — that feel like job-search help but expand past the approved FR boundary.
FR-006 (CV content decisions) is complete; do not reopen it for presentation polish.

**Violate when:** An addition passes the dual-value test, has an approved FR (or explicit
owner request), and can ship without delaying remaining Phase 2 exit criteria.

### Simplicity over flexibility

Optimise for one user, one search context, one profile. Generalise only at stage boundaries (see Extensibility), not inside implementations.

**Violate when:** Simplicity would force false precision — e.g. a single opaque score instead of dimensional fit breakdown.

### Build before automate

Manual confirmation steps are acceptable during early delivery. Trust the assessment loop before collapsing review steps.

**Violate when:** A manual step becomes the adoption bottleneck and the automated step has verifiable correctness with optional review.

### Acceptable technical debt

Acceptable: rough ingestion, manual profile bootstrapping, minimal comparison UI.

Unacceptable: unreproducible assessments, missing outcome records, unexplained tier logic, duplicated operational data in incompatible formats.

**Violate when:** Debt on the critical path to first useful assessment on a real posting this week — if the reasoning chain is sound and outcomes are logged.

### Performance

Optimise time-to-decision for occasional interactive use — a few assessments per day — not throughput or scale.

**Violate when:** Slow assessments cause the owner to bypass the system and revert to manual analysis.

### Testing

Prioritise decision regression over code coverage. Golden cases should come from real postings in the application tracker. One visibly wrong assessment on a cared-about role ends adoption.

**Violate during:** Initial exploration before assessment shape stabilises. Non-negotiable once tiers influence real decisions.

### MVP discipline

Ship the smallest complete loop: profile → analysis → assessment → tier → log → compare. Breadth without a complete loop is not MVP.

**Violate when:** The loop is complete but unused because it does not connect to where the owner already works — extend only enough to bridge adoption, not to add features.

### Extensibility

Build extensible seams between decision stages; keep implementations inside each stage simple. Outcome records and assessment objects should be shaped so future phases can consume them.

**Violate when:** An abstraction serves only Horizon 2, has no Phase 2 consumer, and delays delivery.

---

## Common Failure Modes

Avoid these patterns — they are the most likely causes of project failure in this repository:

1. **Building the next FR (or informal Phase D) while Phase 2 exit is incomplete** —
   cover letters, recruiter outreach, dashboards, and CV *presentation* polish feel
   urgent but must not displace remaining Phase 2 exit criteria or reopen FR-006
2. **Confident assessments without evidence** — erodes trust during a live search after one bad recommendation
3. **A system parallel to existing trackers** — the owner maintains two workflows; the manual one wins
4. **Optimising portfolio or learning objectives over Horizon 1** — impressive engineering that does not shorten the job search
5. **Skipping outcome logging** — no compounding value, no hypothesis validation, repetitive re-analysis forever

---

## Relationship to Other Documents

| Question | Authoritative document |
|----------|------------------------|
| What must the system do? | [04_functional_specification.md](04_functional_specification.md) |
| What phase are we in? | [10_roadmap.md](10_roadmap.md) |
| What are the domain entities? | [06_domain_model.md](06_domain_model.md) |
| What are the product principles? | [03_product_vision.md](03_product_vision.md) |
| Why did decisions change? | [11_changelog.md](11_changelog.md) |

When this document conflicts with the functional specification on requirements, the functional specification wins. When it conflicts on how to prioritise engineering effort, this document wins.

---

## Updating This Document

Record engineering invariant changes here and in [11_changelog.md](11_changelog.md). Do not leave durable tradeoff decisions only in agent conversations.

Architecture Decision Records will be introduced when the first irreversible implementation decision requires them. Until then, note undecided status in [10_roadmap.md](10_roadmap.md).
