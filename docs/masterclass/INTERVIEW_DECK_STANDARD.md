# Interview Deck Standard

**Status:** Permanent Engineering Learning Academy standard  
**Layer:** Rapid interview revision (not deep learning)  
**Scope:** Every completed Functional Requirement after Masterclass + Gamma Learning Presentation  
**Companion:** [INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md)

---

## Purpose

Allow the owner to understand or refresh an FR in roughly **five minutes**, and to
support a **1–2 minute** technical interview discussion.

The Interview Deck is a **short Gamma deck** (approximately **3–5 slides**). It does
**not** replace the deeper Gamma Learning Presentation (~15–20 slides).

---

## When to produce

After:

```text
Lean Masterclass → Masterclass PDF → Gamma Learning Presentation (15–20 slides)
→ Interview Brief (1 page)
```

Derive slides from the Interview Brief and Masterclass Runtime Example. Do **not**
invent architecture. Do **not** expand into a second learning presentation.

FR-016 / FR-017 existing Masterclass and Gamma work is preserved; Interview Decks
may be generated later on owner request using this standard.

---

## Target

| Attribute | Guidance |
|-----------|----------|
| Slide count | Approximately **3–5** (fewer if the FR is simple) |
| Purpose | Rapid visual revision + short spoken story |
| Not allowed | 10–20 slide “interview” decks |

**Do not force five slides.** Use the minimum that carries the story.

---

## Recommended structure

| Slide | Title | Content |
|-------|-------|---------|
| 1 | The Problem | What was wrong / missing? |
| 2 | The Engineering Decision | What did we build and why? |
| 3 | The Architecture / Flow | One simple visual (from Masterclass Runtime Example) |
| 4 | Trade-off + Validation | Why this was the right amount of engineering and how we proved it |
| 5 | Interview Takeaway | 30–60 second story + three things to remember |

Collapse slides when the FR is simple (e.g. combine 2+3, or 4+5).

---

## Rules

- Keep slides sparse — headlines and short bullets  
- One simple visual only (no architecture dump)  
- Preserve interview terminology; expand acronyms once if needed  
- Prefer WHY and trade-offs over feature lists  
- Do not turn the Interview Deck into a Masterclass or Learning Presentation  
- Do not contradict acceptance / ADR / Lean Masterclass  

---

## Relationship to Gamma Learning Presentation

| Deck | Slides | Role |
|------|--------|------|
| Gamma **Learning** Presentation | ~15–20 | Deeper visual learning / reference |
| Gamma **Interview** Deck | ~3–5 | Rapid visual revision before interviews |

Both may exist. The Learning Presentation is **not** replaced.

---

## Artefact role

| Artefact | Role |
|----------|------|
| Lean Masterclass / PDF | Deep study |
| Gamma Learning Presentation | Deep visual learning |
| Interview Brief | Rapid **text** revision |
| Interview Deck | Rapid **visual** revision |

---

## Related

- [README.md](README.md) — Academy workflow  
- [INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md) — rapid text revision  
- [LEAN_MASTERCLASS_STANDARD.md](LEAN_MASTERCLASS_STANDARD.md) — deep learning layer  
