# Benchmark card — agentic-rag-pokedex v0

**Status: draft, not uploaded.** The pre-release `v0.3-examiner` ships the
files described here once the generator audit (G3) passes. This card is
written before the upload; the release log at the end is completed before it.

## What it is

Questions about a counterfactual twin of the PokéAPI world, built to measure
**sequential sufficiency detection**: at each retrieval step, whether the
evidence seen is enough to answer, to keep searching, or to abstain. Every
question comes with its gold answer, the facts the answer is derived from, and
for each fact the corpus units that state it — so the sufficiency of any set
of seen units is computable exactly, step by step, without a model or a human
grader.

Names are renamed into seeded pseudo-words (the twin), so a model's memory of
Pokémon cannot stand in for evidence. In an identity probe on the pages as
published, a model named the real species from 1 of 50 twin pages (E-003,
`experiments/registry.md`).

## Strata

| Stratum | What makes the evidence insufficient | Templates |
|---|---|---|
| S0 | Nothing: one unit answers (control) | S0-A1 … A4, S0-B1 |
| S1 | A missing hop (e.g., the anchor's own value is not the final form's) | S1-A1 … A3, S1-B1 |
| S2 | Another version's learnset gives a different answer | S2-A1, S2-A2, S2-B1 |
| S3 | A list longer than one tool call returns: only the whole list proves it complete | S3-A1, S3-B1 |
| S4 | The answer was removed from the corpus: the right action is to abstain | S4-A1, S4-B1 |

Group A templates are open to tuning; group B templates are held out
(`docs/examiner.md`, Partition).

## Files

`questions.jsonl`, one question per line, sorted by id:

| Field | Meaning |
|---|---|
| `id` | Opaque question id (`q-` + 10 hex) |
| `split` | `dev`, `train` or `pool` (unassigned) |
| `stratum`, `template`, `group` | As above |
| `surface` | Which of the template's three hand-written phrasings (0–2) |
| `question` | Question text, twin names |
| `expected` | `answer` or `abstain` |
| `answer`, `aliases` | Gold answer in twin names or numbers; sets and type pairs as lists sorted by name; damage factors with their written forms (`×0.5`, `x0.5`, `0.5`) |
| `withheld_value` | S4 only: the value the corpus does not contain |
| `material` | S1: whether the gold answer differs from the anchor's own value |
| `set_size` | S3: members of the gold set |
| `gold_facts` | Opaque fact ids the answer is derived from (S1 in chain order; S3: every row of the move's hub, since only the whole list proves the set complete) |
| `cover` | For each gold fact, the opaque ids of the indexed units that state it: a state is sufficient when every gold fact has a seen unit |
| `near_certain_units` | S2 and S4: units stating another version's answer |
| `withheld_units` | S4: the units removed from the corpus |

`manifest.json`: counts, seeds and the file's SHA-256. Split membership, with
evaluation splits by id only, is in `data/splits/`.

**Not included:** unit text, real names, the twin → real map, raw PokéAPI data
(`docs/data-sources.md`, "Published benchmark"). **Evaluation splits**
(eval-L1, its benign slice, val-B, eval-L2, eval-L3) are listed by id only;
their questions are published after each is opened, with the opening counts.

## Rebuilding the corpus

The corpus is rebuilt locally from the pinned PokéAPI commit, the twin seed
and this repository's code (`docs/world.md`). The opaque ids are sha256 of a
public seed and the local id, so the rebuilt corpus produces the same ids
(`examiner/benchmark.py`: `opaque_fact`, `opaque_unit`). The files alone do not
reveal PokéAPI ids; the seed is public, so the ids are not a secret from anyone
who runs the pipeline.

## Counts (v0)

31,370 questions: dev 150, train 150, pool 31,070 (S0 2,959; S1 13,740; S2
10,945; S3 1,450; S4 2,276). Held back: eval-L1 400, eval-L1-benign 40, val-B
60, eval-L2 280, eval-L3 150. Per-template counts and every filter's N-of-M are
in `docs/examiner.md`.

## Quality checks

- Sufficiency labeler: 100% on hand-built golden trajectories.
- Shortcut scan: 160 of 160 planted leaks flagged; 1,272 flagged questions,
  all resolved as coincidences. The scan cannot flag set (S3) or abstain (S4)
  answers.
- Every insufficiency subtype and error code reachable on dev (as states; a
  trajectory-level check under the tool contract follows).
- Export: no raw fact or unit id in any field; no real name in any question or
  answer.
- **Generator audit (G3):** pending — 60 stratified questions checked by hand
  against the games; the result is recorded here before upload.

## Known limitations

- **Rendered, templated text.** Pages are generated from structured data:
  clean, consistent, without the contradictions of real documents. Questions
  use three hand-written phrasings per template.
- **Species-level evolution.** The corpus keeps PokéAPI's species links, so a
  page may say a species evolves when only a regional form of it does
  (Corsola → Cursola). No question depends on such a link.
- **Version skew.** S2 questions lean toward Scarlet/Violet (49 of 80 in
  eval-L1), following the S2 pool (4,450 of its 11,127 questions).
- **Current values.** Move power, category and type are the current
  (Generation IX) values, whatever the question's era.
- **Unscannable answers.** 1,461 S1-B1 questions have a ×4 or ×0.25 answer that
  no page writes; the shortcut scan cannot check them.
- **Residual structure.** A model named one species from a twin page by its
  structure alone (a three-stage line with a Mega form).
- **Clustered questions.** S4 questions share withheld pairs and S3 questions
  share moves (eval-L1: 39 pairs, 21 moves); questions in a cluster are not
  independent.
- **List cues.** Hub units split at exactly 20 rows; a full unit hints that
  more follow (ADR-009, Updates).

## Intended use

Measuring whether retrieval agents stop, continue or abstain at the right
step; training and evaluating sufficiency detectors on group-A templates and
testing them on group B. Not a test of Pokémon knowledge.

## License and attribution

Unofficial, non-commercial fan project. Pokémon and all names are trademarks
of Nintendo, Creatures Inc. and GAME FREAK inc.; the published files carry twin
names only. Game data from PokéAPI (BSD-3-Clause). The generated files are
released under this repository's MIT license, for what this project creates.

## Release log

| Date | Version | Files and SHA-256 | Audit | Uploaded |
|---|---|---|---|---|
| — | v0 | filled before upload | G3 pending | no |
