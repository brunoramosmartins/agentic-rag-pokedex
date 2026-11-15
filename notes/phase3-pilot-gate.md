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

- **Validate evaluation constraints before running model-based experiments.** The trajectory-level check (PI-021) confirmed that no question in the evaluation splits exceeded T_max or B. S0 and S2 required one open_page call each. S1 could, optimistically, be made sufficient by one search if the ranking cooperated, although reading its pages required two or three calls. S3 always required several calls, ranging from two to five in the evaluation splits. This distinction established an important structural difference between questions that could be solved through a lucky search and those requiring multi-step evidence gathering.

- **Search coverage and evidence sufficiency are not the same.** E-002 showed that search alone was sufficient for S0 and S2, while S1 required link-level expansion and S3 required section completion of the asked hub. On dev, the pipeline returned sufficient evidence for 29/30 S0, 23/30 S1, 28/30 S2 and 9/30 S3 questions at k = 5. S4 remained zero by construction. These results establish a descriptive baseline for the fixed pipeline with typed expansion, without attributing the observed coverage to agent behavior.

- **Expansion must support complete answers, not just additional retrieval.** The initial expansion pipeline could retrieve relevant sections but could not reliably complete list-type answers. Adding level 0 (completing each hit's section) addressed this limitation. The fixture-world golden trace provided a controlled check of the resulting behavior: 13 results, 597 tokens and 12 calls.

- **Bound an exact search by what it can still cover.** The trajectory check's exact search, which calculated the minimum number of calls required to reach a sufficient state, initially took approximately four minutes on one S3 question. Every learner's species page entered the cover, making the search unnecessarily expensive. Merging facts reached by the same windows and bounding the search by the best window's coverage of the remaining facts reduced execution time to seconds across dev, train and every evaluation split.

- **Typed expansion provides a useful descriptive baseline before agent tuning.** E-002 established how much evidence the fixed pipeline could recover at each stratum. Its results also exposed a specific limitation in S3: section completion could provide sufficient evidence for the asked hub, but search often missed another move's hub within the same version. This identifies a retrieval-coverage limitation to account for in subsequent phases, rather than evidence that the agent itself needs tuning.

- **Anchor retrieval is a critical dependency for downstream reasoning.** In the train smoke run (10 questions), A1 and A2 answered with the gold wherever the evidence was sufficient and abstained when search missed the anchor. This was particularly visible in questions asking for a hidden ability, where retrieval returned other abilities' Holder units instead. The observation suggests that answer generation does not recover what retrieval missed; E-004's graded readings by arm were not read.

- **Pilot cost estimates should be replaced by measured consumption before setting the experimental sample size.** E-004 cost 0.39× its estimate and E-005 cost 0.26×. Reasoning-token medians were also substantially below the assumed 600 tokens per call. The budget projection was recalculated using observed consumption: US$ 0.73 spent, US$ 10.95 projected with a 1.5× margin after the three cuts, and US$ 11.69 committed out of US$ 20. Without the cuts, the projection would have been approximately US$ 14.1. The measured costs remained comfortably within the 1.3× threshold.

- **The binding constraint for sample size may be operational rather than financial.** The resulting limits were n_max = 884 and n_max_eff = 448, with material S1 determining the effective limit rather than the budget. Both values were recorded in the journal on 2026-11-14 before any rehearsal. The benign S1 slice therefore remains at 40. The preliminary power calculation also indicated that the planned 320 questions were below the proxy-based requirement: with SD(D) = 2.09, n* was 339, increasing to 418 at the upper proxy estimate of 2.32. This remains a preliminary estimate based on the proxy SD, not a final power determination.

- **Grader validation is part of experimental validity, not merely a final quality check.** The first audit round scored 97/100 because valid level answers written with the word "level" before the number (e.g., "level 28" or "Level 37") were incorrectly marked wrong. After correcting the grading logic, a fresh sample achieved 100/100. The corrected audit result supports using the grader for subsequent evaluation.

- **Closed-book controls require both a fictional-world test and a real-name control.** G2 passed: A0 answered 0 of 50 twin questions correctly in 15 of 16 templates. The remaining S0-B1 template returned 2/50 (4%), well below its chance rate of 38%. The real-name control passed in 4 of 4 S0-A templates. In the E-004 dev pilot, A0 also abstained on all 150 twin questions, as expected for the closed-book contamination control. These results support the intended control behavior under the tested conditions.

- **The agent's operational limit on S3 was the step cap, not the evidence budget.** A3 averaged 3.6 steps per question, and 28/30 questions triggered another search. All eight S3 questions reached T_max, while B was never spent. This indicates that the step cap, rather than the evidence budget, was the observed binding limit for the list-heavy S3 questions. These are operational pilot observations, not grounds for agent tuning in this phase.

- **Pilot reporting must remain descriptive.** The purpose of this phase is to characterize noise, cost, retrieval coverage and operational rates before agent tuning. These observations do not establish a performance difference between arms. The pilot report should therefore present rates and measured costs without comparative arm claims.


## Failed Attempts

- **Possessive anchors were not retrieved by the initial BM25 tokenizer.** The tokenizer treated "Kedros's" as a single token, causing possessive questions to miss their search anchor. In the S0-A1 pool, only 0/59 anchors were found in this form. After the tokenizer correction, retrieval increased to 55/59; train retrieval reached 133/150. This issue was documented as PI-023 and subsequently resolved.

- **The initial typed-expansion pipeline could not complete list-type answers.** Retrieving individual hits and following their links was insufficient when the expected answer required a complete list from a section. Level 0 section completion was added to address this failure. The change was checked through a golden expansion trace before the dev run.

- **The trajectory check's exact search was initially too slow.** The first implementation took approximately four minutes on one S3 question because every learner's species page entered the cover. The search was calculating the minimum number of calls needed to reach a sufficient state, not performing the evidence expansion itself. Merging facts reached by the same windows and bounding the search using the best window's coverage of the remaining facts reduced execution time to seconds.

- **The first grader audit exposed a formatting-sensitive classification error.** Valid answers were incorrectly marked wrong when they included the word "level" before the number (e.g., "level 28" or "Level 37"). The grading logic was corrected, and a fresh sample was used to verify the correction. The initial 97/100 audit result was superseded by the second round, which achieved 100/100.

- **Manual judgment initially contaminated the first grading audit pass.** In the first pass of audit round 1, the author judged the model's answer when the task was to judge whether the grader's verdict was correct. This happened on 30 items and was corrected before scoring. The audit instruction was ambiguous to the person performing it. This reinforced the need to state exactly what an audit judges, with a worked example, before it starts.

- **The first attempts to save the E-004 and E-005 predictions did not produce registry changes.** Both attempts returned "nothing to commit", meaning the prediction artifacts had not yet been saved in the registry. The respective rounds waited until the predictions were committed before proceeding. This exposed the need to verify that prediction artifacts are actually registered before running or finalizing an evaluation.
