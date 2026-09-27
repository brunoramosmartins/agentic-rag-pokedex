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

**Cross-refs used throughout:**
- [`docs/hypothesis.md`](../docs/hypothesis.md) — H1/H2, central axis, per-stratum predictions
- `docs/examiner.md` — sufficiency labeler, minimal sufficient sets, subtypes (Phase 2)
- [`docs/adr/adr-001-theme-and-thesis.md`](../docs/adr/adr-001-theme-and-thesis.md) — positioning
- [`docs/adr/adr-006-judge-outputs-boolean-only.md`](../docs/adr/adr-006-judge-outputs-boolean-only.md) — the A4 judge
- `docs/evaluation.md` — grader, cost C ∈ {0, 1, λ}, selective metrics (Phase 4)
- [`experiments/registry.md`](../experiments/registry.md) — E-001 predictions and error taxonomy
- [`notes/phase0-foundation.md`](phase0-foundation.md) — phase note
- [`notes/open-ideas.md`](open-ideas.md) — parking lot

**Legend.** 🔄 = needs synthesis with another source. Cross-source questions
(Joren × Ferrazzi × Singh) go in `notes/phase0-synthesis.md`, not here.

**Reading material** (local extraction, gitignored; paths under
`notes/sources/joren-2025-sufficient-context/`): `manifest.json`, and per
prompt block — §1 → `sections/03`; §2 → `sections/04`; §3.1 → `sections/06`;
§3.2 → `sections/07` + `24`–`27` (autorater prompt); §4.1 → `sections/09`;
§4.2 → `sections/10` + `22`; §4.3 → `sections/11`; §5.1 → `sections/13`;
§5.2 → `sections/14` + `19`, `21`; §6 → `sections/15`; B.3 → `sections/23`.

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

Joren et al. provide the conceptual basis for separating two types of RAG failure: the retrieved context may be insufficient, or the model may fail even when the necessary information is available. Their paper treats sufficiency as a static property of a question–context pair. This project takes the same idea into a different setting: sufficiency is evaluated at each step of the agent loop and becomes a signal for deciding whether retrieval should continue or stop.

A key distinction is between context sufficiency and the LLM's ability to produce the answer. This project does not aim to measure the intrinsic ability of a model to answer the questions, but to evaluate a search policy driven by sufficiency. Therefore, the examiner should provide a judgment independent of the generator model, while final answer quality is evaluated separately. Running the experiment with a previous model serves as an additional robustness check for the strategy, rather than being part of the definition of sufficiency.

**Refined write-up.**

The take gets the core split right, but it answers only part of the prompt. Here
are the three sub-questions, answered from the text (§1).

*Two causes, in the authors' words.* (i) Models "generate incorrect answers on
a non-trivial fraction of instances that have sufficient context", so
"open-book QA cannot be solved by improving retrieval alone". (ii) "When given
instances without sufficient context, models tend to hallucinate more than they
abstain, especially for multi-hop questions." A third finding complicates both:
models are often correct *with* insufficient context, even after filtering out
questions answered closed-book.

*Mapping onto this project.* The mapping has three columns, not two:

| Joren | This project | Where it is measured |
|---|---|---|
| Context insufficient (retrieval did not deliver) | failing to **search** | `never-reached` |
| Answers instead of abstaining on insufficient context | failing to **decide** — the thesis | `stop-missing-hop`, `accepted-wrong-version`, `accepted-truncated-set`, `answered-unanswerable` |
| Wrong despite sufficient context | failing to **use** evidence | `generation-error` |

The project's contribution lives in the middle row. The third row is measured
but is not the thesis.

*Prediction check (time).* The authors define sufficiency as "a function of an
input pair consisting of one question and the associated context": static.
Iteration appears only in the limitations (§6.1 below).

*Which contribution carries the headline.* By the authors' own words, the "main
result" is the selective-generation method (§5.1). The finding that is quoted
most, and the one this project builds on, is contribution 2 (the behavioral
analysis).

*On the model-replication sentence.* It is correct and belongs to ADR-008's
scope statement: the GPT-4o-mini run replicates the *direction* of H1. It says
nothing about the definition of sufficiency, which the examiner fixes
independently of any model.

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

Joren et al. make a fundamental distinction for this project: relevance does not imply sufficiency. A retrieved result may be related to the question and still fail to provide enough evidence to determine an answer. This distinction is important because the agent's goal is not simply to retrieve relevant documents, but to accumulate sufficient evidence to justify terminating the search.

