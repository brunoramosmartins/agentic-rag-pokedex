# ADR-007 — The Graph Is the Examiner, Never a Tool

**Status:** Accepted (Phase 0, 2026-09-25).

## Context

P2 built a Neo4j knowledge graph and used it for retrieval. In P3 the same
kind of graph is available, and two roles are possible: give it to the agent as
a tool, or use it to build the exam.

If the agent could query the graph, **a single Cypher query would resolve the
whole chain and the sufficiency problem would disappear** — there would be no
multi-step reading in which to be wrong about "enough". Meanwhile the graph is
exactly what makes an exact gold possible: questions, answers, chains and
per-step labels can all be derived from it.

## Decision

Neo4j is the **examiner** (`examiner/`):

1. **Templates as Cypher patterns**, 3–5 per stratum, with slots
   (`final form of {X}`, `in {version}`), stored as named constants in
   `examiner/templates.py`.
2. **Hand-written surface forms**, 3 per template (no LLM paraphrase in v1: it
   can change the meaning, and a correct gold for an altered question is a wrong
   gold).
3. **Each generated question carries:** id, stratum, template, surface form, twin
   and real text, canonical answer with aliases, the gold chain of facts, **all
   minimal sufficient sets of units**, the near-certain units (S2), the withheld
   units (S4) and the set size (S3).
4. **Filters with published N-of-M counts:** ambiguity, single-unit shortcut
   (reclassify to S0 or discard), S3 set size in [3, 25], S4 no remaining unit
   implies the answer.
5. **Sufficiency labeler** (`labeling/sufficiency.py`): a pure function over the
   fact → units registry returning sufficient / insufficient with subtype
   (`missing-hop`, `wrong-version`, `truncated`, `nonexistent`).

**No arm may query Neo4j.** The agent only has `search` and `open_page` over
rendered pages.

## Consequences

- The golden set becomes software; the human part shrinks from writing questions
  to auditing the generator (**G3**: ≥ 58 of 60 stratified gold answers correct).
- The generated benchmark (questions + step labels) is a **publishable asset**
  (`v0.3-examiner` pre-release), subject to the license decision in
  `docs/data-sources.md`.
- Reachability: every insufficiency subtype and every error code
  must be producible by at least one dev question, or unreachable by declared
  design.
- Integrity of the minimal sufficient sets and of the fact ↔ unit mapping is
  checked from **outside** the registry by the shortcut scan (ADR-002, gate 7).
  The labeler's golden trajectories test the labeling function given the
  registry; they cannot detect a unit the registry does not know about.
- A Phase 5 anti-leak test: the agent never sees a label, subtype, withheld-unit
  mark or any metadata beyond the section header.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Graph as a tool (as in P2) | One Cypher query answers the chain; nothing left to detect |
| Hand-written questions | Expensive, small n, and per-step labels would need annotation |
| LLM-generated questions + LLM judge | Label no longer exact; the P2 judge ceiling was 0.843 |

## References

- [`contingency.md`](../contingency.md) — G3
- [`measurability-gate.md`](../measurability-gate.md) — gates 4 and 7
- [`notes/trivedi-2022-musique.md`](../../notes/trivedi-2022-musique.md) — anti-shortcut filters
- [`notes/ho-2020-2wikimultihopqa.md`](../../notes/ho-2020-2wikimultihopqa.md) — template generation from a KG
