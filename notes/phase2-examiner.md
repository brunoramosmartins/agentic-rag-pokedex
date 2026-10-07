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

Filled by the author in `notes/phase1-world.md` during this phase.

## Templates per stratum and surface forms (`examiner/templates.py`, `surfaces.py`)

Done 2026-09-29. 16 templates, three hand-written surface forms each: S0 5,
S1 4, S2 3, S3 2, S4 2. Below the planned three to five: S4 (every question
rests on a withheld learnset), S3 (the hidden-ability holders template spans
two units in 24 sets only) and S1-A4 (dropped with PI-017). The B template of
each stratum is its most different shape.

## S1 material and benign

Done 2026-09-29 (PI-015). Material pools S1-A1 64, S1-A2 96, S1-A3 53; S1-B1
is material by construction (12,740). Benign questions form the descriptive
slice eval-L1-benign (40). PI-019 removed lines that pass an evolution only a
non-default form makes (8, 8 and 6 questions).

## Generator and filters (`examiner/generate.py`, `filters.py`)

Done 2026-09-29; regenerated after PI-019 and PI-020: 32,300 questions,
byte-identical across runs. The filters live in `generate.py`, not in a
separate `filters.py`, each with its N-of-M per template in `docs/examiner.md`
(Counts). Scope: every query filters `LEARNS.version_group`, with a test that
fails without the filter.

## Answer-concentration cap

Done 2026-09-29 (PI-012). Majority share per template before and after the
cap is in `docs/examiner.md` (Counts); the cap bit on S0-A2, S0-A4, S0-B1 and
S1-B1.

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
scannable. Unit level would have flagged 2,064. Rerun after PI-019: 160 of
160 planted, 1,272 of 32,300 flagged, 0 discarded.

## Splits and the template partition (`examiner/splits.py`)

Done 2026-09-29. Seven split files of opaque ids plus `manifest.json` in
`data/splits/`; 6,822 families, every split disjoint from every other (0
clashes); dev and train frozen. S1 group A allocated in proportion to material
pools (PI-018, absorbed); the eval-L1 extension for gate 8 is bounded at 57
extra per stratum. Rebuilt after PI-020 (S4 families by withheld pair):
6,425 families, 0 clashes; after PI-021 the extension stops at 32 extra per
stratum (pooled 448).

## G3 audit — 60 stratified questions

`examiner/audit.py`: `draw --round N` writes a local sheet (real names), 12
per stratum from outside the evaluation splits, one per family, S1 material;
`score --round N` reads the verdicts (pass: ≥ 58 of 60). Preparing round 1
surfaced PI-019 (S1 lines through form-only evolutions); round 1 was redrawn
after the fix, before the author opened it.

Round 1 scored 2026-10-06: 60 of 60 ok, 0 wrong, 0 unreadable → G3 passed
(≥ 58). No template needed a fix; no second round.

## `docs/examiner.md` and the benchmark v0

E-001 red-team 2026-09-30: 8 blocking, 11 caveats. PI-020 (S3 closure label,
one-call hubs dropped, S4 families by withheld pair) done and absorbed;
PI-021 (clusters, O2, gate 8 n_max_eff = 448, taxonomy, trap states, A × B)
written into E-001 as amendments, open for Phases 3–6.

Reachability done 2026-09-30: 13 of 13 codes reachable on dev, `format-error`
declared; 14 of 14 after S0 got its own subtype (PI-020) (`examiner/reachability.py`). Opening counts initialised at 0
(`data/splits/openings.json`, `splits.open_split`).

Benchmark v0 export (`examiner/benchmark.py`) and card (`docs/benchmark-card.md`)
done 2026-09-30, opaque ids for questions, facts and units. G3 result and
release log filled in the card 2026-10-06; the upload goes with the Phase 2
close.

---

## Lessons Learned

* **The benchmark needs semantic invariants, not only generation rules.** It was not enough to generate questions that matched the intended template. The questions also had to satisfy constraints about version groups, material, withheld units, gold coverage, split membership, and answer concentration. Making these invariants explicit and testable prevented local fixes from silently changing the benchmark definition.

* **Small semantic ambiguities propagate through the entire examiner.** PI-019 and PI-020 showed that a seemingly local interpretation can affect generation, labeling, reachability, auditability, and the resulting benchmark. In particular, the distinction between a form-specific evolution path and an ordinary evolution path had to be made explicit rather than inferred from the generated question.

* **The unit of independence must match the structure of the evidence.** The first shortcut scan at unit level was too coarse: it treated multiple statements inside the same unit as one signal and produced many false positives. The later analysis also showed that the independent information in eval-L1 is clustered: all S4 questions derive from 39 retained pairs, while S3 derives from 21 hubs. Counting questions as independent observations therefore overstates the effective sample size. PI-021 led to cluster-aware analysis, including a design effect and cluster bootstrap, rather than treating every question as an independent replicate.

* **The benchmark's semantics must be judged in the target world, not only in the source data.** PI-019 is the clearest example. The shortcut scan had already flagged the affected evolution cases, and they were initially classified as "world quirk, not a leak." That classification was reasonable for a leakage check, but wrong for the actual gold answer: under the game's standard-form criterion, only Galarian Corsola evolves. The problem was therefore not that the detector failed to find the cases; the benchmark lacked the correct semantic criterion for deciding whether the gold was correct.

