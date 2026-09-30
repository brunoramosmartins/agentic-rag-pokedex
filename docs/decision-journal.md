# Decision Journal

Every non-trivial decision logged the day it is made. Never reconstructed later;
backfilled entries are marked retrospective.

---

## 2026-09-24 — Phase 0 opened

**Scope.** Phase 0 — Foundation, Licensing & Measurability Gate. Timebox: 5
partial working days. Ends with tag `v0.1-foundation` (no release).

**Gate check.** Phase 0 has no predecessor phase inside this repo. Several
Phase 0 deliverables reuse the previous project, P2 (`graphrag-mtg-rules`):
`power.py` must reproduce P2's E-026 detectability table (measurability gate
7), and the Neo4j loader and `bm25.py` are adapted from it. The P2 repo is not
present on this machine as of today; its location is an open item for this
phase.

**Carry-overs.** None.

**Scope decisions.** None taken at kickoff.

**Housekeeping.** A WSL download artifact (`*:Zone.Identifier`) and `.venv/`
are untracked; both go to `.gitignore` as part of the scaffold task.

## 2026-09-24 — All repo artifacts in English, including `notes/`

Every file in the repo is written in English, notes included, to follow common
development and documentation practice. `notes/phase0-foundation.md` was
rewritten in English the same day.

## 2026-09-24 — Reading companions for the full reading plan; AURC source corrected

Reading companions were written up front for all 15 sources of the reading
plan, plus one synthesis file per phase with more than one source
(`notes/phase{0,2,5,8}-synthesis.md`). Skim-mode sources get short notes that
cover only the sections serving a decision.

Two corrections found while checking the sources:
- **AURC is not in Geifman & El-Yaniv 2017.** Its primary source is Geifman,
  Uziel & El-Yaniv, *Bias-Reduced Uncertainty Estimation for Deep Neural
  Classifiers* (ICLR 2019, arXiv:1805.08206), added as a skim companion inside
  `notes/geifman-2017-selective-classification.md`.
- **Longpre et al. 2021 also serves Phase 1** (the twin's renaming scheme,
  ADR-003), not only Phase 10. Its §2 is flagged for reading before Phase 1.

## 2026-09-24 — Scaffold choices

Built from scratch rather than copied from P2: the P2 repo is not available
locally (open item above).

- **src layout, package `agentic_pokedex`**, only the package root for now.
  Subpackages (`world/`, `examiner/`, `arms/`, …) are created by the phase that
  first needs them, so the tree never shows modules that do not exist yet.
- **Optional extras per concern** (`graph`, `retrieval`, `llm`,
  `observability`, `classifier`, `demo`, `dev`) instead of one flat dependency
  list: torch/sentence-transformers are not installed until Phase 1 needs the
  dense index. Core stays numpy/scipy/pandas.
- **CI integration job tolerates "no tests collected"** (pytest exit code 5)
  until Phase 1 adds the first `@pytest.mark.integration` test. Remove the
  tolerance then.
- **Milestone due dates are soft targets** from the effort estimate (week 1
  starts 2026-09-24); the project has no hard deadline.
- **Phoenix image is `latest`, Neo4j is `5-community`.** Pin exact versions
  before the first registered run (Phase 3), and record them in E-001.

## 2026-09-24 — ADRs 001–010 drafted as Proposed

The ten ADRs record decisions already taken during planning, with links to the
reading companions that motivate them. Status is **Proposed**, not Accepted:
each one is reviewed and flipped by hand, which is the Phase 0 DoD. ADR-001
carries one open item — the exact definition of the sufficiency label —
resolved after `notes/phase0-synthesis.md` S.3.

`papers/` added to `.gitignore` for local PDF copies of the reading plan.

## 2026-09-24 — The repo is self-contained; planning files stay local

The planning document used to steer the project is personal and is not
versioned; neither is local tool configuration. Both are gitignored. Every
repo file must stand on its own: the hypothesis, the measurability gate, the
contingency gates and the ADRs restate their content instead of pointing to an
external plan. `docs/hypothesis.md`, `docs/measurability-gate.md` and
`docs/contingency.md` were written the same day under this rule, and earlier
files were edited to remove references to the planning document.

The power table in `docs/measurability-gate.md` was recomputed before
publishing (MDE = 3.08 · SD / √n; n for 0.25 = 152 / 342 / 608; H3 n = 99 / 223 /
396; per-stratum MDE at n = 80 = 0.31 / 0.47 / 0.63): all values match.

## 2026-09-24 — G1 passed; E-001 and E-002 registered as drafts

**G1 — pass** (`docs/data-sources.md`). PokéAPI BSD-3-Clause and MuSiQue
CC BY 4.0 confirmed from the license files; PokéAPI pinned to commit
`6bbd96bb`; SHA-256 recorded for 14 CSVs and the MuSiQue archive; learnsets
complete for the candidate base version groups. Three findings change later
phases:

- **S2 needs cross-generation versions.** Levels differ in only 3% of shared
  level-up pairs between scarlet-violet and sword-shield (59% vs
  ultra-sun-ultra-moon). The Phase 1 version scope must span generations, and
  the S2 generator keeps only pairs whose level differs.
- **DLC version groups are empty** (moves folded into the base group).
- **MuSiQue-Full test has no labels**: the v1.2 sample comes from dev.

**Published benchmark:** twin-side, fact-level material only (ids, twin
question text, answers, unit ids, seeds, pinned commit). No real names, no
twin map, no unit text, no Pokédex text in any form; the corpus is rebuilt
locally.

**Registry.** E-001 (Layer 1) and E-002 (typed expansion) registered as
`draft`. Analysis choices made explicit while drafting, beyond the
measurability gate: paired bootstrap with 10,000 resamples for D and λ\*; Holm
over the two bootstrap p-values; E-002 uses a deliberately generous A2 (k = 5,
every link type) so its rule errs toward shrinking H2; dev split assumed
balanced at 30 questions per stratum. Noted while drafting: E-002's "≥ 3 of 4
strata" rule can only trigger through S1–S3, since S4 has no sufficient set by
construction.

## 2026-09-24 — Red-team of E-001 / E-002 applied in full

An adversarial review of both drafts found 5 blockers, 4 major and 3 minor
issues. All were adopted; details are in the Amendments of each registry
entry. The decisions that change the design:

- **Power targets the verdict actually published.** "Supported" needs the
  point estimate ≥ 0.25, so sizing for "interval excludes zero" gave only ~50%
  chance of *supported* at a true effect of 0.25. Power is now computed for the
  *supported* event at **Δ_design = 0.35** (n\* = 78 / 175 / 311 for SD 1.0 /
  1.5 / 2.0; the 320 plan holds up to SD ≈ 2.03), separately for H1 and H2.
- **E-002 is descriptive; H2 is always estimated on S1–S4.** Correction to the
  entry "G1 passed; E-001 and E-002 registered as drafts" above: that entry
  said the generous A2 configuration made E-002's rule "err toward shrinking
  H2". It did shrink the pool, but in doing so it **inflated** the H2 effect,
  because the strata removed were exactly those where the pipeline is strong.
  The reasoning was wrong; the gating rule is gone.
- **An A3′ rerun is added** (S1–S4, ~US$ 1.1 central / 1.45 pessimistic) as the
  noise null for the gain decomposition. v1.0 becomes US$ 11.3 / 14.7 against
  the 13.5 cap; the new cut order (A6, cue ablation, then A3′) brings the
  pessimistic case back to ~12.9. O2 moved to the never-cut set, since rows 6–7
  of the outcome space depend on it.
- **Mediation** is measured on the logged judge override, net of the placebo;
  **inference** uses sign-flip p-values and BCa intervals, with a ≥ 10
  discordant-pairs rule per stratum; **λ\*** is published only when the error
  difference is resolved; **prompt-tuning parity** across the agent, pipeline
  and judge prompts.

Documents updated the same day: `experiments/registry.md`,
`docs/measurability-gate.md` (gates 1, 3, 7, 8), `docs/contingency.md`,
`docs/hypothesis.md`, `docs/data-sources.md`, ADR-005, ADR-006, ADR-008,
ADR-010.

## 2026-09-24 — Second red-team pass applied; n_max replaces any cap increase

A second adversarial pass verified the first revision (8 of 12 findings fully
resolved, 4 partially) and found 3 blockers, 5 major and 6 minor issues. All
were adopted; the E-001 Amendments list them. The decisions that change the
design:

