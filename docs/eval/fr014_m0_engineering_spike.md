# FR-014 M0 — Recruiter Document Truth Validation Engineering Spike

**Status:** **Accepted** (owner 2026-08-05)  
**Date:** 2026-08-05  
**Phase:** Horizon 1A Stage 8  
**ADR:** [ADR-006](../adr/006_recruiter_document_truth_validation.md) (Accepted at M1)  
**Succeeded by:** [FR-014 M1 contracts](fr014_m1_truth_validation_contracts.md)  
**Scope (M0):** Architecture only. No production implementation in this milestone.  
**Planning record:** [fr014_recruiter_document_truth_validation.md](fr014_recruiter_document_truth_validation.md)  
**Preceding capability:** [FR-013 Application Pipeline Tracking](fr013_application_pipeline_tracking.md)
(complete and frozen).  
**Builds on:** FR-006 / FR-007 document generation; FR-010 package; render-only;
FR-012 submission; Career Profile public boundary ([ADR-001](../adr/001_python_yaml_profile_foundation.md)).

---

## 1. Executive Summary

Prompt quality and owner review alone are **not** a sufficient trust boundary for
recruiter-facing documents. A real dogfooding defect (Redwolf) framed Job Description
technologies (TypeScript, Vue) as candidate capability. The owner caught it before
submit — that luck must not remain the control plane before automation increases.

**Recommended architecture:** a dedicated **deterministic Truth Validation** layer that:

1. Builds a **Candidate Evidence Catalogue** from the Career Profile (and other
   *candidate-owned* approved facts).
2. Detects **structured factual claims** in recruiter-facing artefacts (initially CV
   and Cover Letter Markdown).
3. Classifies each claim (candidate capability vs employer-context vs aspiration vs
   judgement).
4. Validates candidate claims against the catalogue with **explainable findings**.
5. **Fails closed** on material unsupported candidate claims.
6. Surfaces a **TruthReport** to the owner — never silently rewrites prose.

Truth Validation **validates**. It does not generate, rewrite, score fit, rank
portfolio, advance pipeline status, or submit.

**Proposed ADR (on M1 acceptance):** ADR-006 — Recruiter Document Truth Validation
(deterministic fail-closed boundary; JD evidence ≠ candidate evidence).

---

## 2. Problem Statement

CIC already produces recruiter-facing CV and cover-letter Markdown/HTML/PDF via
planner → composer → render, with mandatory owner review. Existing fidelity checks
(e.g. company / role / project mentioned) do **not** enforce
**candidate-evidence ↔ candidate-claim** integrity.

Failure mode:

| What happened | Why it is dangerous |
|---------------|---------------------|
| JD stack terms entered cover-letter prose | Employer requirements are abundant and attractive to planners/composers |
| Prose framed them as “where I do my best engineering work” | Converts employer evidence into candidate capability |
| Prompt rules did not catch it | Soft constraints are non-deterministic and incomplete |
| Owner review caught it once | Does not scale; automation increases blast radius |

**Engineering question:** What is a factual claim, how is it represented, and how is
it validated deterministically without becoming another LLM pass?

---

## 3. Motivating Example (Redwolf)

Generated cover letter (paraphrased from owner review):

> “Roles centred on Python, TypeScript, and Vue are where I do my best
> engineering work.”

| Token | Status |
|-------|--------|
| Python | Supported by Career Profile |
| TypeScript | Present in JD; **not** supported as candidate capability |
| Vue | Present in JD; **not** supported as candidate capability |
| Framing (“best engineering work”) | Claim strength = proficiency / preference-as-expertise |

**Classification:** Class A candidate technology claims (TypeScript, Vue) with
insufficient candidate evidence — **must FAIL closed**.

**Not the defect:** Merely mentioning that the *role* uses TypeScript/Vue
(employer-context) would be Class B and may PASS if phrasing does not imply
candidate capability.

---

## 4. Alternative Architectures

### A. LLM truth-check pass

Run another model over the letter asking “are claims true?”

- **Pros:** Handles free prose flexibly.
- **Cons:** Non-deterministic; can invent evidence; becomes prompt optimisation;
  violates “not another LLM pass / not sole truth authority”. **Reject as primary.**

### B. Prompt / planner hardening only

Tighten FR-006/007 prompts and composer bans; no separate validator.

- **Pros:** Cheap; may reduce recurrence.
- **Cons:** Already insufficient (Redwolf); soft rules regress; owner edits bypass
  planners; no explainable gate for FR-012. **Reject as sole control.**

