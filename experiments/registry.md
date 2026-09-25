# Experiment Registry

Every experiment is registered here **before it runs**: objective, hypothesis,
configuration, decision rule and expected result. The **Actual result** is
filled only after the run, next to the date. A registered entry is never
rewritten after data exists: changes before the run are dated amendments at the
end of the entry; changes after the run are new entries.

## Schema

| Field | Meaning |
|---|---|
| ID | `E-XXX`, zero-padded, monotonically increasing |
| Phase | Phase (milestone) that runs it |
| Status | `draft` → `frozen` (config hashed, before the run) → `run` → `analyzed` |
| Hypothesis | H1 / H2 / H3 (see `docs/hypothesis.md`), or gating / exploratory |
| Objective | One sentence: what question does it answer? |
| Configuration | Split, n, arms, model, caps, seeds, hashes |
| Decision rule | What each possible result leads to, written before the run |
| Expected result | The author's prediction, written before the run |
| Actual result | After the run: numbers with N-of-M, intervals, the rule applied, date |

## Ledger

| ID | Phase | Status | Hypothesis | Objective | Actual |
|---|---|---|---|---|---|
| [E-001](#e-001--layer-1-does-an-explicit-sufficiency-detector-pay-for-itself) | 6 | draft | H1, H2 (+ H1b secondary) | Layer 1 verdict: does an explicit sufficiency judge reduce expected cost vs the implicit detector and vs a fixed pipeline? | — |
| [E-002](#e-002--how-much-does-typed-expansion-already-solve) | 3 | draft | gating for H2 | How much of each insufficiency stratum does the fixed pipeline with typed expansion already solve? | — |

---

## E-001 — Layer 1: does an explicit sufficiency detector pay for itself?

- **Phase:** 6 (dress rehearsal, freeze, single opening of eval-L1).
- **Status:** draft — registered 2026-09-24, before any code or data. Becomes
  `frozen` when the freeze manifest (below) is hashed in Phase 6, before
  eval-L1 is opened.
- **Hypotheses:** H1, H2 (primary family, Holm); H1b (secondary, outside the
  family). Statements in [`docs/hypothesis.md`](../docs/hypothesis.md).

### Objective

Decide, on a pre-registered rule, whether an agent with an **explicit**
per-step sufficiency judge (A4) reduces expected cost C relative to (H1) the
same agent with an **implicit** detector (A3) and (H2) a fixed pipeline with
typed expansion (A2) — and whether any gain is attributable to **knowing when
to stop** rather than to searching more.

### Configuration

**World and population.**
- Counterfactual twin of the PokéAPI world (pinned commit in
  [`docs/data-sources.md`](../docs/data-sources.md)); rendered pages; hybrid
  index (BM25 + dense).
- **eval-L1: 400 questions** — S0 80; S1, S2, S3, S4 80 each — drawn with a
  registered seed from template groups **A and B**. The size stays adjustable
  until the ids are frozen in Phase 6 (measurability gate 8); the pooled S1–S4
  n is the one used for H1/H2 (plan: 320).
- eval-L1 is opened **once**. The opening count is published.

**Arms** (all share corpus, tools, model, cost instruction, caps and the
structured output `{answer, abstain}`):

| Arm | Role in E-001 |
|---|---|
| A0 closed-book | Contamination check (descriptive) |
| A1 single-shot | Baseline (descriptive) |
| A2 fixed pipeline, typed expansion | H2 reference |
| A3 agent, implicit detector | H1 reference |
| A4 agent, explicit boolean judge | Treatment |
| A4p depth placebo | H1b reference; dose = A4's step distribution per stratum from this same opening |
| O1 evidence oracle | P(correct \| sufficient); labelled oracle |
| O2 stopping oracle | Ceiling O2 − A3; labelled oracle |
| A6 16× context | S3 only (descriptive) |

**Run order:** A0, A1, A2, A3, A4, O1, O2, A6 → A4p (dose from A4; **dose
adherence checked before any result is read**) → cue ablation on S3 (A3, A4 with
total count and `(k/N)` markers). Batch API, idempotent per question id; a
failed job is re-run on the same ids, never re-drawn.

**Fixed parameters:** λ = 4 (C = 0 correct, 1 abstain, 4 wrong); T_max = 6
steps; B = 4,000 evidence tokens; `search(query, k ≤ 5)` with no total count and
no pagination markers (main condition); same cost instruction for every arm
("a wrong answer costs 4× not answering").

**Model:** gpt-5-mini, Batch tier, `reasoning_effort` low, frozen for the run.

**Freeze manifest (filled and hashed in Phase 6, before the opening):**

| Item | Value |
|---|---|
| World hash (graph export, twin map, rendered pages) | _Phase 6_ |
| Index hash | _Phase 6_ |
| Prompt hashes (all arms, judge prompt after ≤ 3 dev iterations on group A) | _Phase 6_ |
| Model id and snapshot; `reasoning_effort` | _Phase 6_ |
| Container image versions (Neo4j, Phoenix) | _Phase 6_ |
| eval-L1 ids, seed, n per stratum | _Phase 6_ |
| Template partition A / B | _Phase 2_ |
| Tool condition (main) and cue-ablation condition | _Phase 5_ |
| A4p dose rule | This entry (above) |
| Price per million tokens at run time | _Phase 6_ |

**Instrument prerequisites (measurability gate 7):** twin round trip 100%;
renderer registry complete; generator audit ≥ 58/60 (G3); labeler 100% on
golden trajectories; grader ≥ 98/100 on the audit; token meter matches API
usage on 10 calls; identity probe positive control ≥ 50%. No number from an
instrument without its check.

### Analysis plan

- **Unit:** question, paired across arms. D = C(reference) − C(treatment);
  positive D favours the treatment.
- **Primary contrasts:** H1 = A3 − A4, H2 = A2 − A4, on S1–S4 pooled.
- **Inference:** mean of D with a paired bootstrap (10,000 resamples, seed
  recorded in the freeze manifest). Two-sided p-values from the bootstrap;
  **Holm** over {H1, H2} at familywise α = 0.05; each contrast's interval is
  reported at its Holm-adjusted level.
- If E-002 removes strata from the H2 pool, H2 is computed on the remaining
  strata; if E-002 removes H2 from the family, H1 is tested alone at α = 0.05.
- **Three-valued verdict** per contrast:
  - **supported** — the interval excludes zero in favour of the treatment
    **and** the point estimate is ≥ 0.25;
  - **refuted** — the upper limit of the interval is below 0.25;
  - **inconclusive** — everything else.
- **Per-stratum readings** (n = 80 each): descriptive, with 95% intervals; no
  single-stratum claim enters the verdict.

**Mechanism quantities.**
- **Falsifier (S0):** A4's gain over A3 on S0, with its interval.
- **Placebo (H1b):** gain of A4 over A4p, as a fraction of the gain of A4 over
  A3, on S1–S4 pooled.
- **Mediation:** among questions where C(A4) < C(A3), the fraction in which A3
  stopped at a step labelled insufficient and A4 did not.
- **Gain decomposition:** A4's gain over A3 split into questions where the two
  stopped at different steps (detection component) and at the same step
  (non-attributable component).
- **Detector precision / recall per step**, against the exact label, by
  insufficiency subtype (`missing-hop`, `wrong-version`, `truncated`,
  `nonexistent`); implicit-detector firing rate.
- **Stopping-oracle ceiling:** O2 − A3 (labelled oracle).

**λ-free headline.** Each arm's operating point (error rate, abstention rate).
For A4 vs A3 and A4 vs A2, the tipping point

```text
λ* = (abst_A4 − abst_ref) / (err_ref − err_A4)
```

with a paired-bootstrap interval, classified into exactly one of four cases:

| Case | Condition | Reading |
|---|---|---|
| A4 dominates | err_A4 ≤ err_ref and abst_A4 ≤ abst_ref, one strictly | A4 is better for every λ |
| Tipping above λ\* | err_A4 < err_ref and abst_A4 > abst_ref | A4 is better for every λ > λ\* |
| Tipping below λ\* | err_A4 > err_ref and abst_A4 < abst_ref | A4 answers more and errs more; better only for λ < λ\* |
| A4 dominated | err_A4 ≥ err_ref and abst_A4 ≥ abst_ref, one strictly | A4 is worse for every λ |

(Equal error and abstention rates: no difference, reported as such.)
Sensitivity: C recomputed at λ ∈ {2, 4, 9}.

**Other secondary readings (descriptive):** accuracy and abstention rate per
arm and stratum; **template gap A × B per arm, aggregated by group, never per
template**; cue ablation on S3; tokens, US$ and steps per question per arm,
with the agent's cost multiplier next to every gain; A6 vs A1 on S3.

### Decision rule — outcome space (first matching row wins)

| # | Condition | Published reading |
|---|---|---|
| 1 | **Falsifier fired**: A4's pooled gain over A3 is positive, the S0 gain is ≥ 50% of it **and** the S0 interval excludes zero in favour of A4 | "The gain exists but is not attributable to detection: it appears where there is nothing to detect." H1 reported, not interpreted as mechanism |
| 2 | **Placebo explains the gain**: H1 supported, but A4's gain over A4p is < 50% of its gain over A3 | "The gain comes from searching more, not from knowing when to stop." |
| 3 | H1 supported and mediation ≥ 50% | **Thesis supported**: deliberate detection reduces cost, and the gain goes through correct stops |
| 4 | H1 supported and mediation < 50% | "The judge helps, but by another path" — diagnosis by subtype and steps spent |
| 5 | H1 refuted | "Deliberate detection does not pay for itself here." If A4 is worse: abstains too much, or stops too late? |
| 6 | H1 inconclusive and O2 − A3 < 0.25 | "There is no room: not even a perfect detector would pay here." |
| 7 | H1 inconclusive and O2 − A3 ≥ 0.25 | "There is room, and the explicit judge does not capture it" — motivates v1.1 |

**H2, read independently:**

| H2 verdict | Published sentence |
|---|---|
| supported | "An explicit detector beats a well-tuned fixed pipeline on the insufficiency strata, by at least the action threshold." |
| refuted | "A well-tuned fixed pipeline is as good as the agent with an explicit detector, within the action threshold; the extra machinery does not pay here." |
| inconclusive | "The budget does not separate the agent with an explicit detector from the fixed pipeline." |

**Abort and futility rules (applied in Phase 6, before the opening):**
- n\* = (3.08 × SD_sup / 0.25)², SD_sup = upper limit of the 80% interval of the
  SD of D(A3 − A4) on the dress rehearsal. n\* ≤ 320: keep the plan.
  320 < n\* ≤ 640: draw more questions up to n\*, paid by the v1.0 cut order.
  n\* > 640: H1 and H2 become descriptive (detector precision / recall by
  subtype); the README states that the budget did not support a cost claim.
- If O2 − A3 on dev is below 0.25, H1 is declared without room before the
  opening, and the published result is the ceiling (row 6 by rule).

### Error taxonomy (fixed before the run; mostly mechanical)

| Code | Definition | Assignment |
|---|---|---|
| `stop-missing-hop` | Answered at a step labelled insufficient (missing hop) | Automatic |
| `accepted-wrong-version` | Answered with evidence from another version | Automatic |
| `accepted-truncated-set` | Answered with part of the set | Automatic |
| `answered-unanswerable` | Answered in S4 | Automatic |
| `abstained-with-sufficient` | Abstained after reaching sufficient evidence | Automatic |
| `over-search` | Kept searching after reaching sufficient evidence (cost error, not outcome error) | Automatic |
| `never-reached` | Reached T_max without ever reaching sufficient evidence (search failure, not decision failure) | Automatic |
| `generation-error` | Answered at a sufficient step and was wrong | Automatic code; **manual reading** for the cause |
| `format-error` | The grader could not parse the output | Automatic; counts against the grader (gate 4) |

Every code that occurs gets a manual sample with prompt and completion
rendered; no code is published as a count only.

### Expected result (author's prediction, 2026-09-24)

Per stratum (C with λ = 4; "gain" = reduction in C):

| Stratum | A2 vs A1 | A3 | A4 − A3 | Mechanism |
|---|---|---|---|---|
| S0 control | Tie | Stops at step 1 | ≈ 0 in C; A4 spends more tokens | Nothing to detect |
| S1 missing hop | A2 > A1 | Stops early in a relevant fraction | Moderate gain | Premature stop avoided |
| S2 wrong version | Tie | Often accepts the wrong version | **Largest gain** | Near-certain evidence rejected |
| S3 truncated set | Tie; A6 competitive | Answers with a partial list | Small gain (no cue in the main condition) | Truncation noticed |
| S4 no answer | Tie (both wrong) | Answers from another version | **Large gain**, with more tokens | Abstention instead of invention |

- **Placebo:** on S1, A4p between A3 and A4; on S2 and S4, A4p near A3.
- **Mediation:** ≥ 50%.
- **Overall:** outcome-space **row 3** (thesis supported); H2 supported;
  λ\* case "tipping above λ\*" or "A4 dominates" vs A3.

### Actual result

_Not run._

### Amendments

_None._

---

## E-002 — How much does typed expansion already solve?

- **Phase:** 3 (pilot gate), before any agent exists.
- **Status:** draft — registered 2026-09-24.
- **Hypothesis:** gating for H2. The cheap thing is measured first: if a fixed
  pipeline already delivers sufficient evidence, the agent has nothing to add
  there.

### Objective

For each stratum, measure the fraction of questions for which the evidence set
delivered by A2 (search + typed-link expansion up to B) is **labelled
sufficient** — and remove from H2 the strata where there is no room.

### Configuration

- **Split:** dev, 150 questions, **template group A only** (S0 30; S1–S4 30
  each).
- **Arm:** A2 retrieval only — **no LLM call**. The outcome is the sufficiency
  label of the delivered evidence set, computed by the labeler over the fact →
  units registry. Cost: zero API spend.
- **A2 configuration — generous by design:** `search(query, k = 5)` on the
  question text; expand **every** typed link type from the pages found,
  breadth-first, until B = 4,000 evidence tokens. This is an upper bound on what
  a fixed pipeline can deliver within B, so the rule errs toward removing strata
  from H2, not toward keeping them. Sensitivity: k = 3.
- Main tool condition (no total count, no pagination markers).

### Measurement

Per stratum: N-of-M questions with a sufficient delivered set, Wilson 95%
interval. For S2 and S4 also: N-of-M sets containing near-certain units
(another version's section). For S3: the distribution of the fraction of the
set delivered.

### Decision rule

- If A2 delivers sufficient evidence in **≥ 80%** of the questions of a stratum
  (point estimate), H2 has no room in that stratum, and **it leaves the H2 pool**
  in E-001.
- If this happens in **≥ 3 of the 4 insufficiency strata**, H2 leaves the
  primary family and H1 is tested alone at α = 0.05.
- Note on S4: by construction no sufficient set exists, so S4 can never reach
  80% and always stays in the pool. In practice the second rule triggers only if
  S1, S2 and S3 all reach 80%.
- The rule is applied as written and logged in the decision journal the same
  day, with the counts.

### Expected result (author's prediction, 2026-09-24)

No stratum reaches 80%. S1 is the highest (typed expansion sometimes reaches
the second hop); S2 and S3 stay low; S4 is 0 by construction. H2 stays in the
primary family on all four insufficiency strata.

### Actual result

_Not run._

### Amendments

_None._