- **n_max instead of a larger budget.** The gate 8 "draw more questions"
  branch could not be paid for in the pessimistic scenario (~120 extra
  questions after all cuts, not 320). n_max — the largest pooled n the US$ 13.5
  cap pays for after the cut order — is computed from the Phase 3 measured
  costs and logged **before the dress rehearsal**. If the dress rehearsal asks
  for more, the verdict becomes descriptive (row 0). The cap is not raised.
  Chosen over a contingency cap of ~US$ 16: a noisy D ends in an honest
  descriptive result rather than in a budget negotiated after seeing dev noise.
- **Futility has its own row (0b)**, so an H1 declared without room before the
  opening can never be published as "thesis supported".
- **The agent decision table is registered** (proposal × detector → action).
  A3, A4 and A4p share one loop and one prompt; the detector can only veto;
  the A4p agent is never told about k. Mediation is now
  (m_A4 − m_A4p) / g_A4 over vetoes, and the placebo dose is a permutation of
  A4's realized steps.
- **The verdict is decided by the 97.5% BCa intervals alone**; p-values are
  descriptive.

The reviewer's refutation-power figure for SD = 1.0 (0.93) was recomputed
before publishing and corrected to 0.99; the values for SD 1.5 and 2.0 (0.77,
0.50) were confirmed.

## 2026-09-24 — Token meter design

`observability/tokens.py` and `observability/pricing.py` keep two numbers
apart: the **pre-flight estimate** (local tokenizer count + assumed output and
reasoning per call, printed before any LLM loop, which then waits for
confirmation or `--yes`) and the **measured usage** (what the API reports per
call — the only source for registered costs). Reasoning tokens are counted
inside output tokens and never billed twice; a tier with no cached-input price
bills cached tokens as uncached input.

Gate 7 tolerance, fixed before the first call: the meter's totals must equal the
raw API usage summed independently, and every local input count must be within
5% or 10 tokens (whichever is larger) of the API's. The check makes 10 small
Standard-tier calls (`scripts/check_token_meter.py`, well under US$ 0.01) and
its result is logged here when it runs.

## 2026-09-24 — power.py passes gate 7; P2 located; one rounding error corrected

**Open item closed.** The P2 repository (`graphrag-mtg-rules`) is public on
GitHub; E-026 and its instrument (`scripts/detectability.py`) were read at
commit `b3f293e`. `evaluation/power.py` generalizes that method from a binary
paired difference (SD² = discordance) to the expected-cost outcome of this
project (any SD of D), and adds the verdict-specific functions (P(supported),
P(refuted), n\*, n_max, the gate 8 decision).

**Gate 7 — power script: PASS.** At P2's pooled discordance (17/57) it
reproduces every published E-026 number: the six simple floors, the six
interaction floors and all eight "n needed" values, the latter exactly. The
check is `python -m agentic_pokedex.evaluation.power --reproduce-e026` and a
test.

**Correction.** The entry "The repo is self-contained; planning files stay
local" above said the gate 3 figures were recomputed and "all values match",
quoting n = 152 / 342 / 608 to detect 0.25. Those were rounded, not ceilinged:
the smallest n reaching 80% power is **153 / 343 / 609**. Fixed in
`docs/measurability-gate.md`; every other figure in gates 3 and 8 (MDE table,
per-stratum MDE, H3 n, P(supported), n\*, P(refuted), the SD thresholds 2.03
and 2.87) now comes from `power.py` and is pinned by tests that also parse the
document.

## 2026-09-24 — Two test assertions corrected; services restart on their own

The first test run (105 passed, 2 failed) exposed two claims of mine that were
too strong, not bugs in `power.py`:

- "*Supported* at a true effect of 0.25 is a coin flip whatever n is" is only
  true once z·SE ≤ 0.25. Below that n the binding condition is "lower limit >
  0" and the probability is slightly under one half (0.498 at n = 320,
  SD = 2.0). Gate 3 now says "at most half"; the test checks both regimes.
- "An interaction needs exactly 114 per group to match the simple floor at
  n = 57" sits on a floating-point boundary (114 or 115). The test now checks
  the SE identity and the 4× ratio, which are the actual claims.

`docker-compose.yml`: both services get `restart: unless-stopped`. Phoenix had
received a stop signal and exited cleanly while Neo4j kept running.

## 2026-09-24 — Secrets come from the environment, with `.env` as fallback

`agentic_pokedex.config.load_env()` reads the gitignored `.env` at the repo
root without overriding variables already set. `docker compose` reads the same
file, so the Neo4j password and the API key live in one place. A project-only
API key with a provider-side spending limit is recommended, as a second guard
on the v1.0 cap. Dependency added: `python-dotenv` (core).

## 2026-09-24 — Gate 7, token meter: PASS

`scripts/check_token_meter.py`, 10 Standard-tier calls to gpt-5-mini
(`reasoning_effort` low). Snapshot returned by the API:
**`gpt-5-mini-2025-08-07`** — the candidate for the E-001 freeze manifest.

- Meter totals equal the raw API usage summed independently: **yes**.
- Local input counts within tolerance (5% or 10 tokens): **10 of 10**.
- Measured cost: **US$ 0.001399** (prices as of 2026-09-24); the pre-flight
  estimate was 0.0038 central / 0.0088 pessimistic, so it erred high, as it
  should.

Observations, recorded without changing the registered tolerance or the
overhead constants:

- The local count is **1 token low** on every call with a system message and
  exact on the single user-message call. The largest gap was **5 tokens (11%)**
  on the 4-message conversation — inside the 10-token absolute allowance, but
  outside 5% relative. Agent prompts in this project are hundreds to thousands
  of tokens, where a per-message offset of this size is well under 1%; the
  multi-turn agent loop is the case to watch when Phase 5 builds it.
- Reasoning tokens on these trivial prompts: 0 on 6 calls, 64–192 on 4 (mean
  ~45). Not representative of agent steps; the central / pessimistic scenarios
  (150 / 400) stay until Phase 3 measures them on real prompts.

## 2026-09-25 — ADR review before acceptance

The author reviewed ADRs 001–010: all ten decisions stand. Five carried a
caveat; each was checked against the current text of the ADRs and E-001.

- **Already covered, no change:** ADR-005 already calls λ = 4 the scenario of
  the registered test, not a measured quantity. ADR-006's judge diagnostic
  against the exact label is already an E-001 mechanism quantity (detector
  precision / recall per step, by subtype).
- **ADR-001:** the open item (definition of the sufficiency label) is now
  marked as blocking for the E-001 freeze, since the labeler's golden
  trajectories need it.
- **ADR-002 and ADR-007:** a real gap. Pokédex flavor text is prose outside the
  fact → units registry, so a flavor unit that states a gold fact would make
  the label say `insufficient` while the agent holds the evidence — a labeler
  error that reads as a detector error. The golden trajectories cannot catch
  it, because they take the registry as given. Added: a **shortcut scan**
  (a unit mentioning the question's anchor together with the answer, outside
  the registered gold units, flags the question), validated on planted leaks,
  and a read of the flavor text of every chain in the G3 audit. First drafted
  as "the answer appears only in gold units"; rejected before writing,
  because a species name appears in type lists and on every move page it
  learns, so the rule would flag almost every question.
- **ADR-008:** scope stated. v1.0 measures one model configuration (GPT-5 mini
  at `reasoning_effort` low); the GPT-4o-mini extension runs A1, A3 and A4
  only, so it replicates the direction of H1, not the mechanism. Mirrored in
  `docs/hypothesis.md` → Scope.
- **ADR-010:** the 50% cut of rows 2–4 is stated as a registered reading
  convention (a majority rule), not a statistical threshold. The author's
  other caveat — A4p's k comes from A4's behaviour, matched by distribution —
  is the design, not a weakness: matching k per question would hand the
  placebo the judge's per-question stopping information, so the placebo would
  contain the treatment.
- E-001 amended (draft; dated entry under Amendments): the shortcut scan joins
  the instrument prerequisites, and the 50% note is added. No row definition
  changed.

**Plan impact PI-001:** Phase 1 — World and Phase 2 — Examiner — the fact →
units registry was assumed complete by construction, but free-text units
(Pokédex flavor text) can state gold facts it does not know about → Phase 2
gains a shortcut scan checked on planted leaks (including one in flavor text),
with its flags resolved and published N-of-M, and the G3 audit reads the
flavor text of each audited chain; Phase 1's renderer must mark flavor units
so the scan can find them. Open.

