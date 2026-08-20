# Document Positioning M3 — Learning Note

This note is source material for the later M6 Gamma presentation. It is not
the Gamma deck.

---

## 1. Why deterministic selection alone produced weak positioning

The production CV already knew which projects to feature and which skills to
bold. It still pasted the same Master Professional Summary onto every job.
Selection without writing leaves the recruiter reading a generic AI Engineer
paragraph that does not argue *this* role.

---

## 2. Why unconstrained LLM CV rewriting is unsafe

A model asked to “write the best CV for this job” will borrow employer words.
AWS becomes Bedrock. A stretch infrastructure role becomes GPU employment.
The document looks strong and is false. Truth cannot be a prompt suggestion.

---

## 3. Why the architecture separates reasoning from writing

Deterministic code decides what may be said: needs, DIRECT / RELATED /
UNSUPPORTED, evidence refs, forbidden claims, trajectory, methodology.
The model only phrases an already-approved argument. If the writer fails,
the argument is still known. If the writer invents, validation can reject it.

---

## 4. What an evidence pack is

A serialisable list of authorised facts and prohibitions. Employer needs are
labelled as employer context. Candidate snippets carry CareerProfile or Master
refs. The writer never receives the whole repository or assessment free text.

---

## 5. Why employer requirements are not candidate evidence

A job ad that asks for Bedrock is not evidence the candidate has Bedrock.
Packing JD technologies into the writer’s “experience” list recreates the
CSK defect. Needs describe the vacancy. Skills describe the person.

---

## 6. DIRECT vs RELATED in generated prose

DIRECT: the summary may say the candidate has that capability.

RELATED: the summary may promote the *real* capability (AWS) and must not
say the requested one (Bedrock experience). Transfer language is allowed.
Identity collapse is not.

---

## 7. Why forbidden claims need deterministic validation

Prompts are not a control. A stubbed writer that emits “AWS Bedrock
experience” must fail even if the prompt said not to. Validators scan
positioned prose for forbidden identities in candidate-claim context.

---

## 8. Why the Master CV remains authoritative

Employment bullets, project overviews, courses, and certifications are the
career record. Positioning changes the scan layer — summary, highlight order,
optional relevance line, methodology presence — not the history.

---

## 9. Why only a small CV surface is rewritten

Recruiters decide in seconds from the top of the page. Rewriting locked
history multiplies hallucination risk without improving the 15-second scan.
Keep the chassis; reposition the argument.

---

## 10. Why silent fallback to a generic summary is dangerous

FR-006c Phase C already falls back to the profile summary when rewrite fails.
The package still looks “prepared.” The original product defect returns, now
hidden behind a success path. M3 raises instead of substituting Master prose.

---

## 11. Deterministic policy vs non-deterministic wording

Same profile, job, plan, and Master → same pack, same classifications, same
forbidden list, same highlight selection. Wording from a live model need not
be byte-identical. Tests pin policy with a fixture writer, not golden prose.

---

## 12. How this generalises beyond one CSK application

CSK exposed Bedrock/chatbot overclaim. The mechanism is identity + pack +
forbidden claims + fail-closed writer. Allura, Maincode, and Repurpose use
the same composer with different PositioningPlans. No employer-named rules.

---

## 13. Why an invalid optional relevance line must not kill the CV

M5 live generation blocked on E1 because the writer named a real Master
project that was not packed. The validator was right to reject the claim.
The line is optional presentation. Discarding the whole CV for that
embellishment is fragility, not extra truth. The bounded correction:

- tightens the prompt: exact packed project names only, or no line;
- drops invalid optional lines;
- revalidates the remainder;
- still fails the CV for summary claims, forbidden/unsupported identities,
  invented metrics/years, unpacked project claims in the summary, and
  locked-section mutation.

A hallucinated relevance line must never survive. An invalid fact must never
be tolerated by deleting whatever failed until the document passes.