The cited literature shows that iterative and adaptive retrieval already exist, including mechanisms that decide when to retrieve again. Therefore, the project's gap should not be framed as introducing iterative retrieval itself. The more precise gap is to study sufficiency as a sequential property of the accumulated context and use it as an explicit criterion for deciding when further retrieval is no longer necessary. This positions the project closer to a study of a retrieval stopping policy than to a new iterative RAG architecture.

**Refined write-up.**

The reframing, from "iterative retrieval" to "a stopping policy", is the right
correction. The text supports it more precisely than the take states.

*Relevant but insufficient.* Figure 1 gives two cases for "Who is Lya L.
married to?":
- Context D is topically relevant (her job, birthplace, children) and says
  nothing about a spouse.
- Context C is relevant *and* mentions a marriage, but also a divorce and a later
  relationship, so no answer is determined.

C is the closer analogue of S2: evidence about the right entity that answers a
slightly different question.

*What the cited iterative work does.* The authors write that several methods
"use a model to predict relevance scores ... without calibration to a formal
definition ..., including for iterative retrieval (Jiang et al., 2024; Yan et
al., 2024)". Yan et al. 2024 is CRAG (read in Phase 5). So the gap Joren
identifies is not "nobody retrieves iteratively". It is that the iterative
controllers decide on an **uncalibrated relevance score**, not on sufficiency
against a definition. None of the cited work measures *when* a loop should stop
against a ground-truth notion of enough.

*Abstention and self-knowledge work cited:* Kadavath et al. 2022 (already on
the Phase 8 list), plus Chuang et al. 2024, Yin et al. 2023 and Zhang et al.
2024a. Only Kadavath has a consumer here (A5 features).

*Caveat for the gap claim.* This is the related-work section of a paper
submitted in 2024. Work published after it is checked in §6.1 below.

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

Joren et al. define sufficiency deliberately independently of the ground-truth answer: it is enough that there exists a plausible answer supported by the context. This makes the concept applicable at inference time, but it also allows a context that supports a plausible yet incorrect answer to be labeled sufficient.

For this project, this is a fundamental distinction. The minimal-sufficient-set construction defines a stronger predicate: it does not ask whether the context supports some plausible answer, but whether the context contains enough evidence to support the gold answer. S2 and S4 are natural examples where Joren may label the context as sufficient while the project's examiner should label it insufficient.

This is not a correction of Joren's definition. They are different predicates designed for different purposes: Joren seeks a ground-truth-independent sufficiency signal that can be computed at inference time; this project seeks an oracle sufficiency label for evaluating a sequential retrieval policy.

The project's label should therefore be understood as an operational definition for this experiment, rather than as a replacement or universal definition of sufficient context.

**Refined write-up.**

The conclusion is right: two predicates, two purposes. One project-level
correction follows.

*The exact definition.* "An instance q′ = (Q, C) has sufficient context if and
only if there exists an answer A′ such that A′ is a plausible answer to the
question Q given the information in C." "Plausible" means type-correct (a
birthplace must be a location). The authors say explicitly that this "allows
for the possibility that the context contains an *incorrect* answer", for two
reasons:
- the label must be usable at inference time, with no gold;
- the findings should be robust to noise in the gold labels.

*Stronger or weaker?* Write S_J for Joren's predicate and S_P for the project's
(the units seen cover at least one minimal sufficient set for the gold answer).
If a minimal sufficient set is covered, the gold answer is entailed by C, so a
plausible answer exists:

$$S_P(Q, C) \Rightarrow S_J(Q, C), \qquad S_J(Q, C) \not\Rightarrow S_P(Q, C).$$

The project's label is strictly stronger. The two can only disagree in one
direction: Joren says sufficient, the project says insufficient.

*Where they disagree — the correction.* The take names S2 and S4. Under a
careful reading they are the *weaker* examples. The section header states the
version (`Version: Ambergleam`) and the question asks for another one. Remark 3
("ambiguous contexts") and the autorater prompt's instruction to check
"assumptions implicit in the QUESTION" should push a competent rater to
*insufficient*. S2 and S4 disagree only if the rater silently assumes that
learnsets do not change between versions. That is rater leniency, not the
definition.

