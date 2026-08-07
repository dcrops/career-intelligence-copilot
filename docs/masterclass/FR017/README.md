# FR-017 — Agent Evaluation & Observability

**Masterclass Source Package** for the Engineering Learning Academy  
**Status:** Complete / Frozen / Accepted (derive-only evaluation substrate)  
**Attach this folder** (`docs/masterclass/FR017/`) when generating the Masterclass.

This package is a **packaging layer**, not a second engineering record.
Authoritative content lives under `docs/eval/`, `docs/adr/`, and related docs.
Files in `sources/` are **generated snapshots** — regenerate; do not hand-edit.

```powershell
python scripts/build_masterclass_package.py FR017
```

---

## What this Functional Requirement teaches

How to build **honest evaluation** over multi-agent audits without observability theatre:

- derive metrics from existing records before inventing instrumentation
- treat reconstructability (R1–R12) as an acceptance criterion
- distinguish **missing** metadata from **measured zero**
- detect parent/child orphans and contradictions without repairing them
- keep evaluation **read-only** and fail closed on invented precision
- refuse dashboards when derive-only already answers the questions

---

## Why it matters

Many teams equate “observability” with dashboards and tracing products. FR-017
records a counter-example: useful owner and interview insight from pure derivation
over FR-016 audits, reusing FR-015 child metrics, with Horizon 1B left unblocked.

---

## Prerequisites

- Familiarity with FR-016 DOS / BOPA / OBS audits and typed handoffs
- Basic FR-015 `AgentRunMetrics` / missing-vs-zero intuition
- Comfort reading ADRs and acceptance reports

---

## Expected learning outcomes

After studying this package (and generating the Masterclass from it), a learner should be able to:

1. Explain derive-only evaluation vs instrumentation theatre
2. Walk R1–R12 reconstructability against an audit
3. Argue why missing ≠ zero for tokens/cost/latency
4. Detect orphan parent/child linkage from correlation reports
5. State why FR-017 did not justify dashboards at freeze
6. Describe when richer observability would become justified

---

## Where the authoritative documents are

| Role | In this package | Repository source of truth |
|------|-----------------|------------------------------|
| Bridge / teaching index | [README.md](README.md) (this file) | — |
| Generation contract | [MANIFEST.md](MANIFEST.md) | — |
| Acceptance (canonical) | [sources/acceptance.md](sources/acceptance.md) | `docs/eval/fr017_agent_evaluation_observability.md` |
| ADR | [sources/adr.md](sources/adr.md) | `docs/adr/009_orchestration_evaluation_substrate.md` |
| Functional requirements § | [sources/functional_specification.md](sources/functional_specification.md) | `docs/04_functional_specification.md` § FR-017 |
| Domain model § | [sources/domain_model.md](sources/domain_model.md) | `docs/06_domain_model.md` § FR-017 |
| Implementation notes § | [sources/implementation_notes.md](sources/implementation_notes.md) | `docs/08_implementation_notes.md` § FR-017 |
| Testing strategy § | [sources/testing_strategy.md](sources/testing_strategy.md) | `docs/07_testing_strategy.md` § FR-017 |
| Milestone history | [sources/optional/](sources/optional/) | `docs/eval/fr017_m0`–`m4` |

**Edit engineering in the repository paths above — never in `sources/`.**

---

## Package layout

```text
FR017/
  README.md
  MANIFEST.md
  sources/          ← regenerable snapshots
    optional/       ← M0–M4 milestone mirrors
```

CLI demos (repository, not packaged as SoT):
`cic agent orchestrate metrics` / `metrics-corpus`

## Generated Masterclass (Lean Edition)

Interview-oriented educational narrative (not SoT; not slides):

- Markdown: [Engineering_Masterclass_002_FR017.md](Engineering_Masterclass_002_FR017.md)
- **PDF (official study edition):** [Engineering_Masterclass_002_FR017.pdf](Engineering_Masterclass_002_FR017.pdf)

Complies with [LEAN_MASTERCLASS_STANDARD.md](../LEAN_MASTERCLASS_STANDARD.md).
Regenerate PDF (formatting only):

```powershell
python scripts/render_masterclass_pdf.py docs/masterclass/FR017/Engineering_Masterclass_002_FR017.md
```

Import Markdown/PDF into Gamma for the **Learning** Presentation (~15–20 slides).
Rapid interview revision (Interview Brief ~1 page + Interview Deck ~3–5 slides) follows
[INTERVIEW_BRIEF_STANDARD.md](../INTERVIEW_BRIEF_STANDARD.md) and
[INTERVIEW_DECK_STANDARD.md](../INTERVIEW_DECK_STANDARD.md) — generate only on owner
request; do not regenerate in process-only updates. Do not treat Masterclass artefacts
as an engineering authority — acceptance + ADR-009 remain canonical.
