# MANIFEST — FR-017 Masterclass Source Package

## Masterclass Title

Agent Evaluation & Observability: Derive-Only Metrics, Reconstructability, and Anti-Theatre Observability

## Functional Requirement

**FR-017** — Agent Evaluation & Observability

## Repository Version

Changelog **1.111** (FR-017 repository close-out; Complete / Frozen since **1.110**).

## Current Status

**Complete / Frozen / Accepted** — narrow derive-only evaluation / learning substrate

Ordinary preparation remains: `cic agent run`  
Evaluation CLI: `cic agent orchestrate metrics` / `metrics-corpus`

## Completion Date

2026-08-07

## Package root (attach this folder)

`docs/masterclass/FR017/`

## Required documents

| Package path | Authoritative repository path | Notes |
|--------------|-------------------------------|-------|
| `sources/acceptance.md` | `docs/eval/fr017_agent_evaluation_observability.md` | Canonical engineering record |
| `sources/adr.md` | `docs/adr/009_orchestration_evaluation_substrate.md` | Normative architecture decisions |
| `sources/functional_specification.md` | `docs/04_functional_specification.md` § FR-017 | Requirements status |
| `sources/domain_model.md` | `docs/06_domain_model.md` § FR-017 | Domain concepts |
| `sources/implementation_notes.md` | `docs/08_implementation_notes.md` § FR-017 | Implementation pointers |
| `sources/testing_strategy.md` | `docs/07_testing_strategy.md` § FR-017 | Test expectations |
| `README.md` | (package-local) | Teaching bridge |
| `MANIFEST.md` | (package-local) | This file |

## Optional documents

| Package path | Authoritative repository path | When to include |
|--------------|-------------------------------|-----------------|
| `sources/optional/m0_spike.md` | `docs/eval/fr017_m0_engineering_spike.md` | Narrow-scope / 1B decoupling |
| `sources/optional/m1.md` | `docs/eval/fr017_m1_observability_contracts.md` | Contracts |
| `sources/optional/m2.md` | `docs/eval/fr017_m2_corpus_reconstructability.md` | Corpus GO |
| `sources/optional/m3.md` | `docs/eval/fr017_m3_owner_cli.md` | Read-only CLI |
| `sources/optional/m4.md` | `docs/eval/fr017_m4_evaluation.md` | Freeze evidence |

## Regenerating snapshots

```powershell
python scripts/build_masterclass_package.py FR017
```

Snapshots are full-file or mechanical section extracts with a generated banner.
They must not be hand-edited. Repository paths remain authoritative.

## Recommended generation order

1. `README.md` — teaching frame  
2. `sources/adr.md` — decisions and out-of-scope  
3. `sources/acceptance.md` — full engineering record (primary)  
4. `sources/functional_specification.md`  
5. `sources/domain_model.md`  
6. `sources/optional/m0_spike.md` — why laundry list was rejected  
7. `sources/optional/m2.md` / `m4.md` — corpus and freeze  
8. `sources/implementation_notes.md` + `sources/testing_strategy.md`  
9. Optional: `m1.md`, `m3.md` for depth  

## Expected outputs

Academy generators should produce (outside this repository unless later requested):

- lean Engineering Masterclass narrative per
  [LEAN_MASTERCLASS_STANDARD.md](../LEAN_MASTERCLASS_STANDARD.md) and
  [MASTERCLASS_GENERATOR_LEAN.md](../MASTERCLASS_GENERATOR_LEAN.md)
- interview-transferable talking points on derive-only observability
- permanent sections: Runtime Example, Why Employers Care, Validation Summary,
  Memorable Closing Statement
- **mandatory package PDFs** (Lean + `sources/` + `sources/optional/`) via
  `python scripts/build_masterclass_package.py FR017` or
  `python scripts/render_masterclass_pdf.py --package FR017`
- **Interview Brief** (~1 page) and **Interview Deck** (~3–5 slides) per
  [INTERVIEW_BRIEF_STANDARD.md](../INTERVIEW_BRIEF_STANDARD.md) and
  [INTERVIEW_DECK_STANDARD.md](../INTERVIEW_DECK_STANDARD.md)
  (produce on owner request; existing Masterclass / Gamma Learning work preserved)

Do **not** create Gamma slides inside this packaging step.
Do **not** rewrite Masterclass content when rendering the PDF.
Do **not** replace the Gamma Learning Presentation with the Interview Deck.
