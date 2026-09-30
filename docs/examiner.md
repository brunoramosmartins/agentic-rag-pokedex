# The Examiner

The golden set is software: questions, gold answers, gold chains and step-level
sufficiency labels are generated from the Neo4j graph (ADR-007) and the fact →
units registry (`docs/world.md`). This document is the specification, written
before the generator; the counts sections are filled as the filters run.

**Status:** specification and first generation (Phase 2, 2026-09-29).

## Principles

- **The stratum is invisible in the question.** S4 questions use the same
  surface forms as the S2 questions they mirror; nothing in the wording says
  whether an answer exists.
- **Every template is version-scoped.** Any `LEARNS` pattern filters
  `version_group` to the scope (x-y, ultra-sun-ultra-moon, scarlet-violet). A
  negative test removes the filter and must fail (PI-016).
- **Filters publish N-of-M**, per template and stratum, in this document.
- **Answers are twin names or numbers**, with aliases only from the twin map.

## Templates

Group A templates are visible to all tuning; group B templates are held out
(`docs/hypothesis.md`). IDs are stable.

### S0 — one hop, sufficient (control)

| ID | Question | Answer | Pool (world) |
|---|---|---|---:|
| S0-A1 | Hidden ability of species X | an ability | 856 (species that have one) |
| S0-A2 | Base power of move M | a number | 546 |
| S0-A3 | Category of move M | physical / special / status | 833 |
| S0-A4 | Type of move M | a type | 833 |
| S0-B1 | Damage factor of attacking type A against defending type B | ×0 / ×0.5 / ×1 / ×2 | 324 |

### S1 — missing hop (version-free)

| ID | Question | Hop that must be taken | Anchors | Material |
|---|---|---|---:|---:|
| S1-A1 | Hidden ability of the final form of X's evolution line | X → final form | 397 | 64 |
| S1-A2 | Types of the final form of X's evolution line | X → final form | 426 | 96 |
| S1-A3 | Hidden ability of the species X evolves into | X → next form | 399 | 53 |
| S1-B1 | Type damage multiplier of move M against species X | M → its type; X → its types; the type chart | many | all |