### C. Plan-field validation only

Validate TailoringPlan / CoverLetterPlan structured fields before compose; skip
Markdown.

- **Pros:** Typed; early fail; cheap.
- **Cons:** Misses free prose composition; misses owner Markdown edits; Redwolf
  often appears in *composed* sentences, not only plan enums. **Insufficient alone.**

### D. Markdown regex / keyword scanner only

Scan Markdown for technology tokens vs profile skill list.

- **Pros:** Simple; works on owner-edited text.
- **Cons:** High false positives on employer-context; no claim-strength; no
  employment/duration/cert classes; brittle. **Useful detector, not full architecture.**

### E. Provenance-annotated composition (claims emitted with prose)

Composer emits structured `Claim[]` alongside Markdown; validator checks claims only.

- **Pros:** Precise for generated content; explainable.
- **Cons:** Owner Markdown edits can introduce untracked claims; requires composer
  redesign; incomplete unless Markdown is also scanned. **Strong complement, not sole.**

### F. Hybrid (recommended) — Evidence Catalogue + Claim Detection + Deterministic Validator + TruthReport

1. Build **Candidate Evidence Catalogue** from authoritative candidate sources.
2. Detect / classify **Claims** from artefact text (and optionally from plans).
3. Validate each material candidate claim against the catalogue.
4. Emit **TruthReport** with PASS / WARNING / FAIL findings.
5. Gate owner workflow / submission on FAIL (fail closed).
6. Never rewrite the document.

---

## 5. Trade-off Analysis

| Concern | A LLM | B Prompt only | C Plan only | D Regex only | E Annotated compose | **F Hybrid** |
|---------|-------|---------------|-------------|--------------|---------------------|--------------|
| Deterministic | No | Partial | Yes | Yes | Yes | **Yes** |
| Catches Redwolf prose | Maybe | Unreliable | Partial | Often | If emitted | **Yes** |
| Owner-edited Markdown | Maybe | No | No | Yes | No alone | **Yes** |
| Explainable findings | Weak | Weak | Strong | Medium | Strong | **Strong** |
| Extensible artefact types | Yes | No | No | Medium | Medium | **Yes** |
| Implementation cost | Medium | Low | Low | Low | High | **Medium** |
| Fits CIC trust style | No | Weak | Yes | Partial | Yes | **Yes** |

**Conclusion:** Prefer **F**. Use plan-level checks and annotated claims later as
*accelerators*, not replacements for Markdown validation.

---

## 6. Recommended Architecture

```
Career Profile (+ candidate-owned facts)
        │
        ▼
Candidate Evidence Catalogue   ← build once per validation run
        │
Artefact under test            ← CV / Cover Letter Markdown (primary)
(optional: TailoringPlan / CoverLetterPlan claim inventory)
        │
        ▼
Claim Detection & Classification
        │
        ▼
Deterministic Claim Validator
        │
        ▼
TruthReport  (findings + overall PASS | WARNING | FAIL)
        │
        ▼
Owner surfaces / gates (review, package verify, FR-012 readiness)
```

| Component | Responsibility |
|-----------|----------------|
| `CandidateEvidenceCatalogue` | Normalised, queryable candidate facts (skills, employment, projects, certs, education, identity, aliases) |
| `Claim` | Structured representation of a factual assertion found in (or planned for) an artefact |
| `ClaimDetector` | Deterministic extraction/classification from Markdown (and optional plan inventory) |
| `TruthValidator` | Evidence lookup + severity rules; fail-closed policy |
| `TruthReport` | Explainable results; never mutates the artefact |
| Owner CLI / gates | Thin presentation + block on FAIL where configured |

**Public package (proposed):** `career_intelligence.truth_validation`  
**Does not own:** generation, rendering, package composition, submission, pipeline status.

---

## 7. Trust Boundary

### In scope (initial)

| Artefact | Why |
|----------|-----|
| Tailored CV Markdown | Recruiter-facing; owner-editable SoT |
| Cover Letter Markdown | Motivating defect surface; owner-editable SoT |

HTML/PDF are **derived presentations**. Validate Markdown (and optionally structured
plan inventories). Do not treat PDF text extraction as the primary validator input.

### Explicitly out of initial implementation scope (design for compatibility)

| Future artefact | Compatibility approach |
|-----------------|------------------------|
| Application form answers | Same Claim + Catalogue + TruthReport; new artefact adapter |
| Recruiter / LinkedIn / networking messages | Same; Horizon 1B surfaces |
| Interview prep talking points | Same; Horizon 2 |
| Package manifest as a whole | Aggregate TruthReports per contained Markdown |

