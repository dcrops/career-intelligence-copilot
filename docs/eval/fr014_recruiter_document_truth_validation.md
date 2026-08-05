# FR-014 — Recruiter Document Truth Validation

**Status:** **Complete** — documentation frozen  
**Date:** 2026-08-05  
**Recommendation:** **FR-014 ACCEPTED**  
**Next:** **FR-015** Bounded Agentic Workflow is now **complete and frozen**
([fr015_bounded_agentic_workflow.md](fr015_bounded_agentic_workflow.md)).
Begin **FR-016** only on explicit owner request.

**ADR:** [ADR-006](../adr/006_recruiter_document_truth_validation.md) (Accepted)

**Milestones:**
[M0](fr014_m0_engineering_spike.md) (Accepted),
[M1](fr014_m1_truth_validation_contracts.md),
[M2](fr014_m2_technology_validation.md),
[M3](fr014_m3_owner_workflow.md),
[M4](fr014_m4_claim_validation.md).

---

## 1. Executive Summary

FR-014 delivers a **deterministic fail-closed trust boundary** for recruiter-facing CV and cover-letter Markdown. Unsupported material candidate claims cannot authorize external use or FR-012 submission. Owner review remains mandatory. The system does not rewrite documents or use an LLM as truth authority.

| Milestone | Delivered |
|-----------|-----------|
| M0 | Architecture spike accepted (Catalogue → Detection → Validator → TruthReport) |
| M1 | Typed contracts + ADR-006 (detection ≠ evidence; PASS requires coverage + performed flags) |
| M2 | Technology/framework validation; Redwolf TypeScript/Vue FAIL |
| M3 | Owner CLI, sidecar persistence, hash freshness, package/submission gates |
| M4 | Employment honesty, certifications, years, delivery, domain — close-out |

Package: `career_intelligence.truth_validation`. Validator version: `fr014-m4-deterministic-1`.

---

## 2. Business Problem

CIC generates recruiter-facing CV and cover-letter artefacts via planner → composer → render, with mandatory owner review. Existing fidelity checks (company / role / project mentioned) do **not** enforce **candidate-evidence ↔ candidate-claim** integrity.

Job Description technologies are abundant and attractive to planners and composers. When framed as candidate capability, they convert employer evidence into false candidate claims — damaging credibility and interview odds. Prompt discipline and owner review caught the motivating Redwolf defect once; that luck must not remain the control plane as automation increases.

FR-014 exists so the owner can trust that material first-person factual claims in outbound documents are profile-backed before external use or submission.

---

## 3. Engineering Problem

**Question:** What is a factual claim, how is it represented, and how is it validated deterministically without becoming another LLM pass?

Two failure modes must not be conflated:

1. **Detection uncertainty** — unsure whether a span is a candidate claim or how to classify it.
2. **Evidence / truth failure** — a claim was identified, but candidate evidence does not support it.

Treating “no claims detected” as proof of truthfulness would recreate the Redwolf risk under a false PASS. Soft prompt rules are non-deterministic, incomplete, and bypassed by owner Markdown edits. Plan-field validation alone misses composed prose. Regex keyword scans without framing classification produce false positives on employer-context mentions.

The engineering solution is a hybrid deterministic pipeline: build a Candidate Evidence Catalogue from the Career Profile, detect and classify structured claims in authoritative Markdown, validate against the catalogue, emit an explainable TruthReport, and fail closed at external-use and submission gates.

---

## 4. Redwolf Motivating Example (Python supported; TypeScript/Vue blocking; outcome fail)

Generated cover letter (paraphrased from owner review):

> “Roles centred on Python, TypeScript, and Vue are where I do my best engineering work.”

| Token | Profile evidence | Result |
|-------|------------------|--------|
| Python | Supported | Class A — **supported** (info) |
| TypeScript | JD only; not in profile as candidate skill | Class A — **unsupported** (blocking) |
| Vue | JD only; not in profile as candidate skill | Class A — **unsupported** (blocking) |

Framing (“where I do my best engineering work”) maps to high claim strength (proficiency / preference-as-expertise). Correct employer-context phrasing (“The role uses TypeScript and Vue”) would be Class B and not blocking.

**M2 validation outcome:** `fail` — TypeScript and Vue blocking; Python supported. Once M3 gates landed, this blocks package external-use readiness and FR-012 submission until the owner edits Markdown and revalidates.

---