The clean definitional disagreement is **S3 in the main condition**:
- A partial list (6 of 14) *is* a plausible answer to "which Ice-type species
  learn Freeze-Dry by level?". A set of species is type-correct.
- With no truncation cue (ADR-009), nothing in C shows that it is partial.
- So S_J holds, S_P does not, and no amount of care from the rater changes that.

This is the case to cite when the label definition is recorded.

*Multi-hop (Remark 1).* Models "should not infer connections that are not in
the context". That matches S1: with the evolution chain unseen, the final form
is not in C, and both predicates say insufficient.

*Consequence for S.3.* The metric label is S_P, computed by the examiner. S_J is
at most a source of *wording* for the A4 judge prompt, which must work without
the gold. This closes ADR-001's open item once it is written in
`notes/phase0-synthesis.md` S.3 and recorded in the journal.

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

Joren et al. show that context sufficiency can be estimated at inference time using only the question and the retrieved context, without access to the ground-truth answer. However, the paper does not provide enough methodological detail about the construction of its human gold set: we know that 115 examples were labeled by human experts, but the number of annotators and inter-annotator agreement are not reported.

For this project, the important methodological point is to separate two roles. A4 acts as an inference-time sufficiency detector inside the agent loop and does not receive the gold answer; O2 provides the exact oracle label used afterward to evaluate whether the stopping decision was correct. Joren's prompt suggests useful concepts for A4, particularly question decomposition, implicit assumptions, and verification of required reasoning hops, but its explanatory output does not need to be transferred. The binary A4 output is a deliberate experimental design choice.

**Refined write-up.**

One factual slip about this project's own design, then the missing numbers.

*Correction: O2 is not the evaluator.* The exact label is computed by the
**labeler** (`labeling/sufficiency.py`) over the fact → units registry. It
scores the stopping decisions of *every* arm, A3 and A4 included. O2 is an
**arm**: it stops as soon as the exact label turns sufficient. It exists to
measure the *room* (O2 − A3), the most any stopping rule could gain, and it is
always labelled as an oracle. Three roles, not two:

| Role | Who | Sees the gold? |
|---|---|---|
| Inference-time detector (treatment) | A4 judge | No |
| Measurement of every stop | labeler | Yes, by construction |
| Ceiling of stopping | O2 (oracle arm) | Yes, and never a system score |

*The autorater.*
- **Model and shots:** Gemini 1.5 Pro, 1-shot; 0-shot drops to 0.870.
- **Output:** a written EXPLANATION (step-by-step sub-questions, then their
  answers), then a JSON binary label. So it produces a rationale plus a binary
  label.
- FLAMe (24B), the cheap rater used in §5.1, sees 1,600-token chunks, and a
  context counts as sufficient if **any** chunk is. That rule cannot see
  sufficiency spread across chunks, which is exactly the multi-hop case.

*Validation.*
- 115 instances drawn from PopQA, FreshQA, Natural Questions and
  EntityQuestions.
- The number of annotators and their agreement are not reported. The take is
  right on this.
- 93% of 115 is 107 of 115. The Wilson 95% interval is **86.9%–96.4%**
  (Wald: 88.4%–97.7%).
- The validation set contains **neither MuSiQue nor HotPotQA**, the multi-hop
  datasets the rater then labels in §4. The 93% does not transfer to them
  without evidence.

*What transfers to the A4 judge.* The concept to take from Appendix C.1 is to
decompose the question into the facts it needs and check the implicit
assumptions. There is one constraint the take does not mention: **prompt
parity** (ADR-006, E-001).
- An instruction such as "check assumptions implicit in the question" steers
  toward S2's version check.
- If it appears only in the judge prompt, H1 could measure the instruction
  rather than the separate call with veto power.
- The same checklist therefore goes verbatim into the shared agent prompt, so the
  only difference between A3 and A4 is the extra call with veto power.

*One observation from the appendix.* The FLAMe prompt as printed (C.2) swaps
the label descriptions: "sufficient: The documents are not sufficient". If that
reflects the prompt actually used, the logistic regression of §5.1 would
simply learn a negative coefficient, so the selective result survives. A
hard-threshold rule would not. This is an argument for measurability gate 7:
an instrument is run against a known answer before its number is trusted.

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

