# ADR-004 — Hand-Rolled Agent Loop

**Status:** Proposed (Phase 0, 2026-09-24).

## Context

Every agent step must log the units seen, the action, the **full prompt**, the
**full completion** and the token usage, and the OTel span must carry prompt and
completion (a standing rule since P2, where missing prompts made failures
unexplainable). The mechanism metrics also need the
**action proposed by the agent recorded before the judge decides** (for the
gain decomposition of A4 over A3), and the arms differ only in who decides to
stop (the "who decides what" table).

Orchestration frameworks (LangGraph, LlamaIndex agents and similar) hide or
rewrite prompts, add their own retries and state, and change across versions —
each of which can move a number without the log showing why.

## Decision

Write the agent loop by hand (`arms/agent.py`, ~200 lines): a ReAct-style loop
over the two tools (`search`, `open_page`), with a pluggable **detector**
(`detectors/implicit.py`, `explicit_judge.py`, `placebo_depth.py`, and later
`trained.py`) and the stopping oracle O2 behind the same interface.

- One loop, shared by A3, A4, A4p, A5 and O2. Arms differ only in the detector.
- Caps enforced in the loop: T_max = 6 steps, B = 4,000 evidence tokens.
- Structured output `{answer, abstain}` at the end of every episode.
- Per-step log and one OTel span per step, exported to Phoenix.
- Prompts are loaded by name from `prompts/`; their hash is logged.

## Consequences

- Full control of what is logged; every branch of the "who decides what" table
  gets its own test (Phase 5).
- No framework features for free (retries, tracing integrations, memory): each
  is written only if needed.
- Phase 7 documents, without implementing, how the detector would sit as a
  conditional node in a production orchestrator ("From experiment to
  production" README section).

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| LangGraph / LlamaIndex agent | Hides or rewrites the prompt; version drift; harder to guarantee the per-step log |
| Provider-native agent APIs (hosted tool loops) | The stop decision and intermediate prompts are not fully observable |
| One loop per arm | Duplicated code becomes an uncontrolled difference between arms |

## References

- [`hypothesis.md`](../hypothesis.md) — the arms
- [`notes/yao-2023-react.md`](../../notes/yao-2023-react.md)
- ADR-006 (judge), ADR-010 (placebo)
