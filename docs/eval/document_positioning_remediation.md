# Document Positioning & Generalisation Remediation

**Status:** **M0 complete — pending owner review before M1**  
**Date opened:** 2026-08-20  
**Not a new FR.** Production-path change inside existing FR-006 / FR-007 / FR-010 /
FR-014 boundaries. Frozen FR-008–FR-018 exit criteria are not reopened.

**Owner-approved CV positioning surface:** bounded LLM over a verified evidence
pack (same production pattern as the cover letter). FR-006c theme-aware
composition is **not** the production fix.

**Next:** M1 PositioningPlan contract — only after explicit owner approval of M0.

M0 audit: [document_positioning_m0_audit.md](document_positioning_m0_audit.md)  
M0 learning note: [document_positioning_m0_learning.md](document_positioning_m0_learning.md)

Historical close-out that this programme does **not** rewrite:
[document_quality_remediation.md](document_quality_remediation.md).

---

## 1. Problem

CIC currently produces documents that are factually conservative and Master-CV
shaped. They are not reliably the strongest truthful application available from
verified evidence across materially different jobs.

Target: **strongest truthful positioning**, competitive with a strong
evidence-constrained LLM, while retaining CareerProfile authority, Master factual
prose, FR-014, provenance, and owner review.

CSK (`opp_01M0E6GQ9XQH9DK9N5T0MS67N0`) exposed the gap. It is **one evaluation
case**, not a design target. Do not add CSK-specific production rules.

---

## 2. Approved architecture (unchanged by M0)

```
Verified Career Evidence
        ↓
Job / Employer Needs
        ↓
Evidence Selection (deterministic PositioningPlan)
        ↓
Bounded Document Generation (LLM expresses packed claims only)
        ↓
FR-014 Truth Validation
        ↓
Recruiter-quality preference evaluation
        ↓
Owner review
```

Deterministic vs bounded LLM (locked):

| Stage | Mode |
|-------|------|
| Factual authority | DETERMINISTIC (CareerProfile + Master facts) |
| Capability classification | DETERMINISTIC (catalogue) |
| Evidence selection / argument spine | DETERMINISTIC (PositioningPlan — M1) |
| CV summary / highlight selection / optional project relevance line | BOUNDED LLM over CV pack (M3) |
| Employment bullets / project bodies | DETERMINISTIC (Master) |
| Cover-letter prose | BOUNDED LLM over letter pack (M4) |
| Factual validation | DETERMINISTIC (FR-014) |
| Quality evaluation | HYBRID (Truth + human preference vs LLM baseline) |

If the bounded LLM fails: **fail closed**. Do not silently paste the Master
summary or the legacy deterministic letter and call it equivalent.

---

## 3. M0 plan corrections (repository vs approved plan)

These are documentation corrections, not product-direction changes.

1. **Truth is not inside `cic package prepare`.** Prepare writes drafts and the
   manifest. FR-014 runs via `cic truth validate-package` /
   `evaluate_package_truth` (and FR-015 agent `validate_truth_package`). Bounded
   cover-letter `compose()` does not call Truth; `assess_truth()` is a separate
   method. M5 still requires Truth PASS before preference scoring.
2. **CSK pipeline JSON under `data/opportunities/artifacts/` is gitignored.**
   The tracked freeze is
   `tests/fixtures/document_positioning/eval_jobs/02_csk_mixed_fit/`.
3. **Do not switch FR-006c on.** Confirmed: `_resolve_summary` returns
   `master_baseline` when `adapt_from_master=True`; `compose_theme_aware_summary`
   is skipped.
4. **OIC drop from the letter is a designed 2-project cap**, not an accidental
   ranking bug. M4 must change the selection rule.
5. **Catalogue v1 is not a drop-in for `_RELATED_CAPABILITY_GROUPS`.** The
   production Azure group also includes Microsoft Fabric and other pipeline
   phrases. M2 must not shrink those live planner relations.

---

## 4. PositioningPlan terminology (frozen for M1)

Design-level only. No Pydantic PositioningPlan in the package yet.