### What the boundary is *not*

- Writing improvement, grammar, tone, or style
- Fit scoring (FR-003), portfolio ranking (FR-004), strategy (FR-005)
- Document generation (FR-006/007) or package composition (FR-010)
- Submission mechanics (FR-012) or pipeline lifecycle (FR-013)
- Silent deletion or auto-rewrite of claims

### Hard invariant

**Job Description / employer evidence must never authorize candidate capability claims.**

---

## 8. Claim Model

### What is a factual claim?

A **factual claim** is an assertion that a reader could reasonably treat as an
objective statement about the **candidate**, the **employer/role**, or a **project
outcome** — not mere preference language.

| Class | Name | Examples | Validation |
|-------|------|----------|------------|
| **A** | Candidate objective claim | “I have commercial AI experience.”; “I built…”, “I implemented…”, “I am proficient in Vue.” | **Must** be supported by candidate evidence |
| **B** | Employer / role context | “The role uses TypeScript and Vue.”; “Your team works in Vue.” | JD/role evidence OK; **must not** be phrased as candidate capability |
| **C** | Aspiration / transition | “I am interested in expanding into Vue.” | Must not imply existing expertise; usually PASS with correct framing |
| **D** | Judgement / motivation | “I am drawn to AI + workflow orchestration.” | No skill evidence required; must not smuggle Class A facts |

Only **Class A** (and Class B misframed as A) produce material **FAIL** outcomes.
Class C/D may **WARNING** if framing is ambiguous.

### Proposed structured claim fields

| Field | Role |
|-------|------|
| `claim_id` | Stable id within a report |
| `claim_class` | A / B / C / D |
| `claim_kind` | technology, employment, duration, certification, education, domain, project_delivery, identity, other |
| `subject` | `candidate` \| `employer` \| `role` \| `project` |
| `predicate` | e.g. `has_skill`, `has_employment`, `delivered`, `holds_cert` |
| `object` | Normalised object (e.g. technology key `vue`, employer name) |
| `strength` | `mentioned` \| `used` \| `experienced` \| `proficient` \| `strongest` \| `expert` \| `interested` |
| `surface_text` | Exact excerpt from artefact |
| `source_artefact` | `cv_markdown` \| `cover_letter_markdown` \| `tailoring_plan` \| … |
| `span` | Optional location hint (paragraph / section) |

### Claim-strength rule (technology)

Higher strength requires stronger / more recent evidence. Example policy (M1+ refine):

| Strength | Evidence bar |
|----------|--------------|
| `interested` | Aspiration OK without skill evidence |
| `used` / `experienced` | Skill or project/experience evidence |
| `proficient` / `strongest` / `expert` | Explicit skill evidence; historical-only skills → WARNING or FAIL if framed as current |

---

## 9. Evidence Model

### Authoritative candidate evidence (may support Class A)

| Source | Use |
|--------|-----|
| **Career Profile** (via `career_intelligence.profile`) | Primary SoT: skills, experience, projects, education, certifications, identity, summary |
| Profile-linked project / experience metadata | Delivery claims, tech via `demonstrates` / skill refs |
| Owner-approved identity / contact facts | Links, name, location as represented in profile |

### Context only — never candidate-capability authorization

| Source | Allowed use | Forbidden use |
|--------|-------------|---------------|
| Job Analysis / JD technologies | Classify employer-context; detect JD→candidate leakage | Authorize “I know X” |
| Opportunity Assessment | Understand gaps for WARNING copy | Invent candidate skills |
| Portfolio Match | Confirm project was selected for emphasis | Invent project capabilities not in profile |
| Application Strategy | Emphasis intent | Authorize unsupported claims |
| TailoringPlan / CoverLetterPlan | Early claim inventory; expected emphasis | Override missing profile evidence |
| Generated Markdown/HTML/PDF | **Validation target** | Evidence source |

### Candidate Evidence Catalogue (derived)

Normalised indexes proposed for M1:

- Technology / skill keys + aliases (e.g. `js` → `javascript`)
- Employment entries (employer, dates, kind: commercial vs independent/portfolio)
- Project ids + demonstrated capabilities
- Certifications / education
- Duration facts derivable from profile (commercial years, etc.)
- Identity facts

Catalogue construction is **deterministic and explainable**. Missing catalogue entries
mean missing evidence — not “unknown OK”.

---

## 10. Validation Lifecycle