## 2026-09-26 — Phase 0 close sweep: plan impacts; Joren et al. read

**Reading.** Joren et al. 2025 read and its lit-note refined. Ferrazzi et al.
2026 and Singh et al. 2025 are still to read; the synthesis note waits for
them. The author wrote the phase note's Lessons Learned and Failed Attempts.

**Sufficiency label fixed** (closes ADR-001's open item; recorded as an
ADR-001 update). The label is coverage of a gold minimal sufficient set. Joren's
"a plausible answer exists given C" is strictly weaker; the clean
disagreement is S3 without truncation cues. Reason: the label must be exact and
tied to the gold answer, because it scores stops; Joren's predicate is built for
inference time, without the gold.

**Positioning.** Later work controls multi-round retrieval with a sufficiency
signal: SIM-RAG (SIGIR 2025; outcome-derived labels), S2G-RAG (2026; gap items
feed the next query), Luo (2026; Search-R1 stopping judge, no abstention).
None measures stopping against an exact per-step label. ADR-001 updated; the
contribution is stated as measurement, not method. The author's earlier framing
("the first iterative sufficiency system") is recorded as a failed attempt in
the phase note.

**E-001 amended** (draft; see Amendments): `correct-at-insufficient` code added
(a lucky stop scores C = 0 and was invisible); prompt parity widened to every
sufficiency-checking instruction (also noted in ADR-006).

**G2 amended** (`docs/contingency.md`, noted in ADR-003): the closed-book check
is chance-adjusted on templates with ≤ 20 admissible answers. Guessing a type
(1 in 18 ≈ 5.6%) would otherwise fail the 5% threshold with no leak at all.

**Plan impacts.** The close sweep found six findings from 2026-09-24/25 that
change later phases and had no line. They are logged here, marked
retrospective, with the author's agreement. PI-008 and PI-009 come from today's
reading.

**Plan impact PI-002** *(retrospective; finding of 2026-09-24, G1)*: Phase 1 —
World and Phase 2 — Examiner — the version scope assumed 3–4 version groups
chosen by coverage; the level differs in only 3% of (species, move) pairs
between adjacent generations, and DLC groups are empty → Phase 1 picks base
groups spanning generations, not adjacent ones; Phase 2's S2 filter keeps only
pairs whose level differs from every other version group in the corpus
(N-of-M published). Open.

**Plan impact PI-003** *(retrospective; red-team of 2026-09-24)*: Phase 3 —
Pilot gate — E-002 was planned with a decision rule removing strata where the
fixed pipeline already delivers sufficient evidence (and, at 3 of 4 strata,
removing H2 from the primary family) → that rule is gone: removing strata where
A2 is strong would inflate H2. E-002 is descriptive and the H2 population is
fixed at S1–S4. Phase 3's definition of done loses the E-002 rule. Open.

**Plan impact PI-004** *(retrospective; red-team of 2026-09-24)*: Phases 3, 5,
6 and the v1.0 budget — the A3′ noise-null rerun was added → the v1.0 estimate
goes from US$ 10.2 / 13.2 to **11.3 / 14.7** (central / pessimistic), so the
pessimistic scenario exceeds the US$ 13.5 cap. The cut order becomes A6 → cue
ablation → A3′, and O2 is never cut (previously cut third, on S3/S4). Open.

**Plan impact PI-005** *(retrospective; second red-team of 2026-09-24)*: Phase
3 — Pilot gate and Phase 6 — Layer 1 verdict — sizing assumed a 320 / 640
question ladder powered for "interval excludes zero" → power now targets
*supported* at Δ_design = 0.35; extra questions are capped by n_max, computed
from Phase 3 measured costs before the dress rehearsal, with no cap increase;
n* > n_max → descriptive row 0; futility row 0b. Phase 3 gains the n_max
computation. Open.

**Plan impact PI-006** *(retrospective; red-team passes of 2026-09-24)*: Phases
4–6 — design details registered in E-001 after planning → Phase 4: the A2 sweep
grid (k × hybrid weight × depth × link order) and prompt-tuning parity (3
recorded iterations per prompt); Phase 5: the agent decision table with veto,
and A4p told nothing about k; Phase 6: A4p runs after A4 in the same opening,
with a dose permuted from A4's realized steps and adherence checked before any
result is read. Open.