## 5. Final Architecture (Catalogue→Detection→Validator→TruthReport→External-Use Gate→Owner Review→Render→Submission→Pipeline)

```
Career Profile (authoritative, via public profile boundary)
        │
        ▼
Candidate Evidence Catalogue
        │
Artefact under test — CV / Cover Letter Markdown (primary)
        │
        ▼
Claim Detection & Classification (technology + extended kinds)
        │
        ▼
Deterministic Claim Validator
        │
        ▼
TruthReport (content-hash freshness)
        │
        ├──► Package external-use gate (cic package verify)
        ├──► Submission readiness gate (FR-012)
        │
        ▼
Owner Review (mandatory)
        │
        ▼
(Optional) Markdown Edit → Revalidate
        │
        ▼
Render → Submission → Pipeline Tracking (FR-013)
```

| Component | Owns | Does not own |
|-----------|------|--------------|
| Catalogue | Profile-derived facts only | JD / assessment / strategy as capability evidence |
| Detection | Framing Class A/B/C; claim kinds in scope | Soft skills / motivation |
| Validator | Evidence status + severity (ADR-006) | Rewriting / auto-correction |
| TruthReport | Explainable findings; hash fingerprint | Mutating the artefact |
| Gates (M3) | Fail-closed external use | SubmissionAttempt success semantics |
| CLI | Thin `cic truth` | Policy |

Markdown is authoritative; HTML/PDF are derived. Dual insertion: advisory after generation (optional); authoritative after owner Markdown edits before external use.

---

## 6. ADR-006 Summary

[ADR-006](../adr/006_recruiter_document_truth_validation.md) records eleven decisions:

1. Hybrid deterministic architecture: Catalogue → Detection → Validator → TruthReport.
2. Markdown primary; dual gates; fail-closed external-use; no silent rewrite; owner review mandatory.
3. Separate `detection_certainty` from `evidence_status` on every finding.
4. Absence of detection is not evidence of truth — PASS requires complete coverage plus performed detection and validation.
5. Ambiguous Class A detection → `review_required` or `blocking`; never implicit pass.
6. JD and downstream planning artefacts are context-only; never authorize Class A capability.
7. Career Profile is the authoritative candidate evidence source (`candidate_authoritative` provenance).
8. Truth Validation validates; it does not generate or rewrite.
9. M1 scope was contracts only; detectors and gates deferred to M2/M3.
10. Breadth is corpus-justified; M4 bounded accordingly.
11. Out of scope: grammar/style, prompt optimisation as primary control, LLM-as-judge, silent submit, pipeline writes, absorbing FR-003–FR-007 / FR-012 / FR-013.

---

## 7. Trust Boundary

**In scope (frozen):**

| Artefact | Role |
|----------|------|
| Tailored CV Markdown | Recruiter-facing; owner-editable SoT |
| Cover Letter Markdown | Motivating defect surface; owner-editable SoT |

**Derived (not primary validation input):** HTML, PDF.

**Hard invariant:** Job Description / employer evidence must never authorize candidate capability claims.

**Explicitly not the boundary:** writing improvement, grammar, tone, fit scoring (FR-003), portfolio ranking (FR-004), strategy (FR-005), document generation (FR-006/007), package composition (FR-010), submission mechanics (FR-012), pipeline lifecycle (FR-013), silent deletion or auto-rewrite of claims.

**Future compatibility (design only):** application form answers, recruiter/LinkedIn messages, interview prep notes — same Claim + Catalogue + TruthReport pattern via new artefact adapters. No Horizon 1B/2 implementation in FR-014.

---

## 8. Claim Model (kinds in force + excluded)

### Claim classes

| Class | Name | Validation |
|-------|------|------------|
| **A** | Candidate objective claim | Must be supported by candidate evidence |
| **B** | Employer / role context | JD evidence OK; must not be phrased as candidate capability |
| **C** | Aspiration / transition | Must not imply existing expertise |
| **D** | Judgement / motivation | No skill evidence required; must not smuggle Class A facts |

Only Class A (and Class B misframed as A) produce material blocking outcomes.

### Claim kinds in force

| Kind | Milestone | Behaviour |
|------|-----------|-----------|
| `technology` | M2 | Profile skills / experience / project tech; Redwolf leakage detection |
| `employment` | M4 | Commercial AI / commercial software / independent engineering honesty |
| `certification` | M4 | Profile certifications only |
| `duration` | M4 | Years only when `supported_years` computable from dates; overclaim → blocking; unknown tenure → review_required |
| `project_delivery` | M4 | Named project / delivery object with catalogue evidence |
| `domain` | M4 | Profile domain skills / project demonstrates |

