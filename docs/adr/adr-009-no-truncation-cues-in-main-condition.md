# ADR-009 — No Truncation Cues in the Main Condition

**Status:** Accepted (Phase 0, 2026-09-25).

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

## Updates

### 2026-09-29 — The principle behind this ADR, applied to absence

A design review at the Phase 1 close generalized this decision into a
principle for every tool:

> **The structure may be artificial; the signal used to decide sufficiency is
> never handed over by the infrastructure.**

Counts and pagination markers were one instance. A second one was found in
`open_page`: a `section` that matched nothing answered "No section matching …",
which labelled a withheld S4 section as absent before the agent had to infer
anything. A neutral empty answer would not fix it — an empty filter result
carries the same information. So a section that matches nothing is ignored and
the whole page is served from the top, as a wiki link to a missing anchor
lands at the top of the page. An agent asking for a withheld learnset sees the
other versions' learnsets — S4's plausible, insufficient evidence — and must
notice the gap itself; the absence stays visible in the page, as legitimate
evidence, but no tool announces it. A test enumerates titles and sections and
fails if the main condition ever states an absence.

`offset` answering "No more units." past the end of a list is kept: the agent
learns the end only by asking for more, which is itself the behavior S3
measures. E-001 reads the two mechanisms apart — fetching the rest before
reaching the end versus learning the end by asking past it (amendment of
2026-09-29).

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