**Plan impact PI-007** *(found in today's sweep)*: Phases 4–5 and the v1.0
budget — development tuning has no budget line. At central per-question costs
(Batch) on the 120 dev questions in S1–S4:
- A2 sweep: 36 × 120 × 0.0010 = 4.32;
- agent prompt: 3 × 120 × 0.0035 = 1.26;
- judge prompt: 3 × 120 × 0.0056 = 2.02;
- A2 prompt: 3 × 120 × 0.0010 = 0.36;
- total ≈ **US$ 8.0**, on top of the 11.3 central estimate.

→ A plan revision must place it under the cap. Candidate: a two-stage A2 sweep —
all 36 configurations screened by the labeler at zero API cost, then the top 3
with the LLM (≈ 0.36) — bringing tuning to ≈ 4. Escalated: revise before the
Phase 0 tag. Open.

**Plan impact PI-008**: Phase 5 — Agent (readings) and Phase 7 — Release
(README) — the positioning assumed that no work controls iterative retrieval
with sufficiency → SIM-RAG and S2G-RAG join the Phase 5 readings next to CRAG;
the README and write-up state the contribution as measurement, citing all three.
ADR-001 already updated. Open.

**Plan impact PI-009**: Phase 1 — World and Phase 3 — Pilot gate — the G2
closed-book check assumed that any correct answer on the twin means leakage →
Phases 1 and 3 compute the admissible-answer count per template and apply the
chance-adjusted check; per-template rates are published. Rule already amended
in `docs/contingency.md`. Open.

## 2026-09-28 — Plan revised at the Phase 0 close

The phase plan was revised to absorb every open plan impact before the Phase 0
tag, so that later phases start from current evidence. The author made three
decisions.

- **Budget (PI-007).** The v1.0 cap goes from US$ 13.5 to **US$ 20**, decided
  before any data. Dev tuning had no budget line. With a two-stage A2 sweep
  (labeler screen of 36 configurations, then the top 3 with the model), tuning
  is ≈ US$ 4.0 central / 5.2 pessimistic, so v1.0 becomes 15.3 / 19.9. The rule
  against raising the cap after the dress rehearsal stands. Rejected: keeping
  13.5 with tuning on 60 questions (the pessimistic case would trigger the cut
  order almost surely), and dropping A6 now.
- **Readings (PI-008).** SIM-RAG (read) and S2G-RAG (skim) join the Phase 5
  readings. Compensating cut: FLARE becomes optional, since Self-RAG and CRAG
  cover low-confidence-triggered retrieval.
- **Hours.** The new tasks in Phases 1–3 (shortcut scan, flavor-unit marking,
  answer-space counts, n_max) add ~1.5 partial days. Compensating cut: the
  Phase 7 demo timebox drops from 6 to 5 partial days, without the interactive
  cost counter; cost per arm stays in the README table.

Repo documents synced: ADR-008 (cap, budget, Updates section),
`docs/contingency.md` (G5), E-001 (two-stage sweep, amendment of 2026-09-28).
Dates are unchanged: Phase 0 closes inside its week-1 timebox.

**Plan impact PI-001 resolved:** plan revised on 2026-09-28 — Phase 1 marks
free-text units in the registry; Phase 2 gains the shortcut scan with planted
leaks and the flavor-text read in the G3 audit.

**Plan impact PI-002 resolved:** plan revised on 2026-09-28 — Phase 1 chooses
base version groups spanning generations and reports the level-difference rate;
Phase 2's S2 filter checks every other version group.

**Plan impact PI-003 resolved:** plan revised on 2026-09-28 — Phase 3 runs
E-002 as descriptive; its stratum-removal rule is gone and H2 stays on S1–S4.

**Plan impact PI-004 resolved:** plan revised on 2026-09-28 — A3′ is part of
v1.0 and of the Phase 6 run order; the cut order is A6 → cue ablation → A3′, and
O2 is never cut.

**Plan impact PI-005 resolved:** plan revised on 2026-09-28 — Phase 3 computes
and logs n_max against the US$ 20 cap before any rehearsal; Phase 6 sizes H1 and
H2 separately for the *supported* verdict at Δ_design = 0.35.

**Plan impact PI-006 resolved:** plan revised on 2026-09-28 — Phases 4–6 carry
the registered sweep grid, prompt parity, the veto decision table and the
permuted A4p dose with its adherence check.

**Plan impact PI-007 resolved:** plan revised on 2026-09-28 — two-stage A2
sweep and a US$ 20 cap, as above.

**Plan impact PI-008 resolved:** plan revised on 2026-09-28 — Phase 5 readings
gain SIM-RAG and S2G-RAG (FLARE optional); the Phase 7 README states the
contribution as measurement and cites the three later works.

**Plan impact PI-009 resolved:** plan revised on 2026-09-28 — Phase 1 counts
admissible answers per template; Phases 1 and 3 apply the chance-adjusted
closed-book check.

## 2026-09-29 — Phase 1 opened

**Scope.** Phase 1 — The World: PokéAPI → graph → twin → pages. 8–11 partial
working days (weeks 2–3). Ends with tag `v0.2-world` (no release).

**Gate check.** Every Phase 0 deliverable is present; PR #9 merged with CI
green and `v0.1-foundation` pushed. The eight Phase 0 issues were still open
(one of them, "ADRs 001–010", duplicated) and are closed as part of the
opening.

**Open plan impacts.** None: PI-001 to PI-009 were resolved on 2026-09-28. The
ones that shape this phase are already in its tasks: free-text units marked in
the registry (PI-001), base version groups spanning generations with the
level-difference rate reported (PI-002), and admissible answers counted per
answer slot for the chance-adjusted closed-book check (PI-009).

**Carry-overs.** None.

**Scope decisions.** None taken at kickoff.

## 2026-09-29 — Rendered examples in docs; the identity probe takes E-003

Two conflicts found while opening Phase 1, both absorbed the same day.

- **Rendered pages in docs.** `docs/data-sources.md` listed "rendered pages or
  any unit text" as never published, yet `docs/world.md` is meant to show one
  rendered page per entity type. The IP risk is the Pokédex prose, not the
  PokéAPI facts under twin names. `docs/data-sources.md` now allows twin-side
  examples in docs with every flavor-text unit elided; the benchmark files
  still carry unit ids only.
- **Registry id.** Registry ids are monotonic. The identity probe is the first
  experiment to run and is registered as E-003; the Phase 8 entry takes the
  next free id. The two Phase 8 reading notes and the milestone description now
  refer to "the Phase 8 entry".

**Plan impact PI-010:** Phase 1 — the published-material rule excludes rendered pages and unit text, yet `docs/world.md` shows one rendered page per type → twin-side pages may appear in docs with every flavor-text unit elided; `docs/data-sources.md` amended to say so, and later case renders follow the same rule. Open.

**Plan impact PI-011:** Phase 8 — its registry entry was assumed to be E-003 → it takes the next free id; the Phase 8 reading notes refer to it as "the Phase 8 entry". Open.

**Plan impact PI-010 resolved:** absorbed — `docs/data-sources.md` amended (documentation examples); the Phase 1 world-doc issue requires elided flavor units.

**Plan impact PI-011 resolved:** absorbed — `notes/phase8-synthesis.md`, `notes/geifman-2017-selective-classification.md` and `.github/setup/milestones.sh` updated; no hours or deliverables change.

## 2026-09-29 — Download and graph load: what enters the graph

`world/download.py` fetches 23 PokéAPI CSVs at the pinned commit and keeps a
file only if its SHA-256 matches the manifest. The 14 files hashed for G1 still
match; 9 files are added for English names, move categories and forms
(`docs/data-sources.md`).

`world/load_graph.py` loads the **real** world; the twin is a renaming layer
built on top of it. Scope filters, each counted in the load statistics:

- **Types:** only types with rows in the efficacy table, i.e. the 18 battle
  types. `unknown`, `shadow` and the Tera-only `stellar` go.
- **Moves:** only moves some Pokémon learns, with a battle type (drops shadow
  moves and the Z- and Max-move variants: 833 of 937 kept).
- **Abilities:** main series only (314 of 374).
- **Names and flavor text:** English only; flavor whitespace collapsed.
- **Learnsets:** every version group and every learn method is loaded
  (638,321 rows). The version scope is chosen from the coverage report and
  applied when pages are rendered, so the coverage report and the S2 filter
  read the same graph.
- **Not loaded:** evolution conditions (level, item, trigger), stats, genus,
  height and weight. Evolution enters as structure only (`EVOLVES_FROM`),
  which is all the S1 templates need.

A load replaces the whole database and then checks every node and relationship
count against the records it wrote, because a `MATCH` that misses an endpoint
writes nothing and raises nothing. Integration tests wipe the database, so they
run only with `NEO4J_TEST_ALLOW_RESET=1` (set in CI).

Found while reading: 4 English Pokémon names are shared by two entries
("10% Zygarde", "Koraidon", "Miraidon", "Mega Meowstic"). Titles must be unique
for `open_page`, so the renderer disambiguates them; the graph keeps the
PokéAPI identifier, which is unique.

## 2026-09-29 — Version scope frozen: x-y, ultra-sun-ultra-moon, scarlet-violet

The learnset coverage report (`docs/world.md`, Version scope) was computed from
the graph and from the raw CSVs; the two agree in every cell. The author chose
**x-y, ultra-sun-ultra-moon and scarlet-violet** (generations 6, 7 and 9).

- **Evidence.** S2 material does not bind: every one-group-per-generation set
  has more than 300 S2-usable pairs in its weakest group. This set is the most
  balanced (weakest group 2,383 pairs), 486 Pokémon have a learnset in all
  three groups, and 999 of 1,025 in at least one, generation 9 included.
  Level-difference rates between the chosen groups: 24% (x-y vs
  ultra-sun-ultra-moon), 56% (ultra-sun-ultra-moon vs scarlet-violet), 63%
  (x-y vs scarlet-violet).
- **Rejected.** x-y + ultra-sun-ultra-moon + sword-shield (more S2 pairs, but
  generation 9 left without learnsets); sword-shield with scarlet-violet (1% of
  levels differ); every four-group set (each adds a near-duplicate group).
- **Consequences.** `VERSION_SCOPE` in `world/pokeapi.py`. The graph keeps
  every version group; the renderer writes learnset sections only for the
  scope, and every examiner template filters `LEARNS.version_group` to it, so a
  gold answer can never come from a group the corpus does not contain. The S2
  filter compares against the other two groups of the scope, and excludes
  level-0 ("on evolution") and multi-level pairs as ambiguous.

## 2026-09-29 — The twin: pinned word list, name shapes, what free text rewrites

`world/twin.py` builds the twin map with `TWIN_SEED = 20260929`. Decisions:

- **Pinned word list.** The dictionary filter uses `words_alpha.txt` from
  `dwyl/english-words` (Unlicense), pinned by commit and SHA-256 and fetched
  with the CSVs. A system dictionary was the first idea and was dropped: it
  differs between machines, so the published seed would not rebuild the same
  twin.
- **Names are drawn independently of the real name**, so no twin name carries
  a trace of its entity. Look-alikes of any English real name (same first or
  last four letters, one edit away, or containing it) are redrawn as well, so a
  twin name does not evoke another real entity either. The first draw produced
  unreadable names (up to 12 letters, "thh" clusters) and one profanity; words
  are now 4–9 letters, never three consonants in a row, with a blocklist.
- **Shapes are kept where they carry structure, not identity:** form names keep
  "<qualifier> <species>" with a consistent pseudo-word per qualifier, and
  version-group names are rebuilt from their versions.
- **Free text** rewrites Title-case and upper-case names only. Lower-case prose
  stays; the identity probe measures what it leaks. Version names are not
  rewritten in prose, where "X" or "Sun" are ordinary words.

Build on the real data: round trip identity for every name, no shared word,
0 of 14,496 flavor texts still naming a real species (`docs/world.md`).

## 2026-09-29 — Page and unit design

The author reviewed the page design before any code; one decision changed in
the discussion.

- **All learn methods on species pages (changed).** The first proposal kept
  level-up only, to keep the corpus small. The author's objection, from a
  concrete use (building a competitive team needs machine, egg and tutor moves
  too), exposed what that loses: a machine unit listing a move is plausible,
  insufficient evidence for a question about its level — a wrong-method
  distractor that strengthens S2 and S4 without touching the label, since the
  registry knows the unit states no level. Species pages now carry one unit
  per method and version group; hubs stay level-up only (a machine hub would
  list most of the corpus). Cost: 13,477 units instead of about 8,800.
- **Forms:** types and abilities only; their learnsets are out of v1.
- **Hub entries carry the learner's types**, so S3 keeps its type filter
  within T_max.
- **S4:** 120 withheld (species, version group) pairs, seeded; their entries
  also leave the hubs of that group, so no indexed unit states a withheld
  level. The examiner's S3 templates must avoid hubs touching them.
- **Notes:** two Pokédex texts per species at most; `--no-notes` is the G2 exit.
- **Unique titles:** one page per ability name; " (2)" for repeated form names.

Parked with the author's agreement: "can X learn Y?" — a negative answer is
sufficient only after every learn method has been seen (`notes/open-ideas.md`).

Build on the real data: 144,861 facts, 13,357 indexed units, registry check
PASS in both namings, forced rebuild byte-identical (`docs/world.md`).

## 2026-09-29 — Index and tool contract

Three decisions, taken by the author before any code:

- **`open_page(title)` reads the page from the top**, up to the call's cap,
  like opening a wiki page. The alternative, a table of contents first, costs a
  step of T_max = 6 on every hop.
- **`offset` continues a section** past one call. Nothing says more remains;
  an agent that suspects an incomplete list asks, and asking is the decision S3
  measures. Without it, hub units beyond the first call could only surface
  through reformulated searches, which would make S3 a test of the ranking.
- **Dense backend: `fastembed` with `BAAI/bge-small-en-v1.5`.** ONNX on CPU, no
  torch; the GPU is not visible from WSL, and 13k units need no approximate
  index. The `retrieval` extra is now `fastembed` only: BM25 is adapted from the
  previous project (standard library), so `rank-bm25`, `faiss-cpu` and
  `sentence-transformers` leave the dependencies.

The 700-token cap per call is now written into E-001's fixed parameters,
counted with `o200k_base` (amendment of 2026-09-29).

## 2026-09-29 — Answer spaces; the G2 chance rate becomes the majority-answer rate

The answer-space count (`docs/world.md`, Answer spaces) shows skewed slots: a
move's type is Normal 22.6% of the time, a damage factor is ×1 63% of the time,
a move's power is 80 in 13% of moves, and a learnable level is 1 in 21.3% of
answerable pairs. The G2 closed-book rule compared A0 with uniform chance on
spaces of at most 20 values and with a flat 5% elsewhere, so a model that knows
only the answer distribution — no leak — would fail it. Escalated the same day
because it touches a `docs/contingency.md` criterion; decided before any A0
run.

**Plan impact PI-012:** Phase 3 — the G2 closed-book check compares A0 with uniform chance on small answer spaces and with a flat 5% on open ones, but answer slots are skewed (always guessing the modal value scores 22.6% on a move's type, 63% on a damage factor, 13% on move power, 21.3% on a learn level, with no leak) → chance becomes each template's majority-answer rate (the share of its most common gold answer among its generated questions, never below uniform), for every template, small or open; the 5-point margin stays; Phase 2 reports each template's majority-answer rate. Open.

The author approved the change and added a generation cap: each template's
majority-answer rate is at most max(10%, 1.5 × its uniform chance). Reason: an
agent that stops early and guesses the modal answer would otherwise score
lucky correct answers (`correct-at-insufficient`) in E-001 as well as in G2.
Cost: answer distributions per template are no longer the world's natural ones.

**Plan impact PI-012 resolved:** absorbed — `docs/contingency.md` G2 amended
(chance = majority-answer rate, never below uniform; generation cap
max(10%, 1.5 × uniform)); ADR-003's consequence and `docs/hypothesis.md` (A0 ≈
chance on the twin) updated. Phase 2's generator enforces the cap and reports
each template's majority-answer rate; Phase 3's closed-book check uses it. No
hours or dates change.

## 2026-09-29 — E-003 registered: the identity probe

The identity half of G2 is registered as E-003 (draft) before any code for it.
The author chose among alternatives:

- **Model:** gpt-5-mini only — the probe asks whether the model of the runs
  recognizes the twin. GPT-4o-mini belongs to the v1.2 extension, where the
  probe can be repeated.
- **Input:** the page as `open_page(title)` serves it, which is what an agent
  sees on one hop, plus a descriptive third condition without the Pokédex notes
  (50 more calls), so a leak can be attributed to the flavor text — the exit
  G2 already names — without a second run.
- **Match rule:** any species or form of the same evolution line counts as
  identified. Knowing the family is enough to answer S1 from memory, so this is
  the conservative rule for the twin. Exact species is descriptive.
- **Sample:** 50 species stratified by generation (6 per generation 1–5, 5 per
  generation 6–9), the same species in every condition. Popularity falls with
  generation, so a simple random draw could miss the most memorized species.

The prompt tells the model it is looking at a renamed Pokémon: the hardest
test for the twin. Cost under US$ 0.10. The author's prediction goes into the
entry before the run.

## 2026-09-29 — E-003 first collection: the twin leaks through the Pokédex notes

The identity probe (E-003) ran on 50 species. The control identified 48 of 50,
so the probe works. The twin identified 22 of 34 valid answers — at least 22 of
50 counting every invalid answer as a miss — so **G2's identity half fails**.
Without the Pokédex notes the twin identified 1 of 37: the flavor text, still
readable in lower-case prose after renaming ("lives in caves… rusts easily"),
carries the leak, as ADR-003 suspected. The author had predicted 2–3 of 50 and
little weight for the notes.

29 answers were invalid: 28 truncated at the registered 1,000-token output cap,
spent on reasoning. With the author's agreement, E-003 is amended (dated,
decided after the rates were seen): the two allowed re-sends keep the
registered cap and the first valid answer per request is kept; what stays
invalid is re-sent once at 4,000; residual invalid answers are counted both
ways, and only a verdict both cases share is taken. The branch of the exit plan
(notes vs structural) waits for those re-sends.

