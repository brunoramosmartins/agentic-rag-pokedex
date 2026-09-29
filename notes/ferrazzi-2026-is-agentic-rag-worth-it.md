# Ferrazzi et al. 2026 — Is Agentic RAG worth it?

**Citation.** Pietro Ferrazzi, Milica Cvjetićanin, Alessio Piraccini, Davide
Giannuzzi. *Is Agentic RAG worth it? An experimental comparison of RAG
approaches.* Industry Day at LREC 2026. arXiv:2601.07711 —
<https://arxiv.org/abs/2601.07711>

**Why this source.** It is the closest published head-to-head of "enhanced"
(fixed pipeline) vs "agentic" RAG, with cost, and it is the empirical anchor for
three project decisions: arm **A3** (the implicit detector: the agent decides on
its own whether to search again), arm **A2** (the fixed pipeline that "must be
ruled out first"), and the Phase 8 feature **novelty of the last search**, which
comes straight from its result that the agent re-retrieves on 10% of queries
and, when it does, 53% of the documents come back unchanged.
Read in Phase 0, **after Joren 2025**: Joren gives the sufficiency vocabulary,
and this paper shows an agent that almost never uses its chance to look again.

**Cross-refs used throughout:**
- [`docs/hypothesis.md`](../docs/hypothesis.md) — H1, the S0 control stratum
- [`docs/adr/adr-001-theme-and-thesis.md`](../docs/adr/adr-001-theme-and-thesis.md) — positioning (see its Updates)
- [`docs/adr/adr-004-hand-rolled-agent-loop.md`](../docs/adr/adr-004-hand-rolled-agent-loop.md) — the loop
- `docs/evaluation.md` — cost per arm, the agent cost multiplier (Phase 4)
- `src/agentic_pokedex/classifier/features.py` — "novelty of the last search" (Phase 8)
- [`notes/joren-2025-sufficient-context.md`](joren-2025-sufficient-context.md)
- [`notes/open-ideas.md`](open-ideas.md) — specification sufficiency (relevant to §3.2, user intent)

**Legend.** 🔄 = needs synthesis with another source → `notes/phase0-synthesis.md`.

**Reading material** (local extraction, gitignored; paths under
`notes/sources/ferrazzi-2026-is-agentic-rag-worth-it/`): `manifest.json`, and
per prompt block — §1 → `sections/02`–`03`; §2 → `sections/04`; §3.1 →
`sections/06`; §3.2 → `sections/07`–`08` + `16` (invalid queries) + `29`–`31`
(routing system); §3.3 → `sections/09` + `36` (agent re-retrieval example);
§3.4 → `sections/10`; §4 → `sections/11`; §5 → `sections/12` + `33`
(limitations). The full agent trace in `sections/35` (C.1) is worth a look for
A3's loop.

---

## §1 — Introduction

### 1.1 — What "Enhanced" and "Agentic" mean here
**Prompt.**
- Write both definitions in the authors' words. Where does this project's A2
  (search → expand typed links up to budget B) fall: Enhanced, or neither?
- Is the paper's agent a ReAct-style loop? Which framework is it built on, and
  what can the agent do that the Enhanced pipeline cannot?
- Predict before reading §3: will the paper measure *answer correctness*, or
  mostly retrieval and routing quality?

**My take.**

Ferrazzi provides the architectural rationale for separating A2 and A3: a fixed
pipeline and an agent can use similar components, but they differ in who controls
the execution flow. A2 represents an explicitly engineered workflow, while A3
transfers that control to the LLM.

The most relevant point for this project is that this autonomy includes the
ability to retrieve again, but Ferrazzi primarily measures whether and how the
agent uses that capability, rather than whether it knows that the accumulated
evidence is already sufficient to stop. The paper therefore provides the
behavioral reference for A3, while this project adds an explicit mechanism for
studying the quality of the stopping decision.

A2 does not need to reproduce Ferrazzi's exact Enhanced implementation to serve
as the baseline. What matters is preserving the property being contrasted:
fixed workflow versus LLM-controlled workflow.

**Refined write-up.**

"Who controls the execution flow" is the right axis. Here are the three
sub-questions the take skipped, answered from the text.

*Definitions, in the authors' words.* **Enhanced RAG** is "a sequence of
modules, each responsible for improving a specific stage of the RAG pipeline",
where "the workflow is fixed" (Figure 1): router → rewriter (HyDE) → retriever →
reranker → generator. **Agentic RAG**: "the LLM acts as an orchestrator",
"no longer fixed pipelines, but rather iterative loops guided by the model
itself".

*Where A2 falls.* A2 (search → expand typed links breadth-first up to B) is
**Enhanced in kind**: a fixed workflow with a module added to naive RAG. It is
not Enhanced in *content*, since it has no router, no HyDE and no reranker. Its
module (typed expansion) is the one that matters for multi-hop evidence, and the
Phase 4 sweep tunes it in good faith. That is why E-002 measures what A2 already
delivers before any agent exists.

*The agent.*
- Built on **PocketFlow**, with **one tool** (the RAG tool); Appendix B states
  the single tool as a limitation.
- Each step: call the tool (optionally rewriting the query) or answer. That is
  ReAct-shaped: reasoning text, then an action, then an observation.
- It is capped at **3 turns** (Table 9 note). This project's A3 has T_max = 6
  and two tools (`search`, `open_page`). "Rarely searches again" is measured
  under a tighter cap than the one used here.
- What it can do that Enhanced cannot: skip retrieval, rewrite the query per
  case, and retrieve again.

*Prediction check.* The paper measures mostly **retrieval and routing quality**:
- routing is scored with F1 / recall;
- rewriting and refinement are scored with NDCG@10 against labelled relevant
  documents;
- answer quality appears only in §3.5, judged by an LLM.

No experiment scores the correctness of a final answer against a gold answer.
That shapes every conclusion below.

---

## §2 — Related Work

### 2.1 — Where the gap is
**Prompt.**
- What prior comparative studies do they cite, and why do they say those are
  insufficient?
- 🔄 Does the related work mention sufficiency, abstention or stopping at all?
  Compare with Joren §2.

**My take.**

Ferrazzi identifies an empirical gap in the literature: prior work had proposed
definitions and Agentic RAG architectures, but there were few controlled
experimental comparisons between Enhanced pipelines and Agentic systems. Their
paper addresses this by comparing the two paradigms across retrieval, intent,
LLM, and cost dimensions.

For this project, however, the reading reveals a second, more specific gap.
Ferrazzi measures whether and when an agent iterates, but does not measure
whether a stopping decision is correct relative to the sufficiency of the
evidence available at that point. Joren provides the notion of sufficiency, but
in a static context. P3 connects the two by treating `sufficiency(C_t)` as an
observable state throughout the trajectory and evaluating the `stop / retrieve`
decision against an exact label.

**Refined write-up.**

The take identifies the gap correctly. The prompt asked two concrete things,
answered here.

*Prior comparative studies and why the authors call them insufficient.*
- Neha and Bhati (2025) "propose a set of definitions and evaluation dimensions
  but stop short of conducting a full empirical study".
- Xi et al. 2025, Yang et al. 2024 and Chen et al. 2024 "limit the
  benchmarking to one of the two settings".

The gap Ferrazzi claims is **comparative and empirical**: nobody put both
paradigms side by side. The taxonomy attempts it cites include Singh et al.
2025, the survey this phase skims next.

*Sufficiency, abstention or stopping in the related work.* None. The words do
not appear. CRAG and Self-RAG are cited only as examples of *Enhanced* RAG
("enhancing the performances of basic pipelines"). Their evaluator and
reflection tokens are exactly the sufficiency-flavoured mechanisms that Joren §2
lists as uncalibrated relevance scores.

So the two related-work sections look at the same systems through different
lenses: Joren through what the context supports, Ferrazzi through who controls
the flow. Neither asks whether a stop was right. This two-sided silence is what
S.1 of the synthesis turns into the project's gap.

---

## §3 — Evaluation

### 3.1 — Datasets (§3.1, Table 2)
**Prompt.**
- List the four datasets and their task type. Are any of them multi-hop? This is
  the claim ADR-001 makes ("only single-hop datasets"): verify it against
  Table 2.
- Is there an unanswerable or out-of-scope condition anywhere? If not, what does
  that imply about what the paper *cannot* say about abstention?
- The project's S0 stratum (one hop, sufficient) is designed to "replicate the
  null" of this paper. After reading Table 2, is that a fair description?

**My take.**

Ferrazzi compares Enhanced and Agentic RAG across four representative tasks, but
none of the datasets is constructed as a multi-hop reasoning benchmark. This
makes the paper useful as a reference for agent behavior on relatively simple
tasks, but limits what its results can establish about iterative evidence
collection.

The presence of invalid queries also does not turn the study into an abstention
evaluation. The experiment primarily measures whether retrieval should be used,
and the authors explicitly leave the handling of out-of-scope queries
application-dependent. The central question of this project therefore remains
open: after retrieving some information, does the agent know when it still does
not have enough evidence?

S0 is a useful conceptual control for this setting because it represents the case
where a single retrieval should be sufficient. It is better described as a
controlled null for the value of iterative retrieval than as a direct replication
of Ferrazzi's experimental conditions.


**Refined write-up.**

The conclusion is right: S0 is a controlled null, not a replication. Table 2
makes it concrete.

*The four datasets (Table 2):*

| Task | Dataset | Domain | Queries | Relevant docs per query |
|---|---|---|---:|---:|
| QA | NQ | general | 3,452 | 1.2 |
| QA | FiQA | finance | 648 | 2.6 |
| IE/R | CQADupStack-EN | grammar forum | 1,570 | 1.4 |
| IE/R | FEVER | Wikipedia (claim verification) | 6,666 | 1.2 |

None is a multi-hop benchmark. With 1.2–2.6 relevant documents per query, one
good retrieval usually suffices. ADR-001's "only single-hop datasets" holds.
Strictly, some FEVER claims need evidence from more than one sentence or page,
but the benchmark is not built around composed hops.

*The consequence the take does not draw.* The headline behavioural finding (the
agent re-retrieves on 10% of queries, §3.4) was measured **only on FiQA and
CQADupStack-EN**, where one retrieval is usually enough. On those datasets,
rarely searching again may be the *right* decision. So the 10% cannot be read
as a stopping failure. That is the strongest reason this project needs strata
where one retrieval is provably *not* enough (S1–S4), with a label that says so.

*Unanswerable condition.* There is none. The "invalid" queries of §3.2 test
routing (should retrieval run at all?), not "the answer is absent from the
knowledge base". The paper can therefore say nothing about abstention, and it
does not try.

*S0 wording.* "Replicates the null" overstated the link. S0 is where the
project's own agent *should* stop at step 1. It tests whether a gain appears
where nothing needs detecting (the falsifier, outcome row 1), a role Ferrazzi's
design cannot play.

### 3.2 — User intent handling and query rewriting (§3.2–3.3)
**Prompt.**
- How is "user intent handling" defined, and how are invalid queries generated
  (Appendix: invalid query generation)? Is an out-of-scope query the same thing
  as this project's S4 (answer absent from the corpus)? Argue yes or no.
- Query rewriting: the agent wins on retrieval quality. Which metric (NDCG, see
  appendix), at which k? Is any significance test or CI reported?

**My take.**

Ferrazzi helps separate two problems that may initially look similar but operate
at different levels. User intent handling asks whether retrieval should be used;
S4 asks whether the answer can be obtained from the corpus. An out-of-scope query
is not necessarily unanswerable, and a valid query may still have no answer in
the corpus.

The query rewriting results show that giving the agent freedom to decide when
and how to rewrite can improve retrieval quality as measured by NDCG@10.
However, this also reinforces the need to isolate the mechanism studied by P3:
A4 should not improve retrieval itself, but decide whether the accumulated
evidence is sufficient to stop. This separation prevents a gain caused by
better query formulation from being attributed to sufficiency detection.

**Refined write-up.**

Both points are right: out-of-scope is not S4, and rewriting gains must not leak
into A4's credit. What follows adds the specifics and one connection.

*Definition and generation.*
- User intent handling is "the need of determining whether a certain query
  requires the usage of retrieval or not".
- Test set: 500 valid queries (from train splits) and 500 invalid ones per
  dataset. The invalid queries are **generated by GPT-4o, 5-shot**, and
  validated only by their average embedding similarity to the valid ones
  (Appendix A.2).
- NQ is excluded, because any query is valid there.
- What happens after an out-of-scope verdict is "application-dependent ... and
  therefore beyond the scope".

*Out-of-scope vs S4, the argument for "no".*
- An out-of-scope query should not trigger retrieval at all. It is a property of
  the query relative to the application.
- An S4 question is in scope: it asks about a Pokémon, a move, a version. It is
  exactly the kind of question the corpus serves, but the one section that
  answers it is withheld. Retrieval is the right first move there, and
  *abstaining after looking* is the right last move.

Routing decides before evidence; S4 decides after it.

*Connection to the parked idea.* Neither is the "specification sufficiency" of
`notes/open-ideas.md` either. An out-of-scope query is not underspecified. It is
addressed to the wrong system. So the paper's "intent" is a routing decision,
not a specification one, and it does not overlap with the parked idea.

*The FEVER result.* The agent's recall on FEVER is 49.3 (F1 64.6 vs 87.9 for the
router). It retrieves when it should not, which the authors attribute to
FEVER's loose domain. It is a first hint that an LLM's own judgment of "do I
need evidence?" is unreliable when the task boundary is vague, the upstream
cousin of Joren's finding.