Joren shows that sufficiency varies substantially with how context is constructed: FreshQA reaches 77.4%, while HotPotQA and MuSiQue are around 46% at the 6k-token limit. MuSiQue is particularly informative because even with 20 supporting snippets provided by the dataset, fewer than half of the instances are classified as having sufficient context.

This reinforces that sufficiency should not be treated simply as a property of the dataset. It is a property of the context actually made available to the model, and that context depends on the retrieval or context-construction strategy. This distinction is even more important in this project because the agent constructs context over multiple steps, so `sufficiency(C_t)` can change throughout the trajectory.

Joren also suggests that additional context does not necessarily continue to increase sufficiency: there is almost no difference between the 6k- and 10k-token limits. However, the project's 4k evidence budget should not be justified as equivalent to the paper's 6k limit; it is an independent experimental constraint.

For Phase 10, MuSiQue should be treated as a difficult external validation domain rather than as a universal calibration reference for sufficiency. Its sufficient/insufficient distribution needs to be taken into account.

**Refined write-up.**

The central point, that sufficiency belongs to the context actually delivered,
is right. Two numbers need correcting, and one inference is stronger than the
take makes it.

*Numbers (Figure 2, % sufficient):*

| Dataset | 2k tokens | 6k tokens | 10k tokens |
|---|---:|---:|---:|
| FreshQA | 63.7 | 77.4 | 77.4 |
| HotPotQA | 45.4 | 46.2 | 46.2 |
| MuSiQue-Ans | 33.4 | 44.6 | 44.6 |

MuSiQue is 44.6%, not ~46%. Figure 1 gives the complement: 55.4% insufficient.

*The "20 supporting snippets" phrasing.* It is the paper's own phrasing, and it
is loose. A MuSiQue instance has 20 paragraphs: the supporting paragraph of
each hop (2–4) plus distractors. More importantly, **in MuSiQue-Ans every
supporting paragraph is present by construction**. The unanswerable
counterparts in MuSiQue-Full are built by removing one.

So an autorater that labels 55.4% of an *answerable-by-construction* set as
insufficient is disagreeing with the dataset's own construction. The paper
calls this "perhaps surprising" and leaves it there. Possible causes:
- the rater's strictness on multi-hop connections (Remark 1);
- a rater validated on single-hop-heavy data (§3.2 above);
- genuine leaks in MuSiQue's decompositions.

Truncation is not the cause: 20 paragraphs fit in 6k tokens, which is why 6k
and 10k coincide. Whatever the mix, this is the strongest argument in the paper
*for* this project's choice. LLM-rated sufficiency on multi-hop data disagrees
with a construction-based label on about half of the instances. ADR-007
replaces the rater with the construction.

*Dataset or retriever?* The three datasets confound the two:
- FreshQA uses oracle URLs;
- MuSiQue uses a fixed paragraph set;
- HotPotQA uses REPLUG top-5 retrieval.

Figure 2 cannot separate "the dataset is hard" from "the context construction is
poor". In a sequential setting the agent *is* the context constructor, so
sufficiency(C_t) is a property of the trajectory. That is why the project labels
states, not questions.

*B = 4,000 and Phase 10.* Agreed: B is an independent cap. For Phase 10, the
calibration sample uses MuSiQue-Full's answerable / unanswerable pairs, a
**construction** label of the same kind as this project's. The 44.6% from
Joren's rater is not a reference value for it.

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

Joren's main result is not simply that insufficient context leads to errors. The more interesting behavioral finding is that RAG does not automatically turn insufficient context into abstention. Models often interpret the presence of some contextual information as enough evidence to produce an answer.

The cases where models remain correct despite insufficient context are particularly relevant to this project. Joren identifies parametric knowledge and contextual cues as possible sources of these successes, but these sources remain partially entangled. The counterfactual twin provides a simple intervention to separate them: remove entity-specific parametric knowledge while preserving the informational structure of the context.

This makes A0 + the twin + G2 more than a sanity check. Together, they help test one of the main alternative explanations for correct answers under insufficient context. Joren demonstrates the phenomenon; this project attempts to identify more clearly where that phenomenon comes from.

Finally, Joren's results are primarily descriptive. The project can adopt a stricter reporting standard by explicitly writing every denominator as N-of-M, reporting uncertainty intervals, and using hypothesis tests and multiple-comparison correction when formal hypotheses require them.

**Refined write-up.**

The take's framing, where Joren shows the phenomenon and the project locates its
source, is good. It overstates what the twin removes, and it skips the table and
the exact comparison the prompt asked for.

