# Phase 3 — Pilot, Typed Expansion First, and Preliminary Gates

**Objective.** Run what is cheap before any agent is tuned. E-002 measures how
much sufficient evidence the fixed pipeline with typed expansion already
delivers, per stratum, as a descriptive reading. The pilot measures noise,
cost and contamination; the measured cost fixes n_max. No difference between
arms is printed.

**Dates.** Opened 2026-10-06 · size S (3–5 partial working days, as an
estimate) · no calendar, no hard deadline.

**Ends with.** Tag `v0.4-pilot-gate` (no release): E-002 published as
descriptive with N-of-M per stratum; G2 closed-book half decided; n_max and
n_max_eff logged in the journal before any rehearsal; measured cost within
1.3× the estimate or the cut order applied; the trajectory-level check
published before dev is first used; a pilot report with noise, cost and rates
only.

---

## Carry-over: Phase 2 lessons and failed attempts

## Trajectory-level check under the tool contract (PI-021)

Done 2026-10-06 (`examiner/trajectories.py`), model-free, before dev was
first used; not an opening (journal 2026-10-06). Shortest `open_page` reading
per question: S0 and S2 one call; S1 two or three; S3 two to five, except one
dev cluster (4 questions, one move's hub) that takes 7 calls, beyond T_max.
No evaluation split has a question beyond T_max or B. Every S1 question could
be made sufficient by one lucky search (its chain is a few short Profiles);
no S3 question could. All 14 codes realized as `open_page` trajectories on
dev. A first exact search took about 4 minutes on one S3 question (every
learner's species page enters the cover); merging facts hit by the same
windows and bounding by the best window's coverage of the remaining facts
brought dev, train and every evaluation split to seconds.

## E-002 — typed expansion on dev (descriptive)

## Pilot on dev: A0, A1, A2 on 150; A3 on 30

## G2 closed-book half: A0 on the twin and on the real world

## Reasoning tokens per arm and the re-estimated budget

## Preliminary power table with the proxy SD

## n_max, n_max_eff and the benign S1 slice

---

## Lessons Learned

## Failed Attempts
