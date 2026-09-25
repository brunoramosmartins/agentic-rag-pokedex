# ADR-010 — Depth Placebo (A4p) and Release Slicing

**Status:** Proposed (Phase 0, 2026-09-24).

## Context

**The confounder.** The A4 judge adds nothing to the context (ADR-006), so "one
more LLM call" is not the confounder. **Searching more** is: A4 can win just by
taking more steps, independently of *when* it stops. The S0 falsifier does not
catch this, because on S0 extra searching does not hurt correctness — only cost.

**The scope.** An earlier plan bundled the explicit detector, a trained
classifier, MuSiQue, a real-world contrast and a second model into one release.
One long release in spare time risks ending with nothing shipped.

## Decision

### Depth placebo A4p

- Runs the A3 loop, but the agent **decides only at step k**; before k every
  answer or abstain proposal is vetoed. k is assigned as a seeded **permutation
  of A4's realized step counts in the same stratum**, so the dose matches A4's
  distribution by construction. The agent is never told about k.
- At step k the model answers or abstains.
- **Why the same stratum:** it is the hardest control possible. A4p knows how
  much to search, on average, for each kind of question — it just does not know
  *when to stop on each question*. If A4 still beats it, the advantage lies in
  per-question stopping time, which is exactly the thesis.
- The dose comes from A4's run in the **same eval-L1 opening**; A4p runs after
  A4, and **dose adherence is checked before any result is read** (gate 7):
  total-variation distance ≤ 0.10 per stratum, one re-run with a new seed on
  failure, otherwise "placebo not delivered".
- If B binds before step k, A4p decides at that step (flagged).
- **Harmful placebo guard:** forced blind search can hurt (more wrong-version
  sections, budget used up). Row 2 is read only if the lower limit of
  C(A3) − C(A4p) is above −0.25; otherwise the placebo is reported as
  uninformative, not as evidence for detection.
- No information from the judge or the label reaches the placebo — only the step
  distribution (tested in Phase 5).
- Read through outcome-space row 2: if A4's gain over A4p is < 50% of its gain
  over A3, "the gain comes from searching more, not from knowing when to stop".
  H1b (A4 > A4p) is secondary, outside the Holm family.

### Release slicing

| Release | Scope | Phases |
|---|---|---|
| **v1.0** | Layer 1: benchmark, A0–A4, A4p, A6, O1, O2, verdict, demo, README | 0–7 |
| v1.1 | Trained detector A5 (H3), or the registered negative from the futility rule | 8–9 |
| v1.2 | External validity: MuSiQue, real world vs twin, second model | 10 |

v1.0 is the product. Extensions are separate releases, decided with the
**measured** v1.0 cost, and cuttable without losing the verdict (G5).

## Consequences

- A4p is in the never-cut set of v1.0 (with A2, A3, A4 and O2): without it the
  mechanism cannot be read.
- Placebo prediction registered in E-001: on S1, blind extra search recovers
  part of the missing hop (A4p between A3 and A4); on S2 and S4 extra search does
  not help reject near-certain evidence or recognize absence (A4p near A3). If
  A4p matches A4 on those two strata, the detection thesis falls.
- Extension cut order: (1) 4o-mini replication, (2) MuSiQue, (3) real world,
  (4) the whole v1.1 — the last only by rule (outcome row 6 or Phase 8
  futility), never by fatigue.
- Extensions open as issues in Phase 7, each with its trigger written down.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| No placebo; rely on the S0 falsifier | S0 cannot reveal "searching more" as the cause |
| Fixed-depth placebo (same k for all) | Too weak: A4 would win by adapting depth per stratum, which is not the thesis |
| Placebo dose from the dev run | Distribution may drift between dev and eval-L1; same-opening dose is the tighter control |
| Single release with everything | Nothing ships if spare time runs out mid-way |

## References

- [`hypothesis.md`](../hypothesis.md) — placebo prediction
- [`measurability-gate.md`](../measurability-gate.md) — outcome-space row 2
- [`notes/ferrazzi-2026-is-agentic-rag-worth-it.md`](../../notes/ferrazzi-2026-is-agentic-rag-worth-it.md) — §3.3, agents rarely search again
- ADR-006 (boolean judge)
