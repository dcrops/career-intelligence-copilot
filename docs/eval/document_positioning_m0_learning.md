# Document Positioning M0 — Learning Note

This note is for later conversion into the required Gamma learning
presentation. It is not the Gamma deck.

---

## 1. Why the previous architecture looked reasonable

After FR-006b/c, generated CVs could invent tone or dump the whole skill list.
The August document-quality remediation chose a conservative production path:

- Master CV as editorial baseline (the owner already trusted that prose)
- TailoringPlan only for inclusion and order
- No LLM rewrite of the CV
- One bounded LLM cover letter over a packed evidence list
- FR-014 as a fail-closed factuality gate

That is good engineering for **trust**. It stops JD technologies leaking into
candidate claims (the Redwolf TypeScript/Vue failure). Tests can prove those
contracts.

---

## 2. What real-world validation exposed that tests did not

CSK needed a **transfer argument**: no Bedrock, no production chatbots, but
real AWS, RAG, orchestration, and testing discipline.

The generator reprinted the Master summary, demoted AWS, treated RAG as an
unsupported JD token, packed a Bakers Delight POS story because the letter
must walk QA → DE → AI, and opened with generic relevance.

Unit tests still passed. Truth still passed. The documents were safe and
mediocre. Tests measured **mechanics and factuality**, not **whether a hiring
manager would prefer this over a strong evidence-constrained draft**.

---

## 3. Software correctness vs product quality

Correctness: given these inputs, the code obeys its contracts (no invented
employers, ranks contiguous, fingerprints preserved).

Product quality: given the same verified evidence, is this the strongest
truthful application a recruiter should see?

A system can be correct and still fail the product. That is not a reason to
abandon tests. It is a reason to add a **preference evaluation** with a frozen
job set and a competing baseline, behind the same Truth gate.

---

## 4. Why deterministic templates are good for truth and weak for persuasion

Templates and Master copy cannot lie about dates, employers, or stacks if they
only rearrange approved strings.

They also cannot say, honestly: “You asked for Bedrock; I have commercial AWS
and a Developer Associate certification, not Bedrock. Here is the RAG system
that shows retrieval, evaluation, and grounding.” That sentence is positioning.
It needs constrained language, not a theme-label splice.

---

## 5. Why an unconstrained LLM is the wrong answer

An unconstrained model given a job ad will claim Bedrock, chatbots, and
commercial AI employment because those words are in the ad. CIC already proved
that failure mode. The fix is not “better vibes”. It is **what the model is
allowed to see and claim**.

---

## 6. Why the proposed pipeline is:

deterministic evidence → deterministic positioning → bounded LLM expression → deterministic Truth

- Evidence and positioning decide **what is true and what may be argued**.
- The LLM only decides **how to say packed claims**.
- Truth checks the prose so neither the LLM nor an owner edit can smuggle
  unsupported Class A claims into external use.

That split is the same idea as the production cover letter, extended to the CV
rewrite surface, with a plan that can distinguish DIRECT / RELATED / GAP.

---

## 7. DIRECT vs RELATED vs UNSUPPORTED

**DIRECT.** JD asks for RAG. Profile has Retrieval-Augmented Generation. Same
capability. Claim RAG.

**RELATED.** JD asks for AWS Bedrock. Profile has AWS, not Bedrock. Promote AWS.
Do not write “Bedrock experience”.

**UNSUPPORTED.** JD asks for production chatbots. Profile has none. Do not
promote a fake chatbot skill. An honest gap may still sit next to related
evidence (RAG as document Q&A is a **different** need, not a chatbot claim).

Java is not JavaScript. Related is an explicit catalogue link, not a substring.

---

## 8. Why we freeze evaluation jobs before implementation

If we implement, then pick jobs, we will pick jobs the new code already wins.
Freezing E1–E4 and the ≥3/4 vs LLM-baseline rule **now** is how we stop another
one-job “READY” that does not generalise.

---

## 9. Why CSK must not become a special-case design target

CSK is useful because it is unlike Master/Repurpose: vendor platform + missing
exact skill + strong adjacent evidence + a real gap.

A `if company == CSK` alias, or a Bedrock prompt stanza, would make CSK prettier
and leave the next SageMaker/Vertex/conversational-AI ad equally generic.

The catalogue v1 encodes **relations** (RAG identity, AWS↔Bedrock RELATED,
chatbot GAP, Java≠JavaScript). Tests use those semantics, not CSK copy.
