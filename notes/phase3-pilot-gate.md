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

2026-10-07, before the run. Amendment: link-type order `evolves-into >
ability > type > move > learner > holder`, the S3 reading under the closure
label. Red-team: 6 blocking, 6 caveats, all taken. The two that changed data:
the BM25 tokenizer kept "Kedros's" as one token, so search missed the anchor
of possessive questions (0 of 59 pool S0-A1 in that form; 55 of 59 after the
fix; train 133 of 150 anchors found after it) — PI-023; and the pipeline as
first written could never complete a list, so level 0 (complete each hit's
section) was added. Hand-traced golden expansion on the fixture world: 13
results, 597 tokens, 12 calls. Smoke runs on train only; dev untouched.

Run on dev 2026-10-07, commit `29453ac`: S0 29, S1 23, S2 28, S3 9 of 30 at
k = 5; S4 0 by construction. Search alone carries S0 and S2; S1 completes at
link level 1; S3 only through section completion of the asked hub, which
search often misses for another move's hub in the same version. B binds in
150 of 150. Actual result in the registry; PI-023 resolved (absorbed).

## Pilot on dev: A0, A1, A2 on 150; A3 on 30

E-004 registered 2026-10-07 with E-005 (journal). Prompts v0 approved by the
author: `answer_closed_book_v0`, `answer_with_evidence_v0`, `agent_v0`, the
cost and format paragraphs verbatim in all three; none says the world is
fictional or hints that a list may be incomplete. Grader moved to this phase
(PI-024): `evaluation/grader.py`, exact match by answer kind, structured
abstention, C = 0 / 1 / λ (an S4 abstention is correct and still costs 1);
33 golden completions.

Arms and runners built 2026-10-07: `arms/single.py`, `arms/agent.py` (one
Batch round per step), `evaluation/batchrun.py`, `evaluation/pilot.py`,
`evaluation/closed_book.py`. Smoke on train: three rounds, no failure, cost
US$ 0.009 (estimate 0.033); reasoning medians 32–96 tokens a call against the
600 assumed. A1 and A2 answered the gold wherever the evidence was
sufficient and abstained where search missed the anchor ("Name the hidden
ability of {X}" returned other abilities' Holders units).

E-004 run on dev 2026-10-08 (prediction committed first): 589 calls, US$ 0.191
(estimate 0.49), reasoning medians 0–128 a call. A3: 3.6 steps on average,
28 of 30 search again, all 8 S3 questions at T_max, B never spent. A0
abstained on all 150 twin questions. SD of D waits for the grader's audit.

## G2 closed-book half: A0 on the twin and on the real world

E-005 run 2026-10-08 (1,600 calls, US$ 0.280). Verdict 2026-11-14, after the
grader's audit: **G2 passes** — twin 0 of 50 in 15 of 16 templates (2 of 50 in
S0-B1, chance 38%); real-name control 4 of 4. Grader audit: round 1 97 of 100
(level answers written with the word "level" graded wrong; fixed), round 2 on
a fresh sample 100 of 100. In round 1's first pass the author judged the
model rather than the grader on 30 items; corrected before scoring.

## Reasoning tokens per arm and the re-estimated budget

`evaluation/budget.py`: US$ 0.73 spent, 10.95 projected with a 1.5× margin
after the three cuts, 11.69 committed of 20 (about 14.1 with no cut).
Measured cost 0.39× (E-004) and 0.26× (E-005) the estimates.

## Preliminary power table with the proxy SD

Proxy SD of D = C(A1) − C(A3) = 2.09 (80%: 1.81–2.32; 30 questions, 20
discordant). n\* = 339 at 2.09 and 418 at 2.32, above the plan of 320.

## n_max, n_max_eff and the benign S1 slice

n_max = 884; n_max_eff = 448 (material S1 binds, not money); logged
2026-11-14 before any rehearsal. Benign S1 slice stays at 40.

---

## Lessons Learned

## Failed Attempts