### Excluded (frozen out of scope)

Education (no profile education section), identity / contact link crawling, soft skills, personality, motivation, aspirations, opinions, future intentions, subjective quality statements, general NL fact checking.

---

## 9. Evidence Model

### Authoritative candidate evidence (may support Class A)

| Source | Use |
|--------|-----|
| **Career Profile** (via `career_intelligence.profile`) | Primary SoT: skills, experience, projects, certifications, summary |
| Profile-linked project / experience metadata | Delivery claims, tech via `demonstrates` / skill refs |
| Owner-approved identity / contact facts | As represented in profile |

### Context only — never candidate-capability authorization

| Source | Allowed | Forbidden |
|--------|---------|-----------|
| Job Analysis / JD technologies | Classify employer-context; detect JD→candidate leakage | Authorize “I know X” |
| Opportunity Assessment | Gap context for warnings | Invent candidate skills |
| Portfolio Match | Confirm project emphasis | Invent capabilities not in profile |
| Application Strategy | Emphasis intent | Authorize unsupported claims |
| TailoringPlan / CoverLetterPlan | Early claim inventory | Override missing profile evidence |
| Generated Markdown/HTML/PDF | **Validation target** | Evidence source |

Catalogue construction is deterministic and explainable. Missing catalogue entries mean missing evidence — not “unknown OK”.

---

## 10. Validation Lifecycle

```
1. Load artefact Markdown (+ optional plan inventory)
2. Build Candidate Evidence Catalogue from Career Profile
3. Detect claims (deterministic detectors)
4. Classify each claim (A/B/C/D); detect JD→candidate leakage patterns
5. For each material Class A claim:
     lookup catalogue → supported | unsupported | ambiguous | contradictory
6. Assign severity → aggregate TruthReport outcome
7. Persist TruthReport (sidecar store) with Markdown content hash
8. Gate: fail / review_required / stale blocks external use and FR-012 readiness
```

**Dual insertion points:**

- After generate (FR-006/007 / FR-010–011): advisory — early detection for owner UX.
- After owner Markdown edit: **authoritative** — trust gate before external use / submit.

Generation-time validation improves UX; post-edit Markdown validation is the trust gate.

---

## 11. Failure Behaviour

| Condition | Result | Behaviour |
|-----------|--------|-----------|
| Supported Class A claim | PASS finding | Continue |
| Unsupported material Class A | **FAIL** | Fail closed; block external-use gate |
| Ambiguous evidence (alias / partial match) | WARNING or FAIL per rule | Prefer FAIL when claim strength is high |
| Missing evidence | **FAIL** for Class A | Do not invent |
| Contradictory evidence | **FAIL** | Explain both sides |
| Class B correctly framed | PASS | |
| Class B misframed as candidate capability (Redwolf) | **FAIL** | JD leakage detector |
| Class C clear aspiration | PASS | |
| Class C implies expertise | WARNING or FAIL | |
| Detector uncertainty on material token | review_required or blocking | Do not “pass because unsure” |
| Stale content hash | **BLOCKED** | Revalidate after Markdown edit |

**Must not:** silently delete or rewrite claims; treat JD requirements as candidate evidence; use LLM as sole truth authority; replace owner review; auto-advance pipeline or submission state.

**Owner exceptions (design intent):** explicit, logged override on a named finding — never a global “skip truth validation” default. Default remains fail closed.

---

## 12. Owner Workflow (cic truth commands)

| Command | Purpose |
|---------|---------|
| `cic truth validate <markdown_path>` | Validate authoritative Markdown; optional persist |
| `cic truth show <report_path>` | Display a persisted TruthReport |
| `cic truth validate-package <opportunity_id>` | Validate CV + cover letter; write current reports |

Owner-visible fields: document path, outcome, coverage, blocking / review-required / supported findings, exact claim text, technology, evidence status, class, strength, detection certainty.

`--check-only` on `validate-package` evaluates freshness of stored reports without re-detecting (stale-hash gate).

**Correction workflow:**

```
Generate → Truth FAIL → Owner reviews exact finding
  → Owner edits Markdown → Render-only → Revalidate
  → Truth PASS → Owner verifies PDF → Submit (manual / assisted)
```

Validator never repairs or rewrites the document.

---

## 13. Package Integration

