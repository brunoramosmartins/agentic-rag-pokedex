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
