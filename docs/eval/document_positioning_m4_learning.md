# Document Positioning M4 — Learning Note

This note is source material for the later M6 Gamma presentation. It is not
the Gamma deck.

---

## 1. Why tag overlap is not enough for evidence selection

Tag density answers “which projects share the most words with the job ad?”
That is a retrieval heuristic. A payroll rules engine and a RAG system can
both match `Python`. The recruiter’s question is different: which truthful
evidence answers the employer’s most important needs? Overlap without
coverage selects popular projects and drops the one that actually carries the
argument.

---

## 2. What “employer-need coverage” means

For each ordered hiring requirement, deterministic code asks: is it DIRECT,
RELATED, or UNSUPPORTED, and which candidate source can support that status?
Coverage is identity-based. A source is chosen because it closes a need, not
because it accumulated points. Once a need is represented, another source
must earn its place by covering something still open.

---

## 3. Why the best evidence source is not always an AI project

Commercial AWS work can be stronger RELATED evidence for a Bedrock-focused
role than a third Python AI project. A certification can support a cloud
identity. Trajectory can be the argument for an adoption role. Projects remain
first-class sources; they are no longer the only ones the letter is allowed
to use.

---

## 4. Why two projects was an arbitrary policy rather than a law

The production cap of two projects was a concision choice. It treated “how
many portfolio demos fit on a page” as the constraint. The real constraint is
“how many distinct employer needs still need a source?” Defaulting to two and
allowing a third only for an uncovered high-priority need keeps the letter
short without pretending two is a law of recruiting.

---

## 5. How PortfolioMatch and PositioningPlan have different roles

PortfolioMatch ranks projects by similarity to the job. That is useful tie
context. PositioningPlan owns the employer-facing argument: what may be
claimed, what is only related, what is forbidden. When rank #1 does not cover
a high-priority need that another source does, PositioningPlan overrides and
records why. Rank without coverage is not authority.

---

## 6. Why career trajectory should be conditional

QA → data engineering → AI is true of this profile. It is not always the
hiring argument. `ai_lead` spends the opening on current AI capability.
`bridge` uses earlier engineering as transfer. `full_chapters` makes the
progression itself the case. Forcing the walk into every letter burns space
and sounds like biography, not positioning.

---

## 7. DIRECT vs RELATED in persuasive prose

DIRECT: the letter may say the candidate has that capability.

RELATED: the letter may promote the real capability and must not say the
requested one. “AWS experience is relevant cloud grounding for a
Bedrock-focused environment” is allowed. “I have AWS Bedrock experience” is
not. Persuasion is not a licence to collapse identities.

---

## 8. Why factual validation and writing quality are separate

Forbidden claims, unsupported tools, invented metrics, and generic openings
are objective enough to reject. Whether a paragraph would survive a 15-second
recruiter scan is not. Scoring “persuasiveness” in code would fake certainty.
M4 rejects contract violations. M5 asks a human which letter they would
submit.

---

## 9. Why deterministic rules cannot fully prove recruiter persuasion

The same pack can be phrased as a tight argument or as dull inventory. Rules
can forbid Bedrock and chatbot. They cannot prove the opening makes someone
keep reading. That is a preference question, not a proof.

---

## 10. Why M5 still requires human preference testing

M0 froze an A/B protocol against a strong evidence-constrained LLM baseline.
M4 produces positioned letters that are truth-safe under local validators.
It does not compare them blindly against that baseline. Release still
requires CIC preferred or tied on at least three of four jobs with zero Truth
failures.

---

## 11. How the cover letter and CV can share an argument without being duplicates

Both documents read the same PositioningPlan. They share DIRECT / RELATED /
UNSUPPORTED, trajectory mode, and forbidden claims. The CV repositions the
scan layer of a locked Master. The letter selects a small evidence set and
writes paragraphs. Same argument, different surface. Contradiction (CV says
AWS is related; letter claims Bedrock) is a validation failure.

---

## 12. How this architecture generalises across very different roles

Allura, CSK, Maincode, and Repurpose do not have employer-named rules. The
same selector sees different PositioningPlans: AI-lead Python/LLM, RAG plus
AWS transfer, honest infrastructure gaps, full-chapter adoption. Coverage,
not a CSK special case, is what generalises.