*The 2×3 table.* The abstain / hallucinate split is only in Figure 3 (a bar
chart, not extractable from the text). The correct column is in Table 5
(LLMEval), for example Gemini 1.5 Pro on MuSiQue:

| Context | Correct | Abstain | Hallucinate |
|---|---:|---|---|
| Sufficient | 83.4% | Fig. 3 only | Fig. 3 only |
| Insufficient | 49.5% | Fig. 3 only | Fig. 3 only |

The claim "models answer instead of abstaining" lives in the insufficient row:
hallucinate > abstain. Across Table 5, the insufficient-context correct rates
for the three large models run 33–61%, which is the paper's "35–62%". Gemma 27B
is far lower.

*What the twin removes — correction.* The authors name two sources:
pre-training knowledge, and contextual cues. The twin removes only the first,
and only its **entity-specific** part. Their own Table 2 (§4.3) lists sources of
correct-but-insufficient answers that the renaming does not touch:
- yes/no and limited-choice guessing;
- inference from domain-general knowledge (a model still knows how Pokémon
  mechanics work);
- reasoning over many hops.

So in the twin, "correct despite insufficient evidence" should shrink, not
vanish. What remains is a measure of guessing and generic inference. That has
a concrete consequence, flagged in chat: **any template with a small answer
space** (a type, one of 18; a yes/no) has a chance-level correct rate. The G2
closed-book threshold (≤ 5%) needs a chance baseline per template, or the gate
could fail on guessing rather than leakage.

*The exact RAG vs closed-book comparison.* Same questions, same model:
abstention without RAG vs with RAG. Claude 3.5 Sonnet 84.1% → 52%; GPT-4o 34.4%
→ 31.2%; Gemini 1.5 Pro 100% → 18.6%. It is an overall rate, not restricted to
insufficient contexts.

This project has the same contrast, controlled: A0 (closed-book) vs A1
(single-shot) on the twin, under the same cost instruction. With memory removed,
A0 should abstain almost always, so the A1 abstention drop isolates "context
makes it answer". It is a descriptive reading, not a new endpoint.

*Statistical rigor.* Instance counts are given per dataset (FreshQA 452; 500
sampled from MuSiQue and from HotPotQA), but not per cell. There are no
intervals and no tests, and model × dataset comparisons are not corrected. The
numbers would not pass the N-of-M rule, as the take says.

### 4.3 — Qualitative analysis of insufficient-context answers (§4.3)
**Prompt.**
- List the categories the authors find for "correct despite insufficient
  context". Does any category match S2 (near-certain evidence from the wrong
  version) or S3 (a partial set)?
- 🔄 Compare their categories with this project's error taxonomy (E-001 draft /
  `docs/evaluation.md`). Is there a category you are missing, or one of theirs
  the twin makes impossible?

**My take.**

Joren shows that "correct despite insufficient context" is not a single phenomenon. It can arise from parametric knowledge, constrained answer spaces, ambiguous interpretation, complex reasoning, or evaluator error. The multi-hop categories are the closest to this project because they show how an LLM can compensate for a missing reasoning hop using knowledge that is not present in the retrieved context.

In this project, the counterfactual twin is an important intervention because it directly attacks the parametric-knowledge explanation. At the same time, the controlled question construction removes or reduces other Joren categories, such as ambiguity. Therefore, the project's error taxonomy does not need to reproduce Joren's taxonomy.

The main implication for E-001 is different: an agent can make an incorrect stopping decision on insufficient context while still producing the correct answer. This should be distinguished between decision error and outcome correctness, because they represent different phenomena for the central hypothesis.

**Refined write-up.**

The last paragraph is the most useful idea in this note, and it exposes a real
gap in E-001.

*The eight categories (Table 2):*
1. yes/no;
2. limited choice;
3. multi-hop fragment (parametric inference);
4. multi-hop partial (parametric knowledge);
5. too many hops;
6. ambiguous query;
7. rater error;
8. closed-book correct.

What the project does to each:

| Category | Fate in this project |
|---|---|
| Closed-book correct; multi-hop partial | Reduced by the twin (entity memory removed) |
| Rater error | **Eliminated**: there is no rater; the label is exact |
| Ambiguous query | Reduced by the generator's ambiguity filter |
| Yes/no; limited choice | **Survive**: chance guessing on small answer spaces |
| Multi-hop fragment | **Survives** in part: domain-general inference is not renamed |
| Too many hops | Not a sufficiency case here (S3 sets are graded by set equality) |