* **A passing automated pipeline does not imply a valid benchmark.** Preparing G3 exposed PI-019 even though the automated generation and validation checks were already passing. The audit therefore serves a different purpose from unit tests: automated tests establish encoded invariants; human review challenges whether those invariants actually capture the intended semantics.

* **Refusal behavior is part of the specification.** The sufficiency labeler was made deliberately conservative: unknown, withheld, or contradictory states are refused rather than assigned a best-effort label. This makes benchmark errors visible instead of turning uncertainty in the examiner into apparently clean training data.

* **Negative controls are necessary to validate the leakage detector itself.** The planted-leak experiment gave a concrete target for the shortcut scan: 160/160 planted leaks were detected. Without planted failures, a zero-flagged result would be difficult to interpret because it could mean either that the benchmark is clean or that the detector is ineffective.

* **Freeze points reduce moving-target problems.** Regenerating the questions and rebuilding the splits after PI-019 and PI-020 was necessary, and explicit freeze points made it possible to distinguish benchmark changes from later analytical changes. PI-021 changed the interpretation of the red-team findings and the gate-8 extension rather than regenerating the question set. The benchmark population and its partitions therefore need to be versioned independently from later statistical analysis.

* **Audit design matters as much as audit size.** G3 was stratified, sampled outside the evaluation splits, and constrained to one question per family. The audit set also remains valid after a fix when the fix does not change the gold answers. In this case, PI-020 occurred after round 1 was drawn, but the round remained valid because the gold answers were unchanged.

* **Information leakage can survive opaque identifiers.** The benchmark export initially preserved structure through ordering: the row order followed National Pokédex order, and the S3 gold-fact ordering exposed PokéAPI ids. Opaque ids therefore did not by themselves make the exported benchmark opaque. Structure and ordering are part of the leakage surface and must be checked explicitly.

* **The gold chain is not an independent audit source.** The gold chain and gold answer are produced by the same underlying pipeline, so agreement between them does not constitute an independent validation of correctness. For G3, the human audit therefore scores the answer itself rather than using the gold chain as a second source of truth.

* **Template count is not a quality objective by itself.** Several strata ended below the planned three-to-five templates. The resulting benchmark is stronger after removing constructions that cannot satisfy the intended constraints than it would be with additional templates retained simply to meet a numeric target.

## Failed Attempts

* **The pre-evolution template was not viable.** S1-A4 was dropped after PI-017 made explicit a structural impossibility already present in the design: the father's Profile cites the child and contains the answer, so one unit is sufficient to answer the question. The single-unit shortcut filter therefore rejects the construction by design. PI-017 did not create the impossibility; it exposed it.

* **The initial S3 sufficiency construction was incomplete.** A state that had already seen all members of the gold set was labeled *sufficient* even when there was no evidence that the observed list was complete. The fix was to define the gold around the full hub and require the closure information needed to establish completeness. Hubs that fit entirely within one `open_page` call were then dropped because they cannot exercise the intended truncation/closure behavior.

* **The first shortcut scan used the wrong granularity.** The original scan was performed at unit level. This was too coarse because a single Profile could contain the anchor in one statement ("Evolves into") and the hidden ability in another. The scan therefore merged two different facts into one unit-level overlap and produced a large number of false positives: 2,064 unit-level flags versus 1,286 statement-level flags. The statement-level scan was retained as the more useful detector for this failure mode.

* **The S1 evolution gold was initially wrong.** The affected questions had already been flagged by the shortcut scan and initially classified as legitimate world quirks rather than leaks. The actual failure was the gold criterion: in the game, only Galarian Corsola evolves, whereas the generated gold treated the broader source-data relation as valid. PI-019 removed the affected questions and forced the benchmark to evaluate the game semantics rather than the source-data relationship.

* **The initial S4 family definition allowed the same dependency to cross splits.** Before PI-020, the family construction did not define the withheld pair as the grouping boundary. The pair **(442, SV)** consequently appeared in two different splits. S4 families were rebuilt around withheld pairs, after which the split families were disjoint.

* **The first G3 round exposed a benchmark issue before scoring.** Preparing round 1 surfaced PI-019, so the round was redrawn after the gold was corrected. The important rule is not that an audit must only be drawn after every possible fix, but that a drawn round remains valid only while subsequent fixes do not change its gold answers.

* **Question count was initially treated too literally in the evaluation analysis.** The eval-L1 extension appeared to provide hundreds of additional questions, but the information was heavily clustered: S4 collapsed onto 39 retained pairs and S3 onto 21 hubs. Treating the raw question count as the effective sample size gave an overly optimistic view of statistical power. PI-021 added the cluster-aware correction.

* **The export still leaked structure despite opaque ids.** Replacing names with opaque ids was not sufficient because ordering itself carried information. The benchmark therefore had to treat row order and gold-fact order as potential side channels rather than assuming that anonymization removed them.

* **The benchmark's gold chain could not serve as an independent correctness check.** Because it was generated by the same pipeline as the gold answer, a disagreement-free comparison between the two would only demonstrate internal consistency. It could not establish that the underlying answer was correct.


