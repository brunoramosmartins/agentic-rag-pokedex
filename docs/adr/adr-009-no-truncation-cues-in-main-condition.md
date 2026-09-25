# ADR-009 — No Truncation Cues in the Main Condition

**Status:** Proposed (Phase 0, 2026-09-24).

## Context

Stratum S3 asks for a set ("which Ice-type species learn Freeze-Dry by level in
version X?"). Long lists are hubs; the renderer splits them into several units,
and `search` returns a fraction per step. Answering with part of the list is a
wrong answer.

An earlier draft of this design leaked how many elements were missing through
two paths at once: the **total hit count** in `search` results, and **pagination markers** `(k/N)`
in section headers. With either cue, "is the set complete?" becomes arithmetic,
and S3 stops measuring sufficiency detection. The previous project (P2) had ended
with "an agent that sees the size of the intermediate set" as a hypothesis — it should be
measured, not assumed.

## Decision

In the **main condition** (every registered arm, every stratum):

- `search(query, k ≤ 5)` returns units with headers and **no total result
  count**;
- hub units share the **same header** and carry **no pagination markers**;
- nothing tells the agent how many elements remain — it has to suspect it,
  which is the general sufficiency problem.

**Cue ablation (S3 only, descriptive):** A3 and A4 re-run on S3 questions with
the tool showing the total count and `(k/N)` markers. It measures how much the
cue changes truncation detection — a practical finding for agent builders:
*what the tool shows changes what the agent can detect.*

## Consequences

- The tool contract (`tools/contract.py`) has a flag for the cue condition,
  off by default, with a test that the main condition never emits a count or a
  marker.
- The ablation is second in the v1.0 cut order (after A6).
- S3 predictions in E-001 are written for the no-cue condition; E-001
  predicts a small A4 − A3 gain on S3 in the main condition.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Show the total count (earlier draft) | Turns S3 into arithmetic; leaked the answer twice |
| Pagination markers only | Same leak through the header |
| Drop S3 | Loses the most practical sufficiency failure (partial lists) |

## References

- [`hypothesis.md`](../hypothesis.md) — stratum S3
- [`notes/yao-2023-react.md`](../../notes/yao-2023-react.md) — §3.1, what ReAct's search reveals
- ADR-002 (rendered pages)
