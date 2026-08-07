# FR-016 — Multi-Agent Orchestration

**Masterclass Source Package** for the Engineering Learning Academy  
**Status:** Complete / Frozen / Accepted (learning proof)  
**Attach this folder** (`docs/masterclass/FR016/`) when generating the Masterclass.

This package is a **packaging layer**, not a second engineering record.
Authoritative content lives under `docs/eval/`, `docs/adr/`, and related docs.
Files in `sources/` are **generated snapshots** — regenerate; do not hand-edit.

```powershell
python scripts/build_masterclass_package.py FR016
```

---

## What this Functional Requirement teaches

How to design **permission-separated multi-agent systems** that stay fail-closed:

- a deterministic supervisor that **delegates only** (DOS)
- a frozen mutating specialist (BOPA) with an unchanged ToolPolicy
- a read-only specialist (OBS) with a distinct allow-list
- typed, audited handoffs that never grant another specialist’s tools
- honest go/no-go when multi-agent does **not** beat a simpler single-agent path

---

## Why it matters

Many “multi-agent” designs are theatre: renamed personas wrapping the same tools.
FR-016 records a production counter-example — and documents when to stop and keep
the single bounded agent as the daily workflow.

---

## Prerequisites

- Familiarity with FR-015 BOPA (bounded agent, ToolPolicy, allow-list)
- Basic CIC Horizon 1A context: opportunities, packages, truth, pipeline
- Comfort reading ADRs and acceptance reports

---

## Expected learning outcomes

After studying this package (and generating the Masterclass from it), a learner should be able to:

1. Explain DOS vs BOPA vs OBS authority boundaries
2. Contrast DelegationPolicy with per-specialist ToolPolicy
3. Describe typed handoff lifecycle and why chat handoffs were rejected
4. Argue why Prep/Truth/Review splitting is multi-agent theatre
5. State why FR-016 remained a learning proof and why `cic agent run` stays preferred for ordinary prep
6. Identify when multi-agent becomes commercially stronger (e.g. Job Discovery)

---

## Where the authoritative documents are

| Role | In this package | Repository source of truth |
|------|-----------------|------------------------------|
| Bridge / teaching index | [README.md](README.md) (this file) | — |
| Generation contract | [MANIFEST.md](MANIFEST.md) | — |
| Acceptance (canonical) | [sources/acceptance.md](sources/acceptance.md) | `docs/eval/fr016_multi_agent_orchestration.md` |
| ADR | [sources/adr.md](sources/adr.md) | `docs/adr/008_multi_agent_orchestration.md` |
| Functional requirements § | [sources/functional_specification.md](sources/functional_specification.md) | `docs/04_functional_specification.md` § FR-016 |
| Domain model § | [sources/domain_model.md](sources/domain_model.md) | `docs/06_domain_model.md` § FR-016 |
| Implementation notes § | [sources/implementation_notes.md](sources/implementation_notes.md) | `docs/08_implementation_notes.md` § FR-016 |
| Testing strategy § | [sources/testing_strategy.md](sources/testing_strategy.md) | `docs/07_testing_strategy.md` § FR-016 |
| Milestone history | [sources/optional/](sources/optional/) | `docs/eval/fr016_m0`–`m4` |

**Edit engineering in the repository paths above — never in `sources/`.**

---

## Package layout

```text
FR016/
  README.md                 ← this bridge
  MANIFEST.md               ← generation contract
  sources/                  ← regenerable snapshots
    acceptance.md
    adr.md
    functional_specification.md
    domain_model.md
    implementation_notes.md
    testing_strategy.md
    optional/
      m0_spike.md … m4.md
```

Follow [MANIFEST.md](MANIFEST.md) for recommended generation order and expected outputs.

## Interview revision layer

Deep learning artefacts (Masterclass / PDF / Gamma Learning Presentation) are preserved.
Rapid interview revision follows Academy standards — generate only on owner request:

- [INTERVIEW_BRIEF_STANDARD.md](../INTERVIEW_BRIEF_STANDARD.md) (~1 page)
- [INTERVIEW_DECK_STANDARD.md](../INTERVIEW_DECK_STANDARD.md) (~3–5 slides)
