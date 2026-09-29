# Phase 0 — Reading Synthesis (Joren 2025 × Ferrazzi 2026 × Singh 2025)

Cross-source questions for the Phase 0 readings. Answer after the three notes
have at least their My takes filled. The output feeds ADR-001 (positioning),
`docs/hypothesis.md` and E-001.

Sources:
- [`joren-2025-sufficient-context.md`](joren-2025-sufficient-context.md)
- [`ferrazzi-2026-is-agentic-rag-worth-it.md`](ferrazzi-2026-is-agentic-rag-worth-it.md)
- [`singh-2025-agentic-rag-survey.md`](singh-2025-agentic-rag-survey.md)

---

### S.1 — One failure or two?
**Prompt.**
- Joren: with insufficient context, models answer instead of abstaining.
  Ferrazzi: agents rarely search again, and when they do they get the same
  documents. Write the project's central axis ("the agent fails because it does
  not know it has not found it yet") as a conclusion of *both* papers. Where is
  the logical gap that only this project's per-step labels can close?

**My take.**

Reading the two papers together made clear to me that "the model answered incorrectly" and "the agent stopped incorrectly" are not the same statement. The first is an outcome; the second is a process-level failure.

I also learned that the two papers should not be merged into a stronger claim than the evidence supports. They point toward the same research question from different directions, but the project needs its own labels to connect those observations into a measurable sequential problem.

Finally, the phrase "the agent does not know it has not found it yet" became more precise for me. It is not just about uncertainty or hallucination. It is about recognizing whether the evidence accumulated so far satisfies the requirements of the question.

**Refined write-up.**

The take draws the right distinction: outcome vs process, and no merging of
the two papers into a claim neither makes. It does not yet do what the prompt
asks, which is to write the central axis as a conclusion of both papers and
name the gap. Here is that argument, step by step.

*Premise 1 (Joren §4.2).* With insufficient context, models more often answer
than abstain. Stated in terms of the decision: **given** an insufficient state,
P(answer) is high.

*Premise 2 (Ferrazzi §3.4).* An agent that may retrieve again does so on 10% of
queries, and then 53% of documents come back unchanged. Stated in terms of the
decision: P(continue) after the first retrieval is low.

*The tempting conclusion.* Agents stop on insufficient states, so they fail
because they do not know they have not found the answer yet.

*Why it does not follow — the logical gap.* The conclusion needs
P(stop | insufficient state) on **agent trajectories**, and neither paper can
compute it:
- Joren conditions on insufficiency, but has **no trajectory**: one fixed
  context per question, no decision to continue.
- Ferrazzi has trajectories but **no sufficiency label**. On FiQA and
  CQADupStack, where one retrieval usually suffices, a low continue rate may be
  *correct* stopping.

The two findings meet only on the insufficient states of a trajectory, and
neither paper can pick those states out.

*What closes it.* A label S_t on every state of every trajectory. Then:
- P(stop | S_t = insufficient) is the failure to decide;
- P(never reaching S_t = sufficient) is the failure to search;
- the error taxonomy separates the two (`stop-missing-hop` vs `never-reached`).

The central axis then becomes a testable statement, not an inference: *at a
state labelled insufficient, the agent stops*.

*An existence proof inside the literature.* Ferrazzi's own Appendix C.2 trace
shows both failures in one run. The agent recognises that its first retrieval
is not enough, retrieves once more, is still not covered, and answers with
five blog-post titles that appear in none of the retrieved documents. Joren's
failure happens inside Ferrazzi's example, and only a sufficiency label on each
step would have flagged it. It is the illustration for the README and the
write-up.

### S.2 — The positioning paragraph
**Prompt.**
- Draft the three-sentence related-work paragraph for ADR-001: what Joren
  measured (static context, autorater), what Ferrazzi measured (single-hop,
  agentic vs enhanced, cost), where the survey's taxonomy has no box for the
  stopping decision, and what this project adds.

**My take.**

Joren studies whether a model can answer correctly when given a fixed context and uses an autorater to characterize whether that context is sufficient. Ferrazzi studies agentic versus enhanced RAG in a setting dominated by single-hop questions, including the additional retrieval behavior and its cost. The Singh survey places these ideas among broader Agentic RAG patterns such as routing, corrective retrieval, adaptive retrieval, multi-agent systems, and evaluator-driven workflows.

My reading of the survey is that stopping appears as part of several mechanisms, but I do not see the stopping decision itself represented as the central object of a taxonomy category. This is where I currently position the project.

The contribution is therefore not "introducing iterative retrieval" or "introducing an evaluator". Those ideas already exist. The narrower contribution is to treat sequential sufficiency detection as an explicit object of study: after each observation, can the system determine whether the evidence accumulated so far is enough to answer, whether it should continue searching, or whether it should abstain? The benchmark makes this measurable through exact step-level labels.

**Refined write-up.**