Rater error is the category only an exact label removes. It is part of why the
project does not need Joren's taxonomy: one of its eight causes cannot occur by
design. The survivors can.

*Decision error vs outcome correctness — the gap.* The error taxonomy in E-001
is outcome-first: its codes describe wrong answers or wasted search. A question
answered **correctly at a step labelled insufficient** (a lucky stop) gets C = 0
and no code. That is Joren's 35–62% phenomenon, and the take is right that it is
a different thing from a correct stop. It matters for H1 in a specific way. When
the judge vetoes a lucky answer, it makes the *right* decision and can raise C
(0 → 1 if the agent then abstains). The mechanism metrics (precision and recall
against the exact label) see this; C alone hides it.

By construction, most strata leave little room for luck:
- S2 filters level pairs that differ from every other version;
- S3 grades by set equality;
- S4's only correct action is to abstain.

The residue is S1 with small answer spaces. Proposed in chat as an E-001
amendment: a counted, non-error code `correct-at-insufficient`, reported per
arm.

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

Joren shows that the sufficient-context signal adds information beyond the model's self-rated confidence and can improve the accuracy-coverage trade-off. The method is essentially a lightweight classifier that combines cheap signals and converts its score into an abstention policy.

The connection to A5 is structural, but A5 is not simply a sequential replication of Joren's method. Joren predicts hallucination for a single decision on a question; A5 predicts sufficiency for the current state of a retrieval trajectory and uses that prediction to decide whether to stop or retrieve again. The main extension is therefore temporal: the stopping decision depends on `C_t`, and that decision changes the context observed at the next step.

There is also a difference in objective. Joren optimizes selective accuracy across different coverage levels without an explicit cost function. This project makes the trade-off explicit through `C` with `λ = 4` and derives the A5 threshold from that cost.

**Refined write-up.**

The distinction between the two uses (one decision per question vs a decision per
trajectory state) is correct. Here it is written as the algorithm the prompt
asked for, followed by what the take leaves out.

*The method (§5.1).*
- **Inputs, per question:**
  - a self-rated confidence: P(True) for open models (20 sampled answers, each
    judged 5 times by the model) or P(Correct) for proprietary models (the most
    likely and second most likely answers with self-stated probabilities);
  - a binary sufficiency label from FLAMe.
- **Model:** logistic regression predicting *hallucination*, with 100 iterations
  of random hyperparameter search.
- **Decision:** abstain when the score is below a threshold. Sweeping the
  threshold traces selective accuracy (correct / answered) against coverage.

*Metric and baseline.*
- The metric is a selective accuracy-coverage curve (Figure 4). There is no AURC
  and no interval across seeds.
- The baseline is confidence alone.
- The "2–10%" is read at chosen coverages: over 10% for Gemma 27B on HotPotQA in
  the high-accuracy region, over 5% for Gemini near 70% coverage.
- For Gemma on MuSiQue the sufficiency coefficient is 0 (18.4% base accuracy),
  so the gain vanishes. That is a useful negative: the signal needs a model with
  non-trivial accuracy on both sides.

*Implicit λ.* There is none. Choosing a coverage *is* choosing λ implicitly. The
selective-classification relation is: answer iff P(correct) > 1 − 1/λ. So
picking a threshold on P(correct) fixes λ = 1 / (1 − threshold). This project
states λ first and derives the threshold (ADR-005).

*What changes sequentially (for Phase 8).* Two things Joren does not face:
- **The decision changes the data.** The state at t+1 exists only if the policy
  said "search" at t, so training states are policy-dependent. This is the
  distribution-shift problem the A5 design handles with real trajectory states.
- **Errors compound over steps.** A per-step false "sufficient" ends the
  trajectory. A per-step false "insufficient" costs one search, until T_max.

Both are carried into the Geifman & El-Yaniv reading.