**EmployerNeed** — one ordered hiring requirement from JobAnalysis (technology,
responsibility, or experience requirement). Needs are employer evidence, not
candidate claims.

**CapabilityIdentity** — canonical name in the v1 catalogue (for example `rag`,
`aws`, `aws_bedrock`). Recruiter phrasing is not the identity.

**CapabilityRelation** — explicit allowed link: a *requested* identity may be
supported by a *different* profile identity as RELATED evidence.

**SUPPORTED_DIRECT** — profile evidences the same identity as the request.
Candidate may claim the requested capability. Promote that identity.

**SUPPORTED_RELATED** — profile does not evidence the requested identity, but
does evidence an explicitly related identity. Promote the **profile**
capability. **Never** claim the employer's requested capability.

Example: JD AWS Bedrock + profile AWS → related evidence is AWS; claiming
Bedrock is forbidden.

**UNSUPPORTED** — no direct identity and no related identity in the profile.
May appear as an honest gap. Must not be promoted as a candidate skill.

**Selected evidence references** — CareerProfile experience/project/skill/
certification refs the plan may pack. Not JD technologies.

**argument_spine** — short deterministic claim sentences the LLM may express.
Not recruiter prose. Not a licence to invent.

**forbidden_claims** — requested identities and phrasings that must not appear
as candidate capability (Bedrock, production chatbot employment, commercial AI
employment when false).

**include_methodology** — whether the Master AI Engineering Methodology section
is relevant for this job's needs (evaluation, HITL, orchestration, reliability,
governance). Not a global omit.

**trajectory_mode** — `full_chapters` (QA → DE → AI is the argument) |
`bridge` (testing only as a packed reliability claim) | `ai_lead` (do not pack
weak testing rows).

**CV rewrite surface (M3):** Professional Summary; selected engineering
highlights (existing strings); optional one-line project relevance; skills
emphasis (prefer deterministic render from the plan).

**Locked Master sections:** experience headings/dates/relationship; experience
bullets; project overview / engineering highlights / technology stack bodies;
courses; certifications; contact.

---

## 5. Capability catalogue v1

Module: `career_intelligence.document_positioning`  
**Not imported** by TailoringPlan, Master-adapt, cover-letter generation, or
package prepare.

Identities: `rag`, `aws`, `aws_bedrock`, `azure`, `azure_data_factory`, `java`,
`javascript`, `chatbot`.

Aliases (same identity): RAG / Retrieval-Augmented Generation / retrieval
augmented generation → `rag`. `data factory` / ADF → `azure_data_factory`.

RELATED pairs: `aws_bedrock` ← profile `aws`; `azure` ↔ `azure_data_factory`.

No Java↔JavaScript relation. No RAG↔chatbot relation. Chatbot remains a gap
when unevidenced even if RAG/AWS/Python are present.

Unknown labels: exact normalised profile match is DIRECT; otherwise
UNSUPPORTED; never invented RELATED.

**M2 warning:** catalogue v1 is **not** a drop-in replacement for
`_RELATED_CAPABILITY_GROUPS`. The production Azure group also includes
Microsoft Fabric and other pipeline phrases. M2 must not shrink those live
planner relations when consuming the catalogue. v1 only freezes the
positioning identities needed for DIRECT / RELATED / GAP tests.

---

## 6. Four-job evaluation set (frozen)

Shared evidence authority for all four: `data/career_profile.yaml` and
`career-documents/cv/master_ai_engineer_cv.md`. Do not invent extra career
facts for a job.

