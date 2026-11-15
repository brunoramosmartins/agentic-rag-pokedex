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
| [E-002](#e-002--how-much-does-typed-expansion-already-deliver) | 3 | analyzed | descriptive | How much sufficient evidence does the fixed pipeline with typed expansion already deliver, per stratum? | Dev, k = 5: S0 29, S1 23, S2 28, S3 9 of 30; S4 0 by construction. S0/S2 from search, S1 from link level 1, S3 from section completion; B binds in 150 of 150 |
| [E-003](#e-003--identity-probe-can-the-model-name-the-real-species-behind-a-twin-page) | 1 | analyzed | gating (G2) | Can the primary model name the real species behind a twin page, when a masked real page shows the probe works? | Run 1: twin 27 of 50 with notes, 1 of 50 without → notes removed. Run 2 (no notes): control 48, twin 1 of 50 — **G2 identity passes** |
| [E-004](#e-004--pilot-noise-cost-and-reasoning-per-arm) | 3 | analyzed | none (noise) | Tokens and reasoning per arm, A3's steps and firing rate, and a proxy SD of D, for n_max and the preliminary power table | US$ 0.191 for 150 + 30 questions; reasoning medians 0–128; A3 3.6 steps, 28 of 30 search again, S3 always at T_max; proxy SD of D 2.09 (80%: 1.81–2.32) |
| [E-005](#e-005--g2-closed-book-does-memory-stand-in-for-evidence-on-the-twin) | 3 | analyzed | gating (G2) | Does A0, with no evidence, answer twin questions above each template's chance rate? | **G2 passes**: twin 0 of 50 in 15 of 16 templates (2 of 50 in S0-B1); real-name control 4 of 4 |

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
- **2026-09-29 — S1 allocation within eval-L1 (Phase 2 splits, before any
  run).** The Configuration draws "equal numbers per template within each
  stratum". Material S1 pools (S1-A1 70, S1-A2 104, S1-A3 57) cannot give equal
  counts once dev, train, eval-L2 and eval-L3 take theirs: S1-A3 would need 63.
  Change: in S1, the group-A share is split across S1-A1 to S1-A3 in
  proportion to their material pools (eval-L1: 18 / 27 / 15); S1-B1 keeps its
  equal share (20), so the A/B proportion per stratum is unchanged. The gate 8
  extension ("draw more questions up to n\*, balanced by stratum") is bounded
  by material S1 at a pooled S1–S4 n of 548. Also recorded: the separation rule
  is implemented on families (shared (template, anchor entity) pair or
  identical gold chain) and applied between every pair of splits. Decided from
  pool counts; no outcome data exists. Plan impact PI-018.
- **2026-09-29 — the S1 pools shrink (Phase 2 G3 preparation, before any
  run).** S1 lines through an evolution only a non-default form makes
  (Cursola, Sirfetch'd, Mr. Rime, Obstagoon, Overqwil, Basculegion) are
  dropped: their gold answers are wrong for the default form the question
  names. Material pools become 64 / 96 / 53; the eval-L1 allocation is
  unchanged (18 / 27 / 15 / 20); the gate 8 extension is now bounded at a
  pooled S1–S4 n of **448** (was 548). Splits redrawn with dev and train
  refrozen before any use. Plan impact PI-019.
- **2026-09-30 — S3 closure, one-call hubs, S4 families (red-team after the
  examiner build, before any run; Plan impact PI-020).**
  1. S3 gold facts become every row of the (move, version) hub. Seeing every
     member did not prove the list complete, so an agent that stopped early
     and got lucky was labelled sufficient, and one that checked the end was
     coded `over-search`. The S3 truncation mechanism now reads against the
     closure label.
  2. S3 keeps only hubs that one `open_page` call cannot return whole (57 of
     80 eval-L1 S3 hubs could). Pools: S3-A1 1,002, S3-B1 630.
  3. S4 families are keyed by withheld pair across templates: one pair sat in
     eval-L1 and eval-L3.
  Questions, scan, splits, golden trajectories and reachability regenerated;
  dev and train refrozen before any use.
- **2026-09-30 — analysis, oracles, sizing and taxonomy (same red-team,
  approved by the author before any run; Plan impact PI-021).**
  1. **O2, operational.** O2 runs A3's loop with the label as its detector:
     at a sufficient state it answers, whatever A3 proposes; at an
     insufficient state it vetoes "answer" and "abstain" and searches; at
     T_max, or when B binds, without a sufficient state, it abstains.
     O2 − A3 is reported per stratum beside rows 0b, 6 and 7. S4 is never
     sufficient, so O2 abstains on every S4 question and O2 − A3 there is
     mechanically C(A3) − 1: **whether rows 0b, 6 and 7 read S1–S3 instead of
     S1–S4 is decided before the freeze** and recorded here. **O1** runs on
     S0–S3 only (S4 has no gold units to give).
  2. **Clusters.** Before the opening, eval-L1 questions are grouped into
     clusters: withheld pair (S4), move (S3), final form of the line (S1-A1
     to A3), move (S0-A2 to A4), type pair (S0-B1), anchor species otherwise;
     connected components across templates. The cluster file is hashed in the
     freeze manifest; the cluster count is published. Inference becomes a
     **stratified cluster bootstrap** (clusters resampled within stratum; BCa
     acceleration from a cluster jackknife) and **sign-flips of cluster
     sums**; per-stratum readings need ≥ 10 **discordant clusters**; mediation
     and decomposition intervals use the same resampling; detector precision
     and recall intervals are clustered by question.
  3. **Gate 8.** n* is multiplied by a design effect from the drawn eval-L1
     cluster sizes: 1 + (m̄ − 1)ρ per stratum, weighted by stratum size, with
     ρ = 1 in S3 and S4 (conservative) and ρ from the dress rehearsal (upper
     80% limit) elsewhere. **n_max_eff = min(n_max, 448)**: balanced growth
     stops at a pooled S1–S4 n of 448 (material S1, PI-019), and n* above
     n_max_eff is row 0. n_max prices the S0 questions the extension adds;
     the benign slice does not grow.
  4. **Error taxonomy as a decision list**, first match wins, with golden
     tests for the assigner among the instrument prerequisites:
     (1) unparseable output → `format-error`;
     (2) abstained at a sufficient state → `abstained-with-sufficient`;
     (3) abstained otherwise → no error code (`abstained`; correct in S4);
     (4) answered in S4 → `answered-unanswerable`;
     (5) answered correctly at an insufficient state → `correct-at-insufficient`;
     (6) answered wrong with a distractor's value in S2 → `accepted-wrong-version`;
     (7) answered wrong with a strict subset of the gold set in S3 →
     `accepted-truncated-set`;
     (8) answered wrong at an insufficient state in S0 or S1 →
     `stop-missing-hop`;
     (9) answered wrong at a sufficient state → `generation-error`;
     (10) anything else → `wrong-other` (residual, counted and sampled).
     `over-search` and `never-reached` are flags beside the code, not codes.
     S0's insufficient states get their own subtype, `not-found`.
  5. **Detector precision and recall** are read primarily on **trap
     states**: S2 and S4 with a near-certain unit seen and the gold unseen; S1
     with at least one gold fact covered; S3 with at least one hub unit seen.
     All insufficient states are a secondary reading.
  6. **A × B gap**, stratum-standardized: within-stratum (A − B), averaged with
     equal stratum weights, published only in aggregate, with and without S4.
     S4-B1 shares S2-A2's wording by design (S4 reads like S2), so its wording
     is not held out.
  7. **Trajectory-level check** (Phase 3, before dev is first used): under the
     tool contract, the minimum calls and tokens from the question to a
     sufficient state, per eval-L1 question, published N-of-M with one call and
     with more than T_max or B.
  8. **The Configuration reads with its amendments:** equal numbers per
     template are superseded in S1 (PI-018/PI-019); "no question in any stratum
     has a withheld unit in its gold chain" means no question outside S4. The
     population adds **eval-L1-benign** (40 benign S1 questions; arms A3, A4,
     A4p; its own opening count; A4p's dose on it from A4's steps on the same
     slice). The freeze manifest adds the hashes of the question file, the
     registry, the withheld set, the labeler, the code assigner,
     `data/splits/manifest.json` and the cluster file, and per-template counts.
- **2026-09-30 — declared threats (same red-team).** Declared, with the
  measurement where one is cheap:
  1. *Material is defined against the anchor only.* A middle form often shares
     the final form's value, so a stop at hop 2 of 3 can score C = 0. The
     share of strictly material questions (gold differs from every non-final
     node) is published N-of-M; `correct-at-insufficient` is split by the node
     answered from.
  2. *Truncation cues remain.* Hubs split at exactly 20 rows (a full unit hints
     that more follow), units of one list share a header, and the next
     version's header closes a list. Logged per S3 step: whether the last hub
     unit seen was full (ADR-009, Updates).
  3. *S2 is mostly a Scarlet/Violet estimand* (49 of 80 in eval-L1) and
     measures wrong-version where versions disagree; S2 is reported by version
     group; S4's version mix differs from S2's.
  4. *The estimand mixes weights:* S1 group A by material pool, other strata by
     equal template shares. S1-B1 is all of S1's group B: a join, not a chain,
     from 40 sampled moves.
  5. *The benign slice* mostly measures the cost of vetoing lucky stops (the
     anchor-only state is the same for benign and material questions); its
     template mix differs from material S1's, so it is compared within
     template.
  6. *Overlap below the family level:* dev and eval-L1 may share gold facts
     (overlapping chains, one hub's A1 and B1). Prompts carry no world content
     from any split; the N-of-M of eval-L1 questions sharing a gold fact with
     dev or train is published.
  7. *The sizing SD comes from dev* — group A only, where prompts are tuned —
     while eval-L1 is 36% group B.
  8. *Gold errors favour the arm that abstains more* (a wrong gold turns a
     correct answer into λ, an abstention stays at 1); G3 samples about three
     questions per template.
  9. *The shortcut scan cannot flag set answers (S3) or abstentions (S4);* its
     zeros there are trivially true.
  10. *S1-B1 is a join of three facts,* not a chain with a plausible early
      answer; its lucky-stop rate is mostly a ×1 guess.
- **2026-09-30 — the two items left open by the previous amendments (decided
  by the author, before any run).**
  1. Rows 0b, 6 and 7 read **O2 − A3 on S1–S3**. S4 is excluded because O2
     abstains on every S4 question by construction, which would make the room
     look larger and keep futility and row 6 from firing for a reason that
     has nothing to do with stopping. O2 − A3 on S4 is still reported.
  2. The design effect uses **ρ estimated on the dress rehearsal** (upper
     limit of its 80% interval) in every stratum, S3 and S4 included, instead
     of ρ = 1 in S3 and S4.
- **2026-10-07 — A2's page reading (E-002 red-team, before any run).** A2's
  retrieval is `arms/typed_expansion.py` at its frozen hash: search, section
  completion of each hit, then breadth-first typed links with first windows,
  up to B. This page-reading policy is a **fixed design, not swept**, and a
  declared threat: a fixed pipeline that read pages differently could deliver
  more. The grid's BM25/dense weights (0.3 / 0.5 / 0.7) need weighted RRF in
  `world/index.py`, which fuses with equal weights today; Phase 4 implements
  it before the sweep, with the equal-weight point unchanged. Search reads
  queries through the corrected tokenizer (PI-023).
- **2026-11-14 — the verdict in four zones (author's revision, before any run
  of E-001 and before the freeze; PI-025).** The three-valued rule called
  *supported* an interval excluding zero with a point estimate ≥ 0.25: that
  shows the treatment reduces cost, not that the reduction is at least 0.25.
  The same registered interval [L, U] (97.5% BCa, Bonferroni, stratified
  cluster bootstrap) now answers two questions — superiority (L > 0) and
  relevance (L ≥ 0.25 shown, U < 0.25 ruled out) — in four zones that do not
  overlap and cover every interval:
  1. **Supported, relevance shown:** L ≥ 0.25 — "the reduction is at least
     0.25".
  2. **Supported, relevance open:** 0 < L < 0.25 ≤ U — "the treatment
     reduces cost, by at least L; whether the reduction reaches the threshold
     is not known".
  3. **Refuted:** U < 0.25 — "a reduction of 0.25 is ruled out" (unchanged).
  4. **Inconclusive:** L ≤ 0 and U ≥ 0.25 — the interval and the n that would
     decide.

  The point estimate is published but does not decide. "A reduction of at
  least 0.25" is written only in zone 1. "H1 supported" in rows 1–4 means
  zone 1 or 2, with the zone printed beside the row; rows 6–7b read zone 4.
  One case moves: an interval above zero with a point estimate below 0.25 and
  U ≥ 0.25 was inconclusive and is now *supported, relevance open*. **H2's
  sentences:** zone 1 — "A4 reduces expected cost versus the fixed pipeline on
  S1–S4 by at least the action threshold"; zone 2 — "A4 reduces expected cost
  versus the fixed pipeline on S1–S4, by at least L; whether the reduction
  reaches the threshold is not known"; refuted and inconclusive as registered.
  **Sizing:** power targets *supported* = {L > 0 and U ≥ 0.25}; n\* at
  Δ_design = 0.35 is unchanged (78 / 175 / 311 for SD 1.0 / 1.5 / 2.0; the
  plan of 320 holds to SD ≈ 2.03), because at those n the lower limit above
  zero was already the binding condition. Zone 1 has little power at the plan
  (0.33 / 0.15 / 0.09 at a true effect of 0.35) and reaches 0.80 only near
  0.50; declared, not bought with n. H3 (non-inferiority) is unchanged.
  Implemented in `evaluation/outcome_space.py` (`Verdict`, four values) and
  `evaluation/power.py` (`p_supported`, `p_relevance_shown`); decided with no
  outcome data of E-001.

---

## E-002 — How much does typed expansion already deliver?

- **Phase:** 3 (pilot gate), before any agent exists.
- **Status:** analyzed — registered 2026-09-24; made descriptive the same day
  after a red-team review; amended and red-teamed again 2026-10-07; run on dev
  2026-10-07 at commit `29453ac` (clean tree; manifests in
  `runs/e002/log.jsonl`).
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

Run 2026-10-07 on dev (150 questions, group A), commit `29453ac`, no API call
(`dev-k5-20261007T132525+0000.json`, `dev-k3-20261007T132552+0000.json`). k = 5 governs. Sufficient delivered
sets, N-of-M with Wilson 95% (intervals ignore clustering; clusters by
E-001's keys); "by level" is the count after search / level 0 / level 1 / …:

| Stratum | Sufficient (k = 5) | Wilson 95% | Clusters | By level | k = 3 |
|---|---|---|---|---|---|
| S0 | 29 of 30 | 83–99% | 30 | 29, 29, 29 | 29 of 30 |
| S1 | 23 of 30 | 59–88% | 30 | 0, 0, 22, 23 | 25 of 30 |
| S2 | 28 of 30 | 79–98% | 30 | 26, 26, 28 | 28 of 30 |
| S3 | 9 of 30 | 17–48% | 8 | 0, 9, 9 | 8 of 30 |
| S4 | 0 of 30, by construction | — | 14 | — | 0 of 30 |

- **Where sufficiency comes from.** S0 and S2: search alone (29 and 26 of
  30). S1: never search or section completion; the chain completes at link
  level 1 (22) or 2 (1) — S1-A1 7 of 9, S1-A2 9 of 14, S1-A3 7 of 7. S3:
  section completion only (9), when search hit the asked hub; 6 of the 8 S3
  clusters have a sufficient question; members all covered in 9 of 30. The 4
  questions beyond T_max: 0 of 4.
- **Near-certain units.** S2: 7 of 30 delivered sets hold another version's
  answer, all 7 also sufficient (sufficient and conflicting 7, sufficient only
  21, neither 2); first delivered by search in 3, level 0 in 1, level 1 in 3.
  S4: 25 of 30 (search first in 18).
- **B binds in 150 of 150** at k = 5: the expansion always fills the budget
  (median 3,672–3,846 evidence tokens per stratum, 6–26 `open_page` calls);
  link level 2 is reached in 3 S1 and 5 S0 questions only.
- **Rendered cases** (before quoting these numbers): an S1-A1 question becomes
  sufficient at level 1 through the anchor's "Evolves into" link, after
  search and section completion had returned the anchor and two ability
  holders; an S3-A1 question's search returned other moves' hubs in the asked
  version (the version and type terms outweighed the move's name), so section
  completion read the wrong hubs and 0 of 4 members arrived.
- **Against the 2026-09-24 prediction** (which predates the closure label and
  the pipeline, amendment 9): S0 and S2 are above 80%; S1 is not the highest;
  S2 is high on delivered and holds a conflicting version in 7 of 30; S3 is
  low; S4 is 0 by construction.

Not used to select strata, thresholds or n for E-001.

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
- **2026-10-07 — pipeline, link-type order and the S3 measurement (Phase 3,
  before the run; approved by the author).**
  1. **Pipeline.** `search(twin question text, k)` under the tool contract
     (700-token cap, so fewer than k units may come back). Links are expanded
     **breadth-first**: level 1 is the links in the search results, level n+1
     the links in the windows opened at level n. Each expansion is
     `open_page(title)`, the first window of the target page from the top;
     each page is opened at most once. Links whose target is not a page title
     are skipped (no call, no tokens). Expansion stops at the first window
     that would take the delivered evidence past B = 4,000 tokens.
  2. **Link-type order (registered before the run):** `evolves-into`
     (species Profile → species), `ability` (Profile or Form → ability),
     `type` (Profile, Form or Matchups → type), `move` (Learnset → move),
     `learner` (Learned by → species), `holder` (Holders → species). Within a
     type, links follow their order of appearance in the delivered evidence.
     Rationale from the construction only, not from any result: first the
     forward hop of a chain (S1), then an entity's own attributes, then the
     lists that fan out widely (learnsets, hubs, holders). Counted in the twin
     corpus: 486 / 2,943 / 3,597 / 134,701 / 31,568 / 2,292 links; 2,770 links
     name no page (forms) and are skipped.
  3. **Measurement under the closure label (PI-020).** Sufficiency is the
     labeler's label of the delivered set; for S3 that is the whole
     (move, version) hub, so "the delivered fraction of the set" becomes two
     readings: set members covered (members with every fact delivered, of the
     set size) and hub units delivered (of the hub's units). S0 states that
     are not sufficient carry the subtype `not-found`.
  4. **Reporting.** N-of-M per stratum with Wilson 95%; the intervals ignore
     clustering, and the reading is descriptive. Also reported: evidence
     tokens delivered, `open_page` calls made, and the N-of-M where B bound.
     The 4 dev S3 questions beyond T_max are reported separately (journal,
     2026-10-07). k = 3 stays descriptive.
- **2026-10-07, later — red-team before the run (6 blocking, 6 caveats;
  approved by the author, nothing run on dev).** Supersedes items 1 and 4 of
  the amendment above where they differ.
  1. **Level 0, section completion.** After the search and before any link,
     each search hit's section is read from its top in rank order —
     `open_page(title, section=<hit's section line>, offset)`, `offset`
     advanced by the units returned, until a reply holds no unit — and a
     section is read once. Without it, pages of the hits were never read and
     each expansion read a first window only, so under the closure label S3
     was near zero by construction. Level 1 is the links in everything search
     and level 0 delivered. The objective's "generous upper bound" no longer
     holds: E-002 measures **what one registered fixed pipeline delivers**.
  2. **The whole specification** (`arms/typed_expansion.py`, docstring):
     search fuses BM25 and dense by unweighted RRF (k = 60, 50 candidates,
     `BAAI/bge-small-en-v1.5`), the equal-weight point of A2's grid; within a
     link level, links by type rank then order of appearance, a title once
     per level; a page is opened by a link at most once, even when its units
     already came back (not delivered twice, but its tokens count); links
     that no type covers or that name no page are skipped with no call;
     evidence tokens are the sum of every result's tokens, search, separators
     and "No more units." included, as for the agent arms; the pipeline stops
     at the first result that would pass B and skips to nothing smaller.
  3. **Attribution.** The label is recorded after search, after level 0 and
     after each link level, N-of-M per stratum, with the level that first
     delivered a near-certain unit and the deepest level reached: search's
     share is never credited to expansion.
  4. **Freeze and log.** Each run writes a manifest — git commit and dirty
     flag; SHA-256 of `pages/twin.jsonl`, `registry.json`, the question file,
     `trajectories.json` and the split file; k, B, cap, link order, fusion
     parameters; `fastembed`, `tiktoken` and `numpy` versions — into its
     output and into `runs/e002/log.jsonl`. Dev runs whole, once per k
     (`--limit` is refused on dev); smoke runs use train or the fixture world.
  5. **Known answer (gate 7).** A hand-traced expansion on the fixture world
     (13 results: calls, tokens, delivered units, the stop point under a
     tighter B) must pass at 100% before the run
     (`tests/test_typed_expansion.py`).
  6. **Use of the result, widened.** A2's retrieval is this module at its
     frozen hash, and only the registered grid parameters vary. Any other
     change to it after E-002's run counts as an A2 prompt-budget iteration,
     needs a plan-impact line and a new E-002 entry. E-002 changes neither the
     world, the rendering, the tool contract, the templates nor the filters.
  7. **Readings (caveats).** S1 per template; S2 and S4 per version group; for
     S2, sufficient × near-certain delivered (the "sufficient but conflicting"
     cell is what A2 faces); the cluster count (E-001's keys) beside every
     N-of-M, and for S3 the clusters with a sufficient question; S4 as "0 of
     30, by construction", with no interval; the distribution of `open_page`
     calls and of the deepest level; B bound, N-of-M; S3 headline pooled, the
     4 questions beyond T_max beside it (B, not T_max, caps a pipeline).
     "Sufficient" means every gold fact is somewhere in up to 4,000 delivered
     tokens, not that the pipeline could answer.
  8. **Declared.** The link-type order was written knowing the shape of S1's
     chains: a choice from the construction, favouring A2, which is
     conservative for H2. With level-major breadth-first, wide level-1 lists
     can spend B before an S1 chain's second hop. "Its reverse" in A2's grid
     is a weak alternative, so the sweep barely tunes the order.
  9. **The 2026-09-24 prediction predates the closure label and the
     pipeline's mechanics** ("S3 is low" now follows from construction); it is
     kept as written and not counted as confirmed if it holds.

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
- **2026-09-29 — the pages changed after the probe (note; the result
  stands).** World v1 was re-rendered after both runs: species Profiles now
  link forward only ("Evolves into", or "—" for a final form) instead of
  showing the whole evolution line (PI-017). Everything else on the pages is
  unchanged. The new Profiles state a subset of what the probed ones stated —
  one line of the evolution family instead of all of it, plus the fact that a
  final form does not evolve, which the whole line already implied — so the
  identity leak on the current pages can only be lower than what run 2
  measured. No re-run.

---

## E-004 — Pilot: noise, cost and reasoning per arm

- **Phase:** 3 (pilot gate).
- **Status:** analyzed — registered 2026-10-07, before any arm or prompt
  exists; run 2026-10-08; graded reading 2026-11-14, after the grader's audit.
- **Hypothesis:** none. The pilot estimates noise, never effect
  (measurability gate 6).

### Objective

Measure what sizing and budgeting need before any arm is tuned: tokens per
arm, reasoning tokens included (PI-014); steps per question and the implicit
detector's firing rate for A3; and a proxy SD of D for the preliminary power
table (gate 3).

### Configuration

- **Split:** dev, template group A. **A0, A1 and A2 on all 150 questions; A3
  on 30**, drawn with a registered seed from dev S1–S4 (7 or 8 per stratum,
  one per cluster where the stratum allows).
- **Arms, untuned, prompts v0** — written in `prompts/` and hashed before the
  run. Every arm receives the same cost instruction ("a wrong answer costs 4×
  not answering") and returns the structured output `{answer, abstain}`.
  - **A0:** the question alone.
  - **A1:** `search(question, k = 5)`, one result, then the answer prompt.
  - **A2:** E-002's pipeline (`arms/typed_expansion.py` at its frozen hash,
    k = 5), then the answer prompt.
  - **A3:** the common agent loop with `search` and `open_page`, T_max = 6
    steps, B = 4,000 evidence tokens; at T_max, or when B binds, the agent
    answers or abstains. The loop is the one Phase 5 builds on (journal,
    2026-10-06).
- **Model:** gpt-5-mini, Batch API, `reasoning_effort` low,
  `max_completion_tokens` 4,000. A3 submits one batch per step.
- **Cost:** the estimate is printed before the run, and the scripts take
  `--limit N`. Estimate at about 600 output tokens a call (E-003's twin
  median): **US$ 0.50 central, 0.90 pessimistic** (A0 0.09, A1 0.11, A2 0.17,
  A3 0.12). Measured cost is recorded here.
- **Grading:** `evaluation/grader.py` (PI-024), read only after the gate 4
  audit passes.

### Measurement

- Input, output and reasoning tokens per call and per question, per arm:
  median, p90, max; calls that reach the output cap.
- A3: steps per question; the share of questions that search again after the
  first observation (the implicit detector's firing rate); B binding.
- **Proxy SD of D** = C(A1) − C(A3) on the 30 shared questions (λ = 4), with
  an 80% cluster-bootstrap interval (E-001's cluster keys).
- One rendered case per arm (prompt, evidence, completion) before any
  aggregate.

### What it can and cannot conclude

- **Can:** cost per arm, which fixes n_max (gate 8) and the re-estimated
  budget; reasoning headroom; the order of magnitude of the SD of D.
- **Cannot:** any difference between arms. **Mean C per arm is not printed.**
  No per-stratum rate decides anything; no prompt is chosen from these
  outputs, and any change made after them counts as prompt iteration 1
  (journal, 2026-10-06).

### Expected result (author's prediction)

Written 2026-10-08, before the run, as a gut call:

1. Reasoning: about 40 tokens per call.
2. A3 takes 2 steps on average.
3. The proxy SD of D comes out above 1.64, gate 3's working value.

### Actual result

**Run 2026-10-08 on dev** (`runs/e004`, prepared at commit `cbc317c`, after
the author's prediction): 7 Batch rounds, 589 calls, no API failure, no
output at the 4,000-token cap. **Measured cost US$ 0.191** (estimate 0.49
central / 0.85 pessimistic). Ungraded readings only; the graded ones (the
proxy SD of D) wait for the grader's audit (PI-024).

| Arm | Calls | Input tokens (median / max) | Output (median / p90) | Reasoning (median / p90 / max) | US$ | US$ per question |
|---|---|---|---|---|---|---|
| A0 | 150 | 163 / 169 | 85 / 149 | 64 / 128 / 320 | 0.019 | 0.00013 |
| A1 | 150 | 603 / 872 | 151 / 345 | 128 / 320 / 640 | 0.039 | 0.00026 |
| A2 | 150 | 3,421 / 3,951 | 92 / 492 | 64 / 448 / 896 | 0.097 | 0.00065 |
| A3 | 139 (30 questions) | 1,327 / 3,594 | 54 / 277 | 0 / 256 / 384 | 0.036 | 0.00118 |

- **A3, 30 of 30 ended:** steps 1 (2), 2 (10), 3 (6), 5 (3), 6 (9); mean
  3.6, median 3. **28 of 30 searched again after the first observation**
  (the implicit detector's firing rate, descriptive). T_max reached in 9 of
  30 — all 8 S3 questions and 1 S4; B never spent (evidence 448–3,049 tokens).
  By stratum: S1 2–5 steps, S2 1–3, S3 6 every time, S4 2–6. Calls: 80
  `search`, 29 `open_page`; no invalid call; every final output ends in a
  JSON object.
- **Abstentions (ungraded):** A0 150 of 150 on the twin; A1 47 of 150; A2 36
  of 150.
- **Rendered cases:** an S0-A1 question in the form "Name the hidden ability
  of {X}" — A1's search returned other abilities' Holders units, A1 abstained,
  A2 answered from 3,438 tokens of expanded evidence (its grade waits for the
  audit); an S1-A2 question where A3 searched, opened the anchor's page, then
  the final form's page, and answered the type pair in 3 calls.
- **Against the prediction:** reasoning was 0–128 tokens a call at the median
  (predicted about 40); A3 took 3.6 steps on average (predicted 2), pushed up
  by S3, which always ran to T_max.

**Graded reading, 2026-11-14** (after the grader's audit passed in round 2,
100 of 100): **proxy SD of D = C(A1) − C(A3) = 2.09, 80% stratified cluster
bootstrap 1.81–2.32**, on the 30 shared questions (30 clusters; 20 of 30 pairs
discordant). Above gate 3's working value of 1.64, as predicted. It is a
proxy: A1 against A3, not A3 against A4, which share their search and should
be more concordant; gate 8 is decided on the dress rehearsal. At SD 2.09,
n\* = 339; at the upper limit 2.32, n\* = 418 — above the plan of 320, below
n_max_eff = 448 before any design effect. Rendered case (an S2 question, "Name
the move Skamsei learns at level 55 in Karek/Zistamdu"): A1's single search
missed the learnset and A1 abstained (C = 1); A3 searched, opened the species'
Learnset section and answered the gold (C = 0). No mean of C and no mean of D
is printed.

**Use, 2026-11-14 (gate 8):** with these costs the v1.0 budget commits US$
11.69 of 20 (`evaluation/budget.py`), and **n_max = 884, n_max_eff = 448**,
logged in the journal before any rehearsal.

### Amendments

- **2026-10-07 — implementation details, before any run (approved by the
  author).**
  1. **Seed:** the 30 A3 questions are drawn with seed `20261007`
     (`evaluation/pilot.py`, `PILOT_SEED`): dev S1–S4, 8 / 7 / 8 / 7 or as the
     seed assigns the two extra, round-robin over clusters.
  2. **Last turn:** after T_max calls, or once B is spent, the agent gets
     `prompts/agent_final_v0.md` ("You have no tool calls left. Reply now
     with your answer, as JSON only.") and no tool.
  3. **Tool replies in the loop:** a result that would pass B is not shown —
     the call returns "Evidence budget reached." and the tools end; a call the
     tools cannot run returns "Invalid call." and counts as a step. A budget
     signal, not a sufficiency cue, identical for every agent arm.
  4. **No API JSON mode:** the `{answer, abstain}` format comes from the
     prompts only, in every arm (JSON mode can conflict with tool calls, and
     using it in some arms only would break parity).
  5. **Smoke runs** use train (`--split train`, `runs/e004-smoke`), never dev.

---

## E-005 — G2 closed-book: does memory stand in for evidence on the twin?

- **Phase:** 3 (pilot gate).
- **Status:** analyzed — registered 2026-10-07, before any run; run
  2026-10-08; verdict 2026-11-14 (G2 passes), after the grader's audit.
- **Hypothesis:** gating — G2's closed-book half (`docs/contingency.md`;
  PI-022). G2's identity half passed in E-003.

### Objective

Whether A0, with no evidence, answers twin questions above each template's
chance rate: memory standing in for evidence, per template.

### Configuration

- **Sample:** 50 questions per template, all 16 templates (800), drawn with a
  registered seed from dev, train and the unassigned pool — never from an
  evaluation split — one per cluster where the pool allows (E-001's cluster
  keys).
- **A0** with E-004's prompt v0, on each question's **twin** text and on its
  **real-name** text (rendered by the generator with real names): 1,600
  calls. gpt-5-mini, Batch API, `reasoning_effort` low,
  `max_completion_tokens` 4,000. **Cost estimate: US$ 1.0 central, 1.8
  pessimistic**; printed before the run, with `--limit N`.
- **Correct:** exact match with aliases (`evaluation/grader.py`, read after
  the gate 4 audit; PI-024). In S4, "correct" means stating the withheld
  value. An abstention is never correct.

### Decision rule (fixed before the run)

- **Chance** per template: its majority-answer rate after the concentration
  cap (`docs/examiner.md`, Counts), never below uniform; for S4, the majority
  rate of the withheld values among the sampled questions.
- **A template fails G2** when the **Wilson 95% lower limit** of A0's correct
  rate on the twin is above chance + 5 points.
- **Positive control:** on real names, the Wilson 95% lower limit exceeds
  chance + 5 points in at least **3 of the 4** templates S0-A1 to S0-A4
  (well-known facts). If not, the probe, the prompt or the grader is broken,
  and G2 is not evaluated until it is fixed.
- **Exit when a template fails:** G2's written exit — the leaking templates
  leave the primary population, decided on dev and recorded.

### What it can and cannot conclude

- **Can:** catch large leaks per template. With n = 50 and a 10% chance rate,
  the rule fails a template only above about 25% correct.
- **Cannot:** show that small leaks are absent.

### Expected result (author's prediction)

Written 2026-10-08, before the run, as a gut call:

1. Whether a template leaks is very hard to call; if one does, perhaps through
   the most famous species (a Pikachu).
2. The positive control may fail: the model can get real-name facts wrong,
   because sources vary on them. To be seen.

### Actual result

**Run 2026-10-08** (`runs/e005`, after the author's prediction, `cbc317c`):
1,600 calls in one Batch round, no API failure, no output at the cap, no
unparseable output. **Measured cost US$ 0.280** (estimate 1.06 central).
Reasoning per call: median 128, p90 256, max 768. Ungraded: on the twin, A0
answered 4 of 800 questions and abstained on 796; on real names it answered
405 of 800. The verdict waits for the grader's audit (PI-024).

**Verdict, 2026-11-14** (after the grader's audit passed in round 2, 100 of
100), by the registered rule: **G2 closed-book half passes.** On the twin, no
template's Wilson 95% lower limit is above its chance rate + 5 points: 0 of 50
correct in 15 of 16 templates, 2 of 50 in S0-B1 (chance 38%). **Positive
control 4 of 4:** on real names, S0-A1 34, S0-A2 35, S0-A3 43, S0-A4 44 of 50
(lower limits 54–76%, chance 3–40%). Real names also above chance in S0-B1
(47), S1-A1 (28), S1-A2 (49), S1-A3 (28), S1-B1 (35); 0 of 50 in S2 and S3;
S4, stating the withheld value: real 7 of 50 (S4-A1, chance 32%) and 2 of 50
(S4-B1), twin 0 of 50.

### Amendments

- **2026-10-07 — implementation details, before any run (approved by the
  author).** The 800 questions are drawn with seed `20261008`
  (`evaluation/closed_book.py`, `CLOSED_BOOK_SEED`), round-robin over
  clusters within each template. The real-name text is rendered by the
  generator with the question's own surface form. No API JSON mode (as
  E-004). `decide` refuses to run until the grader's audit has passed.