### 5.2 — Fine-tuning for abstention (§5.2 + Appendix A.2, B.1)
**Prompt.**
- What exactly was trained (Mistral 7B, 20% of targets replaced by "I don't
  know")? What was the result for abstention rate, and why do the authors think
  it failed?
- Does this negative result support or weaken the project's choice to keep
  fine-tuning out of scope (RL/Search-R1 was parked)?

**My take.**

Joren's fine-tuning experiment is a relevant negative result for this project. Teaching the generator to produce "I don't know" on a fraction of training examples did not create a reliable abstention policy: hallucination remained high, and the abstention rate did not increase relative to Vanilla RAG.

This supports keeping abstention detection outside the generator. The project does not try to make the LLM more "humble"; it introduces a separate component that decides whether the current context is sufficient. This makes the intervention more controllable and allows the stopping policy to be evaluated directly without confounding it with changes in generation behavior.

The result does not justify claiming that fine-tuning is inherently unsuitable. It supports the narrower conclusion that simple abstention fine-tuning is not a sufficiently controllable solution for this project's experimental objective.

**Refined write-up.**

The take is accurate. It even catches a nuance the introduction blurs: the
introduction says fine-tuning "can lead to a higher abstention rate", but
Appendix B.1 shows that holds only relative to Data Mix 1.

*The experiment (B.1).*
- Model: Mistral 3 7B Instruct, fine-tuned with LoRA.
- Data: 2,000 instances per dataset, in three mixes:
  - Mix 1: ground-truth answers;
  - Mix 2: 20% of answers replaced by "I don't know" at random;
  - Mix 3: 20% replaced among instances the rater labels insufficient.
- Results:
  - fine-tuning raised the correct rate on MuSiQue but not on HotPotQA;
  - Mix 2 and Mix 3 abstained more than Mix 1, but **not more than Vanilla
    RAG**, refuting the authors' hypothesis;
  - hallucination stayed high, usually above abstention.

*What it supports.* Exactly the narrow reading in the take. It is evidence
against *naive* abstention fine-tuning at 7B with 2,000 examples. It is not
evidence against training in general. The parked RL detector (Search-R1 style)
stays parked for hardware reasons, not because of this result.

The positive lesson matches §5.1's own argument: a controller that "operates
independently from generation" can be tuned without side effects on the
generator. That is the design of A4 and A5.

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

Joren's limitations are important because the authors themselves identify the natural transition from static sufficiency to iterative retrieval decisions. This provides a direct conceptual origin for this project. However, the gap can no longer be framed as "no prior work uses sufficiency to control iterative retrieval": later work has explicitly studied sufficiency-based control in multi-round RAG.

The project's differentiation therefore needs to be stated at a different level. The focus is on experimentally measuring and decomposing a sequential stopping policy using exact per-step labels, minimal sufficient sets, controlled strata, a counterfactual twin, and a strict separation between detector, oracle, and generator. The contribution is therefore more about experimental design and measurement of the phenomenon than about introducing sufficiency-driven iterative RAG itself.

The main external-validity limitation is generalization. A single QA domain and a constructed world provide strong experimental control, but leave open how well the observed behavior transfers to other domains and tasks.

**Refined write-up.**

The take is right that the gap has moved, and it is the most consequential
point in this note. It needed its sources checked and the differentiation made
specific. Checked on 2026-09-26.

*The positioning sentence.* "Also to achieve the best performance, we could have
used our autorater to iteratively judge whether to retrieve more or answer the
question." (§6, Limitations.) Future work adds "a fine-grained sufficient
context autorater, which outputs a score instead of a binary label".

*Later work that does what the limitation describes:*

| Work | What it does | How "sufficient" is labelled | What it lacks for this project's question |
|---|---|---|---|
| Yang et al., SIGIR 2025 (SIM-RAG, arXiv:2505.02811) | Trained sufficiency Critic per round in multi-round RAG | **By outcome**: a path is "successful" if it reaches the correct final answer | Outcome labels absorb every lucky stop (§4.3); no per-step ground truth |
| Li et al., 2026 (S2G-RAG, arXiv:2604.23783) | Judge outputs sufficient + **gap items**, mapped into the next query | Not stated in the abstract | Stopping is confounded with query reformulation — the variant ADR-006 rejects and parks |
| Luo, 2026 (arXiv:2608.13237) | S2G-style stopping judge inside Search-R1; HotPotQA only | Learned judge (3,009 states) | No abstention, no cost for wrong answers, no depth control; effect −3.7% calls, −0.63 EM |

*Differentiation, stated precisely.* The project does not introduce
sufficiency-driven iterative RAG. What it adds to this line of work:
1. Per-step sufficiency labels that are **exact by construction** (minimal
   sufficient sets), not derived from outcomes or rated by an LLM.
2. A stopping detector that changes **only the stop** (a veto-only boolean
   judge), with a **depth placebo** (A4p) separating "knows when to stop" from
   "searches more".
3. **Contamination control** (the twin), so correct-despite-insufficient
   cannot come from entity memory.
4. **Abstention priced into the outcome** (C = 0 / 1 / λ), with λ\* instead of a
   single operating point.

None of the three works above has more than one of these.

*Binary vs graded.* The project's subtype (`missing-hop`, `wrong-version`,
`truncated`, `nonexistent`) is not the graded score Joren asks for. It is a
*diagnosis* of why a state is insufficient, available because the examiner
knows the gold chain. A graded score is the A5 classifier's output.

