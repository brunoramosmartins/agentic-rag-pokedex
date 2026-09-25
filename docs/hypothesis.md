# Hypothesis (v0.1)

**Status:** v0.1, written 2026-09-24, before any code or data. The per-stratum
predictions below are copied into experiment E-001 (`experiments/registry.md`)
before the first run; after that, changes are new versions with a dated
decision-journal entry, never silent edits.

---

## Research question

> In multi-step retrieval over a closed knowledge base, does an agent know —
> at each step — whether the evidence it has gathered is enough to answer, to
> keep searching, or to abstain? And does making that decision explicit pay for
> itself when a wrong answer costs more than an abstention?

## Central axis

The agent does not fail because it cannot search. **It fails because it does
not know it has not found the answer yet.** That failure can be measured step by
step when "found" is known by construction.

A system can fail in two different ways:

- **Failing to search** — it never reaches the evidence.
- **Failing to decide** — it reaches the evidence and does not notice, or does
  not reach it and answers anyway.

Exact per-step sufficiency labels separate the two. That separation is what
prevents over-claiming: a better detector cannot fix a search that never finds
the evidence.

## Statement

> In multi-step retrieval, the bottleneck is not searching: it is deciding
> whether the accumulated evidence is enough. An agent whose sufficiency
> detector is implicit — the model's own decision to stop or continue — stops
> early on plausible but insufficient evidence (missing hop, wrong version,
> truncated set) and answers when the answer does not exist in the corpus. In a
> controlled world where the sufficiency of every step is known by
> construction, an explicit detector (a sufficiency judge at every step)
> reduces the expected cost of answers relative to the implicit detector; this
> gain (i) concentrates in the insufficiency strata, (ii) does not appear in the
> control stratum, (iii) goes through correct stopping decisions, and (iv) is
> not reached by a placebo that searches the same amount blindly. A trained
> detector — a calibrated classifier over cheap signals of the agent's state —
> matches the explicit detector in expected cost while spending fewer tokens.

## Outcome and cost convention

Per question: **C = 0 if correct, 1 if abstained, λ if wrong**, with **λ = 4** as
the registered scenario. "Gain" means a reduction in C. The rationale for λ and
the headline tipping point λ\* are in
[ADR-005](adr/adr-005-cost-function-lambda-4-and-caps.md).

## The arms

All arms share the corpus, the tools (`search`, `open_page`), the model, the
cost instruction ("a wrong answer costs 4× not answering"), the caps
(T_max = 6 steps, B = 4,000 evidence tokens) and the structured output
`{answer, abstain}`.

| Id | Arm | What changes | Release |
|---|---|---|---|
| A0 | Closed-book | No tools; measures contamination (≈ 0 on the twin) | v1.0 |
| A1 | Single-shot | One hybrid search, k tuned on dev | v1.0 |
| A2 | Fixed pipeline with typed expansion | Search → expand typed links from the pages found, up to B | v1.0 |
| A3 | Agent, implicit detector | The model decides to stop / continue / abstain (ReAct-style) | v1.0 |
| A4 | Agent, explicit detector | After each observation a judge answers only yes/no: "is this enough?" ([ADR-006](adr/adr-006-judge-outputs-boolean-only.md)) | v1.0 |
| A4p | Depth placebo | A3's loop, forced to search until a step k drawn from A4's step distribution in the same stratum ([ADR-010](adr/adr-010-depth-placebo-and-release-slicing.md)) | v1.0 |
| A5 | Agent, trained detector | A calibrated classifier over cheap state signals decides | v1.1 |
| O1 | Evidence oracle | Receives exactly the gold units; ceiling of generation, measures P(correct \| sufficient) | v1.0 |
| O2 | Stopping oracle | A3's search, stop decided by the gold label; ceiling of the detector given the search policy | v1.0 |
| A6 | 16× context | Single-shot with 16 × B; answers "just add more context"; S3 only | v1.0 |

Oracle figures (O1, O2) are never system scores and are labelled as oracle
wherever quoted.

## Strata (one example question each)

Names below are the real ones, for readability. **In the primary population
every name is renamed** — species, moves, abilities, types and versions
([ADR-003](adr/adr-003-counterfactual-twin-as-primary.md)).

