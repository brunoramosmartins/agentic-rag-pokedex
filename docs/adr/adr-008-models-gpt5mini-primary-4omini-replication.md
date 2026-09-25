# ADR-008 — Models: GPT-5 mini Primary, GPT-4o-mini Replication

**Status:** Accepted (Phase 0, 2026-09-25). Prices re-verified in
`docs/data-sources.md` during Phase 0.

## Context

The project runs on spare time and a personal budget, on a laptop with a GTX
1050 Ti (4 GB). Local models that fit (~1.7–4B quantized, short context) are too
weak and too slow to produce registered numbers. The v1.0 has a hard spending
cap of **US$ 13.5**; each extension gets its own cap, set from the measured
v1.0 cost.

The arms must be compared on one model (the same model for every arm), and
the direction of H1 should ideally be checked on a second model generation.

## Decision

- **Primary model: GPT-5 mini**, through the **Batch API** (50% discount) for
  every registered run. `reasoning_effort` is frozen per run (low) and logged.
- **Replication model: GPT-4o-mini**, used only in the v1.2 extension (A1, A3,
  A4 on the eval-L3 twin) to ask whether the direction of H1 holds in another
  generation.
- **Local models (Ollama)** are for the development loop only. No registered
  number comes from a local model.

Prices used for the budget (2026-09-23, Batch): GPT-5 mini US$ 0.125 / 1.00
per million input / output tokens; GPT-4o-mini US$ 0.075 / 0.30. Reasoning
tokens count as output. Estimates assume ~150 reasoning tokens per call
(central) and ~400 (pessimistic); Phase 3 replaces them with measurements.

## Consequences

- **Scope of the claim.** v1.0 measures the effect for **one model
  configuration**: GPT-5 mini (the dated snapshot recorded in the E-001 freeze
  manifest) at `reasoning_effort` low. The effort level is part of the
  configuration, not a detail. The GPT-4o-mini extension runs A1, A3 and A4
  only — no A4p, no O2 — so it can replicate the **direction of H1**, not the
  mechanism (placebo, mediation). Neither result is stated for other models
  or effort levels.
- Budget (central / pessimistic / cap): v1.0 US$ 11.3 / 14.7 / **13.5**
  (including the A3′ noise-null rerun, US$ 1.1 / 1.45; before it: 10.2 / 13.2);
  v1.1 4.1 / 5.3 / **5.5**; v1.2 2.7 / 3.3 / **3.5**.
- Cut order for v1.0 if costs run over: (1) A6, (2) cue ablation, (3) the A3′
  rerun. **Never cut** eval-L1 for A2, A3, A4, A4p and O2. In the pessimistic
  scenario the first two cuts bring v1.0 back to ~US$ 12.9, under the cap.
- Cost gate (Phase 3): if measured cost per question exceeds 1.3× the estimate,
  the cut order is applied before Phase 4.
- Every script that calls an LLM in a loop supports `--limit N` and prints an
  estimated cost first; the token meter is checked against API-reported usage on
  10 calls (gate 7).
- Risk: GPT-4o-mini deprecated before Phase 10 → another cheap model from a
  different generation, registered before use.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| A comparable small model from another provider | ~US$ 40 for the same design vs ~US$ 15 |
| Local model for registered runs | Too weak on 4 GB; results would not transfer |
| A frontier model as primary | Budget; and the thesis is about the decision, not the model's ceiling |
| Synchronous API for registered runs | Twice the price; Batch is idempotent per question id |

## References

- [`contingency.md`](../contingency.md) — G5, cut orders
- [`measurability-gate.md`](../measurability-gate.md) — gate 8, cost check
- `docs/data-sources.md` — dated price table (Phase 0, G1)
