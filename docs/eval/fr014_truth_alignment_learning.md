# FR-014 Truth Alignment — Learning Note

This note is source material for a later Gamma presentation **if** the owner
accepts the detector correction. It is not a Gamma deck. Historical Document
Positioning M5 remains FAIL on the Truth gate; this note does not convert
that result into a PASS.

---

## 1. Why two catalogues became a product defect

M2 needed a canonical capability identity so TailoringPlan and PositioningPlan
could treat `RAG` and `Retrieval-Augmented Generation` as one requirement.
FR-014 needed a catalogue so candidate claims could be checked against Career
Profile evidence. Those look like the same problem. They were implemented as
two matching systems. Positioning already knew `LLM application development`
was `llm`. Truth still asked whether the generated word `LLM` equalled the
profile string. The documents were truthful. The gate was not.

---

## 2. Why identity must not inherit permission

The cheapest reuse would have been “if M2 says RELATED, Truth should pass.”
That would turn AWS evidence into AWS Bedrock experience. RELATED is a
planning fact: the candidate has neighbouring evidence worth packing. DIRECT
is a claim fact: the candidate may say they have the requested capability.
Truth may share identity. It must not share permission.

---

## 3. Why “I do” is a dangerous cue

A candidate-capability cue list is trying to find first-person ownership.
`I do` looks like ownership. In English it is also the start of `I do not`.
The E2 letter told the truth: no direct Bedrock experience. The detector
heard the first two words and classified Bedrock as a claim. Negation has to
be scoped to the phrase being classified, not to the whole sentence, or
`I do not claim X, but I delivered X` would go silent.

---

## 4. Why the comma is not a tenure boundary

`10+ years across testing, automation, data engineering and applied AI`
was already understood as overall career span. The same list with `in`
instead of `across` truncated at the first comma and became `10 years in
testing`. The chronology supports an engineering career, not a decade of
testing specialty. The parser has to keep the list **before** it classifies.
Mapping `intesting` to overall experience would have hidden the defect.

---

## 5. Why M3/M4 were left alone

The M5 quality result was 4/4 CIC preferred. The named Truth failures were
validator false positives. Changing the writers to avoid `LLM` or `RAG`
would have taught the composers to please a broken gate. The product claim
is strongest truthful positioning, not wording that happens to match an
exact profile string.

---

## 6. Why a validator replay is not a new M5

Re-running Truth on frozen CIC Markdown proves the detector no longer
rejects those named spans. It does not re-score recruiter preference,
does not re-blind the owner, and does not regenerate documents under the
frozen protocol. Owner close-out (2026-08-20) nevertheless accepted that
replay as the Truth half of M5 COMPLETE, while keeping the original
execution historically FAIL and making no claim of a fresh end-to-end
rerun.

---

## 7. Why the nbn delivery finding used one previous sentence, not a paragraph

Same-sentence `At nbn, I developed pipelines…` already binds to employment
evidence. The E2 letter put the employer in the previous sentence. A paragraph
walk or “this experience” resolver would be a different product. The later
bound is only: if the immediately previous sentence names **exactly one**
known employer, reuse the existing highlight overlap. Two sentences back,
two employers, and invented GPU clusters still fail closed. Writers were
not retuned.

---

## 8. What fail-closed still means after the correction

Java is still not JavaScript. AWS is still not Bedrock. A header that names
Bedrock is still not a candidate claim. `10+ years of AI engineering` still
fails. Unsupported positive Bedrock claims still block. The gate got
better at reading truthful wording. It did not get more generous about
invented experience.
