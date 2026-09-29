# Phase 2 — The Examiner: Generator, Gold Chains & Step Labels

**Objective.** Turn the graph into the examiner: templates per stratum,
questions with gold answers, gold chains and every minimal sufficient set;
filters with published N-of-M counts; the per-step sufficiency labeler; seeded
splits. Pass G3 with a human audit.

**Dates.** Opened 2026-09-29 · size L (9–12 partial working days, as an
estimate) · no calendar, no hard deadline.

**Ends with.** Tag `v0.3-examiner` (**pre-release**: the benchmark v0): G3
passed (≥ 58 of 60), labeler 100% on golden trajectories, shortcut scan 100% on
planted leaks, dev and train ids frozen, `docs/examiner.md` published.

---

## Carry-over: Phase 1 lessons and failed attempts

## Templates per stratum and surface forms (`examiner/templates.py`, `surfaces.py`)

## S1 material and benign

## Generator and filters (`examiner/generate.py`, `filters.py`)

## Answer-concentration cap

## Sufficiency labeler and golden trajectories (`labeling/sufficiency.py`)

Done 2026-09-29. The label of a state is coverage of every gold fact by the
units seen, computed from the registry for each question; the labeler refuses
unknown or withheld units and questions whose covers contradict their stratum.
Each state also reports the gold facts still missing, the near-certain units
seen (S2, S4) and, for S3, the members covered. The generator now records the
distractor facts and near-certain units of S2 and S4, and the withheld units
of S4. Golden trajectories: 9 hand-labelled on the fixture world plus 6
refusals (`tests/fixtures/golden_trajectories.json`).

## Shortcut scan with planted leaks

## Splits and the template partition (`examiner/splits.py`)

## G3 audit — 60 stratified questions

## `docs/examiner.md` and the benchmark v0

---

## Lessons Learned

## Failed Attempts
