# ADR-005 — Cost Function: λ = 4 as the Test Scenario, λ\* as the Headline, and Hard Caps

**Status:** Proposed (Phase 0, 2026-09-24).

## Context

Accuracy alone rewards an agent that always answers; abstention rate alone
rewards one that never does. The thesis is about the trade-off between a wrong
answer and "I don't know", so the primary outcome must price both. The price
of a wrong answer is not a property of the system — it depends on the reader.

## Decision

**Cost per question:** C = 0 if correct, 1 if abstained, **λ** if wrong. The
optimal rule that follows: answer only if P(correct) > 1 − 1/λ.

**λ = 4 is the scenario of the registered test**, not a measured quantity. H1 and
H2 need one number for power and verdict. Illustrative derivation, with
assumptions stated to be challenged one by one:

```text
λ = 1 + P(act on the answer) × (time lost) / (time to look it up yourself)
```

Example: a false "learns the move at level 42"; half the users act on it and lose
~18 min; looking it up takes ~3 min → λ = 1 + 0.5 × 18/3 = **4** (a lower bound:
lost trust is ignored).

**The headline is the tipping point λ\*.** Given two arms' error and abstention
rates, A4 beats A3 exactly when λ × (err_A3 − err_A4) > abst_A4 − abst_A3. When A4
errs less and abstains more:

```text
λ* = (abst_A4 − abst_A3) / (err_A3 − err_A4)
```

and A4 is worth it for every λ > λ\*. The four cases (A4 dominates; tipping above
λ\*; tipping below λ\*; A4 dominated) are enumerated in E-001. λ\* is reported
with a paired-bootstrap interval **when the error difference is resolved** (see
Consequences), next to each arm's operating point (error, abstention) on one
chart. Sensitivity at λ ∈ {2, 4, 9} is also reported.

**The owner's cost is a cap, not a weight:** **T_max = 6 steps** and **B = 4,000
evidence tokens** per question, identical for all arms. LLM tokens spent are an
**outcome** (reported), not a control.

**Every arm gets the same cost instruction** ("a wrong answer costs 4× not
answering"). Otherwise the implicit detector would be optimizing another
objective and the comparison would measure the instruction.

## Consequences

- The business bridge needs no invented numbers: *"the architecture pays off if
  an error costs more than λ\* abstentions — e.g. λ\* manual reviews"*. No ROI is
  computed on a Pokémon benchmark.
- Risk-coverage curves and AURC exist only for arms with a continuous score
  (A5, v1.1). For A3 and A4 (binary decisions) the λ-free objects are the
  operating point and λ\* — correcting an earlier draft of this design that
  listed them for every arm.
- λ\* is a ratio and breaks when the two error rates are close (the
  denominator crosses zero across resamples). It is published only when the
  interval of Δerr excludes zero; the always-available reading is a λ grid
  (1 to 20) with the λ ranges where A4 is better or worse.
- Action threshold for H1/H2: **0.25 units of C** (≈ 1 in 16 questions going from
  wrong to correct, or 1 in 12 from wrong to abstained).
- The trained detector's theoretical threshold follows from λ:
  ≈ (1 − 1/λ) / P(correct | sufficient), with the denominator measured by O1.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Accuracy as primary | Rewards answering everything; blind to the thesis |
| λ as the only reading | Conclusion would hinge on one arbitrary number; λ\* removes the dependency |
| Business ROI computed for λ | Would invent numbers on a benchmark; λ\* plays that role |
| Token cost as a weight inside C | Mixes units; the owner cares about total spend → caps + reported outcome |
| Declared-preference poll for λ | Parked (open-ideas): λ by context, casual × competitive |

## References

- [`hypothesis.md`](../hypothesis.md) — outcome and cost convention
- [`measurability-gate.md`](../measurability-gate.md) — gates 3 and 5, outcome space
- [`notes/geifman-2017-selective-classification.md`](../../notes/geifman-2017-selective-classification.md) — risk, coverage, and E[C] as a function of both
