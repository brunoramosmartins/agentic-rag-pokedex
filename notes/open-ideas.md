# Open Ideas — parking lot

Ideas with no consumer in the current plan. The house rule: an idea without a
consuming decision does not become a full reading note or a task; it waits
here with the condition that would wake it up. Entries are never deleted;
their status changes.

| Idea | Origin | Possible consumer | Status |
|---|---|---|---|
| [Specification sufficiency — the missing information is held by the user, not the corpus](#specification-sufficiency) | Reading Joren et al. 2025 (2026-09-26) | Next project (P4 candidate), competing with the War Room | Parked |
| Multi-agent *War Room* on open problems | Theme brainstorm (2026-09-23) | P4, if the v1.0 verdict lands on outcome-space rows 3, 4 or 7 | Conditional |
| RL-trained detector (Search-R1 style) | Jin et al. 2025 (Search-R1); BAPO (2026) | Post-v1.1 extension on a free cloud GPU, if the trained classifier works | Dormant |
| Judge that points at the gap | ADR-006 (rejected for the main design) | Secondary experiment if v1.0 lands on row 7. Published instances now exist: S2G-RAG (arXiv:2604.23783) | Dormant |
| Declared-preference poll for λ | Cost-function discussion (ADR-005) | Limitations; λ by context (casual × competitive) | Dormant |
| Pokémon TCG as a second source | Theme brainstorm | External validity, after the verdict | Dormant |
| Real wiki prose as corpus | Corpus discussion (ADR-002) | External validity of rendered text; NC-SA license | Dormant |
| False-premise questions (evidence of absence) | S4 design | Stratum S5 in a v2 | Dormant |
| "Can X learn Y?" — a negative answer is sufficient only after every learn method (level-up, machine, egg, tutor) of X in that version has been seen; completeness of a *no*, close to the previous row. **Extended 2026-09-29:** the true answer often runs through the evolution line and a game mechanic that no page states ("a species keeps the moves it learned before evolving"). In x-y, Gastly learns Nightmare at level 47, Haunter and Gengar only at 61 — the earliest Gengar with Nightmare is a Gastly held back until 47; in scarlet-violet the line cannot learn it at all. In 798 of 1,094 (evolution pair, version) combinations the pre-evolution can learn a move the evolution cannot. Sufficiency would then depend on a rule, which would have to exist as a page of the corpus for the label to stay exact | Page design (2026-09-29); the author's question about Gengar's learnset | A rule-dependent sufficiency stratum in a v2; the facts are already in the world, the rule is not | Parked |
| Locations, encounters, items | World scope | More chain shapes in a v2 | Dormant |
| LLM paraphrase of questions | Generator design (ADR-007) | Surface robustness; risk of changing the meaning | Dormant |
| ML literature via OpenAlex | Theme debate (ADR-001) | Career-aligned project after the trilogy | Registered alternative |
| Real implementation of the detector in an orchestrator (e.g. LangGraph) | External design review | Only if a production use appears; v1.0 documents the design | Dormant |
| Business ROI computed for λ | External design review | Rejected: it would invent numbers on a benchmark; λ\* plays that role | Dropped |
| Elden Ring as domain | Theme debate (ADR-001) | None identified | Dropped |

---

## Specification sufficiency

**Origin.** Raised while reading Joren et al. 2025
([lit-note](joren-2025-sufficient-context.md)), 2026-09-26. Out of scope for
this project by decision: this project controls the question completely
(template, gold chain, minimal sufficient sets), and that control is what
makes its label exact.

**The idea.** Before generating, a system faces three different
insufficiencies, and each calls for a different next action:

| Insufficiency | Question the system must answer | Right next action |
|---|---|---|
| **Specification** | Is the request specified enough for a correct action? | ask the user |
| **Evidence** | Given a specified request, is the evidence enough? | search / call a tool, or abstain |
| **Use** | Evidence is enough; is the answer derived correctly? | (a generation error, not a stopping one) |

The general question: *what should an LLM system do when its information state
is insufficient for reliable action?* The action set is {ask, search, call
tool, abstain, answer}; "answer" is only one of five. This project isolates
one axis of it — evidence sufficiency and when to stop searching — with an
action set of {search, answer, abstain}.

**What reading Joren already says (so the novelty is narrower than it looks).**
- Joren's introduction names the ideal behaviour as "abstain from answering
  and/or **ask for more information**".
- **Remark 2 (ambiguous queries)** folds part of specification into context
  sufficiency: an ambiguous query has sufficient context iff the context
  disambiguates it *and* answers the disambiguated query.
- **Remark 3 (ambiguous contexts)** covers what could be called "answer
  sufficiency": several plausible answers make the context insufficient unless
  it distinguishes them.

So "query sufficiency" and "answer sufficiency" are not new axes in the
abstract. What is not measured there is the **action**: whether the system
picks the right channel for the missing information.

**The sharper formulation: who holds the missing information.**
- If the corpus can resolve the gap (Remark 2's case), the right action is to
  search.
- If only the user can ("compare Q3 with *the* budget" — which budget?), search
  is useless however long it runs, and the right action is to ask.
- Asking cannot fix an evidence gap; searching cannot fix a specification gap.

The measurable question: *does the agent route the gap to the channel that can
close it?* An agent that treats a specification gap as an evidence gap burns
its search budget on a question that was never answerable as asked. That is
this project's `over-search` / `never-reached` pattern with a different cause.

**Measurability — the latent-intent objection is not fatal.** The obvious
objection is that "was the request specified enough?" depends on a latent user
intent with no gold. It can be built by construction, the way this project
builds everything else:
- Take a fully specified template and **delete a slot**. "At what level does X
  learn M in {version}?" loses "in {version}".
- The missing slot is known, so the gold action is known:
  - **ask**, if the corpus holds several versions with different answers;
  - **search**, if only one version exists in the corpus.
- This is the specification-side twin of S2. S2 names a version and offers
  evidence from another; the new stratum names none.
- Asking needs a price (the user's time), a second λ-like parameter. The
  tipping-point reading (λ\*) carries over: ask vs answer vs abstain.

**Limits to state up front.**
- Constructed underspecification is not real user underspecification — the
  same external-validity caveat as the counterfactual twin.
- Conflicting evidence (Remark 3's case) needs contradictions, which this
  project's rendered corpus excludes by design (ADR-002). That is a separate
  axis, knowledge conflict (Longpre et al. 2021, on this project's Phase 10
  reading list).
- The three stages are not a fixed pipeline. Retrieval can *reveal*
  underspecification: two budgets exist only once both are found. The right
  model is a policy choosing among the five actions at every step, not a
  sequence of gates.

**Before committing to it (next project, step one).** Scout the literature on
the *decision*, not the topic. Candidate lines to check, names to be verified:
ambiguous open-domain QA (AmbigQA, Min et al. 2020); clarifying-question
generation and "clarify when necessary" (e.g. CLAMBER, 2024); the survey of
abstention in LLMs (Wen et al. 2024, "Know Your Limits"). The gap, if any, is
likely in the *routing* decision under exact labels, not in the taxonomy.

**Wake-up condition.** The P3 verdict:
- **H1 supported** (outcome row 3): extending detection from evidence to
  specification is the natural next step.
- **Row 6** (no room for stopping): the idea weakens, unless specification
  gaps are shown to be a larger share of failures in real use.