**Plan impact PI-013:** Phase 2 — the corpus was assumed to keep Pokédex notes (flavor units marked for the shortcut scan, flavor text read in the G3 audit) → E-003 finds the notes leak identity (twin 22 of 34 valid, ≥ 22 of 50; without notes 1 of 37); if the no-notes branch holds, pages carry no notes, the shortcut scan's flavor-text planted leak and the G3 flavor read are dropped, and the README states the lost realism. Open.

**Plan impact PI-014:** Phase 3 — the budget assumed 150 (central) / 400 (pessimistic) reasoning tokens per call → on twin pages gpt-5-mini at low effort used a median of 512–576, and 28 of 100 twin calls hit a 1,000-token cap → the pilot measures reasoning per arm before n_max, and every registered run's `max_completion_tokens` leaves headroom (≥ 4,000). Open.

Both were escalated the same day: PI-013 touches the phase in progress and a
`docs/contingency.md` exit; PI-014 touches the budget behind the sizing. The
probe itself cost US$ 0.09, above its pessimistic estimate of 0.076.

## 2026-09-29 — G2's exit taken: world v1 renders no Pokédex notes

After the two registered re-sends, E-003 run 1 reads, in both bounds of its
remaining invalid answers: twin 26–31 of 50, twin without notes 1–4 of 50,
control 48 of 50. Rule 3's branch is "notes": the leak is in the flavor text,
not in the facts. The author confirmed the consequences:

- **World v1 has no notes.** The renderer's CLI leaves them out by default;
  `--notes` restores them for research. 12,452 units (12,332 indexed), the
  same 144,861 facts; registry check PASS; byte-identical on a forced rebuild.
