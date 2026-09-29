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
| [E-003](#e-003--identity-probe-can-the-model-name-the-real-species-behind-a-twin-page) | 1 | analyzed | gating (G2) | Can the primary model name the real species behind a twin page, when a masked real page shows the probe works? | Run 1: twin 27 of 50 with notes, 1 of 50 without → notes removed. Run 2 (no notes): control 48, twin 1 of 50 — **G2 identity passes** |

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
the top and continues with `offset`, with nothing saying whether more remain,
and serves the whole page when `section` matches nothing — no tool states that
evidence is missing; at most 700 tokens of units per call (`o200k_base`); the
same cost instruction for every arm ("a wrong answer costs 4× not answering").

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
- **S3 truncation mechanism**, per arm: of the S3 questions answered with the
  full set, the share where the agent stopped **before** reaching the end of the
  list (it suspected the missing part and fetched it) versus the share where it
  learned the end only by asking past it (`offset` answered "No more units.").
  Both are read from the logged trajectories; the second is detection by
  exhaustion, not by suspicion.
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
- **2026-09-29 — no tool states an absence; S3 mechanism split (Phase 1 close
  review, before any run).** Two changes from a design review:
  1. `open_page` with a `section` that matches nothing now serves the whole
     page from the top, with no message; it used to answer "No section
     matching …", which labelled the absence of a withheld S4 section outright.
     An agent asking for a withheld learnset now sees the other versions'
     sections — the plausible, insufficient evidence S4 is built on — and must
     notice the gap itself. The principle, recorded in ADR-009: the structure
     may be artificial; the signal used to decide sufficiency is never handed
     over by the infrastructure.
  2. The mechanism quantities gain the **S3 truncation mechanism**: stopping
     after fetching the rest before reaching the end, versus learning the end
     only by asking past it.

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

---

## E-003 — Identity probe: can the model name the real species behind a twin page?

- **Phase:** 1 (world), before any question exists.
- **Status:** analyzed — registered 2026-09-29; run 1 frozen from its manifest
  (16:57:47 UTC, before submission; see Amendments); run 2 frozen before
  submission. Verdict: G2's identity half passes on world v1 (no notes).
- **Hypothesis:** gating — the identity half of G2 (`docs/contingency.md`).
  The closed-book half runs in Phase 3.

### Objective

Measure how often the primary model, told that a page describes a renamed
Pokémon species, names the real species — on twin pages, against a positive
control of real pages with the species' own name masked, which shows the probe
can detect identification at all.

### Configuration

- **Sample:** 50 species, stratified by generation — 6 from each of
  generations 1–5 and 5 from each of generations 6–9 — drawn with seed
  `20260929` among the species whose default entry has a level-up learnset in
  the version scope (999 species; the pool questions will come from).
  **The same 50 species in every condition** (paired).
- **Conditions** (150 calls):

| Condition | Page shown | Role |
|---|---|---|
| **Control** | Real page, served as `open_page(title)` returns it (≤ 700 tokens), with every occurrence of the species' own name masked as `[MASKED]` (title, evolution line, form names, notes; case-insensitive, whole word) | Positive control |
| **Twin** | Twin page, served as `open_page(title)` returns it | The G2 measurement |
| **Twin, no notes** | Twin page served with its `Notes` unit removed (the freed budget goes to the next units) | Descriptive: attributes a leak to the Pokédex text |

- **Prompt** (identical in every condition, loaded by name from `prompts/`,
  hash logged): "The page below describes a Pokémon species. Its name — and, on
  some pages, every other name — has been replaced. Which real Pokémon species
  is it? Answer with its English name, or 'unknown'." Telling the model what
  to look for makes this the hardest test for the twin.
- **Output:** structured, `{"guess": string, "confidence": number 0–1}`. An
  invalid output is re-sent up to twice; a residual invalid output is excluded
  and reported N-of-M.
- **Model:** gpt-5-mini, Batch API, `reasoning_effort` low (as E-001).
- **Cost:** printed before the run by the token meter; under US$ 0.10 even at
  the pessimistic reasoning assumption. The script supports `--limit N`.

### Measurement

- **Identified (governs):** the guess, normalized (ASCII letters, lower case),
  equals the English name of **any species or form in the same evolution line**
  as the page's species. Knowing the family is enough to answer an S1 question
  from memory.
- **Descriptive:** exact species (or one of its forms); per-generation rates;
  mean confidence of identified and unidentified guesses; "unknown" rate.
- Counts are published N-of-50, with Wilson 95% intervals. At n = 50 the
  interval around 10% spans roughly 4–21%: the rule below is a registered
  count, not a precise estimate.

### Decision rule

1. **Control identified in < 25 of 50** (< 50%): the probe is broken, not the
   twin safe. No G2 verdict; the masking or prompt is fixed as a dated
   amendment here, and the probe re-runs on the same 50 species.
2. **Control ≥ 25 and twin identified in ≤ 5 of 50** (≤ 10%): the identity half
   of G2 passes (preliminary; Phase 3 completes G2).
3. **Twin identified in > 5 of 50:** G2 fails; the exit plan applies
   (`docs/contingency.md`). If the no-notes condition is ≤ 5 of 50, the world
   is rendered without notes (`--no-notes`) and the probe re-runs on a fresh
   sample of 50 species. Otherwise the leak is structural (the facts
   themselves), and primary-population questions exclude the leaking species'
   templates, decided on dev and recorded.

### Run 2 — the G2 exit (registered 2026-09-29, before its run)

Rule 3 applies: run 1 found the twin leaking and the no-notes condition within
the threshold in both bounds. World v1 is rendered without notes and the probe
re-runs:

- **World:** the default render, no `Notes` units (the preparation step refuses
  a world that has them); registry and page-file hashes recorded in the run
  manifest.
- **Sample:** 50 species, the same stratification, seed `20260930`, **excluding
  run 1's 50 species**.
- **Conditions** (100 calls): **control** (the real page, now without notes,
  masked as before) and **twin** (the twin page, now without notes). The
  no-notes condition is the twin itself.
- **Everything else as run 1**, with the amendment of 2026-09-29 in force from
  the start: `max_completion_tokens` 4,000; up to two re-sends of invalid
  answers; first valid answer kept; residual invalid answers counted both ways.
- **Decision rule:** control < 25 of 50 → probe broken; control ≥ 25 and twin
  ≤ 5 of 50 → **G2's identity half passes**; twin > 5 of 50 → the leak is
  structural (the facts themselves) and rule 3's last branch applies.
- **Expected result (author's prediction, 2026-09-29):** control about 45 of
  50; twin 1 or 2 of 50.
- **Freeze manifest** (from `runs/e003-run2/manifest.json`, prepared 17:41:13
  UTC, **frozen before submission**):

| Item | Value |
|---|---|
| Prompt SHA-256 | `f171878d75425a9f0de24c6d9dbd44244b0e32d38ff6b26d1f9e418e4c3efb3c` (as run 1) |
| Real page file SHA-256 (no notes) | `a3e5179bca94149c79ae401c44a8fd3d865c511b13a646f069473f86ab104873` |
| Twin page file SHA-256 (no notes) | `06b3c54b3984e706ee7437d90873ac10a9d36b7785ac853dd8f1a9fe68ab5f74` |
| Registry SHA-256 | `11530e235001f022b786c119cef6cf2a5f6d1a58a5ce247bb2cf841aa754bf53` |
| Seed; species | `20260930`; 50 species, none of run 1's (list in the run manifest) |
| Model; `reasoning_effort`; max completion tokens | gpt-5-mini; low; 4,000 |
| Requests; estimated cost | 100; US$ 0.025 central / 0.050 pessimistic |

### Expected result (author's prediction, 2026-09-29)

Control: about 45 of 50. Twin: 2 or 3 of 50. The notes weigh little: the
no-notes condition lands close to the twin.

### Freeze manifest (2026-09-29)

| Item | Value |
|---|---|
| Prompt `identity_probe` SHA-256 | `f171878d75425a9f0de24c6d9dbd44244b0e32d38ff6b26d1f9e418e4c3efb3c` |
| Real page file SHA-256 | `630f5e0a31707d3bb3f857392de93276c4304d099c7f610f007ff2ba4459c0fa` |
| Twin page file SHA-256 | `187637561f7e7cd2faeb57a7d7769795972720efd09bd4bb33910f4709d66931` |
| Seed; species | `20260929`; 50 species (list in the run manifest) |
| Model; `reasoning_effort`; max completion tokens | gpt-5-mini; low; 1,000 (4,000 for the last re-send and later runs; Amendments) |
| Requests | 150 (50 species × 3 conditions) |
| Estimated cost | US$ 0.038 central / 0.076 pessimistic |
| Batch | `batch_6abbee1579948190afda9a6ca6f4e60a`, submitted 16:57:58 UTC |

### Actual result

**Run 2 (2026-09-29; world v1 without notes; 100 of 100 answers valid, no
re-send).**

| Condition | Identified | Wilson 95% CI | Exact | "unknown" |
|---|---|---|---|---|
| Control | **48 of 50** (96%) | 87–99% | 48 | 0 |
| Twin | **1 of 50** (2%) | 0–10% | 1 | 22 |

By generation, identified: control G1–G6 all, G7 4 of 5, G8 all, G9 4 of 5;
twin G2 1 of 6, every other generation 0.

**Decision: pass — G2's identity half passes** on world v1 (control ≥ 25, twin
≤ 5 of 50). The one identified species is a generation-2 species with a
three-stage evolution line and a Mega form, named at confidence 0.9 with no
text on the page: a residual **structural** fingerprint, within the threshold
and declared as a limitation. The other 49 twin answers were "unknown" (22) or
a wrong species (27, mean confidence 0.61). Measured cost US$ 0.0545.
Prediction: control about 45 (48); twin 1 or 2 (1).

**Run 1, final (2026-09-29; 150 of 150 answers valid after the two registered
re-sends and the 4,000-token re-send of 8).**

| Condition | Identified | Wilson 95% CI | Exact | "unknown" |
|---|---|---|---|---|
| Control | **48 of 50** (96%) | 87–99% | 48 | 1 |
| Twin (with notes) | **27 of 50** (54%) | 40–67% | 27 | 0 |
| Twin, no notes | **1 of 50** (2%) | 0–10% | 1 | 27 |

By generation, identified: control G1–G8 all, G9 3 of 5; twin G1 5/6, G2 3/6,
G3 3/6, G4 3/6, G5 4/6, G6 3/5, G7 4/5, G8 2/5, G9 0/5; no notes: G1 1/6, all
others 0.

**Decision (rule 3): fail — notes.** The probe works; the twin with Pokédex
notes leaks (27 of 50, far above 5); without notes it does not (1 of 50). The
exit is taken: world v1 renders no notes, and run 2 tests that world. Measured
cost, every call and re-send included: US$ 0.1614. Prediction: control about
45 (48); twin 2–3 (27); notes weigh little (they carry nearly all of the leak).

**First collection (2026-09-29, batch `batch_6abbee…`; partial — 29 of 150
answers invalid, see Amendments).** Kept for the record; superseded by the
final counts above.

| Condition | Identified (valid answers) | Bounds with the invalid ones | "unknown" |
|---|---|---|---|
| Control | **48 of 50** (96%; Wilson 95% CI 87–99%), all exact | — (0 invalid) | 1 |
| Twin | **22 of 34** (65%; 48–79%), all exact | 22–38 of 50 | 0 |
| Twin, no notes | **1 of 37** (3%; 0–14%) | 1–14 of 50 | 21 |

By generation, identified of valid: control G1–G8 all, G9 3 of 5; twin G1 4/4,
G2 3/4, G3 3/5, G4 3/6, G5 2/2, G6 2/4, G7 4/5, G8 1/2, G9 0/2.

- The probe works (control 96%).
- **The twin leaks**: at least 22 of 50 (44%) even if every invalid twin answer
  were a miss — above 10% in every case. G2's identity half fails.
- **The Pokédex notes carry the leak**: 65% with them, 3% without. Whether the
  no-notes condition is at most 5 of 50 — which selects the branch of rule 3 —
  depends on its 13 invalid answers: undetermined until they are re-sent.
- Invalid answers: 28 truncated (the model spent the whole 1,000-token output
  cap on reasoning) and 1 error, all in the two twin conditions. Median
  reasoning tokens of valid answers: control 128, twin 512, twin no-notes 576.
- Measured cost: US$ 0.0905 (estimate: 0.038 central / 0.076 pessimistic).
- Prediction: control about 45 (actual 48); twin 2–3 (actual ≥ 22); notes weigh
  little (they carry almost all of the leak).

### Amendments

- **2026-09-29 — freeze recorded after submission.** The protocol freezes an
  entry before its run; here the freeze is written from the run manifest
  (`runs/e003/manifest.json`), which the preparation step wrote at 16:57:47
  UTC, 11 seconds before the batch was submitted and before any answer existed.
  Every item above is copied from that manifest; nothing in the configuration
  changed after it. Recorded so the order of events is visible.
- **2026-09-29 — output cap and invalid answers (decided after the first
  collection, with its rates seen).** 28 answers were truncated at the
  registered cap of 1,000 output tokens, reasoning included; invalid answers are
  the calls where the model reasoned longest, so excluding them is not neutral.
  Changes:
  1. The two re-sends the entry allows ran with the registered cap (batches
     `batch_6abbf235…` and `batch_6abbf246…`, the same 29 requests). Per request
     the **first valid answer in submission order** is kept; a later one never
     replaces it.
  2. Answers still invalid after those two are re-sent once more with
     `max_completion_tokens` = **4,000** (the rewritten request file is kept).
     Every later run of this probe uses 4,000.
  3. Residual invalid answers are counted both ways: worst case for the twin
     (invalid twin answers identified, invalid control answers missed) and best
     case. A verdict both cases share is taken; otherwise the result is
     "undetermined" and the branch of rule 3 is not taken on it.
  The decision rule and its thresholds are unchanged. Reason: truncation is a
  defect of the instrument (the cap was set without a measurement), not an
  outcome. The raw batch outputs are now kept in `runs/e003/outputs/`.

