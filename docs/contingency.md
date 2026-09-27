# Contingency Gates

**Status:** registered 2026-09-24, before any data was downloaded.

Each gate names **when** it is checked, the **condition that fails it**, and the
**exit plan** written in advance. Failing a gate is not failing the project: it
triggers the registered plan. Every gate evaluation gets a dated entry in
[`decision-journal.md`](decision-journal.md) with the numbers that decided it.

| Gate | When | Fails if | Exit plan |
|---|---|---|---|
| **G1 — Data and licenses** | Phase 0 | The PokéAPI CSV is unavailable, its license is not BSD-3, or the chosen game versions have learnset gaps | Swap the versions in scope for others with complete coverage; as a last resort, any CC0 graph (e.g. Wikidata) — the pipeline is domain-agnostic |
| **G2 — The twin does not leak** | Phases 1 and 3 | Identity probe: the model recognizes the real entity from the renamed page in > 10% of 50 pages; or closed-book (A0) on the twin scores > 5% (open answer spaces; > chance + 5 points on small ones — see below) | Mask or remove the Pokédex flavor text (main suspect); if it persists, primary-population questions exclude the leaking templates, decided on dev and recorded |
| **G3 — Generator correct** | Phase 2 | Human audit of 60 stratified questions finds < 58 correct gold answers | Fix and re-audit a **fresh** sample; after 3 iterations, remove the failing templates and record it |
| **G4 — Power** | Phases 3 and 6 | The pooled n required, using the SD of D measured on dev, exceeds n_max (what the cap pays for after cuts) | Abort criterion of [measurability gate 8](measurability-gate.md#gate-8--the-abort-criterion) |
| **G5 — Last exit** | Any | Motivation or budget collapses | v1.0 (Layer 1 verdict + release) is the product; the v1.1 and v1.2 extensions are separate releases, cuttable without losing the verdict |

---

## G1 — Data and licenses

- **Checked in:** [`data-sources.md`](data-sources.md), with a verdict per source:
  ok / ok-with-restriction / blocked.
- **Evidence required:** license text for PokéAPI and MuSiQue, a sample of each
  downloaded with its SHA-256, and a learnset-coverage count for the candidate
  version groups.
- **Standing constraint regardless of verdict:** raw PokéAPI CSVs and Pokédex
  text are never committed (names and game text belong to Nintendo, Creatures
  Inc. and GAME FREAK inc.). Whether the published benchmark includes Pokédex
  text, or the generator reconstructs it locally, is decided in the same
  document.

## G2 — The twin does not leak

- **Identity probe** on 50 renamed pages: the model is asked which real entity
  the page describes.
- **Positive control** (fixed before running): real pages with their own name
  masked must be identified in ≥ 50%. If the control fails, the probe is broken
  and G2 is not evaluated until it is fixed.
- **Closed-book check:** A0 on twin questions must stay ≤ 5% correct on
  templates with an open answer space (species, moves, abilities, sets).
  Templates whose answer takes **≤ 20 admissible values** in the corpus
  (e.g. a type, one of 18) are checked separately: A0's correct rate on each
  must stay within 5 points of its uniform chance rate (1 / number of admissible
  values). Guessing on a small answer space is not leakage. Per-template rates
  are published. (Amended 2026-09-26.)
- Checked first on the world build (Phase 1) and again on the pilot (Phase 3).

## G3 — Generator correct

- 60 questions stratified across S0–S4, audited by hand with the real names
  restored through the twin's inverse map.
- Threshold ≥ 58/60. Each re-audit uses a sample never seen before.
- Template removals are reported with N-of-M counts in `docs/examiner.md`.

## G4 — Power

- Preliminary check in Phase 3 (pilot SD, proxy contrast A1 vs A3).
- Power targets the *supported* verdict at Δ_design = 0.35, separately for
  H1 and H2; the larger n\* governs.
- Binding check in Phase 6 (dress-rehearsal SD of A3 vs A4 and of A2 vs A4,
  upper limit of the 80% interval), before eval-L1 ids are frozen.
- Branches (keep plan / draw more questions / descriptive claim) are fixed in
  measurability gate 8.

## G5 — Last exit

- **v1.0 cut order** (applied if the budget runs short): (1) arm A6, (2) cue
  ablation, (3) the A3′ rerun. **Never cut:** eval-L1 for A2, A3, A4, A4p and
  O2 — without the placebo the mechanism cannot be read, and without O2 rows
  6–7 of the outcome space cannot be told apart.
- **Pessimistic scenario:** with A3′ the v1.0 estimate is US$ 11.3 central /
  14.7 pessimistic against the 13.5 cap. Cutting A6 and the cue ablation saves
  ~US$ 1.8 in the pessimistic case (→ ~12.9).
- **n_max:** with Phase 3 measured costs, the largest pooled S1–S4 n the cap
  pays for after all three cuts is computed and logged **before the dress
  rehearsal**. If gate 8 asks for more than n_max, the verdict becomes
  descriptive (row 0). **The cap is not raised.**
- **Extension cut order:** (1) GPT-4o-mini replication, (2) MuSiQue, (3) real
  world, (4) the whole v1.1 — the last only by rule (outcome-space row 6, or the
  Phase 8 futility rule), never by fatigue.
- Budget caps per release are in
  [ADR-008](adr/adr-008-models-gpt5mini-primary-4omini-replication.md).