- **Anchor answer:** the same attribute read on X itself (X's hidden ability,
  X's types). A question is **material** when the gold answer differs from the
  anchor answer, and **benign** when they coincide.
- **Material S1** forms S1 in the H1 pool; **benign S1** is a descriptive
  slice (40 questions in eval-L1, run by A3, A4 and A4p only; PI-015). S1-B1 is
  material by construction: no single fact gives the multiplier.
- S1 avoids version-scoped relations on purpose: a hop through a learnset would
  mix a wrong-version trap into a missing-hop question.
- **Profiles link forward only** ("Evolves into", or "—" for a final form,
  itself a registered fact). With the whole evolution line on every Profile,
  the final form's Profile held both the anchor and the answer, and the
  single-unit shortcut filter discarded every evolution-based S1 question
  (PI-017). With forward links, all 397 S1-A1 anchors need at least two units.
  A pre-evolution template is impossible in any design — the parent's Profile
  names X and holds the answer — so it was dropped.
- **Only evolutions the default form makes are hops (PI-019).** PokéAPI links
  evolutions per species, but `pokemon_evolution.csv` names the form that
  must evolve (`required_pokemon_form_id`). Six single-child evolutions need a
  regional or variant form — Cursola (Galarian Corsola), Sirfetch'd, Mr. Rime,
  Obstagoon, Overqwil (Hisuian Qwilfish), Basculegion (white-striped
  Basculin) — so "the final form of Corsola's line" is Cursola in the graph and
  nothing in the game, where Corsola as its Profile shows it does not evolve.
  A line through such an evolution is dropped (22 questions, 18 of them
  material). The corpus keeps PokéAPI's species link ("Evolves into:
  [[Cursola]]"): a declared simplification no question depends on.
- S1-B1 multiplies type factors only (abilities that change effectiveness are
  outside the question): ×0, ×0.25, ×0.5, ×1, ×2, ×4.

### S2 — wrong version

| ID | Question | Distractor that must exist | Pool |
|---|---|---|---:|
| S2-A1 | Level at which X learns M by level-up in V | M in X's level-up learnset of another scope group, at a different level | ~8,300 pairs |
| S2-A2 | Move X learns at level L in V | another scope group lists a different move at level L | 2,893 |
| S2-B1 | Last move X learns by level-up in V | another scope group's last move differs | to count |

### S3 — truncated set

| ID | Question | Pool |
|---|---|---:|
| S3-A1 | Species of type T that learn M by level-up in V | 1,961 (see Counts) |
| S3-B1 | Species of type T that learn M by level-up in V at or below level L | to count |

- The gold set has 3–25 members **and is spread over at least two indexed
  units**: a set that one hub unit holds entirely is not truncated (2,115 such
  sets dropped). An early estimate of 323 excluded every hub touching a
  withheld species; the rule is narrower — only sets whose *members* include
  one (PI-016) — and leaves 1,961.
- "Of type T" means T is one of the species' types.
- A hidden-ability holders template was dropped: 24 sets spread over two
  units.

### S4 — no answer in the corpus

| ID | Question (surface forms of) | Withheld evidence | Pool |
|---|---|---|---:|
| S4-A1 | S2-A1: level at which X learns M in V | X's level-up learnset in V (one of 120 withheld pairs); M is in X's level-up learnset of another scope group | 1,926 |
| S4-B1 | S2-A2: move X learns at level L in V | same | to count |

- Two templates, not three to five: every S4 question rests on a withheld
  learnset, and a third shape would be artificial. The correct action is to
  abstain.
- Within a split, questions come from distinct withheld pairs where possible.

### Partition

| Stratum | Group A | Group B |
|---|---|---|
| S0 | S0-A1 … S0-A4 | S0-B1 |
| S1 | S1-A1 … S1-A3 | S1-B1 |
| S2 | S2-A1, S2-A2 | S2-B1 |
| S3 | S3-A1 | S3-B1 |
| S4 | S4-A1 | S4-B1 |

The B template of each stratum is its most different shape, so the A × B gap
measures generalization rather than a paraphrase.

## Surface forms

Three per template, hand-written (no LLM paraphrase in v1). Placeholders are
filled with twin names in the twin population and real names in eval-L3.
`{TERM}` is the world's word for "Pokémon", the same in singular and plural
(as "Pokémon" is).

| ID | Surface forms |
|---|---|
| S0-A1 | What is {X}'s hidden ability? · Which ability does {X} have as its hidden ability? · Name the hidden ability of {X}. |
| S0-A2 | What is the base power of {M}? · How much power does the move {M} have? · What power does {M} have? |
| S0-A3 | Is {M} a physical, special or status move? · What damage category does {M} belong to? · Which category is the move {M}: physical, special or status? |
| S0-A4 | What type is the move {M}? · Which type does {M} belong to? · {M} is a move of which type? |
| S0-B1 | How effective is a {A}-type attack against a {B}-type target? · What damage multiplier does {A} deal to {B}? · Against a {B}-type defender, how effective is a {A}-type attack? |
| S1-A1 | What is the hidden ability of the final form of {X}'s evolution line? · {X} eventually reaches a final evolution. What is that form's hidden ability? · Which hidden ability does the last evolution of {X} have? |
| S1-A2 | What types does the final form of {X}'s evolution line have? · {X} eventually reaches a final evolution. What are its types? · Which types does the last evolution of {X} have? |
| S1-A3 | What is the hidden ability of the species {X} evolves into? · {X} evolves into another species. What is that species' hidden ability? · Which hidden ability does {X}'s evolution have? |
| S1-B1 | How effective is {M} against {X}? · If {M} hits {X}, what is its type damage multiplier? · What type-effectiveness multiplier does {M} get against {X}? |
| S2-A1, S4-A1 | At what level does {X} learn {M} in {V}? · In {V}, at which level does {X} learn {M}? · {X} learns {M} by leveling up in {V}. At what level? |
| S2-A2, S4-B1 | Which move does {X} learn at level {L} in {V}? · In {V}, what move does {X} learn upon reaching level {L}? · Name the move {X} learns at level {L} in {V}. |
| S2-B1 | What is the last move {X} learns by leveling up in {V}? · In {V}, which move does {X} learn at the highest level? · Which level-up move does {X} learn last in {V}? |
| S3-A1 | Which {T}-type {TERM} learn {M} by leveling up in {V}? · List every {T}-type {TERM} that learns {M} by level-up in {V}. · In {V}, which {TERM} of type {T} learn {M} by leveling up? |
| S3-B1 | Which {T}-type {TERM} learn {M} by leveling up in {V} at or below level {L}? · List every {T}-type {TERM} that learns {M} by level {L} or earlier in {V}. · In {V}, which {TERM} of type {T} learn {M} by leveling up no later than level {L}? |

## Filters

Applied in this order; each publishes N-of-M per template.

1. **Scope.** Every learnset fact is in a scope group (negative test).
2. **World constraints (PI-016).** Hidden-ability templates sample species
   that have one; level 0 ("on evolution") and pairs listed at several levels
   are not answers; branching lines have no single final form (S1-A1, S1-A2
   excluded there; S1-A3 needs a single next form); non-default forms are never
   anchors or answers; S3 avoids hubs whose gold set includes a withheld
   species; S1 lines never pass an evolution only a non-default form makes
   (PI-019).
3. **Ambiguity.** The answer is unique (one level, one move at level L, one
   final form, one last move).
4. **Stratum conditions.** S1 material/benign tag; S2 distractor present;
   S3 size 3–25 and spread over ≥ 2 units; S4 answer fact only in withheld
   units and a plausible distractor present.
5. **Single-unit shortcut** (MuSiQue): for S1 and S3, if one indexed unit
   covers every gold fact, the question is discarded — it is not multi-hop.
   S0 is one unit by design, and S2 is one fact by nature: its difficulty is
   the wrong-version distractor, not a hop.
6. **Answer concentration (PI-012).** Each template's majority-answer rate is
   at most max(10%, 1.5 × uniform chance); the answer distribution before and
   after the cap is published.
7. **Shortcut scan** (gate 7): a statement naming every anchor together with
   the answer outside the gold units flags the question; flags are inspected
   and resolved by class. Validated first on planted leaks, in every run. See
   "Shortcut scan" below.

## The question record

Published fields carry opaque ids (`q-`, `f-`, `u-`; `docs/benchmark-card.md`);
evaluation splits are published by id only until opened.

| Field | Published | Notes |
|---|---|---|
| `id`, `stratum`, `template`, `surface` | yes | |
| `question` (twin text) | yes | real text only in eval-L3, local |
| `answer`, `aliases` | yes | twin names or numbers; sets sorted |
| `gold_facts` | yes | fact ids |
| `cover` | yes | for each gold fact, the indexed units that state it |
| `distractor_facts` | yes | S2, S4: the same question answered by another version group |
| `near_certain_units` | yes | S2, S4: indexed units stating a distractor fact |
| `withheld_units` | yes | S4: the withheld units stating the gold facts |
| `set_size` | yes | S3 |
| `material` | yes | S1: material or benign |
| `majority_share` | yes | per template, not per question |

## The sufficiency label

A state is the set of unit ids seen so far. It is **sufficient** when every
gold fact is stated by at least one seen unit — equivalently, when the seen
units cover at least one minimal sufficient set (fixed 2026-09-26). Covers are
computed on indexed units only, so an S4 state is never sufficient.

Insufficient states carry the question's subtype: `missing-hop` (S0, S1),
`wrong-version` (S2), `truncated` (S3), `nonexistent` (S4). The labeler is a
pure function over the registry, tested against hand-built golden trajectories
(100% required, gate 7).

**Labeler** (`labeling/sufficiency.py`). A trajectory is the list of unit ids
each observation showed (`ToolResult.unit_ids`); the state after step t is the
union of steps 1…t, and step 0 is the state before any tool call. Each state's
label records:

| Field | Meaning |
|---|---|
| `state`, `subtype` | `sufficient`, or `insufficient` with the stratum's subtype |
| `missing` | gold facts no seen unit states, in gold-fact order |
| `covered` / `total` | gold facts stated by a seen unit, of all gold facts |
| `near_certain` | near-certain units seen so far (S2, S4): reported, never part of the label |
| `members` | S3: set members whose facts are all seen, of the set size |

The label at the final action is `abstained` when the agent abstains, and the
state's label otherwise. Covers are recomputed from the registry for every
question, never read from its record. The labeler refuses, rather than labels:

- a seen unit the registry does not know (a logging fault);
- a seen withheld unit (the index must never serve one);
- a question outside S4 with a gold fact no indexed unit states, or an S4
  question with a gold fact an indexed unit states;
- a gold or distractor fact the registry does not know.

Adding units never removes a covered fact, so labels are monotone along a
trajectory: once sufficient, a state stays sufficient.

Golden trajectories (`tests/fixtures/golden_trajectories.json`) run on the
fixture world; every expected label is written by hand from the rendered
units. They cover every stratum and subtype, a fact with two copies, an empty
step and a repeated unit, the S1 state that holds the right answer before the
line is known to end (a lucky stop if answered), a move hub stating a
defender's type, the S2 distractor seen before the gold unit, an S3 set
arriving member by member, an S4 state that never becomes sufficient, and one
case per refusal.

Inspect a trajectory by hand on the generated questions:

```bash
python -m agentic_pokedex.labeling.sufficiency <question id> "<unit>,<unit>" "<unit>"
```

## Splits

`python -m agentic_pokedex.examiner.splits` (`examiner/splits.py`). Ids and
seeds only are versioned (`data/splits/`): one file of opaque ids per split,
in draw order, and `manifest.json` with the seed, the allocation, each file's
hash and each split's distributions. Seed `20260929`.

| Split | Size | Templates | Frozen | Opening |
|---|---|---|---|---|
| `dev` | 150 (30 per stratum) | group A | now | free |
| `train` | 150 real-trajectory questions (30 per stratum); the pool of simulated states is the group-A families left once eval-L1 is frozen | group A | now | free |
| `eval-L1` | 400 (80 per stratum) | A and B | dress rehearsal | once |
| `eval-L1-benign` | 40 benign S1 (A3, A4, A4p only; PI-015) | S1-A1 to A3 | dress rehearsal | with eval-L1 |
| `val-B` | 60 (12 per stratum) | group B | dress rehearsal | once |
| `eval-L2` | 280 (S0 40; S1–S4 60) | A and B | dress rehearsal | once |
| `eval-L3` | 150 (30 per stratum), asked in twin and real names | A and B | dress rehearsal | once |

**Separation.** Questions sharing a (template, anchor entity) pair or an
identical gold chain form a **family**; a family belongs to one split. The
anchor entity is the species X, the move M (S0-A2 to A4, S3) or the type pair
(S0-B1). Identical chains join S2-A1 with S2-A2 and S4-A1 with S4-B1, the same
learn fact asked two ways. 33,697 questions form 6,800 families. Every split is
disjoint from every other, which is stricter than the registered rule (dev and
train against eval-L1): eval-L2 and eval-L3 stay independent too. The
splitter counts clashes per split; all are 0 of n.

**Sizes.** Each stratum's size is split evenly across its templates by
largest remainder, group A first (S2 in eval-L1: 27 / 27 / 26; S0 in dev:
8 / 8 / 7 / 7). In S1, the group-A share is then split across S1-A1 to A3 in
proportion to their material pools, 64 / 96 / 53 (PI-018, PI-019): equal
shares do not fit S1-A3 (53 material questions against 63 demanded). S1-B1
keeps its even
share, so the A/B proportion does not change.

| Split | S1-A1 | S1-A2 | S1-A3 | S1-B1 |
|---|---:|---:|---:|---:|
| dev, train | 9 | 14 | 7 | — |
| eval-L1 | 18 | 27 | 15 | 20 |
| eval-L2 | 14 | 20 | 11 | 15 |
| eval-L3 | 7 | 10 | 6 | 7 |

Material questions used: S1-A1 57 of 64, S1-A2 85 of 96, S1-A3 46 of 53.

**Draw.** Per template, a seeded permutation of its families; each pass takes
at most one question per family, so a split covers as many anchors as it can
before repeating one. S4 has 121 families (withheld pairs) for 242 questions
demanded, so each split may claim families in proportion to its demand
(eval-L1: 40 pairs for 80 questions); every other pool has more families than
questions. S1 is material in every split except `eval-L1-benign`. Questions
the shortcut scan discarded never enter, and the splitter refuses to run while
any is unresolved.

**Gate 8 extension.** `--eval-l1-extra N` adds N questions per stratum to
eval-L1, drawn after every other split: the other splits and the first 400
eval-L1 questions do not change. Material S1 caps it at N = 32 (112 per
stratum, a pooled S1–S4 n of 448); at N = 33 S1-A1 runs out. (Before PI-019
the cap was N = 57, a pooled n of 548.)

**Ids.** `q-` + the first 10 hex digits of sha256(`20260929:{question id}`).
The seed is public, so anyone running the splitter can map them back; the
point is to keep PokéAPI ids — which map twin names to real ones — out of
published files. The mapping is written locally
(`data/world/examiner/splits.json`).

**Freezing.** Rewriting `dev.txt` or `train.txt` with different ids fails.
Evaluation ids are frozen at the dress rehearsal, after gate 8 sets eval-L1's
size.

**Openings.** `data/splits/openings.json` counts each evaluation split's
openings, all 0 now. `splits.open_split` is the only reader of an evaluation
split's ids: it logs the date and purpose of every opening and refuses a
second one unless asked to reopen, which is counted too. An opened split can
no longer be redrawn or extended. The counts are published with the results.

Distributions, first draw (`manifest.json`): S2 versions in eval-L1 are
scarlet-violet 49, x-y 17, ultra-sun-ultra-moon 14, following the S2 pool
(4,450 / 3,323 / 3,354 questions); S3 set sizes 3–20, median 4; S4 covers 40
withheld pairs.

## Counts

Generated 2026-09-29 (`python -m agentic_pokedex.examiner.generate`; the
question file is byte-identical across runs; regenerated the same day after
PI-019). **33,697 questions** before splitting.

| Template | Candidates | After filters | Kept (after cap) | Majority before → after | S1 material / benign |
|---|---:|---:|---:|---|---|
| S0-A1 | 856 | 856 | 856 | 3% → 3% (cap 10%) |  |
| S0-A2 | 546 | 546 | 527 | 13% → 10% (cap 10%) |  |
| S0-A3 | 833 | 833 | 833 | 40% → 40% (cap 50%) |  |
| S0-A4 | 833 | 833 | 713 | 23% → 10% (cap 10%) |  |
| S0-B1 | 324 | 324 | 192 | 63% → 38% (cap 38%) |  |
| S1-A1 | 434 | 397 | 397 | 3% → 3% (cap 10%) | 64 / 333 |
| S1-A2 | 434 | 426 | 426 | 6% → 6% (cap 10%) | 96 / 330 |
| S1-A3 | 438 | 399 | 399 | 3% → 3% (cap 10%) | 53 / 346 |
| S1-B1 | 41,000 | 41,000 | 12,740 | 57% → 25% (cap 25%) | 12,740 / 0 |
| S2-A1 | 28,443 | 7,897 | 7,897 | 4% → 4% (cap 10%) |  |
| S2-A2 | 24,618 | 2,893 | 2,893 | 1% → 1% (cap 10%) |  |
| S2-B1 | 2,141 | 337 | 337 | 5% → 5% (cap 10%) |  |
| S3-A1 | 12,730 | 1,961 | 1,961 | 0% → 0% (cap 10%) |  |
| S3-B1 | 12,730 | 1,068 | 1,068 | 0% → 0% (cap 10%) |  |
| S4-A1 | 1,662 | 1,479 | 1,479 | exempt (S4 answer: abstain) |  |
| S4-B1 | 1,431 | 979 | 979 | exempt (S4 answer: abstain) |  |

Drops by reason:

- **S1-A1:** final form has no single hidden ability 29; the line needs a non-default form to evolve 8
- **S1-A2:** the line needs a non-default form to evolve 8
- **S1-A3:** next form has no single hidden ability 33; the line needs a non-default form to evolve 6
- **S2-A1:** ambiguous: level 0 or several levels 1,962; another group has the same level 16,986; no distractor: other groups do not list the move 1,375; no other group lists this learnset 223
- **S2-A2:** ambiguous: level 0 or several moves at the level 2,162; another group has the same move at the level 13,407; no distractor: other groups list nothing at the level 5,933; no other group lists this learnset 223
- **S2-B1:** ambiguous: several moves at the top level 73; another group has the same last move 1,508; no other group lists this learnset 223
- **S3-A1:** a member's learnset is withheld 1,977; set size outside 3-25 6,677; single-unit shortcut 2,115
- **S3-B1:** a member's learnset is withheld 1,977; set size outside 3-25 2; single-unit shortcut 1,244; the level cap removes no learner 399; too few learners for a level cap 8,040
- **S4-A1:** ambiguous: level 0 or several levels 104; no distractor: other groups do not list the move 79
- **S4-B1:** ambiguous: level 0 or several moves at the level 136; no distractor: other groups list nothing at the level 316

## Shortcut scan

`python -m agentic_pokedex.examiner.shortcuts` (`examiner/shortcuts.py`). The
label trusts the registry; the scan checks that trust by reading text only.

- **Statement.** One body line of a structured unit read with the unit's
  header line, or a whole free-text unit. A unit is too coarse: a
  pre-evolution's Profile names the anchor on one line ("Evolves into") and
  its own hidden ability on another, two facts that a unit-level scan reads
  as one. Measured on the first scan: 2,064 questions flagged at unit level,
  1,286 at statement level, the difference all of that kind.
- **Match.** Every anchor of the question (species, move, types, version
  group, level) and the answer, outside the question's gold units. Names match
  as whole token sequences, numbers as whole digit tokens, categories and
  damage factors as their rendered phrase. Withheld units are not scanned: no
  agent can see them.
- **Naming.** The twin pages, which the agents read. Real names collide
  lexically ("Fire" inside "Fire Punch") — noise of the scan, not a leak.
- **Planted leaks.** Every run plants two leaks (a prose note and a structured
  line) for 5 sampled questions per template and requires all flagged.
- **Resolution.** Flags are grouped by class (template, section, line kind);
  each class is read with rendered examples and given a verdict, `coincidence`
  (the question is kept) or `leak` (discarded). A class without a verdict
  fails the scan.
- **Not scannable:** S1-B1 questions whose multiplier is ×4 or ×0.25; no page
  writes those values.

Scan of 2026-09-29, rerun after PI-019: planted leaks flagged **160 of 160**;
**1,272 of 33,697** questions flagged, in 18 classes, all read and resolved as
coincidence; **0 discarded**. S1-B1: 1,461 of 12,740 not scannable. (The first
scan, before PI-019, flagged 1,286 of 33,719.)

| Template | Flagged | Classes (questions) | What the flagged statement says |
|---|---:|---|---|
| S0-A1 | 80 of 856 | Form · Abilities (80); Holders · entry (31) | a form of the anchor has the answer ability |
| S0-A2 | 20 of 527 | Learned by · entry (20); Learnset · Level N (20) | a learn level equals the move's power |
| S0-A3 | 0 of 833 | | |
| S0-A4 | 611 of 713 | Learned by · entry (611) | a learner of the move has the move's type |
| S0-B1 | 149 of 192 | six Matchups line kinds (22–72 each) | a third type's line lists both types |
| S1-A1 | 12 of 397 | Form · Abilities (9); Holders · entry (5) | a form's, or the anchor's own, hidden ability (all benign) |
| S1-A2 | 243 of 426 | Learned by · entry (240); Form · Types (11) | the anchor's own types in a learner list, or a form's (all benign) |
| S1-A3 | 14 of 399 | Form · Abilities (10); Holders · entry (6) | as S1-A1 (all benign) |
| S1-B1 | 0 of 12,740 | | 1,461 not scannable |
| S2-A1, S2-A2 | 0 of 7,897; 0 of 2,893 | | |
| S2-B1 | 143 of 337 | Learnset · Moves (143) | the same move learned by machine or tutor |
| S3-A1, S3-B1 | 0 of 1,961; 0 of 1,068 | | |
| S4-A1, S4-B1 | 0 of 1,479; 0 of 979 | | |

A question can fall in more than one class. The first scan also flagged 10
material S1 questions in Form classes: a regional form sharing the final
form's types or ability (Galarian Corsola is Ghost-type, like Cursola). They
were exactly the questions whose line needs that form to evolve, the defect
PI-019 removed; after it no material S1 question is flagged. Verdicts and their reasons are in `VERDICTS`; per-question status is
written to `data/world/examiner/shortcuts.json` (local), which the splits
read.


## G3 audit

`python -m agentic_pokedex.examiner.audit draw --round N` writes a local sheet
(`data/world/examiner/audit/`, real names); `score --round N` reads the
verdicts. 60 questions per round, 12 per stratum spread evenly over the
stratum's templates, one per family, S1 material, drawn only from outside the
evaluation splits (dev, train and unassigned families), so the audit opens
nothing. Each round excludes every question an earlier round drew.

Each question shows its real-name text, gold answer, the units that state its
gold chain (S4: the withheld units), the other version's unit for S2 and S4,
the anchor's own value and material tag for S1, and what to check.

**Standard (fixed 2026-09-29, before round 1):** a gold answer is correct when
it matches the game for the question as asked — the named version group, the
default form — and the question has exactly that answer; S1 also needs the
material tag right, S3 the set complete and exact, S4 the withheld value
right. PokéAPI agreeing is not enough. Pass: at least 58 of 60 (G3 in
`docs/contingency.md`); a failed round is fixed and re-audited on a fresh
sample.

**Sources.** The gold chain is not a source: it comes from the same pipeline
as the gold answer, so their agreement tests nothing. The auditor checks each
question in an independent source first, then compares with the gold, and
reads the chain only to locate a disagreement (PokéAPI's data or the
generator). Sites built on PokéAPI are not independent and are not used.

| Template | Source |
|---|---|
| S0-A1 | Bulbapedia species page, abilities box (default form) |
| S0-A2, S0-A3, S0-A4 | Bulbapedia or PokémonDB move page, current (Generation IX) values |
| S0-B1 | Type chart, Generation VI onward |
| S1-A1 to A3 | Bulbapedia species page, evolution section; then the final or next form's abilities or types, and the anchor's own for the material tag |
| S1-B1 | The move's type, the species' types (default form), the type chart |
| S2, S4 | Serebii per game (`pokedex-xy`, `pokedex-sm` with its USUM column, `pokedex-sv`), level-up learnset; or Bulbapedia's per-generation learnset pages, or PokémonDB `/pokedex/<name>/moves/<gen>` with its per-game tabs |
| S3 | Serebii attackdex of the generation (`attackdex-xy`, `attackdex-sm`, `attackdex-sv`), level-up learners, filtered by type and default form |

Version traps: X/Y is not ORAS and Sun/Moon is not USUM — the named group's
column only; Scarlet/Violet marks moves learned on evolution ("Evo.", level 0
here, never an answer) and moves only relearnable ("Rem.").

## Reachability

`python -m agentic_pokedex.examiner.reachability` (ADR-007): every
insufficiency subtype and every error code of E-001 must be producible by at
least one dev question, or be unreachable by declared design. For each code the
module finds a dev question and a reachable state (indexed units) whose label,
computed by the labeler, is the one the code needs.

Run of 2026-09-30 on dev: **13 of 13 codes reachable**, 1 declared; witness
states hold 1–2 units (T_max = 6).

| Code | Witness state (dev) | Label |
|---|---|---|
| missing-hop, stop-missing-hop | one unit of an S1 chain | insufficient (missing-hop) |
| wrong-version, accepted-wrong-version | another version's unit, the asked version's unseen | insufficient (wrong-version) |
| truncated, accepted-truncated-set | the units of one member of an S3 set | insufficient (truncated) |
| nonexistent, answered-unanswerable | another version's unit for a withheld learnset | insufficient (nonexistent) |
| abstained-with-sufficient, over-search, generation-error | an S0 question's gold unit, one step | sufficient |
| never-reached | an S1 question no single unit makes sufficient | insufficient |
| correct-at-insufficient | the final form's Profile: the answer shown, the chain to it unseen | insufficient (missing-hop) |
| format-error | declared: a property of the output, not of the question | — |