- **E-003 run 2** is registered before it runs: a fresh sample of 50 species
  (seed 20260930, excluding run 1's), control and twin on the no-notes world,
  the 4,000-token cap from the start.
- **The vector cache is per unit.** Re-rendering re-embeds only units whose
  text changed; the earlier whole-corpus file was imported, so the no-notes
  index needed no embedding at all (12,332 vectors reused).
- **Documents:** `docs/world.md`, `docs/data-sources.md`, `docs/contingency.md`
  (G2 status), and Updates sections in ADR-002 and ADR-003.

PI-013 stays open until run 2 passes. The last re-send of run 1 (4,000
tokens, 8 answers) completes its published counts; it cannot change the
verdict, which both bounds already share.

## 2026-09-29 — E-003 run 1 final; run 2 frozen before submission

Run 1 closed with every answer valid after the registered re-sends: control 48
of 50, twin with notes 27 of 50, twin without notes 1 of 50. Decision: fail —
notes; the exit (no notes in world v1) stands. Total cost US$ 0.16.

World v1 was re-rendered without notes: page hashes equal the ones of the test
render made earlier the same day, and the index reused every cached vector.
Run 2 was prepared on it (50 species, none of run 1's) and **frozen from its
manifest before submission** — the order run 1 missed. The author's prediction
for run 2: control about 45 of 50, twin 1 or 2.

## 2026-09-29 — E-003 run 2: G2's identity half passes on world v1

On the no-notes world, with 50 species none of which run 1 used: control 48 of
50, twin 1 of 50 (22 "unknown", 27 wrong species at mean confidence 0.61). The
author had predicted about 45 and 1–2. The one species named — at confidence
0.9, with no text on the page — has a three-stage evolution line and a Mega
form: identification from structure alone is possible for the most distinctive
species. It is within the threshold and is declared as a limitation; it does
not call for another exit. The closed-book half of G2 runs in Phase 3.

**Plan impact PI-013 resolved:** contingency G2 taken — Pokédex notes removed from world v1 (the renderer's default; `--notes` for research), E-003 run 2 passes on the no-notes world. Phase 2 drops the shortcut scan's flavor-text planted leak and the G3 audit's flavor read, since no unit is free text; the README states the lost realism in Phase 7.

## 2026-09-29 — Phase 1 close review: decisions stress-tested

Before closing Phase 1 the author reviewed every Phase 1 decision and brought
in an external design review. Findings and what was adopted (A–F):

- **S1 skipped hops that do not change the answer.** Measured: in 246 of 299
  single-final evolution lines the base and final forms share their hidden
  ability, so an agent that skips the missing hop is right by coincidence 82%
  of the time. Adopted (A): S1 splits into *material* missing hops (the
  anchor's own answer differs from the gold answer), which form S1 in the H1
  pool, and *benign* ones (they coincide), kept as a descriptive slice outside
  H1 — it tests whether a detector reacts to missing evidence or to an
  implausible answer, the line between this project's label and Joren et al.'s.
  S1 gets templates beyond hidden ability, which leaves 53 material lines.
- **A tool announced an absence (B).** `open_page` answered "No section
  matching …" for a withheld S4 section. A neutral empty answer carries the same
  information, so a section matching nothing now serves the whole page. The
  principle is recorded in ADR-009: the structure may be artificial; the signal
  used to decide sufficiency is never handed over by the infrastructure. E-001
  amended (tool contract).
- **S3 mechanism split (C):** fetching the rest before the end versus learning
  the end by asking past it; E-001's mechanism quantities amended.
- **Scope filter guarded by a negative test (D):** in Phase 2, removing a
  template's version-group filter must make a test fail.
- **Answer-concentration cap published before and after (E)**, as an
  experimental intervention (`docs/contingency.md`).
- **Cost never changes the treatment (F).** If Phase 3 finds the agent costlier
  than budgeted (PI-014), n shrinks — the abort and descriptive branches of
  measurability gate 8 exist for that — while `reasoning_effort`, T_max, B and
  the prompts stay as registered. Raising `max_completion_tokens` is headroom,
  not a treatment change.

Not adopted: adding structural difficulty to compensate for the notes'
removal. Making the environment harder to recover effect size would shape the
design around the expected result; any addition must be justified by the
construct. The strata carry the construct (finding *a* record is never enough
in S1–S4); the notes added reading difficulty, a different construct. The
README will state that the benchmark measures sufficiency over a structured,
rendered corpus.

**Plan impact PI-015:** Phase 2 — S1 assumed the missing hop changes the answer → in 246 of 299 single-final evolution lines base and final share their hidden ability (an agent that skips the hop is right 82% of the time) → S1 templates filter to material hops (anchor's own answer ≠ gold) for the H1 pool, benign hops form a descriptive slice outside H1, S1 gets templates beyond hidden ability (53 material lines there), and a negative test proves every template's version-group filter. Open.

## 2026-09-29 — Plan revised at the Phase 1 close

The phase plan was revised before the Phase 1 tag, so the later phases start
from the Phase 1 evidence. Retrospective impact found in the close sweep:

**Plan impact PI-016 (retrospective, logged 2026-09-29):** Phase 2 — the generator's filters were planned before the world existed → the world design adds constraints: S3 templates avoid hubs whose gold set includes a withheld species; hidden-ability templates sample only species that have one; level-0 ("on evolution") and multi-level pairs are ambiguous answers; 19 evolution lines branch, so "final form" is ambiguous there; non-default forms have no learnsets. Open.

The author decided three things:

- **No calendar.** This is a personal project worked on sporadically; phase
  sizes stay as relative effort estimates, not dates. Milestones lose their due
  dates; Phase 8's three-week timebox becomes 15 partial days of effort, still
  the guard against sunk cost. Author preference.
- **The S1 benign slice** is 40 questions in eval-L1, run by A3, A4 and A4p
  only, descriptive and outside H1; its size is confirmed against n_max in
  Phase 3.
- **PI-016** is accepted as above.

Phase 2 grows by about one partial day (S1 material and benign, templates beyond
hidden ability, the negative scope test, the concentration cap) and loses the
flavor-text tasks; the surplus of Phase 1 pays for it. The measurability-gate
answers are unchanged: the measured cost per arm arrives in Phase 3, which
re-runs gates 3 and 8 with it, and the S1 material pool arrives in Phase 2.

**Plan impact PI-014 resolved:** plan revised on 2026-09-29 — Phase 3 measures reasoning tokens per arm before n_max; every registered `max_completion_tokens` leaves headroom (≥ 4,000); if the measured cost binds, n shrinks and the treatment (`reasoning_effort`, T_max, B, prompts) stays as registered.

**Plan impact PI-015 resolved:** plan revised on 2026-09-29 — Phase 2 builds material S1 (H1 pool) and a benign S1 slice (descriptive; 40 questions in eval-L1 for A3, A4, A4p), adds S1 templates beyond hidden ability, and proves the version-group filter with a negative test.

**Plan impact PI-016 resolved:** plan revised on 2026-09-29 — the five constraints become Phase 2 generator filters, each with its N-of-M count in `docs/examiner.md`.

## 2026-09-29 — Phase 2 opened

**Scope.** Phase 2 — The Examiner: generator, gold chains and step labels. Size
L (9–12 partial working days, as an estimate; no calendar). Ends with the
`v0.3-examiner` pre-release (the benchmark v0) and the G3 verdict.

**Gate check.** Every Phase 1 deliverable is present; PR #18 merged, tag
`v0.2-world` pushed, Phase 1 issues and milestone closed. One gap: the Phase 1
note's Lessons Learned and Failed Attempts are empty.

**Carry-overs.** The Phase 1 lessons and failed attempts, written by the
author, are the first task of Phase 2 (author's decision).

**Open plan impacts.** None: PI-001 to PI-016 are resolved. The ones that shape
this phase are already in its tasks — S1 material and benign (PI-015), the
world's constraints on the generator and the negative scope test (PI-016), the
answer-concentration cap with before/after tables (PI-012), no flavor-text case
in the shortcut scan or the G3 audit (PI-013).

**Scope decisions.** None taken at kickoff.

## 2026-09-29 — Template design for the examiner

Measured before deciding (`docs/examiner.md`). The author approved:

- **S3 requires the gold set spread over at least two indexed units.** Of
  1,504 candidate "type-T learners of M in V" sets of size 3–25, 1,181 fit in
  one hub unit — one unit is sufficient there, nothing is truncated. 323 remain.
  A hidden-ability holders template was dropped (24 sets span two units).
- **S1 uses version-free relations only** (evolution, abilities, types, the
  type chart). A hop through a learnset would mix a wrong-version trap into a
  missing-hop question. Five templates; four evolution-based ones give ~320
  material anchors; the fifth (a move's type multiplier against a species)
  needs three facts and is material by construction.
- **S4 keeps two templates**, below the planned three to five: every S4
  question rests on a withheld learnset, and a third shape would be artificial.
  S4 reuses S2's surface forms, so the wording never reveals the stratum.
- **Partition:** the B template of each stratum is its most different shape
  (S0-B1 type chart, S1-B1 move vs species, S2-B1 last move, S3-B1 level cap,
  S4-B1 move at level).
- **Surface forms** are hand-written, three per template; the author reviews
  them.

Also added: `world/explore.py`, a local tool to see any page in both namings.

## 2026-09-29 — Profiles link forward only (escalated and absorbed)

Writing the S1 templates showed that species Profiles carrying the whole
evolution line put the anchor and the answer of every evolution-based S1
question in one unit — the final form's Profile — so the single-unit shortcut
filter would discard all of them. Measured alternatives (anchors / material):
forward links only keep S1-A1 405 / 70, S1-A2 434 / 104, S1-A3 405 / 57;
immediate links both ways keep only 103 / 19 and 110 / 41 and lose S1-A3. The
author chose forward links.

**Plan impact PI-017:** Phase 2 (and the Phase 1 world) — species Profiles were assumed to be able to show the whole evolution line → that puts the anchor and the answer of every evolution-based S1 question in one unit (the final form's Profile), so the single-unit shortcut filter discards all of them → Profiles show forward links only ("Evolves into"), final forms state "Evolves into: —" as a registered fact, S1-A4 (pre-evolution) is dropped, world v1 is re-rendered; E-003 stands, since the new pages show a subset of what it probed. Open.

Done the same day: `render.py` links forward and registers `evoend` facts
(145,429 facts; registry check PASS in both namings); all 405 S1-A1 anchors now
need at least two units; `docs/world.md` examples regenerated;
`docs/examiner.md`, `docs/hypothesis.md` (S1 example now Dratini, a material
case — the old Charmander example was benign), ADR-002 (Updates) and a note in
E-003 updated.

**Plan impact PI-017 resolved:** absorbed — the world was re-rendered within Phase 2, S1 keeps four templates (S1-A1 to A3 and S1-B1), no hours or deliverables change.

## 2026-09-29 — Examiner templates and the first generation

`examiner/templates.py` (Cypher per template), `examiner/surfaces.py` and
`examiner/generate.py` generate 33,719 questions from the graph, byte-identical
across runs; counts per template and per drop reason in `docs/examiner.md`.
Decisions made while building, none changing the approved design:

- **The single-unit shortcut filter applies to S1 and S3 only.** S0 is one
  unit by design and S2 is one fact by nature — its difficulty is the
  wrong-version distractor; the specification said "S1–S3" and was corrected.
- **Gold facts are the facts the answer is derived from.** For "the last move
  X learns" that is the whole learnset, so only the learnset unit covers it; a
  hub entry naming the move at the top level does not prove it is the last.
- **S4 is exempt from the concentration cap:** its correct answer is always to
  abstain, so no guess can be lucky.
- **"Pokémon" takes no plural `s`**, in the twin as in English, so real and
  twin questions stay parallel.
- **S3 pool:** 1,961 sets, not the 323 first estimated; the estimate excluded
  every hub touching a withheld species, the rule excludes only sets whose
  members include one.
- **S1-B1** samples 40 damaging moves (seeded) against every species.
- **Question ids** carry PokéAPI ids and are local. The published benchmark
  must use opaque ids: a PokéAPI species id maps a twin name back to its real
  species.

## 2026-09-29 — The sufficiency labeler

`labeling/sufficiency.py` labels every state of a trajectory as a pure
function of the question's gold facts, the registry and the unit ids each
observation showed; specification in `docs/examiner.md`. Decisions:

- **Covers are recomputed from the registry**, never read from the question
  record, so a stale record cannot move a label.
- **Refuse, never guess.** A seen unit the registry does not know, a seen
  withheld unit, an unanswerable non-S4 question or an answerable S4 question
  raise an error instead of producing a label; each one is a fault in the
  logger, the index or the generator, and a label computed over it would be
  silently wrong.
- **Near-certain evidence is reported beside the label, not inside it.** The
  generator now records, for S2 and S4, the distractor facts (the same
  question answered by another version group of the scope) and the indexed
  units stating them; the label says which of those units were seen. The
  error taxonomy's `accepted-wrong-version` and E-002's near-certain count
  read this field. S4 questions also record their withheld units. The
  question set is unchanged: at most one version group is withheld per
  species, so every distractor has indexed units; the question file gains
  three fields and its hash changes.
- **S3 labels report members covered** (entries whose learn and type facts
  are all seen, of the set size) for E-002's delivered fraction of the set.
- **Golden trajectories run on the fixture world**, with labels written by
  hand from its rendered units: 9 trajectories covering every stratum and
  subtype, and 6 refusals.

## 2026-09-29 — Shortcut scan: statements, the twin, verdicts by class

`examiner/shortcuts.py` implements filter 7. The first run, on the approved
design, planted 160 leaks and flagged all of them, then flagged 1,286 of
33,719 questions. The author approved four points after reading the classes
with rendered examples:

- **Statements, not units.** A statement is a body line with its unit's
  header (a free-text unit is one statement). At unit level the scan flagged
  2,064 questions; the extra 778 were two facts on different lines of one
  unit, such as a pre-evolution's Profile naming the anchor and its own hidden
  ability. ADR-002 updated.
- **The twin pages only.** Real names collide lexically ("Fire" inside "Fire
  Punch", "Porygon" inside "Porygon-Z"): noise of the scan, not a leak of the
  registry.
- **All 18 classes are coincidences; 0 questions discarded.** A form of the
  anchor (its own entry, with its own ability or types); the anchor's own value
  in S1 (the benign case, already tracked by the material tag); another fact
  with the same names (a learner's types in a move's hub, a third type's
  matchup line, the same move by machine or tutor); a learn level equal to a
  move's power. Verdicts with reasons live in `VERDICTS`; a class seen for the
  first time fails the scan until it is read.
- **S1-B1 at ×4 or ×0.25 is not scannable** (1,461 of 12,740): no page writes
  those values. Published N-of-M.

S2-A1, S2-A2, S3 and S4 have no flag at all. Noted while reading: some
material S1 questions have a regional form that is what actually evolves
(Galarian Corsola, Ghost-type, evolves into Cursola); the graph records
evolution per species, so this is a world quirk, not a leak.

## 2026-09-29 — Splits

`examiner/splits.py` draws dev, train, eval-L1 (with the 40-question benign S1
slice as its own file), val-B, eval-L2 and eval-L3 from the 33,719 kept
questions; `docs/examiner.md` → Splits. dev and train are frozen; evaluation
ids are drawn now and frozen at the dress rehearsal. Measured before writing
the code, and approved by the author:

- **Families.** Questions sharing a (template, anchor entity) pair or an
  identical gold chain go to one split together: 6,822 families. Identical
  chains join S2-A1 with S2-A2 (418 families) and S4-A1 with S4-B1 (112).
  Every split is disjoint from every other, stricter than the registered rule,
  so eval-L2 and eval-L3 stay independent of eval-L1.
- **No stratification beyond the template.** A simple seeded draw within each
  template estimates that template's population; the manifest reports the
  distributions (S2 versions, S3 set sizes, S4 withheld pairs, S1 material).
  Each pass takes one question per family, so S4 spreads over withheld pairs
  where it can: 121 families for 242 questions demanded, capped in proportion
  to each split's demand.
- **Largest-remainder rounding, group A first** (S2 in eval-L1: 27 / 27 / 26).
- **Opaque ids from the start**: `q-` + 10 hex of sha256(seed:id). They keep
  PokéAPI ids out of published files; with the seed public they are not a
  secret.
- **Growth.** A gate 8 extension draws after every other split, so nothing
  already drawn changes.

**Plan impact PI-018:** Phase 6 — the freeze and gate 8's extension assumed eval-L1 draws equal numbers per template within each stratum, growing balanced up to n* → material S1 pools (S1-A1 70, S1-A2 104, S1-A3 57) cannot give equal counts even at the base size once dev, train, eval-L2 and eval-L3 take theirs → group-A S1 is split across S1-A1 to A3 in proportion to their material pools (S1-B1 keeps its equal share, so the A/B proportion is unchanged), and balanced growth stops near a pooled S1–S4 n of 548; E-001 amended before its freeze. Open.

Escalated the day it was found, since it touches a registry entry and gate
8. Measured after the change: the extension works up to 57 extra questions
per stratum (137, pooled 548) and fails at 58; material questions used by the
base splits are 57 of 70, 85 of 104 and 46 of 57.

**Plan impact PI-018 resolved:** absorbed — E-001 amended (draft, before its freeze), the splitter implements the proportional S1 allocation and the bounded extension; no sizes, hours or phases change. If Phase 3 puts n_max above 548, the gap is recorded then.

## 2026-09-29 — S1: only evolutions the default form makes

Preparing the G3 sheet, a drawn question asked for "the final form of
Corsola's evolution line", gold Cursola. PokéAPI links evolutions per species;
in the game only Galarian Corsola evolves, and Corsola as its Profile shows it
does not. PokéAPI records this: `pokemon_evolution.csv` at the pinned commit
names the form that must evolve (`required_pokemon_form_id`). Ten evolutions
need a non-default form; four sit on branching lines S1 already excluded
(Perrserker, Runerigus, Sneasler, Clodsire), six do not (Cursola, Sirfetch'd,
Mr. Rime, Obstagoon, Overqwil, Basculegion).

**Plan impact PI-019:** Phase 2 — S1 assumed every species-level evolution in PokéAPI is one the anchor's default form makes → 6 single-child evolutions need a regional or variant form (`required_pokemon_form_id` in `pokemon_evolution.csv`), so 18 material S1 gold answers are wrong for the default form → the examiner drops chains through form-only evolutions, `pokemon_evolution.csv` joins the pinned download, questions, scan and splits are regenerated with dev and train refrozen before any use, and the gate 8 ceiling of PI-018 is re-measured. Open.

Escalated the day it was found (it touches the phase in progress and a frozen
split). The author chose, of two options:

- **A (taken): drop at the examiner.** `world/pokeapi.form_only_evolutions`
  reads the CSV; S1-A1 and S1-A2 drop a line through such an evolution, S1-A3
  a next form reached that way (22 questions: 8, 8 and 6; 18 material).
- **B: fix the world** (Corsola's Profile "Evolves into: —", the evolution on
  Galarian Corsola's Form unit). More faithful, but a new fact kind and a
  re-render of Phase 1 pages. The corpus keeps PokéAPI's species link as a
  declared simplification no question depends on.

The author also fixed the G3 standard: a gold answer is correct when it
matches the game for the question as asked (named version group, default
form), not merely PokéAPI — the stricter reading, since eval-L3 asks in real
names and a model that knows the game would contest the gold.

Regenerated the same day: 33,697 questions (was 33,719); material S1 pools 64
/ 96 / 53. The shortcut scan, rerun: 160 of 160 planted leaks, 1,272
questions flagged in the same 18 classes, 0 discarded — and the 10 material S1
questions the first scan flagged in Form classes are gone: they were exactly
these lines (a regional form sharing the final form's value). Splits redrawn
with `--refreeze`: 6,800 families, 0 clashes; allocations unchanged; dev and
train changed in their S1 draws only (24 and 22 ids), before any use. The
gate 8 extension now stops at 32 extra per stratum, a pooled S1–S4 n of 448
(PI-018 measured 548).

**Plan impact PI-019 resolved:** absorbed — the filter, the pinned CSV and the regenerated questions, scan and splits fit Phase 2; E-001 amended (draft). The lower growth bound (448) is compared with n_max when Phase 3 computes it.

## 2026-09-30 — Opening counts, reachability, audit sources

- **Opening counts.** The splits issue asked for opening counts initialised at
  0; they were missing. `data/splits/openings.json` now holds them, and
  `splits.open_split` is the only reader of an evaluation split's ids: every
  opening is logged with its date and purpose, a second one needs an explicit
  reopen and is counted, and an opened split can no longer be redrawn or
  extended.
- **Reachability (ADR-007).** `examiner/reachability.py` finds, for each
  insufficiency subtype and error code, a dev question and a reachable state
  whose label is the one the code needs: 13 of 13 reachable, `format-error`
  declared (a property of the output). The `correct-at-insufficient` witness
  is the final form's Profile seen alone: it shows the answer but not that the
  form is on the anchor's line.
- **Audit sources.** The G3 sheet's gold chain comes from the same pipeline as
  the gold answer, so their agreement tests nothing; the auditor checks an
  independent source first (Bulbapedia, Serebii per game, PokémonDB; never a
  site built on PokéAPI) and reads the chain only to locate a disagreement.
  The sources per template are in `docs/examiner.md` → G3 audit.

## 2026-09-30 — Benchmark v0 export and card

`examiner/benchmark.py` exports the benchmark v0 locally
(`data/world/benchmark/v0/`); `docs/benchmark-card.md` is its card, written
before any upload. Decisions:

- **Opaque fact and unit ids** (approved by the author), like question ids:
  `f-`/`u-` + 12 hex of sha256(seed:id). Raw ids carry PokéAPI ids, which map
  twin names back to real ones. A rebuilt corpus computes the same ids.
- **Two more orderings leaked the same map** and were closed while building:
  rows came out in PokéAPI id order (national dex order: the first S0-A1 rows
  named species 1, 2, 3), and S3 gold facts listed members by PokéAPI id. Rows
  are sorted by opaque id; gold facts keep chain order in S1 only, where the
  order is the chain, and are sorted elsewhere.
- **Evaluation splits by id only until opened.** Publishing their answers
  before the project measures on them would add a contamination path for no
  gain; they follow with the opening counts. `--include-evaluation` exists for
  that later release.
- **Checks before writing:** no raw fact or unit id in any field, no real
  species, move, ability or type name in any question or answer (both checked
  on planted cases). v0: 32,767 questions (dev 150, train 150, pool 32,467).

## 2026-09-30 — E-001 red-team after the examiner build

The `experiment-redteam` review planned for after the templates read E-001
against the built examiner: 8 blocking findings and 11 caveats. The claims
that change data were checked before anything was proposed: 57 of 80 eval-L1
S3 hubs fit in one 700-token call; withheld pair (442, scarlet-violet) sat in
eval-L1 and eval-L3; E-001 names O2 in a table row only. The author approved
all of it.

**Plan impact PI-020:** Phase 2 — S3 assumed that seeing every member makes a state sufficient and that a set spread over two units needs two steps; S4 families assumed per template → seeing the members does not prove the list complete (only the whole (move, version) hub does), 57 of 80 eval-L1 S3 hubs fit in one 700-token call, and one withheld pair sat in eval-L1 and eval-L3 → S3 gold facts become every row of the hub (members still reported), S3 keeps only hubs longer than one call, S4 families are keyed by withheld pair; questions, scan, splits, golden trajectories and reachability regenerated, dev and train refrozen before any use. Open.

Done the same day. Questions: 32,300 (S3-A1 1,002, S3-B1 630; 9,238 hub
sets dropped as one-call). Scan: 160 of 160 planted leaks, 1,272 flagged, 0
discarded. Splits refrozen: 6,425 families, 0 clashes; S3 now draws 242
questions from 65 moves and S4 from 120 pairs, both capped in proportion
(eval-L1: 21 moves, 41 hubs; 39 pairs). S3 golden trajectories rewritten for
the closure label, with a new case: the only member seen, the list not yet
proved complete. S0 got its own subtype, `not-found`. Reachability: 14 of 14
codes. Benchmark v0 export: 31,370 questions. The G3 round in progress stays
valid: gold answers did not change, only what proves an S3 set complete.

**Plan impact PI-020 resolved:** absorbed — filters, labels and regenerated artifacts fit Phase 2; no hours or deliverables change.

**Plan impact PI-021:** Phases 3–6 — E-001's analysis assumed independent questions, an operational O2, a gate 8 extension feasible up to n_max and an unambiguous error taxonomy → eval-L1 is clustered (S4 pairs, S3 moves, S1 lines), O2 had no decision rule and is mechanically ahead on S4, balanced growth stops at 448, codes overlapped → clusters with a cluster bootstrap and a design effect in gate 8, an O2 decision rule with per-stratum O2 − A3, n_max_eff = min(n_max, 448), the taxonomy as a decision list with golden tests for the assigner, trap-state precision and recall, a stratum-standardized A × B gap and a Phase 3 trajectory-level check; E-001 amended before its freeze, with 10 threats declared. Open.

Still open inside PI-021: whether rows 0b, 6 and 7 read O2 − A3 on S1–S3
rather than S1–S4, decided before the freeze. The new work (cluster
inference, code assigner and its golden tests, trajectory-level check) lands
in Phases 3 to 6 and is triaged at this phase's close.
