# ADR-001 — Theme and Thesis: Sequential Sufficiency Detection on a Pokémon Twin

**Status:** Accepted (Phase 0, 2026-09-25).

## Context

This is the third project of a RAG trilogy. P1 (`rag-pix-regulation`) showed
that reliable RAG cites its source; P2 (`graphrag-mtg-rules`) showed that some
answers are not written anywhere — they are paths. P2 also measured two things
that point here:

1. **8 of 9 subgraphs labelled `insufficient` were answered** instead of refused
   (P2, Phase 5, E-007). The system did not know that it did not know.
2. **The three-hop chain reached the context in 3 of 100 questions** at the
   default budget (P2, E-015); the problem was a hub in the middle of the
   traversal, not depth (E-017).

The literature says the same from outside. Joren et al. (ICLR 2025) show that
models answer well with sufficient context but **often answer wrongly instead of
abstaining when the context is insufficient**. Ferrazzi et al. (LREC 2026) find
that agents re-retrieve in ~10% of cases, with 53% of documents unchanged — but
only on single-hop datasets.

The original P3 plan was a **vector | graph | both router** inside the Magic
domain. P2 measured 0.60 / 0.61 / 0.65 for those three arms; a router can at
best tie "always both" on quality, and its possible gain is bounded by that
spread — below any reachable action threshold. Routing is a cost thesis, not a
quality thesis.

## Decision

**Thesis.** *In multi-step retrieval the bottleneck is not searching; it is
deciding whether the accumulated evidence is enough.* The contribution is
**sequential sufficiency detection** — the agent is the experimental mechanism,
and "agentic RAG" is a label for discoverability, not a claim.

Central axis: *the agent does not fail because it cannot search; it fails
because it does not know it has not found the answer yet* — and that is
measurable step by step when "found" is known by construction.

**Domain: Pokémon (PokéAPI).** Chosen for the ground truth, not for the thesis;
the thesis works on any graph with chains of varying depth. Pokémon won on
three properties no other candidate combined:

1. **A rich, open, structured source.** PokéAPI: BSD-3, CSV, species, types,
   moves, abilities, evolution chains and learnsets **split by game version**.
   Gold answers come from queries, not annotation.
2. **A natural generator of near-certain evidence.** One version's learnset is
   similar to another's, and different. Evidence from the wrong version is
   plausible and insufficient — exactly the case where Joren et al. show models
   failing.
3. **Real author motivation**, the strongest predictor of completion in a
   spare-time project (P2 Phase 0 TIL).

The price of Pokémon — contamination — is handled by the counterfactual twin
(ADR-003).

## Consequences

- The research question is answered on five strata (S0 control, S1 missing hop,
  S2 wrong version, S3 truncated set, S4 no answer in corpus) with exact
  per-step labels, which separate failing to **search** from failing to
  **decide**.
- The positioning claim must survive the reading of Joren (static context,
  autorater labels) and Ferrazzi (single-hop, no sufficiency labels). If either
  already measures per-step sufficiency in a multi-hop loop, this ADR is
  revised.
- **Open item:** the exact definition of the sufficiency label (Joren's
  "a plausible answer exists given C" vs "the units seen cover a gold minimal
  sufficient set") is fixed in `docs/examiner.md` after
  `notes/phase0-synthesis.md` S.3. The two can disagree on S2 and S3.
  **Blocking for the E-001 freeze:** the labeler's golden trajectories
  (measurability gate 7) cannot be written until the definition is fixed.
- Honest framing: the twin controls the model's memory; it does not reproduce a
  company corpus. No business ROI is computed on the benchmark (see ADR-005).

## Updates

**2026-09-26 — Positioning check after reading Joren et al.** Work published
after Joren et al. already **controls** multi-round retrieval with a
sufficiency signal:
- SIM-RAG (Yang et al., SIGIR 2025, arXiv:2505.02811) trains a sufficiency
  Critic per round, labelled by whether the path reached the correct final
  answer.
- S2G-RAG (Li et al., 2026, arXiv:2604.23783) judges sufficiency and emits gap
  items that become the next query.
- Luo (2026, arXiv:2608.13237) adds an S2G-style stopping judge to Search-R1
  on HotPotQA, without abstention or a cost for wrong answers.

None **measures** stopping against an exact per-step label. The decision
stands; the contribution is stated as measurement, not method:
1. per-step labels exact by construction (not outcome-derived, not
   LLM-rated);
2. a detector that changes only the stop, with a depth placebo;
3. contamination control through the twin;
4. abstention priced into the outcome.

The project does not claim to introduce sufficiency-driven iterative
retrieval.

**2026-09-26 — Open item resolved.** The sufficiency label is **coverage of a
gold minimal sufficient set** by the units seen up to step t. Joren's
definition ("a plausible answer exists given C") is strictly weaker: every
state sufficient under the project's label is sufficient under Joren's, not
conversely. The clean disagreement is S3 without truncation cues, where a
partial list is a plausible answer. Joren-style wording may inform the A4 judge
prompt, under the prompt-parity rule of E-001. The labeler specification goes
into `docs/examiner.md` in Phase 2.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Router vector \| graph \| both on Magic (original P3) | Gain bounded by P2's 0.60–0.65 spread; routing is a cost thesis |
| "Agents win at multi-hop" | Competes with a well-built fixed pipeline: any chain of known shape can be programmed |
| Elden Ring | Structured source assembled by scraping with admitted bugs; interesting questions are interpretive lore |
| Tolkien / Harry Potter | Maximum contamination, little structure, fan-wiki text only |
| ML literature via OpenAlex | Cleaner measurement, career-aligned, lower motivation — kept as a registered alternative |
| Multi-agent *War Room* on open problems | No gold, unfreezable web corpus, multiplied cost — P4 candidate, conditional on the Layer 1 verdict |
| Bulbapedia prose as corpus | NC-SA license; gold alignment error-prone (see ADR-002) |
| Pokémon TCG | A second source and a second gold to validate |
| RL phase (Search-R1 style) | Not feasible on a 4 GB GPU; parked with a named consumer |

## References

- [`hypothesis.md`](../hypothesis.md) — research question, statement, strata, predictions
- [`notes/joren-2025-sufficient-context.md`](../../notes/joren-2025-sufficient-context.md)
- [`notes/ferrazzi-2026-is-agentic-rag-worth-it.md`](../../notes/ferrazzi-2026-is-agentic-rag-worth-it.md)
- [`notes/singh-2025-agentic-rag-survey.md`](../../notes/singh-2025-agentic-rag-survey.md)
- [`notes/jeong-2024-adaptive-rag.md`](../../notes/jeong-2024-adaptive-rag.md) — why routing is not the thesis
- [`notes/phase0-synthesis.md`](../../notes/phase0-synthesis.md)
