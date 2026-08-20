# Document Positioning M5 — Learning Note

This note is source material for a later Gamma presentation **if** M6 is
authorised. M5 failed the frozen Truth gate. It is not a Gamma deck.

---

## 1. Why unit tests cannot prove a CV is persuasive

Unit tests prove contracts: no invented employer, Bedrock not claimed, locked
Master bullets unchanged, fail-closed on provider error. A recruiter does not
score those contracts. They glance for fifteen seconds and decide whether this
person looks relevant. A document can pass every test and still look generic,
cautious, or off-target. M5 exists because M0–M4 could not ask that question.

---

## 2. Why M5 compares against a strong LLM rather than the old CIC output

The old CIC path was Master-shaped on purpose. Beating it would only prove we
are less generic than a conservative reprint. The product claim is stronger:
the new architecture should be competitive with a capable writer who has the
same truthful evidence. That is the alternative a skilled owner already has.

---

## 3. Why both systems must receive the same evidence

If the baseline sees extra career facts, a win is just more information. If
CIC sees hidden evidence the baseline cannot use, a win is privilege. The
comparison is only about positioning and expression when the factual inventory
is identical.

---

## 4. Why the baseline must make its own positioning decisions

If we handed B CIC’s selected projects and argument spine, we would be asking
a strong model to rewrite CIC’s argument. That tests wording, not whether
deterministic selection plus a bounded writer is worth the complexity. B must
choose emphasis independently, inside the same truth boundaries.

---

## 5. What blind evaluation prevents

Knowing which stack produced a document changes how we read it. We forgive
our own system and pick holes in the other. Shuffled Version A / Version B
forces a submit-preference judgement before identity is revealed.

---

## 6. Why the four jobs deliberately represent different fit patterns

One job can be overfit. E1 is a stronger applied-AI match. E2 is mixed-fit
transfer. E3 is an honest stretch. E4 may need a career-trajectory argument
rather than two flagship AI projects. Generalisation means the architecture
holds across those patterns, not that CSK looks better.

---

## 7. Why Maincode is a useful stretch control

Infrastructure needs (GPU, Linux, HPC) are real gaps. A good document may be
less aggressive. The failure mode is sounding like an infrastructure engineer
from generic AI projects. Restraint can be the correct persuasive move.
Confidence is not the scoring dimension.

---

## 8. Why Truth and persuasion are separate dimensions

FR-014 answers “is this claim authorised by CareerProfile / Master facts?”
Preference answers “would I rather submit this?” Passing Truth does not mean
the document is the strongest truthful application. Failing Truth means it is
not a valid application, however readable.

---

## 9. Why a truthful document can still lose

Safe, validated, technically elegant prose can bury the relevant evidence,
lead with the wrong chapter of a career, or sound like a template. Recruiters
do not award points for fail-closed validators.

---

## 10. Why a persuasive hallucination is still a failure

A beautiful letter that invents Bedrock, chatbot employment, or commercial AI
experience is a correctness failure. Persuasiveness never overrides fabricated
candidate evidence. M5 records that as a Truth failure, not as a style note.

---

## 11. Why the acceptance threshold was frozen before seeing results

After outputs exist, every awkward job looks “unrepresentative” and every
loss looks like a scoring-rule problem. M0 froze E1–E4, the rubric, and
≥ 3/4 preferred-or-tied plus zero CIC Truth failures so the goalposts cannot
move. 2/4 is not a pass. CSK-only is not a pass.

---

## 12. What we learn if CIC loses

The engineering may still be correct and still not be the best writer from
the same evidence. Failure analysis must separate architecture defects,
policy/calibration, generative wording, harness issues, and genuine
candidate/job mismatch. The lesson is where complexity failed to earn its
keep — not a licence to silently tune until CIC wins.

---

## 13. What we learn if CIC wins

Then deterministic classification plus packed selection plus a bounded writer
is at least as useful as asking a strong model to position from the same
facts, without giving that model a free hand to invent. That is the
justification for wiring the path in M6 — still behind owner approval.

---

## 14. Why production wiring waits until M6

M5 is an evaluation gate. Wiring `cic package prepare` before the owner has
scored the blind pack — and before a **pass** — would replace a trusted (if
generic) production path with an architecture that has not yet cleared the
product question. A quality win still needs a Truth pass **and** owner
approval before M6. This run had the quality win and not the Truth pass.

---

## 15. What M5 actually showed (after unblinding)

Quality and Truth must stay separate. CIC was preferred on **4/4** jobs: the
owner would submit the Master-backed CIC documents over the thinner baseline
rewrites (wrong nbn/PD order on E1/E2; thin projects; over-strong ADF /
vague “computational skills”). That does **not** mean M5 passed.

CIC failed FR-014 on **3/4** pairs (E3 passed). Failures clustered on
writer/token collisions (`llm`, `intesting` from “in testing”, `rag` /
`awsbedrock` including denial phrasing and job-title overlay), not on
invented employers or metrics. Baseline failed Truth on all four pairs.

Frozen contract: ≥ 3/4 preference **and** zero CIC Truth failures. Original
execution result: **FAIL**. Do not regenerate. Do not retune this run into a
pass. Full unblinded report:
[document_positioning_m5_unblinded.md](document_positioning_m5_unblinded.md).

A later bounded FR-014 detector correction is recorded in
[fr014_truth_alignment.md](fr014_truth_alignment.md). Owner close-out
(2026-08-20) recorded **M5 COMPLETE** from quality 4/4 plus Truth PASS on
unchanged CIC replay through the corrected validator. That close-out does not
rewrite this learning note’s historical FAIL and is not a fresh end-to-end
rerun. See
[document_positioning_m5_acceptance.md](document_positioning_m5_acceptance.md).

