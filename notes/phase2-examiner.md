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

Done 2026-09-29. Statement-level lexical scan on the twin pages: planted leaks
160 of 160 flagged; 1,286 of 33,719 questions flagged in 18 classes, all read
and resolved as coincidences, 0 discarded; S1-B1 at ×4 or ×0.25 (1,461) not
scannable. Unit level would have flagged 2,064.

## Splits and the template partition (`examiner/splits.py`)

Done 2026-09-29. Seven split files of opaque ids plus `manifest.json` in
`data/splits/`; 6,822 families, every split disjoint from every other (0
clashes); dev and train frozen. S1 group A allocated in proportion to material
pools (PI-018, absorbed); the eval-L1 extension for gate 8 is bounded at 57
extra per stratum.

## G3 audit — 60 stratified questions

## `docs/examiner.md` and the benchmark v0

---

## Lessons Learned

## Failed Attempts