FR-010 `ApplicationPackageManifest` is unchanged (`extra=forbid`). Truth metadata lives in sidecars under `data/truth_reports/{opportunity_id}/`:

| Artefact | Role |
|----------|------|
| `{report_id}.json` | Immutable history |
| `current_cv_markdown.json` | Latest CV report pointer |
| `current_cover_letter_markdown.json` | Latest cover-letter report pointer |

| Question | Mechanism |
|----------|-----------|
| Which Markdown files were validated? | Report `artefact.path` + kind |
| Which report belongs to each document? | `current_{kind}.json` |
| Do current Markdown bytes still match? | SHA-256 content fingerprint |
| Is external use allowed? | `evaluate_package_truth` / `require_package_external_use` |

`cic package verify` evaluates the truth gate (BLOCKED without fresh passing reports).

External use requires every in-scope recruiter-facing Markdown document to have a current report with outcome ∈ {pass, warning}, complete coverage, performed detection and validation, no blocking findings, and matching content hash.

---

## 14. Submission Integration

`SubmissionOrchestrator` defaults `enable_truth_gate=True`:

- `check_readiness` soft-blocks on missing / stale / failing truth
- `submit` / manual completion hard-raise `SubmissionGateError` via `require_package_external_use`
- Owner approval remains mandatory
- `SubmissionAttempt` success remains separate from truth validation and FR-013 status
- Successful technical upload cannot bypass the truth gate

Legacy FR-012 unit helpers set `enable_truth_gate=False` only where they intentionally isolate pre-M3 submission mechanics; production CLI keeps the gate on.

FR-012 may consume TruthReport for readiness; it does not own truth policy.

---

## 15. Manual Validation Summary (M2/M3/M4 PASS)

| Script | Result | Key evidence |
|--------|--------|--------------|
| `scripts/run_fr014_truth_manual.py` (M2) | **PASS** | Redwolf fail; supported pass; employer-context pass. Artefact: `data/_fr014_m2_manual/redwolf_report.json` |
| `scripts/run_fr014_m3_manual.py` (M3) | **PASS** | Redwolf FAIL; corrected PASS; stale blocks; package FAIL on one bad document; submission Not Ready then Ready after revalidate. Workspace: `data/_fr014_m3_manual/` |
| `scripts/run_fr014_m4_manual.py` (M4) | **PASS** | Commercial AI fail; commercial software pass; independent pass; cert present/absent; years supported/overclaim/ambiguous; delivery supported/unresolved; domain supported/unsupported; Redwolf technology fail |

---

## 16. Test Summary

| Suite | Result |
|-------|--------|
| `tests/unit/truth_validation/` (M1–M4) | **PASS** — models, catalogue, detection, gates, CLI, extended claim kinds |
| `tests/functional/test_fr014_m2_truth_validation.py` | **PASS** |
| `tests/functional/test_fr014_m3_owner_workflow.py` | **PASS** |
| `tests/functional/test_fr014_m4_claim_validation.py` | **PASS** |
| FR-010/012 CLI regression (package verify + submission with truth seeded) | **PASS** |
| Focused package/submission/truth regression (M3 close-out) | **150 passed** |
| Focused M4 + prior FR-014 functional | **45+ passed** |

Key invariant tests: detection certainty ≠ evidence status; empty findings + no performed flags ≠ PASS; Class A cannot be supported by JD alone; unsupported Class A blocking; ambiguous detection severity; stale-hash gate; package external-use evaluation.

---

## 17. Technical Debt Classification

| Item | Class | Justification |
|------|-------|---------------|
| Advisory generate-time gate | **Deferred** | Dual-gate “after generate” remains optional advisory; authoritative gate is M3 post-edit. Wiring at compose time deferred to avoid scope creep. |
| Sidecar vs manifest | **Accepted** | Sidecars under `data/truth_reports/` avoid FR-010 manifest redesign; cross-linking by opportunity_id + kind is sufficient for single-user phase. |
| Unresolved delivery | **Accepted** | Delivery verbs without named projects → `review_required`; certain miss → blocking. Full NL resolution is out of scope. |
| Years / dates | **Accepted** | Years only when `supported_years` computable from profile dates; unknown tenure → review_required, not invented precision. |
| Education / identity | **Out of Scope** | No profile education section; identity/link crawling excluded by ADR-006 and M4 scope boundary. |
| Soft skills | **Out of Scope** | Subjective / motivational claims cannot be validated deterministically; excluded by design. |
| LLM judge | **Out of Scope** | Non-deterministic; can invent evidence; violates ADR-006. |
| Generate auto-invoke deferred | **Deferred** | Truth validation not auto-invoked at generation time in production path; owner runs `cic truth validate-package` explicitly. |
| WeasyPrint stub accepted | **Accepted** | Autouse stub when WeasyPrint missing in tests; real PDF tests still need the package. Does not affect truth boundary. |
| FR-015 consuming TruthReport | **Delivered (FR-015 frozen)** | BOPA may request `validate_truth_package` / stop on block; never waives ([ADR-007](../adr/007_bounded_agentic_workflow.md)). |

