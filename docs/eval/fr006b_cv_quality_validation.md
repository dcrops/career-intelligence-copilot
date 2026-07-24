# FR-006b CV Quality — Integrated System Validation Report

**Date:** 2026-07-24  
**Milestone:** FR-006b (Master CV ↔ Profile ↔ Planner ↔ Renderer)  
**Golden drafts:** `career-documents/cv/generated/fr006b_golden/`  
**Proposed Master CV:** `career-documents/cv/master_ai_engineer_cv.md`
**(Canonical Master CV v4 — released 2026-07-24)**

---

## 1. Master CV review

Reviewed Master CV v3 PDF (4 pages; vector layout, no text layer — reviewed via rendered page images).

| Finding | Assessment |
|---------|------------|
| Overall presentation | Strong: blue hierarchy, Purpose / Highlights / Stack, scannable |
| Professional summary | Solid, but understates current methodology depth |
| Chase / nbn | Accurate; Chase still Cursor-tool framed |
| Projects | Strong structure; missing Career Intelligence Copilot |
| **AI-Assisted Engineering Practices** | **Understates current capability.** Over-emphasises Cursor Plan/Agent/Ask modes. Should be reframed as transferable **AI Engineering Methodology** |
| Methodology gap | Product vision, TDDs, roadmap delivery, living docs, documentation freeze, golden suites, GO/NO-GO, human-in-the-loop are real practices from CIC work but absent or weak on v3 |

**Decision:** Do not treat Master v3 as perfect. Proposed Master content is in
`master_ai_engineer_cv.md` (canonical Master CV v4; PDF at `master_ai_engineer_cv.pdf`).

---

## 2. Career Profile review

`data/career_profile.yaml` updated to support Master v4 and stronger generated CVs:

- Stronger identity summary (methodology + stack + outcomes)
- Chase highlights rewritten as transferable methodology (Cursor removed from tech list)
- Stronger nbn bullets (closer to Master achievement voice)
- Soft skills: Roadmap-driven delivery, Human-in-the-loop validation, Living documentation
- `selected_engineering_highlights` (Master-style scan aids)
- `engineering_methodology` (Planning → Delivery categories; no Cursor mode names)
- New project: **Career Intelligence Copilot** (factual portfolio evidence)

No invented employers, clients, or commercial AI employment claims.

---

## 3. Engineering changes

| Area | Change |
|------|--------|
| Profile schema | Optional `selected_engineering_highlights`, `engineering_methodology` |
| Content selection | `content_selection.py` — relevance select/reorder of existing strings |
| Generation | Highlight selection; project outcome/demonstrates curation; methodology + highlights on `TailoredCv` |
| Planner | Theme-weighted project re-rank within strategy; CIC append for AI-family roles |
| Plan refs | Allow relevance reorder + profile-backed project appends |
| Render | Master-aligned sections: Highlights, Core Skills, Professional Experience, Featured AI Projects (Purpose / Engineering Highlights / Technology Stack), AI Engineering Methodology |
| Prior P0 retained | Submit-ready default, theme-aware summary, curated skills, role-family anchors |

---

## 4. Presentation improvements

- Section naming and order aligned to Master CV
- Purpose / Engineering Highlights / Technology Stack project template
- Selected Engineering Highlights for 15-second scan
- Methodology section with bold category labels and · separators
- Strategic bolding of plan-prioritised technologies
- No review chrome on submit surface

Markdown cannot reproduce Master PDF blue/serif typography; structure and scanability now match Master intent.

---

## 5. Content improvements

- Methodology depth matches real CIC engineering practice
- Role-aware summary + highlight selection
- Stronger Chase / nbn prose from profile
- CIC project surfaces on AI-family roles
- Project lead order prefers AI themes over single shared tech (e.g. G1 leads with Operational Intelligence Copilot)

---

## 6. Benchmark Suite (G1–G5)

| ID | Role | Content | Presentation | Lead project (new) |
|----|------|---------|--------------|--------------------|
| G1 | AI Engineer | Strong | Strong | Operational Intelligence Copilot |
| G2 | AI Automation | Strong | Strong | Operational Intelligence Copilot |
| G3 | AI Infrastructure | Honest stretch; no invented GPU employment | Strong | AI methodology + Python/FastAPI emphasis |
| G4 | AI Adoption | Adoption-oriented anchors + CIC | Strong | Methodology / explainability |
| G5 | Senior AI (stretch) | Honest; Docker + AI anchors | Strong | Operational intelligence + stack |

Tests: **71 passed** (`tests/unit/cv_generation` + FR-006 functional).

---

## 7. Owner preference results

Comparison basis: Master v3 PDF vs previous generated review artefact vs new `fr006b_golden` drafts.

| Benchmark | Preferred submit artefact | Why |
|-----------|---------------------------|-----|
| **G1** | **New generated** | Role title, Core skills, methodology, CIC, OIC lead — beats manually editing outdated Master v3 |
| **G2** | **New generated** | Automation-relevant Core skills + tailored highlights |
| **G3** | **New generated** (with caveats) | Honest infra stretch without invention; Master v3 also cannot invent GPU employment |
| **G4** | **New generated** | Adoption-oriented emphasis Master v3 does not provide |
| **G5** | **New generated** | Stretch narrative + methodology; still no false senior commercial AI claim |

**Where Master v3 PDF still wins:** pixel-level visual polish (blue headers, serif body, print layout). That is a **format** advantage, not a **content/tailoring** advantage.

**Against proposed Master v4 Markdown:** generated wins on per-role tailoring; Master v4 remains the best single baseline document once exported to PDF.

---

## 8. Remaining weaknesses

1. No PDF/DOCX export — Markdown ≠ Master print layout.
2. Professional-development entries can still occupy mid-page space.
3. Theme-aware summary “Background:” bridge remains slightly formulaic vs hand-crafted Master prose.
4. Master v4 PDF not yet owner-exported (proposed Markdown only).
5. FR-004 portfolio rankings do not yet include CIC until strategies are re-run.

---

## 9. Recommendation

The integrated pipeline now produces submission-ready, role-tailored CVs that a reasonable owner would prefer for real applications over manually editing Master CV **v3** (which understates methodology and omits CIC).

**READY FOR DAILY USE**

Owner follow-ups (non-blocking for daily Markdown use):

1. Use `career-documents/cv/master_ai_engineer_cv.md` (+ `.html` / `.pdf`) as the Master visual SoT.
2. Optionally re-run FR-004/005 on golden jobs so strategy JSON includes CIC natively.
3. Optional Phase C summary rewrite for final prose polish on Platinum/Gold applications.