```
1. Load artefact Markdown (+ optional plan inventory)
2. Build Candidate Evidence Catalogue from Career Profile
3. Detect claims (deterministic detectors + optional plan claims)
4. Classify each claim (A/B/C/D); detect JD→candidate leakage patterns
5. For each material Class A claim:
     lookup catalogue → supported | unsupported | ambiguous | contradictory
6. Assign severity → aggregate TruthReport status
7. Persist / present TruthReport (M2+/M3)
8. Gate: FAIL blocks FR-012 readiness / package “ready for external use”
   (exact wiring in M3; owner review remains mandatory either way)
```

### Recommended validation surface

| Surface | Role |
|---------|------|
| **Markdown** | **Primary** — generation output and owner-edit SoT |
| Structured plans | Optional early gate at compose time |
| HTML / PDF | Not primary; derived; validate before render when possible |

**Rationale:** Owner edits Markdown then render-only refreshes HTML/PDF. Validating only
pre-edit generation misses the Redwolf class after correction attempts and after
accidental reintroduction. Validating PDF is brittle and late.

### Dual insertion points (recommended)

```
Generate (FR-006/007 / FR-010–011)
    ↓
Truth Validation (generation-time advisory or soft gate)     ← early detection
    ↓
Owner Review
    ↓
Optional Markdown Edit
    ↓
Truth Validation (mandatory before external use / submit)  ← authoritative gate
    ↓
Render Only (if needed)
    ↓
Verify
    ↓
Submit (FR-012) — readiness may require latest TruthReport = not FAIL
```

Generation-time validation improves UX; **post-edit Markdown validation** is the
trust gate. Exact CLI/package/submission hooks are M3.

---

## 11. Failure Semantics

| Condition | Result | Behaviour |
|-----------|--------|-----------|
| Supported Class A claim | PASS finding | Continue |
| Unsupported material Class A | **FAIL** | Fail closed; block external-use gate |
| Ambiguous evidence (alias / partial match) | **WARNING** or **FAIL** per rule | Prefer FAIL when claim strength is high (`proficient`+) |
| Missing evidence | **FAIL** for Class A | Do not invent |
| Contradictory evidence | **FAIL** | Explain both sides |
| Class B correctly framed | PASS | |
| Class B misframed as candidate capability (Redwolf) | **FAIL** | JD leakage detector |
| Class C clear aspiration | PASS | |
| Class C implies expertise | WARNING or FAIL | |
| Class D motivation only | PASS | |
| Detector uncertainty | WARNING + fail-closed on material tech tokens unmatched to catalogue when framed as capability | Do not “pass because unsure” |

**Must not:**

- Silently delete or rewrite claims
- Treat JD requirements as candidate evidence
- Use LLM as sole truth authority
- Replace owner review
- Auto-advance pipeline or submission state

**Owner exceptions (design intent, M3/M4):** explicit, logged override on a named
finding — never a global “skip truth validation” default. Default remains fail closed.

---

## 12. Owner Workflow

Documented end-to-end path after FR-014:

```
Opportunity
  → Assessment
  → Strategy
  → Application Package (CV + Cover Letter)
  → Truth Validation          ← NEW deterministic gate
  → Owner Review
  → (optional) Markdown Edit → Truth Validation again
  → Render
  → Manual / Assisted Submission
  → Pipeline Tracking
  → Reporting / Operational History
```

| Stage | Truth Validation role |
|-------|------------------------|
| After generate | Surface findings early |
| After owner edit | Re-validate Markdown (authoritative) |
| Before submit | FAIL blocks readiness |
| Owner review | Still mandatory; TruthReport assists judgment |

Owner experience should show: claim text, class/kind, evidence found or missing,
severity, recommended action (edit claim / add profile evidence / reframe as
employer-context / aspiration).

---

## 13. Service Boundaries

| Capability | Owns | Does not own |
|------------|------|--------------|
| FR-003 Assessment | Fit judgments + dual evidence refs | Recruiter prose truth |
| FR-004 Portfolio Match | Project ranking | Authorizing skills not in profile |
| FR-005 Strategy | Posture / tier / next actions | Document claims |
| FR-006 / FR-007 | Plan + compose + render documents | Truth gate |
| FR-010 / FR-011 | Package composition / orchestration | Claim validation rules |
| Render-only | Markdown → HTML/PDF | Validation |
| FR-012 | Submission assistance + attempt audit | Truth policy (may *consume* TruthReport) |
| FR-013 | Pipeline lifecycle | Document claims |
| **FR-014 Truth Validation** | Catalogue, claims, validation, TruthReport, gates | Generation, rewrite, scoring, submit, pipeline |

