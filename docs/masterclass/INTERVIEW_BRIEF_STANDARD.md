# Interview Brief Standard

**Status:** Permanent Engineering Learning Academy standard  
**Layer:** Rapid interview revision (not deep learning)  
**Scope:** Every completed Functional Requirement after Masterclass + Gamma Learning Presentation  
**Companion:** [INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md)

---

## Purpose

Allow the owner to refresh **one Functional Requirement in approximately 2–5 minutes**.

The Interview Brief is a **one-page** text revision aid. It is **not** a Masterclass,
not a substitute for repository documentation, and not a second engineering source
of truth.

---

## When to produce

After:

```text
Lean Masterclass → Masterclass PDF → Gamma Learning Presentation (15–20 slides)
```

Produce the Interview Brief **before** or alongside the Interview Deck. Use the
Lean Masterclass (and acceptance/ADR only if a fact must be checked) as source —
do **not** invent engineering.

FR-016 / FR-017 existing Masterclass and Gamma artefacts are preserved; Briefs may
be generated later on owner request without rediscovering this structure.

---

## Target

| Attribute | Guidance |
|-----------|----------|
| Length | Approximately **one page** |
| Voice | Plain engineering language |
| Priority | **WHY** over WHAT |
| Depth | Enough for a **1–2 minute** spoken answer |

---

## Required structure

Use these eight headings in order:

1. **What problem existed?**  
2. **What did we build?**  
3. **Why did we choose this approach?**  
4. **What alternative or risk mattered most?**  
5. **How did we validate it?**  
6. **Why does this matter to an employer?**  
7. **30–60 second interview answer**  
8. **Three things to remember**

---

## Rules

- Stay concise — one page, not a short Masterclass  
- No implementation walkthrough  
- No long test lists or corpus matrices  
- No detailed class / module names unless essential to the interview story  
- Preserve important terminology the owner may hear in interviews  
- Explain acronyms **once** on first use  
- Prioritise WHY over WHAT  
- Do not duplicate or rewrite repository engineering truth  
- Do not invent architecture that contradicts acceptance / ADR / Masterclass  

---

## Artefact role

| Artefact | Role |
|----------|------|
| Repository docs | Authoritative engineering truth |
| Lean Masterclass | Authoritative educational source |
| Interview Brief | Rapid **text** revision |

Suggested filename when retained in-repo:

`Interview_Brief_FRnnn.md` beside the Masterclass package.

---

## Related

- [README.md](README.md) — Academy workflow  
- [INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md) — rapid visual revision  
- [LEAN_MASTERCLASS_STANDARD.md](LEAN_MASTERCLASS_STANDARD.md) — deep learning layer  