| ID | Role | Why | Tracked freeze |
|----|------|-----|----------------|
| E1 | Generic AI Engineer (control) | G1 Allura; strong applied AI Engineer | [manual_validation/jobs/001_strong_ai_engineer.txt](../../manual_validation/jobs/001_strong_ai_engineer.txt), [manual_validation/outputs/001_strong_ai_engineer.json](../../manual_validation/outputs/001_strong_ai_engineer.json) |
| E2 | Mixed-fit specialist | Exact vendor tech missing; related AWS + RAG exist; chatbot is a gap | [tests/fixtures/document_positioning/eval_jobs/02_csk_mixed_fit/](../../tests/fixtures/document_positioning/eval_jobs/02_csk_mixed_fit/) — opportunity `opp_01M0E6GQ9XQH9DK9N5T0MS67N0`. Live `data/opportunities/artifacts/…` is gitignored and is **not** the tracked freeze. |
| E3 | AI infrastructure / platform stretch | G3 Maincode; honest stretch, no invented GPU employment | [manual_validation/jobs/012_maincode_ai_infrastructure_engineer.txt](../../manual_validation/jobs/012_maincode_ai_infrastructure_engineer.txt), [manual_validation/outputs/012_maincode_ai_infrastructure_engineer.json](../../manual_validation/outputs/012_maincode_ai_infrastructure_engineer.json) |
| E4 | Adoption / enablement | G4 Repurpose AI Adoption Specialist; QA→DE→AI trajectory may be the strongest argument | [manual_validation/jobs/008_repurpose_it_ai_adoption_specialist.txt](../../manual_validation/jobs/008_repurpose_it_ai_adoption_specialist.txt), [manual_validation/outputs/008_repurpose_it_ai_adoption_specialist.json](../../manual_validation/outputs/008_repurpose_it_ai_adoption_specialist.json) |

Live Repurpose AI Engineer (`opp_01KZQJY6AX3EGX7TGYTHR3ABG1`) is **not** E1.
That opportunity is closer to a generic AI Engineer *application*, but E1 is
the golden-suite Allura job so the four cases stay distinct from E4.

Do not edit these advertisements to improve scores.

---

## 7. M5 evaluation protocol (frozen now)

Do **not** generate A/B documents in M0–M4 as the release gate. Protocol is
frozen so the goalposts cannot move after seeing outputs.

For each of E1–E4:

1. Freeze one canonical verified evidence pack (PositioningPlan + CV pack +
   cover-letter pack + forbidden_claims) from CareerProfile + Master facts +
   that job. The pack is the Truth authority for both sides.
2. **A** = CIC production documents after this remediation.
3. **B** = strong LLM draft using **exactly** that pack and the same forbidden
   claims. B is an evaluation baseline, not production Truth authority.
4. Hard gate: both A and B must FR-014 PASS (zero blocking unsupported candidate
   claims). A job that “wins” by inventing evidence is a fail for that side.
5. Blind owner (or second reviewer) scores shuffled A/B on: 15-second recruiter
   scan; role positioning; evidence selection; transfer argument; honest gaps;
   specificity; clarity; concision; overall submit preference.
6. **Release:** CIC preferred or tied vs B on **≥ 3/4** jobs. **Zero** Truth
   failures. Winning E2 (CSK) alone is not acceptance.

Do not freeze generated prose as the Gold Standard.

---

## 8. Milestones

| Milestone | Intent | Status |
|-----------|--------|--------|
| M0 Audit / contract | Architecture trace, terminology, catalogue v1, eval freeze, tests | **This document — owner review** |
| M1 PositioningPlan | Types + deterministic builder | Not started |
| M2 Related-capability in planner | Production planner consumes catalogue | Not started |
| M3 CV positioning | Pack + bounded LLM rewrite surface; Master chassis | Not started |
| M4 Cover-letter positioning | Need coverage, trajectory modes, opening gate | Not started |
| M5 Preference eval | Four-job A vs B | Not started |
| M6 Production + Gamma | Wire prepare; docs; required Gamma-ready learning artefact | Not started |

M1 acceptance tests (not implemented in M0): PositioningPlan builder on a
**synthetic** specialist job asserts AWS promoted, Bedrock forbidden, RAG
DIRECT, chatbot GAP; adoption job prefers `full_chapters` trajectory.

---

## 9. Explicitly out of scope until later milestones

- Implementing PositioningPlan or wiring the catalogue into production
- Regenerating CSK or any live application documents
- SEEK / Playwright / AAS
- CSK-specific aliases or prompts
- Unconstrained CV rewrite / production `rewrite_summary=True`
- Relaxing FR-014
- Marking this programme complete