**Write boundaries:**

- Truth Validation may persist TruthReports (proposed under
  `data/truth_reports/{opportunity_id}/` or beside package artefacts — decide at M1).
- It must not mutate Career Profile, Opportunity status, packages, or SubmissionAttempts.
- It must not call OpenAI as the validator of record.

---

## 14. Risks

| Risk | Mitigation |
|------|------------|
| False positives on employer-context tech mentions | Claim classification + framing detectors; Class B PASS path |
| False negatives on clever paraphrases | Start with high-value detectors (tech + strength verbs); expand kinds by milestone; keep fail-closed on known leakage patterns |
| Alias / naming drift (`Node` vs `Node.js`) | Explicit alias table in catalogue; ambiguous → WARNING/FAIL by strength |
| Historical vs current proficiency | Strength + recency rules; WARNING/FAIL for overclaim |
| Independent vs commercial employment | Employment kind in catalogue; Redwolf-adjacent matrix case |
| Owner edits bypass generation-time checks | Mandatory post-edit Markdown validation |
| Scope creep into rewriting | Explicit non-goals; report-only remediation |
| Absorbing FR-003/006/007 | Service boundary table; ADR guardrails |
| Performance on long Markdown | Deterministic lexicon scan; no LLM; catalogue built once per run |

---

## 15. Future Compatibility

Design Claims / Catalogue / TruthReport / artefact adapters so new surfaces plug in:

| Future surface | Adapter need |
|----------------|--------------|
| Application answers | Text → Claim[] |
| Recruiter email / LinkedIn DM | Message body → Claim[] |
| Networking messages | Same |
| Interview prep notes | Same |
| Multi-document package | Aggregate reports |

No Horizon 1B/2 implementation in FR-014. Extensibility is structural only.

---

## 16. Recommended M0–M4 Milestones

| Milestone | Intent | Deliverables | Exit |
|-----------|--------|--------------|------|
| **M0** | Engineering spike | This document; owner accept/reject architecture | Architecture accepted |
| **M1** | Contracts + ADR-006 | `Claim`, catalogue model, TruthReport schema, detector/validator interfaces, append-only report store sketch, unit tests for models; **no** full detectors | Contracts frozen |
| **M2** | Core deterministic validation | Technology claim detection + JD→candidate leakage (Redwolf); catalogue from profile; TruthValidator; fixture matrix; functional tests | Redwolf FAIL / Python PASS |
| **M3** | Owner workflow & gates | Thin `cic truth` (or equivalent); validate CV/CL Markdown; integrate advisory/mandatory gates with package verify / FR-012 readiness; owner exception logging design | Owner-operable gate |
| **M4** | Breadth + freeze | Add broader claim kinds **only where deterministic validation is justified by corpus evidence** (not a general NL fact checker); manual matrix; acceptance freeze; docs | FR-014 ACCEPTED |

**Explicit non-goals across milestones:** rewriting, grammar, LLM-as-judge, prompt
retuning as the primary fix, FR-015 agents, Horizon 1B messaging.

---

## 17. Definition of Done (FR-014 overall — planned)

| Criterion | M0 expectation |
|-----------|----------------|
| Engineering spike report | **This document** |
| Architecture accepted by owner | Pending |
| ADR recorded | M1 (proposed ADR-006) |
| Typed models / contracts | M1 |
| Unit + functional tests | M1–M4 |
| Manual validation matrix | M2–M4 (see planning record) |
| Owner workflow / gates | M3 |
| Acceptance report + docs freeze | M4 |
| No implementation in M0 | **Held** |

### M0 exit criteria

✓ Problem and Redwolf motivation recorded  
✓ Alternatives compared; hybrid recommended  
✓ Trust boundary, claim model, evidence model defined  
✓ Validation lifecycle and fail-closed semantics defined  
✓ Owner workflow insertion points recommended  
✓ Service boundaries vs FR-003–007 / 012 / 013 clear  
✓ M0–M4 milestones proposed  
✓ No parser/validator/prompt/code changes in this milestone  

---

## Recommendation for owner acceptance

**Status:** **Accepted** (owner 2026-08-05) — hybrid architecture approved, including
Markdown primary surface, dual gates, fail-closed external-use gating, no silent
rewrite, mandatory owner review, and JD/assessment/strategy/plans never authorizing
candidate capability.

Proceed to **M1 contracts + ADR-006**.

---

*End of FR-014 M0 engineering spike. No implementation included.*