*The limitation a reviewer would use.* The take names one domain and a
constructed world. Add the model: one configuration (ADR-008). All three are
already stated in `docs/hypothesis.md` → Scope.

*Consequence.* ADR-001 said its positioning is revised if prior work already
measures per-step sufficiency in a multi-hop loop. These works *control*
retrieval with a sufficiency signal. They do not *measure* it against an exact
label. The ADR stands, but its context should cite them, and the reading plan
gains them (proposed in chat).

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

Joren's comparison shows that simple lexical evaluation is too strict for free-form QA: formatting differences and semantic equivalents create false negatives, while substring matches can create false positives. The numerical differences can be substantial, but the main qualitative patterns remain consistent across both evaluators.

For this project, this does not justify using an LLM judge. A deterministic grader with explicit aliases provides a useful middle ground: it captures known semantic equivalences without introducing another probabilistic model as the source of truth. This is especially important because the project aims to measure a stopping policy; correctness evaluation should not itself depend on another LLM judgment.

**Refined write-up.**

The take is right. The table makes the argument sharper.

*What is compared.* Contains Answer (does the response contain a gold string)
vs LLMEval (an LLM classifies each response as correct / abstain /
hallucinate). **The headline numbers use LLMEval.** It is applied to responses
where a clear string match "could not be determined" (§4.2).

*How big is the gap (Table 5, sufficient context).*
- Gemini 1.5 Pro on MuSiQue: 60.1% vs 83.4% (23 points).
- Gemma 27B on HotPotQA: 40.7% vs 64.1%.
- One inversion: Gemma on FreshQA with insufficient context, 11.8% vs 6.9%.
  There, Contains counts *more* answers as correct than LLMEval does. That is
  the partial-match false positive of the paper's own example ("The Rings of
  Power"): a string metric can be too lenient as well as too strict.

The *patterns* survive (hallucination with sufficient context; poor abstention
with insufficient context). The *levels* do not. So the evaluator changes the
number, not the phenomenon, exactly as the Lessons below put it.

*Why the project's grader escapes both failure modes.*
- Contains Answer fails on formatting and synonyms. The project's answers are
  **generated from the graph**, so the alias list is enumerable: twin names,
  numbers, and set members. It is not open-ended.
- LLMEval fails by being a model, and an LLM-judged endpoint in a study whose
  treatment is an LLM judge would stack two models.
- Structured output removes the third problem, detecting abstention in free
  text.

The remaining risk is a *format* failure, not a semantic one: `format-error`,
audited at gate 4 (≥ 98/100).

---

## Lessons Learned

### 1. Evaluation can change the number without changing the phenomenon

Joren's B.3 comparison shows that lexical and LLM-based correctness measures can
produce substantially different absolute rates while preserving the same
qualitative conclusions. The evaluator is therefore part of the measurement
instrument, not a neutral implementation detail.

### 2. Determinism does not require naive string matching

The alternative to an LLM judge is not necessarily raw exact match. Explicit
aliases provide a deterministic way to handle known semantic or formatting
variants while keeping the correctness decision auditable.

### 3. The primary endpoint should remain independent of the treatment

Because A4 itself is an LLM-based intervention, using another LLM to grade the
primary outcome would introduce an avoidable measurement dependency. The
deterministic grader keeps the treatment and the measurement instrument
separate.

## Failed Attempts

No project-level failed attempt was identified from this reading. Instead, Joren's
B.3 comparison prevented two design choices from entering the experiment:
using raw lexical matching as the sole correctness criterion, and using an LLM
judge as the primary endpoint grader.