---

## 18. Risks Considered

| Risk | Mitigation |
|------|------------|
| False positives on employer-context tech mentions | Claim classification + framing detectors; Class B PASS path |
| False negatives on clever paraphrases | High-value detectors first; expand kinds by milestone; fail-closed on known leakage patterns |
| Alias / naming drift (`Node` vs `Node.js`) | Explicit alias table; ambiguous → WARNING/FAIL by strength |
| Historical vs current proficiency | Strength + recency rules; WARNING/FAIL for overclaim |
| Independent vs commercial employment | Employment kind in catalogue; M4 honesty matrix |
| Owner edits bypass generation-time checks | Mandatory post-edit Markdown validation + content hash |
| Scope creep into rewriting | Explicit non-goals; report-only remediation |
| Absorbing FR-003/006/007 | Service boundary table; ADR guardrails |
| Performance on long Markdown | Deterministic lexicon scan; no LLM; catalogue built once per run |
| Stale report authorizing submit | SHA-256 fingerprint; timestamps alone never authorize |

---

## 19. Lessons Learned (short pointer to retrospectives)

Detailed retrospective content is in §21–§22 below and in milestone records:

- [M0 spike §5 trade-offs](fr014_m0_engineering_spike.md) — why hybrid beat LLM / prompt-only / plan-only / regex-only
- [M2 §4 Redwolf before/after](fr014_m2_technology_validation.md) — technology validation proof
- [M3 §7 correction workflow](fr014_m3_owner_workflow.md) — operational gate proof
- [M4 §2 claim matrix](fr014_m4_claim_validation.md) — corpus-bounded breadth
- [Changelog v1.91](../11_changelog.md) — freeze record

---

## 20. Operational Readiness

| Capability | Status |
|------------|--------|
| `cic truth validate` / `show` / `validate-package` | Operational |
| Sidecar TruthReport persistence | Operational |
| Content-hash freshness | Operational |
| `cic package verify` truth gate | Operational |
| FR-012 submission truth gate (default on) | Operational |
| Manual validation scripts (M2/M3/M4) | PASS |
| Validator version pinned | `fr014-m4-deterministic-1` |
| Documentation frozen | This report + ADR-006 + functional spec |

Owner can operate the full correction loop: generate → validate → review findings → edit Markdown → revalidate → verify package → submit.

---

## 21. Engineering Retrospective

### What worked

- Hybrid catalogue → detection → validator kept explainability high and aligned with CIC’s deterministic-first style.
- Separating detection certainty from evidence status prevented false PASS when detectors were uncertain.
- Sidecar TruthReports avoided redesigning FR-010 manifests while preserving audit history.
- Content-hash freshness beat timestamp-based authorization — owner edits immediately invalidate stale reports.
- Commercial honesty rules aligned with FR-003 employment kinds and real corpus patterns.

### What surprised / proved difficult

- Years of experience without complete dates must not be estimated — fail-closed / review_required is correct but requires owner patience.
- Delivery verbs without named projects are inherently ambiguous; unresolved → review_required is the honest outcome.
- Lexicon pollution (domains/certs in technology scan) required kind filtering in M4.
- False-positive bare keywords vs material Class A framing required explicit ignore rules.

### Why deterministic validation was chosen

Soft prompt rules did not stop Redwolf leakage. An LLM-as-judge would blur explainability, vary run-to-run, and invite silent “fixes.” Deterministic, fail-closed findings give the owner exact claim text, evidence status, and remediation while preserving human review.

### Why prompts alone are insufficient

Planners and composers see JD stack terms as attractive emphasis. Soft constraints regress, do not cover owner Markdown edits, and provide no explainable gate for FR-012. Redwolf proved employer-evidence → candidate-evidence leakage survives generation-time prompt discipline.

### Why Markdown is the primary surface

