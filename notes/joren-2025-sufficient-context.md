# Joren et al. 2025 — Sufficient Context: A New Lens on RAG Systems

**Citation.** Hailey Joren, Jianyi Zhang, Chun-Sung Ferng, Da-Cheng Juan,
Ankur Taly, Cyrus Rashtchian. *Sufficient Context: A New Lens on Retrieval
Augmented Generation Systems.* ICLR 2025. arXiv:2411.06037 —
<https://arxiv.org/abs/2411.06037>

**Why this source.** It is the one Phase 0 reading to do if there is time
for just one. It serves one decision: **how this project defines
"sufficient" and how the per-step label is built** (`labeling/sufficiency.py`,
ADR-006). It also positions the project's contribution. Joren et al. define and
measure sufficiency for a *single, static* context. This project measures it
*sequentially*, at each step of an agent loop, and uses exact labels instead of
an LLM autorater. Read this first in Phase 0, before Ferrazzi et al. 2026 (the
agentic-vs-enhanced comparison assumes you already have a sufficiency vocabulary)
and before skimming Singh et al. 2025 (the survey).

**Cross-refs used throughout** (most are Phase 0 deliverables still to write):
- [`docs/hypothesis.md`](../docs/hypothesis.md) — H1/H2, central axis, per-stratum predictions (planned)
- [`docs/examiner.md`](../docs/examiner.md) — sufficiency labeler, minimal sufficient sets, subtypes (planned, Phase 2)
- [`docs/adr/adr-001-theme-and-thesis.md`](../docs/adr/adr-001-theme-and-thesis.md) — positioning (planned)
- [`docs/adr/adr-006-judge-outputs-boolean-only.md`](../docs/adr/adr-006-judge-outputs-boolean-only.md) — the A4 judge (planned)
- [`docs/evaluation.md`](../docs/evaluation.md) — grader, cost C ∈ {0, 1, λ}, selective metrics (planned)
- [`experiments/registry.md`](../experiments/registry.md) — E-001 predictions (planned)
- [`notes/phase0-foundation.md`](phase0-foundation.md) — phase note
- `notes/open-ideas.md` — parking lot (to create if an idea shows up with no consumer)

**Legend.** 🔄 = needs synthesis with another source. Cross-source questions
(Joren × Ferrazzi × Singh) go in `notes/phase0-synthesis.md`, not here.

---

## §1 — Introduction

### 1.1 — The problem as the authors frame it
**Prompt.**
- The paper splits RAG errors into two causes. What are they, in the authors'
  words? Map them onto this project's split: failing to **search** vs failing to
  **decide** (`docs/hypothesis.md`, "Central axis").
- Before reading on, predict: do the authors ever consider sufficiency *changing
  over time* (step by step), or only for a fixed retrieved context?
- Which of the listed contributions carries the headline result: the
  definition, the autorater, the empirical finding, or the selective-generation
  method?

**My take.**

**Refined write-up.**

---

## §2 — Related Work

### 2.1 — Sufficiency vs relevance vs entailment
**Prompt.**
- How do the authors separate their notion from earlier "relevant / irrelevant
  context" work? Is there a concrete example where a context is relevant but
  insufficient?
- Which prior work on abstention or self-knowledge do they cite (e.g.
  P(True)-style confidence)? Note any you would want to read in Phase 8
  (Kadavath et al. 2022 is already on the list).
- 🔄 Does any cited work treat retrieval as multi-step (iterative, agentic)? If
  so, does it measure *when* to stop? This is the gap claim in ADR-001; check it
  here instead of assuming it.

**My take.**

**Refined write-up.**

---

## §3 — Sufficient Context

### 3.1 — The formal definition (§3.1)
**Prompt.**
- Copy the exact definition. Pay attention to the quantifier: "there exists an
  answer A′ that is *plausible* given C". Why do the authors avoid tying it to
  the ground-truth answer?
- The project defines sufficiency by construction: the units seen up to step t
  cover **at least one minimal sufficient set** for the gold answer. Is that the
  same notion, stronger, or weaker? Write down one case where the two
  definitions disagree.
- Test the definition on each stratum. Would Joren's definition label as
  "sufficient":
  (a) S2 — the learnset section for the *wrong* version?
  (b) S3 — a partial list (6 of 14 elements)?
  (c) S4 — other versions' sections, with the asked-for version removed?
  If a context that yields a *plausible but wrong* answer can count as
  sufficient, what does that mean for using their definition as this project's
  label?
