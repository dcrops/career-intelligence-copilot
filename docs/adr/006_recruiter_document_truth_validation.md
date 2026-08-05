# ADR-006: Recruiter Document Truth Validation

**Status:** Accepted (FR-014 M1)  
**Date:** 2026-08-05  
**Reaffirms:** [ADR-001](001_python_yaml_profile_foundation.md) (Career Profile public
boundary); human review on consequential recruiter-facing outputs  
**Does not amend:** [ADR-002](002_opportunity_persistence.md),
[ADR-003](003_application_workflow_orchestration.md),
[ADR-004](004_opportunity_review_boundary.md),
[ADR-005](005_application_pipeline_lifecycle.md)

**Spike:** [eval/fr014_m0_engineering_spike.md](../eval/fr014_m0_engineering_spike.md)
(Accepted)

---

## Context

FR-006 / FR-007 generate recruiter-facing CV and cover-letter Markdown. Owner review
and prompt discipline remain mandatory, but a real dogfooding defect (Redwolf) showed
Job Description technologies framed as candidate capability. Soft generation rules are
not a sufficient trust boundary before automation increases.

FR-014 must provide a **deterministic fail-closed validation boundary**. It must not
become another LLM pass, a rewriter, a fit scorer, or a general natural-language fact
checker.

Two distinct failure modes must not be conflated:

1. **Detection uncertainty** — the system is unsure whether a span is a candidate
   claim, or how to classify it.
2. **Evidence / truth failure** — a claim was identified, but candidate evidence does
   not support it (or contradicts it).

Treating “no claims detected” as proof of truthfulness would recreate the Redwolf
risk under a false PASS.

---

## Decision

1. **Hybrid deterministic architecture.** Recruiter Document Truth Validation is:
   Candidate Evidence Catalogue → Claim Detection → Validator → TruthReport.
   Package: `career_intelligence.truth_validation`.

2. **Markdown is the primary authoritative validation surface.** HTML/PDF are derived.
   Dual gates: advisory after generation; authoritative after owner Markdown edits.
   Fail-closed external-use gating. No silent rewriting. Owner review remains
   mandatory.

3. **Separate detection certainty from evidence validation.** Every material finding
   records both:
   - `detection_certainty` (`certain` | `ambiguous`)
   - `evidence_status` (`supported` | `unsupported` | `ambiguous` | `contradictory` |
     `not_applicable`)
   These fields answer different questions and must not be collapsed into one score.

4. **Absence of detection is not evidence of truth.** A TruthReport must not receive
   overall `pass` merely because no candidate claims were detected. `pass` requires
   explicit coverage completeness plus recorded detection **and** validation having
   been performed for the in-scope artefact. Incomplete or insufficient coverage yields
   at least `review_required` (or `fail` when policy marks coverage failure blocking).

5. **Ambiguous detection is not silent PASS.** Ambiguous detection on a material
   Class A (candidate objective) claim produces an explainable `review_required` or
   `blocking` finding according to severity / claim strength — never an implicit pass.

6. **JD and downstream planning artefacts never authorize candidate capability.**
   Job Analysis, Opportunity Assessment, Portfolio Match, Application Strategy,
   TailoringPlan, and CoverLetterPlan are **context-only**. They may help classify
   employer-context phrasing or detect JD→candidate leakage; they must never set
   Class A evidence to `supported`.

7. **Career Profile is the authoritative candidate evidence source** (via the public
   profile boundary). Catalogue entries that support Class A must declare
   `authority=candidate_authoritative` with provenance.

8. **Truth Validation validates; it does not generate or rewrite.** Findings explain
   claim, class, detection certainty, evidence status, severity, and recommended owner
   action. Remediation is owner edit (or explicit logged exception in later
   milestones) — never silent mutation of prose.

9. **M1 scope is contracts only.** Typed models, catalogue contract, claim classes /
   strengths, TruthFinding / TruthReport, outcomes / severity, provenance rules,
   ADR-006, and contract-invariant tests. No claim detectors, catalogue population
   from profile, CLI, package gates, or submission integration in M1.

10. **Breadth is corpus-justified.** Later milestones may add claim kinds only where
    deterministic validation is justified by observed corpus evidence — not as a
    general NL fact checker. M4 must remain bounded accordingly.

11. **Out of scope.** Grammar/style improvement, prompt optimisation as the primary
    control, LLM-as-sole-judge, silent submit, pipeline status writes, absorbing
    FR-003–FR-007 / FR-012 / FR-013 responsibilities.

---

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| LLM truth-check pass as primary | Non-deterministic; can invent evidence |
| Prompt / planner hardening only | Already insufficient (Redwolf) |
| Plan-field validation only | Misses composed prose and owner Markdown edits |
| Regex keyword scan alone | Weak classification; not a full trust boundary |
| PASS when findings list is empty | Conflates non-detection with truthfulness |

---

## Consequences

- M1 froze contracts in `career_intelligence.truth_validation`.
- M2 implemented deterministic technology / leakage validation against the catalogue.
- M3 wired owner CLI and fail-closed external-use gates.
- M4 added corpus-justified claim kinds; **FR-014 is complete and frozen**
  ([eval/fr014_recruiter_document_truth_validation.md](../eval/fr014_recruiter_document_truth_validation.md)).
- FR-012 consumes TruthReport for readiness; it does not own truth policy.
- FR-006/007 remain generators; they are not the trust boundary.

---

## Guardrails

- Do not treat Job Description requirements as candidate evidence.
- Do not award `pass` without complete coverage and performed detection + validation.
- Do not collapse detection certainty into evidence status.
- Do not silently rewrite or delete claims.
- Do not replace owner review.
- Do not implement detectors or gates under the guise of “just contracts.”
