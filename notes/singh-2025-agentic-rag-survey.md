# Singh et al. 2025 — Agentic RAG: A Survey (skim)

**Citation.** Aditi Singh, Abul Ehtesham, Saket Kumar, Tala Talaei Khoei,
Athanasios V. Vasilakos. *Agentic Retrieval-Augmented Generation: A Survey on
Agentic RAG.* arXiv:2501.09136 (2025, revised 2026) —
<https://arxiv.org/abs/2501.09136>

**Why this source.** Mode: **skim**, not a full read (42 pages). It serves one
decision: **placing the arms (A1–A5) in a published taxonomy** so the README and
ADR-001 use vocabulary a reader recognizes. Read last in Phase 0, after Joren
and Ferrazzi. Only the sections below are worth your time; the application
sections (healthcare, finance, legal…) are not.

Rule for surveys: every claim this project relies on must be traced to its
primary source; the survey is a map, never a citation for a number.

**Cross-refs used throughout:**
- [`docs/adr/adr-001-theme-and-thesis.md`](../docs/adr/adr-001-theme-and-thesis.md) — positioning (see its Updates)
- `README.md` — "how this fits the literature" paragraph (Phase 7)
- [`notes/yan-2024-crag.md`](yan-2024-crag.md), [`notes/jeong-2024-adaptive-rag.md`](jeong-2024-adaptive-rag.md) — the primary sources behind two taxonomy boxes

**Legend.** 🔄 → `notes/phase0-synthesis.md`.

**Reading material** (local extraction, gitignored; paths under
`notes/sources/singh-2025-agentic-rag-survey/`; the extraction splits the
survey into 105 small files): `manifest.json`, and per prompt block — T.1 →
`sections/27`–`69` (taxonomy §5: router 28–30, multi-agent 31–36,
hierarchical 37–42, **corrective 43–47**, **adaptive 48–52**, graph 53–63,
document workflows 64–69) + `70` (comparative table); W.1 → `sections/22`
(prompt chaining), `23` (routing), `26` (evaluator-optimizer); L.1 →
`sections/89` and `93` (lessons), `96` (benchmarks), `99` (evaluation beyond
output quality).

---

## §Taxonomy — "Taxonomy of Agentic RAG Systems"

### T.1 — Where do the arms sit?
**Prompt.**
- For each box (Single-Agent Router, Multi-Agent, Hierarchical, Corrective,
  Adaptive, Graph-Based, Document Workflows), write one line: who decides to
  retrieve again, and on what signal?
- Place A3 (implicit), A4 (boolean judge after each observation) and A5
  (calibrated classifier) in the taxonomy. Is A4 "Agentic Corrective RAG"? What
  is different (the judge only controls the loop; it never rewrites or adds
  context)?
- Does any box name the *stopping decision* as its central object? If not, that
  is the gap sentence for ADR-001.

**My take.**

My reading is that the survey organizes the systems mainly around how control is distributed, rather than around the stopping decision itself. In Single-Agent Router systems, a central agent chooses the source or retrieval strategy based on the query. In Multi-Agent systems, a coordinator distributes parts of the task among specialized agents, often allowing retrieval to happen in parallel. In Hierarchical systems, a higher-level agent evaluates the query and decides which agents or sources should be invoked. In Corrective RAG, an evaluator checks the relevance or quality of the retrieved context and, when it is inadequate, the system can refine the query or retrieve additional information. In Adaptive RAG, a classifier estimates query complexity and selects among no retrieval, simple retrieval, or a multi-step strategy. In Graph-Based RAG, the system combines graph and text retrieval with critique or feedback mechanisms to refine the search. Document Workflows treat retrieval as part of a broader workflow, maintaining state across multiple stages.

Within this map, I see A3 as closest to a Single-Agent Agentic RAG system with implicit control: the model itself decides what to do, including when to stop. A4 is clearly related to Corrective RAG because an evaluator is introduced after an observation, but I would not simply call A4 Agentic Corrective RAG. The important difference is that the A4 judge is designed to control only the decision to continue or stop; it does not improve the query, add context, or perform the correction itself. This is intentional in the project because we want to isolate the effect of sufficiency detection.