| Stratum | Example | What makes it hard |
|---|---|---|
| **S0 — one hop, sufficient (control)** | *"What is Charmander's hidden ability?"* | Nothing: one section answers. Every arm should stop at step 1 |
| **S1 — missing hop** | *"What is the hidden ability of the final form of Charmander's evolution line?"* | Step 1 finds Charmander; the final form exists only after reading the evolution chain. Stopping at step 1 is stopping with insufficient evidence |
| **S2 — wrong version** | *"At what level does Charmander learn Flamethrower in Scarlet/Violet?"* | The corpus has the learnset of other versions, with different levels. Answering from the wrong version is accepting plausible, insufficient evidence |
| **S3 — truncated set** | *"Which Ice-type Pokémon learn Freeze-Dry by level in Scarlet/Violet?"* | The answer is a set; search returns part of it per step. A partial list is a wrong answer, and nothing says how many elements are missing ([ADR-009](adr/adr-009-no-truncation-cues-in-main-condition.md)) |
| **S4 — no answer in the corpus** | *"At what level does X learn Y in Scarlet/Violet?"*, with that version's learnset section **withheld** | Other versions' sections remain. The only correct answer is to abstain |

## Claims

| Claim | Design | Population | Threshold |
|---|---|---|---|
| **H1** — A4 (explicit) reduces C relative to A3 (implicit) | Superiority | S1–S4 pooled, eval-L1 | 0.25 units of C |
| **H2** — A4 reduces C relative to A2 (fixed pipeline) | Superiority | S1–S4 pooled, eval-L1 | 0.25 |
| H1b — A4 beats the placebo A4p | Superiority, **secondary** (outside the Holm family) | S1–S4 pooled, eval-L1 | Read through outcome-space row 2 |
| **H3** — A5 (trained) is not worse than A4 in C while spending fewer tokens | **Non-inferiority**, margin 0.25, token condition as co-requirement | S1–S4 pooled, eval-L2 | margin 0.25 |

H3 is non-inferiority because the classifier's reason to exist is being
**cheaper** than the judge; demanding superiority would test the wrong thing.
Power, thresholds and the verdict rule are in
[`measurability-gate.md`](measurability-gate.md).

## A-priori predictions per stratum

| Stratum | A2 (fixed pipeline) vs A1 (single-shot) | A3 (implicit detector) | A4 (explicit) − A3 | Mechanism prediction |
|---|---|---|---|---|
| S0 control | Tie | Stops at step 1 | **≈ 0 in C**; A4 spends more tokens | Nothing to detect |
| S1 missing hop | A2 > A1 (typed expansion sometimes reaches hop 2) | Stops early in a relevant fraction | Moderate gain | Premature stop avoided |
| S2 wrong version | Tie | Often accepts the wrong version | **Largest predicted gain** | Near-certain evidence rejected |
| S3 truncated set | Tie; A6 (16×) competitive | Answers with a partial list | Small gain, only if the tool reported the total | Truncation noticed |
| S4 no answer | Tie (both answer wrongly) | Answers from another version | **Large gain in C**, with more tokens | Abstention instead of invention |

If S0 shows a gain of the same size as the insufficiency strata, the gain comes
from extra calls, not from detection — outcome-space row 1.

**Placebo prediction (A4p).** On S1, blind extra search recovers part of the
missing hop, so A4p lands between A3 and A4. On S2 and S4, searching more does
not help reject near-certain evidence or recognize absence, so A4p stays near
A3. If A4p matches A4 on those two strata, the detection thesis falls —
outcome-space row 2.

**Mediation prediction.** Among the questions where A4 reduces C, in **≥ 50%**
A3 stopped at a step labelled insufficient and A4 did not.

## Scope

- The contribution is **sequential sufficiency detection**; the agent is the
  experimental mechanism.
- The counterfactual twin removes the model's memory — **one** property of a
  private corpus — and none of the others (messy text, contradictory documents,
  internal jargon). It is a controlled sufficiency benchmark, not a stand-in for
  company data. The v1.2 extension measures how much the conclusion changes in
  the real world, where the model remembers.
- Per-stratum readings are **descriptive**, with intervals; no single-stratum
  claim enters the verdict.