- How does the definition handle multi-hop questions ("only inferences present
  in C")? Compare with S1 (missing hop).

**My take.**

**Refined write-up.**

### 3.2 — The autorater (§3.2 + Appendix C.1)
**Prompt.**
- Which model, how many shots, what output format? Does the autorater produce a
  binary label, a score, or a rationale? Compare with ADR-006 (the A4 judge
  outputs **yes/no only** and puts nothing into the answer context).
- Validation: 93% accuracy on 115 human-labeled instances. How were those 115
  chosen and labeled? How many annotators, and is agreement reported? With
  n = 115, what is the rough 95% CI on 93%?
- The autorater runs *without* the gold answer, so it can be used at inference
  time. Which arm in this project plays that role (A4), and which role does the
  exact label play (O2, the stopping oracle)?
- Read the prompt in Appendix C.1. Is anything in it reusable as a *concept* for
  the A4 judge prompt? (Concepts transfer, constants do not: do not copy the
  prompt text.)

**My take.**

**Refined write-up.**

---

## §4 — A New Lens on RAG Performance

### 4.1 — How much sufficient context do benchmarks have? (§4.1)
**Prompt.**
- Record the sufficient-context share per dataset (FreshQA, MuSiQue-Ans,
  HotpotQA). Why is MuSiQue so low, and what does that say about using it for
  external calibration in Phase 10?
- Contexts are truncated to 6000 tokens after exploring 2000–10000. How does
  that choice interact with the sufficiency share? Compare with this project's
  cap B = 4,000 evidence tokens.
- Is sufficiency here a property of the dataset's context, of the retriever, or
  of both? What does that imply for a *sequential* setting, where the agent
  builds its own context?

**My take.**

**Refined write-up.**

### 4.2 — The headline findings (§4.2)
**Prompt.**
- Fill a 2×3 table for one model: {sufficient, insufficient} × {correct,
  abstain, hallucinate}. Which cell carries the claim "models answer instead of
  abstaining when context is insufficient"?
- "With insufficient context, models are still correct 35–62% of the time." The
  authors attribute this to pretraining knowledge and contextual cues. Which of
  the two does the **counterfactual twin** remove? Which one survives it?
- "RAG increases hallucination relative to closed-book." What is the exact
  comparison: same questions, same model, abstention allowed in both? How does
  this relate to arm A0 (closed-book) and the G2 gate (closed-book on the twin
  must be ≤ 5%)?
- Statistical rigor: n per cell, confidence intervals, significance tests,
  multiple models vs multiple comparisons. Would these numbers pass this
  project's rule "every denominator is written as N-of-M"?

**My take.**

**Refined write-up.**

### 4.3 — Qualitative analysis of insufficient-context answers (§4.3)
**Prompt.**
- List the categories the authors find for "correct despite insufficient
  context". Does any category match S2 (near-certain evidence from the wrong
  version) or S3 (a partial set)?
- 🔄 Compare their categories with this project's error taxonomy (E-001 draft /
  `docs/evaluation.md`). Is there a category you are missing, or one of theirs
  the twin makes impossible?

**My take.**

**Refined write-up.**

---

## §5 — Techniques to Reduce Hallucinations

### 5.1 — Selective generation with the sufficiency signal (§5.1)
**Prompt.**
- Write the method as an algorithm: inputs (self-rated confidence P(True) /
  P(Correct), the binary sufficiency label), model (logistic regression, how it
  was tuned), output (a hallucination-risk score), decision (threshold →
  coverage).
- What is the evaluation metric: selective accuracy at a given coverage? Do they
  report a risk-coverage curve or AURC? Compare with `evaluation/selective.py`
  and the cost function C = 0 / 1 / λ = 4. Is there an implicit λ in their
  setup?
- The 2–10% gain: over which baseline (confidence alone)? At which coverage
  levels? Is variance across seeds or CIs reported?
- 🔄 This is structurally a one-shot version of the **trained detector (A5,
  Phase 8)**: cheap signals → calibrated classifier → threshold. What changes
  when the decision is made at every step t instead of once? Park the answer for
  the Phase 8 reading (Geifman & El-Yaniv 2017).

**My take.**

**Refined write-up.**

### 5.2 — Fine-tuning for abstention (§5.2 + Appendix A.2, B.1)
**Prompt.**
- What exactly was trained (Mistral 7B, 20% of targets replaced by "I don't
  know")? What was the result for abstention rate, and why do the authors think
  it failed?
- Does this negative result support or weaken the project's choice to keep
  fine-tuning out of scope (RL/Search-R1 was parked)?

**My take.**

**Refined write-up.**

---

## §6 — Conclusion and Limitations

### 6.1 — What the authors admit they did not do
**Prompt.**
- List the stated limitations. One of them should be close to this project's
  thesis ("no iterative retrieval driven by the sufficiency signal"). Quote it:
  it is the cleanest positioning sentence for the README and ADR-001.
- "Binary vs graded sufficiency": this project uses a binary label with a
  **subtype** (`missing-hop`, `wrong-version`, `truncated`, `nonexistent`). Is
  that an answer to their limitation, or something different?
- Which limitation would a reviewer use against *this* project? (Hint: QA only,
  a single domain.)

**My take.**

**Refined write-up.**

---

## Appendix — Evaluation metrics (B.3)

### A.1 — How "correct" is graded
**Prompt.**
- Which QA metrics do they compare (exact match, contains, LLM-based eval such
  as FLAMe / LLMEval)? Which one do they use for the headline numbers?
- This project forbids an LLM judge on any primary endpoint (exact match +
  aliases; abstention from structured output). Does their comparison show a
  gap between LLM-graded and string-matched correctness large enough to change
  their conclusions? Use it as an argument for or against `evaluation/grader.py`.

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