A5 also does not look like Adaptive RAG in the classical sense used by the survey. Adaptive-RAG uses query complexity to choose the strategy. A5 uses a classifier over the current process state to decide whether the accumulated evidence is already sufficient. The relationship is clearly close, but the object of the decision is different.

What stands out to me is that the survey explicitly discusses the need to decide when the available evidence is sufficient and also discusses stopping criteria, but this does not appear as a category or central dimension of the taxonomy. My reading, therefore, is that there is substantial literature on adaptive retrieval, correction, and control, but I did not find in this taxonomy a category whose definition is the sequential decision to stop based on the sufficiency of the accumulated evidence.

**Refined write-up.**

The take is accurate. Its strongest claim, that the survey names the decision
but gives it no box, checks out against the text, and the evidence can be
quoted.

*The two places the survey names it.*
- §1 describes agentic RAG as "autonomous control mechanisms that dynamically
  decide when to retrieve, how to reformulate queries, and **when sufficient
  evidence has been collected**".
- §10.4 recommends "bounded planning horizons, predefined tool access policies,
  and **explicit stopping criteria**".

Across the whole survey, "sufficien-" appears 7 times, and three concern
evidence:
- the §1 sentence;
- twice in Corrective RAG (§5.4), "when context is insufficient", where web
  search is triggered. There, insufficiency is inferred from **per-document
  relevance**, not judged on the accumulated state.

The §1 and §10.4 mentions are different things.
- §10.4's stopping criteria are **budget bounds**. In this project that is
  T_max = 6 and B = 4,000.
- §1's "when sufficient evidence has been collected" is a **detector**. In this
  project that is A3's implicit judgment, A4's judge, or A5's classifier.

The survey conflates them. The project keeps them apart, since the caps are
identical in every arm and never the treatment. That gives the gap sentence
for ADR-001, with a citation: *the survey lists deciding "when sufficient
evidence has been collected" among the defining capabilities of agentic RAG,
but none of its seven taxonomy categories is organised around that decision,
and its only stopping guidance is a budget bound.*

*Box by box: who decides to retrieve again, and on what signal.*

