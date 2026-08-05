# FR-014 — Recruiter Document Truth Validation

**Status:** Planned (not started)  
**Phase:** Horizon 1A Stage 8  
**Date recorded:** 2026-08-05  
**Identifier note:** FR-013 remains **Application Pipeline Tracking** (unchanged).
This FR is inserted immediately afterwards.

This is a **planning and Definition of Done** record. Implementation has not
started. Do not treat this file as an acceptance report.

---

## 1. Purpose

Prevent unsupported, misleading, or incorrectly framed **candidate** claims from
reaching recruiter-facing CVs, cover letters, application answers, or future
semi-automated / automated submissions.

**Core principle:** Every material first-person candidate claim must be supported
by approved profile, employment, certification, project, or application evidence.

This is a **deterministic factual trust boundary**.

It is **not**:

- grammar checking
- writing-quality improvement
- prompt optimisation

Owner review remains mandatory. Truth validation does **not** replace owner review.

---

## 2. Problem statement (motivating defect)

During owner review of a Redwolf cover letter, CIC produced:

> “Roles centred on Python, TypeScript, and Vue are where I do my best
> engineering work.”

- **Python** was supported by the career profile.
- **TypeScript** and **Vue** were taken from the job description and framed as
  candidate capability without sufficient profile evidence.

This is an **evidence-boundary failure**: employer/JD evidence was allowed to
become candidate evidence. That class of defect is a material trust risk before
any increase in application automation.

---

## 3. Architecture intent

```
Planner
  → Composer
  → Recruiter Document Truth Validation   ← FR-014
  → Markdown
  → HTML
  → PDF
  → Owner Review
  → (optional) Owner Markdown edit → Render-only → Verify
  → Submission (FR-012)
```

Exact insertion points (pre-Markdown vs post-Markdown vs package/submission gate)
are decided by the engineering spike. Validation must run before recruiter-facing
artefacts are approved for submission. Manually edited Markdown must also be
validatable.

Related owner artefact workflow (already shipped):
[Document Rendering](../08_implementation_notes.md#document-rendering-render-only).

---

## 4. Roadmap dependency

| Rule | Meaning |
|------|---------|
| FR-013 identifier unchanged | Application Pipeline Tracking stays FR-013 |
| FR-014 inserted next | Recruiter Document Truth Validation |
| Automation gate | **FR-014 must be accepted before any future work that increases application automation or reduces owner review** |

FR-013 may proceed as the established next pipeline milestone. FR-014 is the
safety prerequisite before automation scales.

---

## 5. Claim classification

| Class | Examples | Evidence rule |
|-------|----------|---------------|
| **A. Candidate claims** | “I build with FastAPI.”; “I am strongest in Vue.” | Require candidate evidence |
| **B. Employer-context** | “The role uses TypeScript and Vue.” | JD evidence OK; must **not** become candidate capability |
| **C. Aspirational / transition** | “I am interested in expanding into Vue.” | Must stay truthful; must not imply existing expertise |
| **D. Judgement / motivation** | “I am drawn to AI + workflow orchestration.” | May not need skill evidence; must not misrepresent facts |

---

## 6. Initial validation scope

1. Technology and framework claims
2. Experience-duration claims
3. Employment claims (never equate independent work with commercial employment without evidence)
4. Certification and education claims
5. Domain claims
6. Project and delivery claims
7. Recruiter vs employer attribution
8. Links and identity facts

---

## 7. Engineering spike (required before implementation)

Investigate at least:

- where candidate claims are currently created
- whether claims can carry provenance from planner/composer inputs
- deterministic extraction of first-person claims
- candidate-evidence catalogue design
- exact vs alias technology matching
- current/recent vs historical proficiency
- claim-strength distinctions: used / experienced / proficient / strongest / expert
- validation of generated **and** manually edited Markdown
- Application Package and FR-012 submission-gate integration
- truth-report persistence
- validate before vs after HTML/PDF render
- owner-approved exceptions without weakening the default rule

Prefer the smallest deterministic, explainable architecture justified by evidence.
Do not prescribe a large NLP or LLM solution prematurely.

---

## 8. Manual validation matrix (acceptance)

| Scenario | Expected |
|----------|----------|
| Redwolf-style unsupported TypeScript/Vue candidate claim | **FAIL** / blocked |
| Supported Python / FastAPI candidate claims | **PASS** |
| Historical Flask not framed as current expertise | Pass or warning per rules; must not overclaim |
| Independent AI work not framed as commercial AI employment | **FAIL** if overclaimed |
| Correct commercial Data Engineering duration | **PASS** |
| Unknown certification | **FAIL** |
| Employer technology mention remains employer-context | **PASS** |
| Manually edited Markdown validated | Supported |
| Recruiter vs direct-employer voice distinguished | Supported |

---

## 9. Definition of Done (FR-008 onward standard)

| Criterion | Status |
|-----------|--------|
| Engineering spike report | Planned |
| Accepted architecture decision (ADR or recorded decision) | Planned |
| Typed models / contracts | Planned |
| Unit tests | Planned |
| Functional tests | Planned |
| Repeatable manual validation (matrix above) | Planned |
| Acceptance report | Planned |
| Documentation updates | Planned (this planning record) |
| Changelog and roadmap updates | Planned |
| Owner review | Planned |
| DoD checklist complete at close-out | Planned |

---

## 10. Numbering note

FR-013 remains Application Pipeline Tracking. Former FR-014+ (bounded agents and
later) shift by one after this insertion. See [11_changelog.md](../11_changelog.md)
§ 1.84.
