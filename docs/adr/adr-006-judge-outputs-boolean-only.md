# ADR-006 — The Sufficiency Judge Outputs a Boolean Only

**Status:** Accepted (Phase 0, 2026-09-25).

## Context

Arm A4 (the explicit detector) adds a **judge call** after every observation:
"is this enough?". H1 claims A4 reduces cost relative to A3 (the implicit
detector) *because it stops at the right time*. For that attribution to hold,
the judge must change **only the stopping decision**.

Published evaluators do more. CRAG's retrieval evaluator triggers knowledge
refinement and web search; Self-RAG's critique tokens steer decoding. A judge
that says *what is missing* would feed a better next query; a judge that
summarizes evidence would change what the answering model reads. Each is a
confounder: A4 could win through better queries or better context, not better
stopping.

## Decision

The A4 judge (`detectors/explicit_judge.py`):

- answers **only yes/no** ("the evidence is sufficient" / "not sufficient");
- **puts nothing into the answering context** — no rationale, no summary, no
  missing-piece hint;
- controls the loop and nothing else. It is called on **every** proposal the
  agent makes after an observation (answer / search / abstain), and it can only
  **veto an answer**: (answer, yes) → answer; (answer, no) → search; search and
  abstain proposals pass through; at T_max, (answer, no) → abstain. The full
  table, shared with A3 and A4p, is registered in E-001.

Prompt discipline: at most **3 iterations on dev, group-A templates only**, each
recorded; then frozen with its hash in E-001. **Parity:** the shared agent prompt
(A3, A4, A4p) and the A2 answer prompt get the same budget, and any
stratum-specific instruction that enters the judge prompt ("check the
version", "is the list complete?") is copied verbatim into the shared agent
prompt. Otherwise H1 would measure the instruction, not the detector — the same
reasoning that gives every arm the same cost instruction (ADR-005).

## Consequences

- "One more LLM call" is not the confounder. The remaining confounder is
  **searching more** — A4 may win just by taking more steps regardless of *when*
  it stops. That is what the depth placebo A4p exists for (ADR-010).
- Gain decomposition becomes interpretable: A4's gain is split by the label
  state at the final action (sufficient / insufficient / abstained), and a
  second run of A3 (A3′) gives the same split under pure sampling noise; only
  the excess is attributed to the judge. If the excess is small, the judge's
  stopping decisions do not explain the gain — reported, not explained away.
- The agent's proposed action is logged **before** the judge decides (ADR-004).
- The judge is an LLM, but it is a **treatment**, not a measurement: no primary
  or mechanism endpoint is graded by an LLM.
- A "judge that points at the gap" variant is parked (open-ideas) as a secondary
  experiment if v1.0 lands on row 7 of the outcome space.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Judge with a rationale in context (CRAG/Self-RAG style) | Confounds stopping with context quality |
| Judge that names the missing piece | Confounds stopping with query reformulation — parked as a separate experiment |
| Graded score (0–1) from the judge | Needs a threshold → another tuning surface on dev; binary keeps A4 comparable to A3's binary decision. Continuous scores belong to A5 (v1.1) |

## References

- [`hypothesis.md`](../hypothesis.md) — the arms, mediation prediction
- [`notes/yan-2024-crag.md`](../../notes/yan-2024-crag.md) — §4.3, refinement changes the context
- [`notes/asai-2024-self-rag.md`](../../notes/asai-2024-self-rag.md)
- [`notes/joren-2025-sufficient-context.md`](../../notes/joren-2025-sufficient-context.md) — §3.2, the autorater
- ADR-010 (depth placebo)
