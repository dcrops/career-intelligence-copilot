# FR-006b CV Quality — Findings Report

**Date:** 2026-07-24  
**Status:** Findings only — **no generation-code changes in this step**  
**Inputs:** Master CV PDF (visual/layout source; no text layer), Career Profile
(Master-CV-aligned structured content), generated Markdown CVs for pay.com.au,
Maincode, Bluefin, Officeworks; FR-006 owner reviews; planner/render/generation
implementation.

**Golden suite:** [fr006b_cv_quality_golden_suite.md](fr006b_cv_quality_golden_suite.md)

---

## 1. Comparison basis

| Source | Role in review |
|--------|----------------|
| `career-documents/cv/archive/master_ai_engineer_cv_v3.pdf.pdf` | Prior submit-grade Master (archived; superseded by canonical v4) |
| `data/career_profile.yaml` | Structured Master-CV-aligned facts (summary, highlights, projects) used by the generator |
| Generated `.md` under `career-documents/cv/generated/` | Current FR-006 Phase B/C output |
| `manual_validation/reviews/tailored_cv_reviews.md` | Owner judgments on plan vs render |

**Limitation:** Direct line-by-line Master CV text comparison was not possible without
OCR. Findings below compare generated drafts to (a) profile content that was derived
from / aligned with the Master CV, (b) submit-readiness vs a professional CV artefact,
and (c) owner FR-006 review notes. Owner visual confirmation against the PDF remains
required for preference scoring.

---

## 2. Strengths (keep)

1. **Fidelity discipline** — Generation does not invent employers, skills, or projects;
   unsupported JD technologies can be excluded from promotion (post–Bluefin/Officeworks
   planner fixes).
2. **Plan → render contract** — Phase B faithfully applies TailoringPlan emphasis,
   project order, and experience scope (owner Q2 PASS repeatedly).
3. **Master-CV experience scope** — Default `master_cv_only` excludes extended pre-nbn
   history that is not on the Master CV.
4. **Evidence-backed themes (when planner is correct)** — Summary themes can be
   restricted to profile-supported capabilities (e.g. Python / SQL / Operational
   intelligence on pay.com.au).
5. **Optional Phase C** — Summary rewrite is gated, validated, and fail-soft; Bluefin
   run proves the path works.

---

## 3. Weaknesses (quality gap vs Master CV / submit preference)

Observed across recent generated drafts (pay.com.au 2026-07-24, Maincode 2026-07-24,
Bluefin Phase C, Officeworks):

### W1 — Not submit-ready presentation

- Internal meta surfaces in the “CV”: owner-review banner, **Summary themes** section,
  skill category suffixes `(technical)`, experience `` `kind` `` tags, experience-guidance
  footer.
- Master CV is a polished document; generated Markdown reads as a **debug/review
  artefact**, not something an owner would email to a recruiter without heavy cleanup.

### W2 — Summary is rarely role-tailored

- Default path **copies the Career Profile summary verbatim** (themes listed separately).
- Themes therefore do not reshape the opening narrative unless Phase C is enabled.
- Phase C (Bluefin) improves topic focus but can drift into generic LLM marketing tone
  (“extensive experience”, “Proven ability”, “specializing”) vs the denser Master/profile
  voice.

### W3 — Skills section is an inventory dump

- Emphasised set is often tiny (1–2 items) while **Additional** lists nearly the full
  profile skill catalogue (20+ lines).
- Master CV practice is a **curated** skill presentation. The dump dilutes emphasis and
  hurts scannability.

### W4 — Weak or misaligned emphasis for some roles

- **Maincode (AI Infrastructure):** emphasised skill / theme **“Test automation”** —
  poorly matched to GPU/infra/platform signals; underplays Python, systems, production
  engineering posture the profile *does* support.
- Indicates planner theme/skill selection can latch onto shallow JD tokens or weak
  relatedness rather than role-family-aware emphasis.

### W5 — Experience bullets are thin and static

- nbn and other Master-scope bullets are short, generic, and **identical across jobs**
  (no highlight selection or impact reordering for the target role).
- Profile nbn highlights are already compressed (3 bullets). Generated CV does nothing
  to recover Master-CV-level achievement storytelling if richer wording only exists in
  the PDF layout.

### W6 — Projects are content-stable, weakly framed

- Same project bodies/outcomes/demonstrates appear across roles; only **order** changes
  with the plan.
- No role-specific framing of *why this project matters for this job* (still evidence-
  safe, but weak tailoring).

### W7 — Target role / header not job-specific

- Header uses profile `target_role` (“AI Engineer”) even when applying for
  “AI Infrastructure Engineer” / “AI Automation Engineer” / “AI Adoption Specialist”.