| Box | Decides to retrieve again | Signal | Closest arm |
|---|---|---|---|
| Single-agent router | the one agent | query type → source choice | A3, as a single agent |
| Multi-agent | coordinator | subtask split | — |
| Hierarchical | top-level agent | query analysis | — |
| **Corrective** | relevance evaluator (5 agents in the survey's version) | per-document relevance below a threshold → refine query, web search | A4's *placement*, not its *action* |
| **Adaptive** | complexity classifier, **before** any retrieval | query complexity | A5's *shape*, not its *object* |
| Graph-based (Agent-G, GeAR) | critic module | quality of graph/text evidence | — |
| Document workflows | workflow state | stage completion | — |

*A4 and Corrective, precisely.* The survey's Corrective RAG has a relevance
evaluator **and** three corrective actors: query refinement, external search,
and response synthesis over "validated and refined information". A4 keeps only
the first and removes its output: the judge's yes/no controls the loop and
reaches nothing else (ADR-006). Two further distinctions:
- A4 judges **the accumulated state** (is all of this enough?); CRAG's
  evaluator judges **each document** (is this one relevant?). Relevant-but-
  insufficient is exactly where they part (Joren §2).
- The survey's five-agent version is its own agentic re-description. The
  primary source, Yan et al. 2024, has a lightweight evaluator with three
  actions (correct / incorrect / ambiguous) plus knowledge refinement. Cite Yan
  for CRAG, never the survey (the rule for surveys at the top of this note).

*A5 and Adaptive.* Adaptive-RAG decides **once, before evidence**, from the
query alone. A5 decides **at every step, after evidence**, from the state. A
complexity classifier cannot tell that the second search returned the wrong
version. The take has this right; the "before / after evidence" split is the
one-line version for the README.

---

## §Workflow patterns — "Evaluator-Optimizer" and "Routing"

### W.1 — Two patterns that look like this project
**Prompt.**
- Is the A4 loop an instance of Evaluator-Optimizer? Is A2 an instance of
  Prompt Chaining? One line each.
- Routing (Adaptive-RAG style) is the thesis ADR-001 discarded. Does the
  survey present routing as a quality or a cost argument?

**My take.**

A4 has a clear relationship to the Evaluator-Optimizer pattern: there is an evaluator inside a loop, and its evaluation can trigger another iteration. However, I would not consider A4 a complete instance of this pattern because the judge's feedback is not used to improve the answer, reformulate the query, or modify the context. It controls only the decision to stop or continue.

A2 resembles Prompt Chaining because it is a fixed sequence of steps, but I would not directly call it Prompt Chaining. Typed expansion in the pipeline is a deterministic retrieval operation, whereas the pattern described in the survey is about decomposing a task into stages where each stage builds on the previous one. So I see A2 as a fixed sequential pipeline that is analogous to chaining at the control-flow level, but not necessarily as an implementation of Prompt Chaining.

Routing in the survey appears as both a quality and an efficiency concern. The idea is to direct different queries to specialized processes and, in some cases, use smaller models for simple queries and more sophisticated strategies for complex ones. This reinforces the decision not to make routing the thesis: routing primarily answers the question "which strategy should I use for this query?", whereas our problem is "given the evidence I already have, do I need to keep searching?"

**Refined write-up.**

All three answers hold up against the text. Each can be made one line sharper.

*A4 vs Evaluator-Optimizer (§4.5).* The pattern "iteratively improves content
by generating an initial output and refining it based on feedback from an
evaluation model". Three differences, not one:
- the evaluated object is an **output** there and an **evidence state** here;
- the evaluation comes **after** generation there and **before** it here;
- the feedback is **consumed** there and **discarded** here.

A4 borrows the loop and the evaluator and removes the feedback channel. That
removal is the experimental control.

*A2 vs Prompt Chaining (§4.1).* Prompt chaining "decomposes a complex task into
multiple steps, where each step builds upon the previous one", and each step is
an LLM call. A2 has **one** LLM call, the answer, after a deterministic retrieval
and expansion. There is no chain of prompts. The survey's taxonomy has no
separate name for "deterministic retrieval → one generation"; its §2.3 calls
this *Advanced/Modular RAG*, the closest match, and the same family Ferrazzi
calls *Enhanced*.

*Routing: quality or cost?* Both, as the take says. §4.2 claims routing
improves "efficiency and response quality". The argument against making it the
thesis is stronger than a matter of emphasis, though. ADR-001 rejects routing
because its possible **quality** gain was bounded by a measured spread (P2:
0.60 / 0.61 / 0.65 for vector / graph / both), so what remains is a cost thesis.
The survey offers no measurement that changes that. It asserts both benefits
and measures neither.

---

## §Lessons + Open issues — "Lessons Learned and Practical Guidance", "Evaluation Methodologies Beyond Output Quality"

### L.1 — Process evaluation
**Prompt.**
- "Evaluation Must Account for Process, Not Just Outcomes": what do they
  propose? Does anything resemble per-step labels?
- "Agentic RAG Is Not Always the Right Default": which primary source backs it?
  🔄 Is it Ferrazzi?
- In "Benchmarks and Datasets", is there any benchmark with step-level
  sufficiency labels? If none, note it: it supports the claim that the
  generated benchmark is a publishable asset.

**My take.**

The part that connects most strongly with the project is the idea that evaluating only the final outcome is not sufficient for agentic systems. The survey argues that evaluation should also consider the process, including reasoning trajectories, tool use, adaptation, and cost. This directly supports the decision to log every agent step rather than only the final answer.

At the same time, the survey does not present a specific schema of step-level sufficiency labels. The benchmarks listed are mainly organized around QA, multi-hop reasoning, retrieval, generation, robustness, and related tasks. Therefore, within the inventory presented by the survey itself, I did not find a benchmark whose primary unit is a sufficiency label for each intermediate agent state. I would avoid turning this into the broader claim that no such benchmark exists in the literature; the safer conclusion is that it does not appear in this review.

Regarding the claim that Agentic RAG is not always the right default, I see this more as a synthesis of the survey than as a conclusion directly attributable to a single paper. Ferrazzi et al. is an appropriate primary source for the empirical discussion of cost and performance between Enhanced and Agentic RAG, but I would not use Ferrazzi as if it were the source of the survey's formulation itself.

**Refined write-up.**

The caution in this take is the right instinct for a survey, and the text
confirms it on every point.

*Process evaluation (§10.5, §12.2).* The survey says "existing benchmarks focus
on output quality with limited visibility into intermediate decisions" and calls
for "process-level metrics capturing reasoning efficiency, tool usage patterns,
and adaptation". It proposes no metric, no schema and no labelled data. It is a
call, not a method. The project's per-step label answers one specific version of
that call: *the correctness of each stop, against an exact label*. The README
can cite §12.2 as the stated need and the benchmark as one concrete response,
without claiming more.

*"Not always the right default" (§10.1).* The paragraph carries **no
citation**. It is the survey's own synthesis. The primary evidence for it is
Ferrazzi et al. (neither paradigm uniformly better; the agent costs up to 3.6×
more input tokens). So the take's rule is exactly right: cite Ferrazzi for the
evidence, and the survey only as a map.

*Benchmarks (§11, Table 4).*
- The eleven named benchmarks are retrieval (BEIR, MS MARCO, TREC), multi-hop
  QA (MuSiQue, 2WikiMultiHopQA, HotpotQA), toolkits (BERGEN, FlashRAG), and
  three others: AgentG, RAGBench and GNN-RAG.
- None labels intermediate agent states with sufficiency.
- RAGBench (TRACe metrics) is the nearest: it scores relevance and completeness
  of a *static* context and a response, the same unit as Joren.

The take's scoping is the correct claim: *not present in this review*. Two
things support a stronger claim without overreaching:
- the later sufficiency controllers (SIM-RAG, S2G-RAG, Luo 2026) *train* on
  outcome-derived or model-judged labels, which they would not do if an exact
  step-level set existed;
- MuSiQue-Full has answerable / unanswerable pairs, which are construction
  labels, but per question, not per step.

So the publishable-asset claim is: *a benchmark with exact per-step sufficiency
labels over multi-hop trajectories, which none of the resources surveyed here,
nor the controllers published since, provides.*

## Lessons Learned

The main lesson from this reading was realizing that "agentic" covers different mechanisms that can look similar at the surface level but solve different problems. Corrective, Adaptive, Routing, and Evaluator-Optimizer systems can all produce additional searches or iterations, but the question each mechanism answers is not necessarily the same.

It also became clearer to me that three decisions should be separated: whether to stop, what to search for next, and how to improve the context. A4 was designed specifically to isolate the first of these decisions.

Another lesson is that multi-agent is not synonymous with stopping. The survey presents multi-agent systems mainly as a way to distribute responsibilities, specialize agents, and execute tasks in parallel. This can be useful in other scenarios, but it is not necessary to test the central hypothesis of this project.

Finally, the survey reinforced an important methodological decision: for an agentic system, logging only the final answer loses part of the behavior we actually want to study. The process itself needs to be treated as evaluation data.

## Failed Attempts

My first interpretation of Corrective RAG was too broad: I understood it as a system that looks at its own answer and tries to improve it. The more precise interpretation is that the original CRAG focuses on the quality of retrieval and on corrective actions taken when the retrieved documents are inadequate.

I also initially treated Adaptive RAG as any system that adapts to the query. Jeong et al.'s Adaptive-RAG is more specific: it uses the complexity of the question to choose the treatment strategy. This is different from deciding, after several observations, whether the accumulated evidence is already sufficient.

Another interpretation I had to revise was the idea that multi-agent could itself be the solution to the stopping problem. The survey shows that the main purpose of this pattern is specialization and coordination among agents. A stopping decision can exist within a multi-agent system, but it is not what defines the category.

Finally, I would avoid stating that A4 "is Corrective RAG." The architectural similarity is real, but A4 was deliberately reduced to a binary judge that controls only the loop. Treating the two as equivalent would erase precisely the experimental distinction we want to measure.