*Query rewriting (Table 4).*
- Metric: NDCG@10.
- Agentic averages 55.6 vs Enhanced 52.8 (+2.8); +7.8 on NQ; about equal on FiQA
  (43.2 vs 43.5).
- **No intervals, no significance test, one run.** A 2.8-point average over four
  datasets, with one of them tied, is suggestive rather than established.
- For queries where the agent did not rewrite, the metric uses the original
  query, so part of the "agentic" score is simply naive retrieval.

### 3.3 — Document list refinement: the 10% / 53% result (§3.4, Appendix C.2)
**Prompt.**
- Quote the exact sentence with "10% of the times" and "53%". What is the
  denominator of each percentage (queries? retrieval calls? documents)?
- The authors interpret it as "once the model has taken a decision, it is not
  likely to reconsider it". Is that a claim about *search* or about *deciding*?
  Map it to the project's split (failing to search vs failing to decide).
- Read the example in Appendix C.2. Would a feature "overlap between the
  current and previous retrieval" have flagged it? This is the Phase 8 feature.
- How does this finding motivate arm A4p (the depth placebo)? If the agent
  rarely searches again, what does "searching more, blindly" buy?

**My take.**

Ferrazzi provides evidence that Agentic RAG has a low propensity for re-retrieval and that repeated retrieval often produces low document novelty. However, the experiment does not determine whether stopping or continuing was *correct* with respect to evidence sufficiency.