### W8 — Contact often absent

- Contact block only appears if CLI/options supply it; Master CV always shows contact.

---

## 4. Root causes (prioritised)

| Priority | Root cause | Drives |
|----------|------------|--------|
| **R1** | Phase B is **structured assembly from profile + plan**, not a writing/presentation layer aimed at Master-CV quality | W1, W3, W5, W6 |
| **R2** | **Submit surface vs owner-review surface** are the same Markdown | W1 |
| **R3** | Summary default = **profile copy**; themes do not rewrite prose unless Phase C | W2 |
| **R4** | Skills render = **emphasised ∪ all remaining profile skills** | W3 |
| **R5** | Deterministic planner optimises for **evidence-safe JD overlap**, not role-family narrative quality; can select weak themes (e.g. test automation for infra) | W4 |
| **R6** | No per-job **highlight selection / impact ordering** (and profile bullets may under-represent Master CV richness) | W5 |
| **R7** | Projects copied wholesale from profile; plan only reorders | W6 |
| **R8** | Header fields bound to profile identity, not posting title | W7 |
| **R9** | Contact optional in generation options | W8 |

**Not primary causes (for this quality gap):** Opportunity Assessment, Application
Strategy policy, Opportunity persistence, or ranking. FR-006 reviews already showed
renderer faithfulness; **quality debt is in planning emphasis + render presentation +
content selection depth**.

---

## 5. Opportunities for improvement (impact-ordered)

### P0 — Highest impact (do first)

1. **Submit-ready Markdown mode** — Separate or strip owner-meta (themes list, kind tags,
   category suffixes, guidance footer) from the artefact meant for external use; keep a
   review companion if needed.
2. **Curate skills output** — Cap emphasised + additional; omit long residual inventory
   from the submit CV (or move to an appendix review-only section).
3. **Role-aware summary by default** — Either enable a constrained Phase C path for
   golden suite / daily use, or deterministically compose summary from evidence-backed
   themes + profile sentences without inventing facts (preserve Master voice).
4. **Planner emphasis quality** — Bias themes/promoted skills toward role family and
   strong profile AI/DE capabilities; avoid weak residual matches (e.g. lone “test
   automation” for infra roles).

### P1 — High impact

5. **Experience highlight selection** — Per plan, pick/reorder existing highlights that
   best support the role; never invent bullets. Optionally enrich profile from Master CV
   if PDF content is richer than YAML (owner data task).
6. **Job-specific target title** in header (from posting / plan), keeping profile target
   as fallback.
7. **Default contact** from a single owner-configured source (profile extension or
   generation defaults) so submit CVs are complete.

### P2 — Medium impact

8. **Project framing lines** — Short evidence-safe “relevance” notes derived from plan
   themes without new factual claims.
9. **Phase C tone constraints** — Tighten prompt to preserve owner voice; forbid
   generic marketing stock phrases.
10. **Golden suite automation assist** — Script to regenerate all five golden jobs and
    open a review checklist (still human-scored).

### Out of scope for FR-006b (do not do now)

- Cover letters (FR-007)
- Dynamic layouts / Intelligent Document Presentation FR
- Changing FR-003/FR-005 behaviour
- Architectural redesign of service boundaries

---

## 6. Proposed engineering strategy (for next implementation step)

Smallest change set aligned to P0→P1:

1. Render options: `submit_ready=True` (default for drafts intended for use) vs
   `review_debug=True`.
2. Skills rendering policy: top-N emphasised + limited related; no full dump.
3. Planner: role-family-aware theme/skill ranking; regression tests on Maincode ≠
   “test automation”-only emphasis.
4. Summary: constrained rewrite or deterministic theme-aware composition with
   fidelity checks.
5. Header: prefer `job_analysis.posting.title` when present.
6. Validate on Golden Suite G1–G5 before/after; owner preference is the gate.

**No code changes in this findings step.**

---

## 7. Interim recommendation

**FURTHER QUALITY IMPROVEMENTS REQUIRED**

Generated CVs are **technically faithful** but not yet at Master CV **submit preference**.
Proceed to implement P0 items against the Golden Validation Suite, then re-score with
the owner.

---

## Appendix — Artefacts sampled

| Job | Generated draft (example) |
|-----|---------------------------|
| pay.com.au | `20260724T034140Z_pay.com.au_ai_automation_engineer.md` |
| Maincode | `20260724T034109Z_maincode_ai_infrastructure_engineer.md` |
| Bluefin (Phase C) | `20260723T081042Z_bluefin_resources_pty_limited_ai_systems_developer.md` |
| Officeworks | `20260723T062439Z_officeworks_ai_engineer.md` |