The content is right and the framing ("not introducing iterative retrieval or
an evaluator") is the mature one. It needs three repairs.

1. It is five sentences, not three.
2. It omits the later work that already controls retrieval with sufficiency
   (ADR-001, Updates). A reviewer who knows SIM-RAG would read the omission as
   ignorance.
3. It describes Joren as studying "whether a model can answer correctly when
   given a fixed context". Joren's object is the *context's* sufficiency and the
   model's behaviour across it.

Three sentences for ADR-001 and the README, with one optional fourth:

> Joren et al. (2025) define sufficient context for a single, fixed
> question–context pair and, using an LLM autorater, show that models answer
> rather than abstain when it is insufficient; Ferrazzi et al. (2026) compare
> enhanced and agentic RAG on single-hop retrieval tasks and find that the agent
> rarely retrieves again and costs up to 3.6× more input tokens, without
> labelling whether its stops were justified. Singh et al. (2025) list deciding
> "when sufficient evidence has been collected" among the defining capabilities
> of agentic RAG, yet none of their taxonomy's categories is organised around
> that decision, and later systems that do control retrieval with a
> sufficiency signal (SIM-RAG, S2G-RAG) learn it from answer outcomes or model
> judgments. This project measures the stopping decision itself: at every step
> of a multi-hop trajectory, against an exact sufficiency label built from a
> knowledge graph, with a depth placebo separating *when* an agent stops from
> *how much* it searches.

The optional fourth sentence, for the README only: *the benchmark with per-step
labels is the missing instrument for evaluating such controllers.*

Each clause maps to a note:
- the Joren clause → its §3.1 and §4.2 write-ups;
- the Ferrazzi clause → its §3.1, §3.4 and §5.1 write-ups;
- the Singh clause → its T.1 write-up;
- the later-work clause → Joren §6.1 write-up and ADR-001's Updates.

### S.3 — Definition of the label
**Prompt.**
- After Joren §3.1: does the project adopt Joren's definition, a stricter one
  (coverage of a gold minimal sufficient set), or both (exact label for
  metrics, Joren-style for the A4 judge prompt)? Record the choice as a decision
  journal entry with the reason.

**My take.**

I would use both definitions, but for different purposes. The benchmark should use a stricter operational definition: a state is sufficient when the units seen so far cover at least one minimal sufficient set for the gold answer (the same fact can appear in several units, so there can be more than one such set). This gives the project an exact, reproducible label that can be generated from the graph rather than assigned by an LLM judge.

For the A4 judge, I would use the simpler Joren-style notion of sufficiency in the prompt: "Is the evidence sufficient to answer the question?" The judge does not need to reconstruct the gold chain or see the benchmark labels. It only needs to make the same conceptual distinction the benchmark defines operationally.

This separation is important. The gold label is an evaluation instrument; the judge is an experimental treatment. The former needs to be exact and deterministic. The latter needs to represent the practical decision an agent would make from the evidence it sees.

I would therefore register the decision as: **strict graph-derived labels for evaluation, plain-language sufficiency for the A4 judge**.

**Refined write-up.**

This is the decision recorded on 2026-09-26: ADR-001, Updates; decision journal;
E-001 amendment. The take adds a useful rule, *plain language for the judge*,
with two constraints to keep it honest.

*Why the two definitions can coexist.* Write S_J for Joren's predicate and S_P
for the project's:
- S_P(C_t): the units seen up to step t cover at least one minimal sufficient
  set for the gold answer;
- S_J(C_t): some plausible answer exists given C_t.

Then S_P ⇒ S_J, and not conversely. The judge, working without the gold, can at
best approximate S_J. The labeler computes S_P exactly. So every A4 error
against the label falls into one of two kinds:
- a **false "sufficient" that S_J would also make**: the judge accepted a
  plausible partial answer, as in S3 without cues. This is the gap between the
  two definitions;
- a **false "sufficient" that S_J would not make**: the judge simply misjudged,
  as with a wrong version it overlooked (S2).

Precision and recall by subtype (E-001) separate the two. That is why the
definition's weakness, used deliberately in the judge, becomes a measurement
rather than a confound.

*Constraint 1: parity.* The plain-language question is fine. But any checklist
the judge prompt carries ("list the facts the question needs", "check the
version") goes verbatim into the shared agent prompt (E-001, amendment of
2026-09-26). Otherwise H1 measures the wording, not the separate call.

*Constraint 2: nothing from S_P leaks into the prompt.* Words such as "minimal
sufficient set", "gold chain" or "withheld section" would hint at the labeler's
construction. A generic question like "is the list complete?" is allowed, since
ADR-006 names it, but only under Constraint 1. The judge sees the question, the evidence and the plain
question. The Phase 5 anti-leak test covers metadata. The prompt review at the
freeze should cover wording too.

---

## Lessons Learned

The three papers helped me separate three things that I was initially treating as one: whether the context is sufficient, whether the agent retrieves again, and whether the agent knows when it should stop. Together, they point toward a process-level problem, but they do not directly measure sequential stopping decisions. This makes the per-step sufficiency labels the key addition of this project.

I also learned to define the contribution narrowly. The project is not about introducing iterative retrieval, evaluators, or adaptive RAG; those ideas already exist. The focus is on making the stopping decision itself an explicit, measurable object, while keeping retrieval strategy and context improvement separate from the detector.

## Failed Attempts

My main mistake across the three readings was grouping related mechanisms too quickly. I initially treated Corrective, Adaptive, Evaluator-Optimizer, and agentic retrieval as variations of the same idea, and I also tended to equate a correct answer with sufficient evidence. The readings forced me to separate the retrieval process, the evidence state, and the stopping decision.

I also initially looked for novelty at the level of architecture or taxonomy. A stronger framing is to focus on the experimental question: whether an agent can detect, step by step, that the evidence it has is not yet sufficient, using an exact label defined independently of the model's answer.