# ADR-003 — Counterfactual Twin as the Primary Population

**Status:** Accepted (Phase 0, 2026-09-25).

## Context

Models know the Pokémon universe. For this thesis that is not a side nuisance:
**if the model already knows the answer, it answers correctly with insufficient
context, and the label "insufficient" stops predicting the outcome.** The
evaluation of the detector loses its object. Joren et al. report that models are
still correct 35–62% of the time with insufficient context, partly from
pretraining knowledge.

P2's E-008 (nine fictional nodes) showed the effect of removing memory on a small
scale.

## Decision

The primary population is a **counterfactual twin**: the same graph with every
entity renamed consistently, facts intact (`world/twin.py`).

- **Rename, never alter facts.** Species, forms, moves, abilities, **types** and
  **version names** get pronounceable pseudo-words, generated with a fixed seed
  and filtered against real names and dictionary words. Numbers (levels, power)
  stay intact.
- **Types too.** With real types the model skips the type-effectiveness hop by
  memory ("Fire beats Grass") — a parametric shortcut in the middle of the
  chain.
- **Renaming runs through free text.** Pokédex text is rewritten with the same
  map.
- **Round trip is identity**, tested on 100% of entities (gate 7).
- The **real world** becomes a secondary contrast in the v1.2 extension
  (eval-L3, real vs twin).

## Consequences

- Gate **G2 — the twin does not leak** (Phases 1 and 3): an identity probe
  must not recognize the real entity from the renamed page in > 10% of 50 pages,
  and closed-book (A0) on the twin must stay ≤ 5%. The probe has a positive
  control: real pages with their own name masked must be identified in ≥ 50%, or
  the probe is broken.
- Exit plan if G2 fails: mask or remove Pokédex text (main suspect, e.g. "the
  lizard with a flame on its tail"); if it persists, primary-population
  questions exclude the leaking templates, decided on dev and recorded.
- **Honest framing:** the twin reproduces **one** property of a private corpus —
  the model does not know it — and none of the others (messy text,
  contradictory documents, internal jargon). It is a controlled sufficiency
  benchmark with contamination removed, not a stand-in for company data. The
  README must not pitch it as "safe for your private data".
- Aliases for exact match come only from the twin map (keeps the grader tight).

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Real names only | Memory substitutes for evidence; the label stops predicting correctness |
| Rename species only | Types and versions remain parametric shortcuts mid-chain |
| Alter facts (swap levels, types) as in knowledge-conflict studies | Creates memory × context conflicts — a different research question; the twin removes memory instead of fighting it |
| A fully synthetic world | Loses the real structure and distributions of PokéAPI; harder to argue the chains are natural |

## References

- [`contingency.md`](../contingency.md) — G2
- [`measurability-gate.md`](../measurability-gate.md) — gate 7, renamer and identity probe
- [`notes/longpre-2021-knowledge-conflicts.md`](../../notes/longpre-2021-knowledge-conflicts.md) — the substitution framework (read §2 before Phase 1)
- [`notes/joren-2025-sufficient-context.md`](../../notes/joren-2025-sufficient-context.md) — §4.2, correct despite insufficient context