The key distinction for P3 is:

> Ferrazzi observes agent behavior; P3 measures whether that behavior is appropriate given the current evidence state.

This also provides a strong motivation for A4p. If A4 outperforms A3, the gain could come from simply performing more retrievals rather than from better stopping decisions. A4p isolates this alternative explanation by providing additional retrieval depth without explicit sufficiency-based stopping.

The relevant contrast is:

`A3` → implicit stopping  
`A4` → explicit sufficiency detection  
`A4p` → additional retrieval without sufficiency-based stopping

If A4 ≈ A4p, the observed gain may be explained primarily by greater search depth. If A4 > A4p, this provides stronger evidence that the quality of the stopping decision contributes to performance.

The retrieval-overlap feature also fits naturally into Phase 8, but it should be interpreted as a **search novelty** signal rather than a sufficiency signal. High overlap indicates that the new retrieval produced little novel document evidence; it does not, by itself, indicate that continuing to search was incorrect.

**Refined write-up.**

The A3 / A4 / A4p logic and the "novelty, not sufficiency" reading of the
feature are both right. The exact sentence and its denominators were missing,
and they change how strongly the result can be quoted.

*The sentence (§3.4):* "On average, in those cases in which the agent decided to
perform again the retrieval (10% of the times), 53% of the retreived documents
remain the same (example reported in Appendix C.2). This highlights that once
the model has taken a decision, it is not likely to reconsider it."