Owner edits Markdown then render-only refreshes HTML/PDF. Validating only pre-edit generation misses defects after correction attempts and accidental reintroduction. Validating PDF is brittle and late. Markdown is the owner-editable SoT.

### Lessons for future recruiter-facing artefacts

- Validate the authoritative Markdown bytes the owner can edit.
- Never treat JD requirements as candidate evidence.
- Gate external use on fresh reports, not generation-time PASS alone.
- Prefer `review_required` over invented precision.
- Extend claim kinds only with corpus justification — not as a general NL fact checker.

### What changed for FR-015 (now complete)

- FR-015 BOPA **consumes** TruthReport findings via `validate_truth_package` / stop on
  block and must not bypass or weaken the gate ([ADR-007](../adr/007_bounded_agentic_workflow.md)).
- Automation increase beyond FR-015 still requires explicit owner request and must
  preserve fail-closed external-use semantics.
- Agent loops treat blocking findings as hard stop conditions, not prompt hints.

---

## 22. Dogfooding Retrospective

| Experience | Architecture influence |
|------------|------------------------|
| **Redwolf cover letter** | Motivated entire FR-014; proved JD→candidate leakage is real, not theoretical; drove Class A/B framing detectors and fail-closed policy |
| **Markdown editing** | Confirmed Markdown as primary validation surface; owner correction loop (edit → revalidate) is the operational path, not validator rewrite |
| **Hash freshness** | Owner edits after validation immediately stale reports; timestamp-only authorization would have been unsafe |
| **Package blocking** | `cic package verify` truth gate prevents “looks ready” packages with unsupported claims; sidecar design preserves FR-010 manifest stability |
| **Submission blocking** | FR-012 readiness/submit hard-gate ensures no assisted or manual completion bypasses truth validation; separates SubmissionAttempt success from truth policy |

Redwolf remains the regression anchor: Python supported, TypeScript/Vue blocking, outcome `fail`.

---

## 23. Recruiter-Facing Production Workflow confirmed

```
Job Analysis
  → Opportunity Assessment
  → Portfolio Match
  → Application Strategy
  → CV Generation
  → Cover Letter Generation
  → Truth Validation          ← FR-014 deterministic gate
  → Owner Review
  → (optional) Markdown Edit → Truth Validation again
  → Render
  → Submission
  → Pipeline Tracking
```

Truth Validation assists owner judgment; it does not replace owner review. FAIL blocks external use and submission readiness until Markdown is corrected and revalidated.

---

## 24. Definition of Done (met checklist)

- [x] Architecture accepted (M0) and ADR-006 accepted (M1)
- [x] Technology validation + Redwolf blocked (M2)
- [x] Owner CLI + package/submission gates (M3)
- [x] Expanded deterministic claim kinds justified by profile evidence (M4)
- [x] Manual matrices PASS (M2/M3/M4)
- [x] Unit + functional regression green
- [x] Documentation updated and FR frozen
- [x] No rewriting; owner review mandatory
- [x] No future FR (FR-015) started without owner request *(historical at FR-014 freeze; FR-015 later completed under owner request)*
- [x] Validator version pinned (`fr014-m4-deterministic-1`)

---

## 25. Final Acceptance Recommendation

**Accept FR-014 as complete and frozen.**

Recruiter Document Truth Validation delivers the deterministic fail-closed trust boundary required before any increase in application automation. Unsupported material candidate claims are blocked from external use and FR-012 submission with explainable findings. Owner review remains mandatory.

Next Horizon 1A work after FR-014 was **FR-015 Bounded Agentic Workflow**, which is
now **complete and frozen**
([fr015_bounded_agentic_workflow.md](fr015_bounded_agentic_workflow.md)).
**Active FR:** **FR-016** Multi-Agent Orchestration (not started — owner request
required). Do not increase automation without the FR-014 gate remaining in force.

---

## 26. Final Repository Status

| Item | Status |
|------|--------|
| FR-014 Recruiter Document Truth Validation | **Complete and frozen** |
| FR-015 Bounded Agentic Workflow | **Complete and frozen** |
| FR-016 Multi-Agent Orchestration | **Active FR — not started** (owner request required) |
| Package | `career_intelligence.truth_validation` |
| Validator version | `fr014-m4-deterministic-1` |
| ADR | [ADR-006](../adr/006_recruiter_document_truth_validation.md) (Accepted) |
| Milestones | M0–M4 complete — see links in header |

Do not reopen FR-014 exit criteria without explicit owner request.
