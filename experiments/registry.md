# Experiment Registry

Every experiment is registered here **before it runs**: objective, hypothesis,
configuration, decision rule and expected result. The **Actual result** is
filled only after the run, next to the date.

- While an entry is `draft`, its body may be edited, and **every change is
  logged with its date and reason under Amendments**.
- Once `frozen` (configuration hashed, before the run), the body is immutable;
  corrections become new entries.

## Schema

| Field | Meaning |
|---|---|
| ID | `E-XXX`, zero-padded, monotonically increasing |
| Phase | Phase (milestone) that runs it |
| Status | `draft` → `frozen` (config hashed, before the run) → `run` → `analyzed` |
| Hypothesis | H1 / H2 / H3 (see `docs/hypothesis.md`), or gating / descriptive |
| Objective | One sentence: what question does it answer? |
| Configuration | Split, n, arms, model, caps, seeds, hashes |
| Decision rule | What each possible result leads to, written before the run |
| Expected result | The author's prediction, written before the run |
| Actual result | After the run: numbers with N-of-M, intervals, the rule applied, date |

## Ledger

| ID | Phase | Status | Hypothesis | Objective | Actual |
|---|---|---|---|---|---|
| [E-001](#e-001--layer-1-does-an-explicit-sufficiency-detector-pay-for-itself) | 6 | draft | H1, H2 (+ H1b secondary) | Layer 1 verdict: does an explicit sufficiency judge reduce expected cost vs the implicit detector and vs a fixed pipeline? | — |
| [E-002](#e-002--how-much-does-typed-expansion-already-deliver) | 3 | draft | descriptive | How much sufficient evidence does the fixed pipeline with typed expansion already deliver, per stratum? | — |

---

## E-001 — Layer 1: does an explicit sufficiency detector pay for itself?

- **Phase:** 6 (dress rehearsal, freeze, single opening of eval-L1).
- **Status:** draft — registered 2026-09-24, before any code or data; revised
  the same day after a red-team review (see Amendments). Becomes `frozen` when
  the freeze manifest is hashed in Phase 6, before eval-L1 is opened.
- **Hypotheses:** H1, H2 (primary family); H1b (secondary, outside the family).
  Statements in [`docs/hypothesis.md`](../docs/hypothesis.md).

### Objective

Decide, on a pre-registered rule, whether an agent with an **explicit**
per-step sufficiency judge (A4) reduces expected cost C relative to (H1) the
same agent with an **implicit** detector (A3) and (H2) a fixed pipeline with
typed expansion (A2) — and whether any gain is attributable to **knowing when
to stop** rather than to searching more or to sampling noise.

### Definitions

- **Step:** one tool call plus its observation. **Stopped at step t:** the
  final action (answer or abstain) is taken after observation t. A2 has a single
  step (its delivered evidence set); A4p stops at its drawn k.
- **Label at the final action:** the sufficiency label of the units seen up to
  the stopping step — `sufficient`, `insufficient` (with subtype), or
  `abstained` when the final action is abstention.
- **Outcome per question:** C = 0 if correct, 1 if abstained, λ = 4 if wrong.
  `abstain = true` overrides any answer text. An unparseable final output
  scores **C = λ** in every arm (a model error; it is also logged as
  `format-error` for the grader audit). An API failure after 3 retries on the
  same id scores **C = λ**, is counted per arm, and is never excluded.
- **Judge output** other than yes/no is read as "no".
- **Agent decision table** (A3, A3′, A4 and A4p run the same loop with the same
  agent prompt; only the detector differs). After each observation the agent
  proposes one of {answer, search, abstain}; the proposal is **logged before the
  detector decides**.

  | Proposal | A3 / A3′ (implicit) | A4: judge "yes" | A4: judge "no" | A4p before k | A4p at k |
  |---|---|---|---|---|---|
  | answer | answer | answer | search (**veto**) | search (**veto**) | answer |
  | search | search | search | search | search | answer or abstain (the agent is asked to decide) |
  | abstain | abstain | abstain | abstain | search (**veto**) | abstain |
  | at T_max (search is not offered; the agent proposes answer or abstain) | as proposed | as proposed | abstain | — (k ≤ T_max) | — |

  The A4 judge is called on **every** proposal. A **veto** is a detector
  overriding an "answer" (or, for A4p, "abstain") proposal. The A4p agent is
  never told about k; it proposes freely, and the vetoes are logged exactly as
  for A4.
- **S3 grading:** set equality after alias normalization; a partial or
  over-complete set is wrong.
- **Pooled estimand:** the mean of D over S1–S4 with **equal weight per
  stratum** (the design is balanced, so this is the plain mean).

### Configuration

**World and population.**
- Counterfactual twin of the PokéAPI world (pinned commit in
  [`docs/data-sources.md`](../docs/data-sources.md)); rendered pages; hybrid
  index (BM25 + dense).
- **eval-L1: 400 questions** — S0 80; S1, S2, S3, S4 80 each — drawn with a
  registered seed from template groups A and B, with **equal numbers per
  template within each stratum** (so the A/B proportion equals the template
  proportion, recorded in the manifest). Extra questions under gate 8 keep the
  strata balanced.
- **Separation from dev:** no eval-L1 question shares a gold chain, or a
  (template, anchor entity) pair, with any dev or train question. Checked by the
  generator and logged with N-of-M.
- **S2:** a (species, move) pair is kept only if the asked level differs from
  its level in **every other version group in the corpus** (N-of-M logged). The
  selection shift toward moves whose level changed is a declared threat.
- **S4:** withheld units are absent from the index **globally**; the generator
  asserts that no question in any stratum has a withheld unit in its gold
  chain.
- eval-L1 is opened **once**. The opening count is published.

**Arms** (all share corpus, tools, model, cost instruction, caps and the
structured output `{answer, abstain}`):

| Arm | Role in E-001 |
|---|---|
| A0 closed-book | Contamination check (descriptive) |
| A1 single-shot | Baseline (descriptive) |
| A2 fixed pipeline, typed expansion | H2 reference; configuration pinned in the manifest after the Phase 4 sweep |
| A3 agent, implicit detector | H1 reference |
| **A3′ second run of A3** | Noise null for the gain decomposition; S1–S4 only |
| A4 agent, explicit boolean judge | Treatment |
| A4p depth placebo | H1b reference; dose = A4's step distribution per stratum from this same opening |
| O1 evidence oracle | P(correct \| sufficient); labelled oracle |
| O2 gold-label stop on A3's search | Reference for "room" (rows 6–7); labelled oracle. Not a strict ceiling under C: abstaining on sufficient but error-prone questions can beat it |
| A6 16× context | S3 only (descriptive) |

**Prompt tuning parity.** The A3 agent prompt (shared by A3, A3′, A4 and A4p),
the A2 answer prompt and the A4 judge prompt get the **same tuning budget**: at
most 3 recorded iterations each, on dev group-A templates, with mean C on dev
S1–S4 as the criterion. Any sufficiency-checking instruction that enters the
judge prompt — stratum-specific (e.g. "check the version", "is the list
complete?") or generic (e.g. "list the facts the question needs", "check
assumptions implicit in the question") — is added verbatim to the shared agent
prompt.

**A2 sweep (Phase 4, dev group A):** grid k ∈ {2, 3, 5} × hybrid weight
BM25/dense ∈ {0.3, 0.5, 0.7} × expansion depth ∈ {1, 2} × link-type order ∈
{the E-002 order, its reverse}. **Two stages** (amended 2026-09-28):
1. all 36 configurations are screened by the labeler, ranked by the share of
   dev S1–S4 questions whose delivered set is sufficient (no API call);
2. the top 3 run with the model, and the criterion is mean C on dev S1–S4.

Ties go to the smaller k, then depth 1. The link-type set is defined in Phase 1
and appended here as a dated amendment before the sweep runs. The full grid,
including what is not adopted and the stage-1 ranking, is published.

**Run order:** A0, A1, A2, A3, A3′, A4, O1, O2, A6 → A4p (dose from A4;
adherence checked before any result is read) → cue ablation on S3 (A3, A4 with
total count and `(k/N)` markers). Batch API, idempotent per question id; a
failed job is re-run on the same ids, never re-drawn.

**Depth placebo rules.**
- If B binds before step k, A4p decides at that step; the question is flagged.
- **Dose assignment:** within each stratum, A4p's k values are a seeded
  random **permutation of A4's realized step counts** (not independent draws),
  so the dose matches A4's distribution exactly by construction.
- **Adherence:** total-variation distance ≤ 0.10, per stratum, between the
  realized A4p step distribution and A4's; with the permutation it measures
  only B binding and early termination. On failure, one re-run with a new
  registered seed; if it fails again, row 2 reads "placebo not delivered".

**Fixed parameters:** λ = 4; T_max = 6 steps; B = 4,000 evidence tokens;
`search(query, k ≤ 5)` with no total count and no pagination markers (main
condition); `open_page(title, section=None, offset=0)`, which reads a page from
the top and continues with `offset`, with nothing saying whether more remain;
at most 700 tokens of units per call (`o200k_base`); the same cost instruction
for every arm ("a wrong answer costs 4× not answering").

**Model:** gpt-5-mini, Batch tier, `reasoning_effort` low, frozen for the run.

**Freeze manifest (filled and hashed in Phase 6, before the opening):**

| Item | Value |
|---|---|
| World hash (graph export, twin map, rendered pages) | _Phase 6_ |
| Index hash | _Phase 6_ |
| Prompt hashes (all arms, after ≤ 3 dev iterations each on group A) | _Phase 6_ |
| A2 configuration (from the Phase 4 sweep) | _Phase 4_ |
| Model id and snapshot; `reasoning_effort` | _Phase 6_ |
| Container image versions (Neo4j, Phoenix) | _Phase 6_ |
| eval-L1 ids, seed, n per stratum, A/B proportion per stratum | _Phase 6_ |
| Template partition A / B | _Phase 2_ |
| Tool condition (main) and cue-ablation condition | _Phase 5_ |
| Randomization and bootstrap seeds | _Phase 6_ |
| Price per million tokens at run time | _Phase 6_ |

**Instrument prerequisites (measurability gate 7):** twin round trip 100%;
renderer registry complete; generator audit ≥ 58/60 (G3); shortcut scan 100%
on planted leaks, with its flags on the generated questions resolved and
published N-of-M; labeler 100% on golden trajectories; grader ≥ 98/100 on the audit; token meter matches API
usage on 10 calls; identity probe positive control ≥ 50%.

### Analysis plan

- **Unit:** question, paired across arms. D = C(reference) − C(treatment);
  positive D favours the treatment.
- **Primary contrasts:** H1 = D(A3 − A4) and H2 = D(A2 − A4), both on S1–S4
  pooled. The H2 population is **always S1–S4**; E-002 cannot change it.
- **Inference.**
  - The **verdict is decided by the intervals alone**: BCa bootstrap (10,000
    resamples) at **97.5%** for both contrasts (Bonferroni over the family).
  - p-values from a paired **sign-flip randomization test** on D (10,000
    flips), raw and Holm-adjusted, are reported as **descriptive**; any
    disagreement between a p-value and its interval is reported.
  - All **secondary intervals** are 95% two-sided BCa (exact sign-flip for a
    single stratum), pointwise, not adjusted for multiplicity.
- **Three-valued verdict** per contrast:
  - **supported** — the interval excludes zero in favour of the treatment
    **and** the point estimate is ≥ 0.25;
  - **refuted** — the upper limit of the interval is below 0.25;
  - **inconclusive** — everything else.
- **Per-stratum readings and the S0 falsifier:** exact sign-flip test and
  interval; an interval "excludes zero" only if the stratum has **≥ 10
  discordant pairs**. Per-stratum readings are descriptive.

**Mechanism quantities.**
- **Mediation.** m_X = number of questions with C(X) < C(A3) **and** at least
  one detector veto of an "answer" proposal at a step labelled insufficient,
  for X ∈ {A4, A4p}; g_A4 = number of questions with C(A4) < C(A3).
  **Mediation = (m_A4 − m_A4p) / g_A4**, with a paired-bootstrap 95% interval.
  - It can be negative: that reads as row 4, "forced search explains the
    vetoes".
  - If the placebo is not delivered or is harmful, rows 3–4 use the **gross**
    mediation m_A4 / g_A4, labelled "not net of placebo".
- **Gain decomposition.** Questions are classified by the transition of the
  label state at the final action (sufficient / insufficient / abstained)
  between A3 and the compared arm. For each transition cell, the net C-gain
  is reported for **A4 vs A3, A4p vs A3 and A3′ vs A3**, on the same A3 run.
  The share attributed to the judge in a cell is **(A4 − A4p)**, with a
  paired-bootstrap interval; A3′ only calibrates how often each transition
  happens by sampling noise. If A3′ is cut, the decomposition is published with
  "no noise null".
- **Placebo (H1b):** gain of A4 over A4p as a share of the gain of A4 over A3,
  with its bootstrap interval.
- **Detector precision / recall per step**, against the exact label, by
  subtype (`missing-hop`, `wrong-version`, `truncated`, `nonexistent`);
  implicit-detector firing rate.
- **O2 − A3** on S1–S4 (labelled oracle).

**λ-free headline.**
- Each arm's operating point (error rate, abstention rate), S1–S4 pooled.
- For λ in {1, 1.5, 2, …, 20}: the paired interval of
  D(λ) = λ·Δerr − Δabst, for A4 vs A3 and A4 vs A2, and the set of λ where the
  lower limit is > 0 (A4 better) or the upper limit is < 0 (A4 worse).
- The tipping point λ\* = Δabst / Δerr and its case are reported **only if the
  95% interval of Δerr excludes zero**; otherwise "case undetermined".

| Case | Condition | Reading |
|---|---|---|
| A4 dominates | err_A4 ≤ err_ref and abst_A4 ≤ abst_ref, one strictly | A4 is better for every λ |
| Tipping above λ\* | err_A4 < err_ref and abst_A4 > abst_ref | A4 is better for every λ > λ\* |
| Tipping below λ\* | err_A4 > err_ref and abst_A4 < abst_ref | A4 answers more and errs more; better only for λ < λ\* |
| A4 dominated | err_A4 ≥ err_ref and abst_A4 ≥ abst_ref, one strictly | A4 is worse for every λ |

- Sensitivity: C recomputed at λ ∈ {2, 4, 9}.

**Other secondary readings (descriptive):** accuracy and abstention rate per
arm and stratum; **template gap A × B per arm, aggregated by group, never per
template**; cue ablation on S3; tokens, US$ and steps per question per arm, with
the agent's cost multiplier next to every gain; A6 vs A1 on S3.

### Decision rule — outcome space (first matching row wins)

| # | Condition | Published reading |
|---|---|---|
| 0 | **Gate 8 descriptive branch** (n\* > n_max) | No verdict. Detector precision / recall by subtype with intervals; the README states the budget did not support a cost claim |
| 0b | **Futility fired before the opening** (upper 80% limit of O2 − A3 on dev S1–S4 < 0.25) | "A gold-label stop applied to A3's search did not reach the threshold on dev." H1 on eval is descriptive only and cannot enter rows 1–7; H2 is read as usual |
| 1 | **Falsifier fired**: H1 supported, the S0 gain is ≥ 50% of the pooled gain, **and** the S0 interval excludes zero in favour of A4 (≥ 10 discordant pairs) | "The gain exists but is not attributable to detection: it appears where there is nothing to detect." |
| 2 | H1 supported, placebo delivered and not harmful (lower limit of C(A3) − C(A4p) > −0.25), and A4's gain over A4p is < 50% of its gain over A3 | "The gain comes from searching more, not from knowing when to stop." |
| 3 | H1 supported and mediation ≥ 50% | **Thesis supported**: deliberate detection reduces cost, and the gain goes through correct stops |
| 4 | H1 supported and mediation < 50% | "The judge helps, but by another path" — diagnosis by subtype and steps spent |
| 5 | H1 refuted | "Deliberate detection does not pay for itself here." If A4 is worse: abstains too much, or stops too late? |
| 6 | H1 inconclusive and the upper 95% limit of O2 − A3 is < 0.25 | "A gold-label stop applied to A3's search does not reach the threshold." |
| 7 | H1 inconclusive and the lower 95% limit of O2 − A3 ≥ 0.25 | "There is room, and the explicit judge does not capture it" — motivates v1.1 |
| 7b | H1 inconclusive otherwise | "Neither the gain nor the room is resolved at this n." |

Notes on the rows:
- O2 − A3 in rows 6–7 uses a 95% BCa interval on eval S1–S4.
- Rows 2–4 are assigned on point estimates (the 50% share of row 2, the 50%
  mediation of rows 3–4); the interval is printed next to the row, and the
  assignment itself is not a significance test. The 50% cut is a reading
  convention (a majority rule), fixed before any data and derived from
  nothing; the printed interval lets a reader apply another cut.
- Placebo not delivered or harmful: row 2 cannot fire; it is stated next to
  rows 3–4 ("placebo uninformative").
- If the S0 gain is large but H1 is not supported, the S0 reading is published
  as a caveat under rows 5–7.

**H2, read independently:**

| H2 verdict | Published sentence |
|---|---|
| supported | "A4 reduces expected cost versus the fixed pipeline on S1–S4: the point estimate is at least the action threshold and the interval excludes zero." |
| refuted | "The fixed pipeline is within the action threshold of the agent with an explicit detector; the extra machinery does not pay here." |
| inconclusive | "The budget does not separate the agent with an explicit detector from the fixed pipeline." |

**Sizing, abort and futility (applied in Phase 6, before the opening):**
- Power targets the event *supported* = {point ≥ 0.25 and lower limit > 0}.
  Design effect **Δ_design = 0.35**, chosen for budget: 0.30 would need
  n ≈ 638 at SD 1.5. True effects in [0.25, 0.35) have 50–88% power at the plan.
  n\* = the smallest pooled n with P(supported | Δ_design) ≥ 0.80 under the
  normal approximation.
- SD_sup = upper limit of the 80% percentile-bootstrap interval of the SD of D
  on the dress-rehearsal S1–S4 questions, computed **separately for D(A3 − A4)
  and D(A2 − A4)**. **The larger n\* governs both contrasts** (intended: the two
  share one eval-L1 draw).
- **n_max** = the largest pooled S1–S4 n the v1.0 cap pays for after cuts
  (1)–(3) of the cut order, computed with the **Phase 3 measured costs** and
  written in the decision journal **before the dress rehearsal**.
- n\* ≤ 320: keep the plan. 320 < n\* ≤ n_max: draw more questions up to n\*,
  balanced by stratum. **n\* > n_max: row 0.** There is no cap increase after
  the dress rehearsal.
- **Futility:** if the upper 80% limit of O2 − A3 on dev S1–S4 is below 0.25,
  row 0b applies. eval-L1 is still opened, for H2 and for a descriptive H1.

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
| `format-error` | Unparseable final output (scored C = λ) | Automatic; also audited against the grader (gate 4) |
| `correct-at-insufficient` | Answered **correctly** at a step labelled insufficient (a lucky stop). **Not an error in C** (C = 0); a stopping miss with a correct outcome, counted per arm and per stratum | Automatic; manual sample for the source (guess on a small answer space, domain-general inference, or a labeler fault) |

Every code that occurs gets a manual sample with prompt and completion
rendered; no code is published as a count only.

### Expected result (author's prediction, 2026-09-24)

| Stratum | A2 vs A1 | A3 | A4 − A3 | Mechanism |
|---|---|---|---|---|
| S0 control | Tie | Stops at step 1 | ≈ 0 in C; A4 spends more tokens | Nothing to detect |
| S1 missing hop | A2 > A1 | Stops early in a relevant fraction | Moderate gain | Premature stop avoided |
| S2 wrong version | Tie | Often accepts the wrong version | **Largest gain** | Near-certain evidence rejected |
| S3 truncated set | Tie; A6 competitive | Answers with a partial list | Small gain (no cue in the main condition) | Truncation noticed |
| S4 no answer | Tie (both wrong) | Answers from another version | **Large gain**, with more tokens | Abstention instead of invention |

- **Placebo:** on S1, A4p between A3 and A4; on S2 and S4, A4p near A3.
- **Mediation (m_A4 − m_A4p) / g_A4:** ≥ 50%.
- **Decomposition:** the (A4 − A4p) share is concentrated in the insufficient → sufficient/abstained cells.
- **Overall:** outcome-space **row 3**; H2 supported; vs A3, λ\* case "tipping
  above λ\*" or "A4 dominates".

### Actual result

_Not run._

### Amendments

- **2026-09-24 — red-team revision (before any code or data).** Changes:
  1. Power now targets the *supported* event, with Δ_design = 0.35, and n\* is
     computed for H1 and H2 separately (previously sized for "interval excludes
     zero", which gives ~50% chance of *supported* at a true effect of 0.25).
  2. The H2 population is fixed at S1–S4; E-002 became descriptive. Dropping
     strata where A2 is strong would have inflated the H2 effect.
  3. Mediation redefined on the logged judge override, net of the A4p
     baseline; decomposition by label state, with an **A3′ rerun** as noise
     null.
  4. Outcome space: row 0 added; row 1 requires H1 supported; row 2 requires a
     delivered, non-harmful placebo; row 6 uses an interval and new wording;
     futility uses the upper 80% limit.
  5. Prompt-tuning parity across the agent, A2 and judge prompts.
  6. Inference: sign-flip p-values, BCa intervals at 97.5%, and a ≥ 10
     discordant-pairs rule for per-stratum intervals.
  7. λ\*: a λ-grid reading; λ\* only when Δerr is resolved.
  8. Placebo: rule for B binding before k, adherence tolerance, re-run rule.
  9. S2 level-difference filter against every in-corpus version; S4
     withheld units removed globally.
  10. Definitions (step, stop, error handling, S3 grading), dev/eval
      separation, balanced template sampling.
- **2026-09-24 — second red-team pass (before any code or data).** Changes:
  1. Row 0b: futility fired before the opening keeps H1 descriptive.
  2. Agent decision table registered (proposal × detector → action; veto
     defined; A4p never told about k).
  3. Gate 8 extra-questions branch capped at **n_max**, computed from Phase 3
     costs before the dress rehearsal; n\* > n_max → row 0; no cap increase.
  4. A4p dose as a permutation of A4's realized steps.
  5. Mediation = (m_A4 − m_A4p) / g_A4, negative reading and gross fallback
     defined.
  6. Row 7 requires the lower limit of O2 − A3 ≥ 0.25; row 7b added.
  7. Decomposition attributes (A4 − A4p) per transition cell; A3′ calibrates
     noise only.
  8. The verdict is decided by the intervals alone; p-values descriptive;
     secondary intervals 95% BCa pointwise.
  9. A2 sweep grid and criterion registered; the larger n\* governs both
     contrasts; rows 2–4 print intervals; Δ_design rationale stated.
- **2026-09-25 — ADR review (before any code or data).** Changes:
  1. Instrument prerequisites: the shortcut scan (ADR-002) is added — 100% on
     planted leaks, flags on the generated questions resolved and published.
     Reason: the labeler's golden trajectories take the fact → units registry
     as given, and flavor text can state a gold fact the registry does not
     know about.
  2. Notes on the rows: the 50% cut of rows 2–4 is stated as a reading
     convention, not a statistical threshold. No row definition changes.
- **2026-09-26 — after the Joren et al. reading (before any code or data).**
  Changes:
  1. Error taxonomy: `correct-at-insufficient` added, a counted non-error code.
     Reason: C scores a lucky stop as 0, so a judge that correctly vetoes it can
     raise C; the code makes those stops visible next to the mechanism metrics.
  2. Prompt parity widened from stratum-specific to every sufficiency-checking
     instruction in the judge prompt. Reason: a generic decomposition
     instruction still steers toward S2's version check.
  3. The sufficiency label is fixed as coverage of a gold minimal sufficient
     set (ADR-001, update of 2026-09-26). This unblocks the labeler's golden
     trajectories.
- **2026-09-28 — plan revision (before any code or data).** Changes:
  1. The A2 sweep runs in two stages: a labeler screen of all 36
     configurations, then the top 3 with the model. Reason: dev tuning had no
     budget line, and the full grid with the model would cost ≈ US$ 4.3 of the
     ≈ 8 total tuning cost.
  2. The v1.0 cap becomes US$ 20 (ADR-008, update of 2026-09-28). n_max is
     computed against it; there is still no cap increase after the dress
     rehearsal.
- **2026-09-29 — tool contract fixed in Phase 1 (before any run).** The fixed
  parameters now describe `open_page` as built: without `section` it returns
  the page from the top; `section` filters units by their section line;
  `offset` skips units to continue a list longer than one call; past the end it
  answers "No more units." Every call returns at most 700 tokens of units
  (`o200k_base`), the first unit always. Reason: the parameters named only
  `search`, and a species page (~1,500 tokens) or a large hub does not fit in
  one call; `offset` lets an agent that suspects an incomplete list ask for the
  rest, which is the decision S3 measures, while the main condition still says
  nothing about what remains.

---

## E-002 — How much does typed expansion already deliver?

- **Phase:** 3 (pilot gate), before any agent exists.
- **Status:** draft — registered 2026-09-24; made descriptive the same day
  after a red-team review (see Amendments).
- **Hypothesis:** descriptive. It **cannot** change the H2 population, the
  primary family, or any E-001 rule.

### Objective

For each stratum, measure the fraction of questions for which the evidence set
delivered by a fixed pipeline with typed expansion is **labelled sufficient** —
the ceiling on what the non-agentic approach can put in front of the model
within B.

### Configuration

- **Split:** dev, 150 questions, **template group A only**, balanced: S0 30,
  S1–S4 30 each.
- **Pipeline:** retrieval only — **no LLM call**. The outcome is the
  sufficiency label of the delivered set, computed by the labeler over the
  fact → units registry. Cost: zero API spend.
- **Configuration (governs):** `search(query, k = 5)` on the question text;
  expand every typed link type from the pages found, breadth-first, in a
  **link-type order registered in this entry before the run** (link types are
  defined in Phase 1), until B = 4,000 evidence tokens. This is a generous
  upper bound on what a fixed pipeline can deliver; it is **not** the tuned A2
  of E-001.
- **Descriptive only:** k = 3.
- Main tool condition (no total count, no pagination markers).

### Measurement

Per stratum: N-of-M questions with a sufficient delivered set, Wilson 95%
interval. For S2 and S4: N-of-M sets containing near-certain units (another
version's section). For S3: the distribution of the delivered fraction of the
set. S4 is 0 by construction (no sufficient set exists).

### Use of the result

- Reported in the Phase 3 pilot report and in `docs/evaluation.md`.
- It informs the Phase 4 A2 sweep only through the registered sweep grid, on
  group A, under the prompt-tuning parity rule of E-001.
- It never selects strata, thresholds or n for E-001 (measurability gate 6).

### Expected result (author's prediction, 2026-09-24)

No stratum above 80%. S1 is the highest (typed expansion sometimes reaches the
second hop). S2 is high on "delivered" but not on "used correctly": the
breadth-first expansion will often bring every version's section. S3 is low;
S4 is 0 by construction.

### Actual result

_Not run._

### Amendments

- **2026-09-24 — red-team revision (before any code or data).** Changed from a
  gating rule (a stratum with ≥ 80% sufficient delivered sets left the H2 pool;
  ≥ 3 of 4 removed H2 from the family) to descriptive. Reasons:
  - removing strata where the pipeline is strong inflates the pooled H2 effect;
  - "sufficient delivered set" is a poor proxy for the pipeline answering
    correctly, especially on S2;
  - the rule could reduce H2 to S4 alone while the published sentence still
    claimed all insufficiency strata.
  k = 5 now governs, and the link-type order must be registered before the
  run.