*Denominators.*
- **10%** is of *queries*, on the FiQA and CQADupStack-EN test sets only, with
  the agent capped at 3 turns.
- **53%** is of *retrieved documents* across those re-retrievals: the overlap
  between the second list and the first.
- The next sentence, "only in one case out of two modifies the retrieved
  documents", reads as a per-retrieval rate. The two readings are not the same
  statistic, and the paper does not reconcile them.
- No counts are given, only percentages. Under this project's N-of-M rule
  neither number would be quotable as is.

*Search or deciding?* The authors' gloss ("once the model has taken a decision,
it is not likely to reconsider it") is a claim about **deciding**: the agent
treats its first evidence as enough. The 53% is a claim about **searching**: when
it does look again, it barely looks anywhere new. So the result touches both
columns of the project's split. The design cannot tell which failure it is,
because nothing labels whether the first retrieval was sufficient (§3.1 above).

*Appendix C.2, the example, read closely.*
- The query: "What's the difference between 'these' and 'those'?"
- First retrieval: five forum *questions* about similar phrases, none
  explaining the difference. The agent says so ("do not provide a clear
  explanation") and retrieves again.
- The second list partly overlaps the first.
- It then **answers with five blog-post titles that appear in none of the
  retrieved documents** ("These vs. Those: Clarifying Usage", …), each
  attributed to a document and step.

That is Joren's failure inside Ferrazzi's own example: it recognised
insufficient evidence once, searched once more, stayed insufficient, and
answered anyway with fabricated support. An overlap feature would flag the
second retrieval as low-novelty. Only a sufficiency label would flag the
answer. This trace is the best single illustration for S.1 of the synthesis.

*Why this motivates A4p.* If blind extra search rarely finds new documents (53%
unchanged), then "searching more" should buy little on its own. A4p tests
exactly that. If A4 still beats A4p, the gain comes from *when* the agent stops,
not how much it searches.

The project also removes one reason for low novelty: A3 has `open_page` and typed
links, so a second step can reach evidence a re-query would not.

### 3.4 — Underlying LLM (§3.5)
**Prompt.**
- Which models are compared, and how is quality judged here (an LLM-as-judge)?
  This project forbids an LLM judge on primary endpoints; note which of the
  paper's conclusions depend on a judge.

**My take.**

This section exposes an important methodological limitation in Ferrazzi: the analysis of the underlying LLM depends directly on evaluation by another LLM.

They compare four Qwen3 generators — 0.6B, 4B, 8B, and 32B — under both Enhanced and Agentic settings. Final-answer quality is evaluated with Selene-70B, a fine-tuned model based on Llama-3.3-70B-Instruct. For FIQA, they use a binary classification metric; for CQADupStack-EN, they use a pairwise comparison between answers.

The authors make a reasonable effort to validate the judge. For CQADupStack-EN, they manually annotated 5% of the test set, covering 312 answer pairs. Inter-annotator agreement was 71.9%, while human-model agreement with Selene-70B was 65.4%. For FIQA, they rely on previous evidence that Selene is aligned with human judgments on financial QA.

Still, the conclusions in §3.5 are conclusions about **quality as measured by Selene**, rather than an independently measured ground-truth outcome.

For P3, the methodological distinction is important:

> Ferrazzi uses an LLM-as-a-judge to measure the outcome; P3 should not use an LLM-as-a-judge for primary endpoints.

This does not make Ferrazzi's experiment invalid. The judge is being used to answer a different question: how does apparent RAG quality change when the underlying generator is replaced? In P3, the central question concerns **evidence state and stopping decisions**. Allowing an LLM to determine correctness or sufficiency could contaminate the very mechanism being measured.

Conceptually:

`Qwen size → final-answer quality → Selene judge`

versus

`evidence state → gold sufficiency → deterministic evaluation`

The §3.5 result also does not show that Agentic RAG makes better use of stronger models. It shows that **both architectures benefit from more capable generators, with broadly similar scaling trends**. That conclusion remains conditional on the evaluation metric used for final-answer quality.

**Refined write-up.**

The facts are right: Qwen3 0.6B / 4B / 8B / 32B, Selene-70B as judge, 312
annotated pairs, 71.9% inter-annotator agreement, 65.4% human–model agreement.
Three things sharpen the conclusion.

*What the FiQA metric measures.* The binary score is "1 if the answer follows
the instruction, 0 otherwise" (Figure 2). That is **instruction-following**, not
answer correctness. The FiQA curve says larger models follow the prompt more
often, which is weaker than "answer better".

*How good the judge is.* On CQADupStack-EN the task is pairwise (pick A or B), so
chance agreement is about 50%.
- Humans agree with each other 71.9% of the time: about 22 points above chance.
- The judge agrees with humans 65.4%: about 15 points above chance, and **below
  the human ceiling**.

The judge adds noise on top of an already noisy task. This is the same
grader-ceiling problem measured in the previous project (its judge ceiling was
0.843), and the reason for measurability gate 4 here.

*What "no significant differences" rests on.* No test is described. The claim
is a visual comparison of two curves in Figure 2, on two datasets, judged by a
model below human agreement. The honest reading: *no difference visible at this
resolution*. That is not the same as *no difference*.

*For this project.* The take's diagram is the right contrast. One addition: in
an agent, the model also makes the *control* decisions, and the authors say so
("the model must not only produce the final answer but also make decisions at
each stage"). §3.5 then measures only the final answer, never the decisions. So
it cannot show whether a weaker model stops worse. That question is in scope
here only as a replication of H1's direction (ADR-008), not as a model-scaling
study.

---

## §4 — Cost and Time

### 4.1 — The cost multiplier
**Prompt.**
- What is measured (tokens, US$, latency) and how? Record the headline
  multipliers (the abstract says up to 3.6× cost).
- Is cost reported *next to* the quality gain, per dataset? The project reports
  the agent's cost multiplier next to every gain; is there a template here worth
  copying as a concept?

**My take.**

Ferrazzi does not directly measure monetary cost. They define runtime cost approximately through the number of input and output tokens processed, and separately report end-to-end latency. This choice is explicitly hardware-agnostic, allowing deployment cost to be estimated later from model throughput and infrastructure pricing.

The average Agentic-to-Enhanced multipliers in Table 9 are:

| Dataset | Input tokens | Output tokens | Latency |
|---|---:|---:|---:|
| FIQA | 2.7× | 1.7× | 1.5× |
| CQADupStack-EN | 3.6× | 1.8× | 1.4× |

Therefore, the abstract's "up to 3.6× cost" should not be interpreted as a direct 3.6× increase in US-dollar cost. The 3.6× figure is the largest observed multiplier for **input tokens**. The paper uses token usage as a runtime-cost proxy rather than reporting direct monetary cost per query in this analysis.

The broader idea of reporting cost next to quality gain is worth adopting. Ferrazzi does not always place quality and cost in the same table, but the paper explicitly frames the comparison as a performance-versus-cost trade-off.

For P3, this is especially useful because an apparent performance improvement could come from different mechanisms: better answers, better abstention, or simply more retrieval. Reporting the operational cost alongside the outcome makes those possibilities easier to distinguish.

The conceptual template is:

`performance gain + cost delta + latency delta`

For P3, an even more appropriate version is:

`Δ expected cost C + Δ tokens + Δ steps`

This prevents a conclusion such as "A4 improves accuracy" from standing alone. The relevant experimental question is also how much additional computation, retrieval, and generation were required to obtain that improvement.

**Refined write-up.**

The reading of the numbers is right: 3.6× is the largest *input-token* ratio,
not a dollar multiplier. The table matches Table 9's average rows. Three
additions.

*An internal inconsistency.* §4's text says agents need "an average of 3.3×
more input tokens and 1.9× more output tokens among datasets, as well as 1.5×
more time". Table 9's average rows give 2.7× / 1.7× / 1.5× (FiQA) and
3.6× / 1.8× / 1.4× (CQADupStack-EN). Their mean is about 3.15× / 1.75× / 1.45×.
The prose and the table disagree slightly, and the abstract's "up to 3.6×"
comes from the table. Quote the table, with its dataset.

*Under what cap.* Table 9's note: "Agentic RAG always performed a maximum of 3
turns. In scenarios requiring more turns, tokens consumed by the agent would
increase." The 3.6× is therefore a **lower bound** for deeper loops. This
project's A3 runs up to 6 steps, and A4 adds a judge call per step. The v1.0
budget already prices A4 at 5.6× A2 per question (central estimate), above
Ferrazzi's ratio. Phase 3 replaces the estimate with a measurement (and PI-007
is open on tuning cost).

*The template worth copying.* The take's `Δ expected cost C + Δ tokens + Δ
steps` is the right shape and matches how E-001 already reports: C is the
outcome, and tokens and steps are reported outcomes, never weights inside C
(ADR-005). One element from Ferrazzi's framing does *not* transfer directly:
**latency**. Registered runs use the Batch API, which is asynchronous, so
end-to-end latency there is meaningless. Latency is the cost a user feels first
in an agent with a judge call per step, but here it can only be measured on
synchronous calls: the dev loop and the demo. There it is a descriptive
number, labelled as such, and never an E-001 outcome. Steps per question is the
latency proxy that does survive batching.

---

## §5 — Conclusion and Limitations

### 5.1 — What the paper does not claim
**Prompt.**
- List the stated limitations. Is multi-hop reasoning among them?
- One-sentence positioning: "Ferrazzi et al. compare agentic and enhanced RAG
  on ___ and find ___; they do not measure ___." Fill the blanks. This sentence
  goes to ADR-001 and the README.
- 🔄 Joren shows models *answer* when context is insufficient; Ferrazzi shows
  agents rarely *search again*. Are these the same failure seen from two sides?

**My take.**

The main value of this section for P3 is that it clearly bounds what Ferrazzi actually established.

Ferrazzi shows that Agentic RAG can be more flexible in user-intent handling and query rewriting, that this flexibility comes with a substantial cost increase, and that Agentic RAG is not universally superior. However, the paper does not answer the central P3 question:

> When an agent decides to stop, is it stopping at the right point given the evidence it has accumulated?

The connection with Joren is strong as motivation, but there is still a causal gap between the two findings. Joren shows that models may answer with insufficient context; Ferrazzi shows that agents often do not retrieve again. Neither study measures evidence sufficiency at each retrieval step and compares that state with the agent's decision.

Therefore, the more defensible P3 gap is:

> **The missing measurement is not whether agents retrieve iteratively, but whether they know when the accumulated evidence is sufficient to stop.**

This is more precise than claiming that Ferrazzi does not study stopping at all. They do observe the agent's implicit decision to retrieve again or answer. What they do not measure is the **correctness of that decision relative to the sufficiency of the available evidence**.

The resulting conceptual bridge is:

`evidence state C_t → sufficiency S_t → decision d_t`

This connects the two strands of prior work without claiming that either paper already established the full causal chain.

**Refined write-up.**

The gap sentence at the centre of the take is the right one, and more careful
than the first version of ADR-001. The prompt's concrete asks follow.

*Stated limitations (Appendix B):*
- no document summarization or repacking;
- agents restricted to pure RAG with **a single tool**, so no insight into
  agents doing anything else.

Multi-hop reasoning is **not** listed. Neither is the absence of answer-level
ground truth, nor the 3-turn cap. The limitations a reader would add are larger
than the ones stated.

*The positioning sentence (for ADR-001 and the README):* "Ferrazzi et al.
compare agentic and enhanced RAG on four single-hop retrieval tasks (routing,
query rewriting, reranking, generator size) and find that neither is uniformly
better while the agent costs up to 3.6× more input tokens; they do not measure
whether the agent's decision to stop searching is correct given the evidence it
holds."

*Same failure from two sides?* Partly, and the precise answer matters:
- Joren's failure is **deciding**: with insufficient context, answer anyway.
- Ferrazzi's is **not searching again**, which is a failure only if the first
  retrieval was insufficient. On FiQA and CQADupStack-EN it often was not.

So they are the same failure *only on the insufficient states*, and neither
paper can pick those out on a trajectory:
- Joren has the label but no trajectory;
- Ferrazzi has the trajectory but no label.

The project's per-step label is the missing join. It lets the two findings be
tested as one: *at a state labelled insufficient, does the agent stop?* The C.2
trace (§3.3 above) shows they can co-occur in a single run.

---

## Lessons Learned

1. **More agentic does not automatically mean better RAG.**
   Additional flexibility can improve some dimensions while increasing token usage, latency, and operational complexity. The choice between Agentic and Enhanced RAG is therefore a context-dependent trade-off rather than a linear progression toward greater autonomy.

2. **Adaptive behavior must be measured, not assumed.**
   Allowing an agent to iterate does not mean that it will iterate usefully. The low re-retrieval rate and the substantial overlap in repeated retrievals illustrate why "agentic" should not be treated as synonymous with effective adaptive search.

3. **Cost should be reported alongside performance gains.**
   An architecture can improve a quality metric while being operationally less attractive because of higher token usage, latency, or execution cost. This reporting principle is directly relevant to P3.

4. **The underlying LLM is part of the workflow experiment.**
   In Agentic RAG, changing the underlying model affects not only final generation but also workflow-control decisions. Agentic results are therefore more sensitive to the choice of LLM than results from fixed pipelines.

5. **Final-answer evaluation is not sufficient to explain agent behavior.**
   The paper primarily evaluates retrieval behavior and final-answer quality. This shows what happened, but does not establish why the agent stopped, continued, or failed. This distinction motivates explicitly measuring the evidence state in P3.

## Failed Attempts

These are better recorded as **failed assumptions** rather than implementation failures by the authors.

1. **"More agentic" does not automatically mean better.**
   The implicit assumption that greater autonomy necessarily produces better retrieval does not hold uniformly.

2. **Iteration does not automatically mean useful exploration.**
   An additional retrieval round may simply reproduce evidence already obtained. Iteration count alone is therefore not a sufficient measure of search quality.

3. **A behavioral difference does not identify its mechanism.**
   Observing that Agentic RAG retrieves again in some cases does not establish whether the agent recognized insufficiency, attempted to improve retrieval, reformulated the query, or simply made an incorrect decision. An observable intermediate state is needed to distinguish these mechanisms.

4. **Final-answer quality cannot by itself diagnose stopping quality.**
   A correct answer does not prove that the stopping decision was correct; similarly, an incorrect answer does not by itself identify whether the problem was retrieval, stopping, or generation.

5. **Aggregate benchmark results can hide the control problem.**
   Aggregate quality and cost metrics are useful for comparing architectures, but they do not explain individual decisions along the retrieval trajectory. Studying stopping therefore requires observing `C_t`, `S_t`, and `d_t` at each step.