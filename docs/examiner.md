# The Examiner

The golden set is software: questions, gold answers, gold chains and step-level
sufficiency labels are generated from the Neo4j graph (ADR-007) and the fact →
units registry (`docs/world.md`). This document is the specification, written
before the generator; the counts sections are filled as the filters run.

**Status:** specification (Phase 2, 2026-09-29). Counts: pending.

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
| S1-A1 | Hidden ability of the final form of X's evolution line | X → final form | 405 | 70 |
| S1-A2 | Types of the final form of X's evolution line | X → final form | 434 | 104 |
| S1-A3 | Hidden ability of the species X evolves into | X → next form | 405 | 57 |
| S1-A4 | Hidden ability of the species X evolves from | X → pre-evolution | 445 | 87 |
| S1-B1 | Type damage multiplier of move M against species X | M → its type; X → its types; the type chart | many | all |

- **Anchor answer:** the same attribute read on X itself (X's hidden ability,
  X's types). A question is **material** when the gold answer differs from the
  anchor answer, and **benign** when they coincide.
- **Material S1** forms S1 in the H1 pool; **benign S1** is a descriptive
  slice (40 questions in eval-L1, run by A3, A4 and A4p only; PI-015). S1-B1 is
  material by construction: no single fact gives the multiplier.
- S1 avoids version-scoped relations on purpose: a hop through a learnset would
  mix a wrong-version trap into a missing-hop question.
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
| S3-A1 | Species of type T that learn M by level-up in V | 323 |
| S3-B1 | Species of type T that learn M by level-up in V at or below level L | to count |

- The gold set has 3–25 members **and is spread over at least two indexed
  units**: 1,181 of 1,504 candidate sets fit in one hub unit, where one unit is
  sufficient and nothing is truncated.
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
| S1 | S1-A1 … S1-A4 | S1-B1 |
| S2 | S2-A1, S2-A2 | S2-B1 |
| S3 | S3-A1 | S3-B1 |
| S4 | S4-A1 | S4-B1 |

The B template of each stratum is its most different shape, so the A × B gap
measures generalization rather than a paraphrase.

## Surface forms

Three per template, hand-written (no LLM paraphrase in v1). Placeholders are
filled with twin names in the twin population and real names in eval-L3.
`{TERM}` is the twin's word for "Pokémon" (its plural takes an `s`).

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
| S1-A4 | What is the hidden ability of the species that evolves into {X}? · {X} evolves from another species. What is that species' hidden ability? · Which hidden ability does {X}'s pre-evolution have? |
| S1-B1 | How effective is {M} against {X}? · If {M} hits {X}, what is its type damage multiplier? · What type-effectiveness multiplier does {M} get against {X}? |
| S2-A1, S4-A1 | At what level does {X} learn {M} in {V}? · In {V}, at which level does {X} learn {M}? · {X} learns {M} by leveling up in {V}. At what level? |
| S2-A2, S4-B1 | Which move does {X} learn at level {L} in {V}? · In {V}, what move does {X} learn upon reaching level {L}? · Name the move {X} learns at level {L} in {V}. |
| S2-B1 | What is the last move {X} learns by leveling up in {V}? · In {V}, which move does {X} learn at the highest level? · Which level-up move does {X} learn last in {V}? |
| S3-A1 | Which {T}-type {TERM}s learn {M} by leveling up in {V}? · List every {T}-type {TERM} that learns {M} by level-up in {V}. · In {V}, which {TERM}s of type {T} learn {M} by leveling up? |
| S3-B1 | Which {T}-type {TERM}s learn {M} by leveling up in {V} at or below level {L}? · List every {T}-type {TERM} that learns {M} by level {L} or earlier in {V}. · In {V}, which {TERM}s of type {T} learn {M} by leveling up no later than level {L}? |

## Filters

Applied in this order; each publishes N-of-M per template.

1. **Scope.** Every learnset fact is in a scope group (negative test).
2. **World constraints (PI-016).** Hidden-ability templates sample species
   that have one; level 0 ("on evolution") and pairs listed at several levels
   are not answers; branching lines have no single final form (S1-A1, S1-A2
   excluded there; S1-A3 needs a single next form); non-default forms are never
   anchors or answers; S3 avoids hubs whose gold set includes a withheld
   species.
3. **Ambiguity.** The answer is unique (one level, one move at level L, one
   final form, one last move).
4. **Stratum conditions.** S1 material/benign tag; S2 distractor present;
   S3 size 3–25 and spread over ≥ 2 units; S4 answer fact only in withheld
   units and a plausible distractor present.
5. **Single-unit shortcut** (MuSiQue): for S1–S3, if one indexed unit covers
   every gold fact, the question is discarded — it is not multi-hop.
6. **Answer concentration (PI-012).** Each template's majority-answer rate is
   at most max(10%, 1.5 × uniform chance); the answer distribution before and
   after the cap is published.
7. **Shortcut scan** (gate 7): a unit naming the anchor together with the
   answer outside the gold units flags the question; flags are inspected and
   resolved. Validated first on planted leaks.

## The question record

| Field | Published | Notes |
|---|---|---|
| `id`, `stratum`, `template`, `surface` | yes | |
| `question` (twin text) | yes | real text only in eval-L3, local |
| `answer`, `aliases` | yes | twin names or numbers; sets sorted |
| `gold_facts` | yes | fact ids |
| `cover` | yes | for each gold fact, the indexed units that state it |
| `near_certain_units` | yes | S2: the other groups' units giving a different answer |
| `withheld_units` | yes | S4 |
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

## Splits

Ids and seeds only are versioned (`data/splits/`).

| Split | Size | Templates | Opening |
|---|---|---|---|
| `dev` | 150 (30 per stratum) | group A | free |
| `train` | simulated states + 150 real trajectories | group A | free |
| `eval-L1` | 400 (S0 80; S1–S4 80) + 40 benign S1 | A and B | once |
| `val-B` | 60 | group B | once |
| `eval-L2` | 280 (S0 40; S1–S4 60) | A and B | once |
| `eval-L3` | 150, twin and real | A and B | once |

## Counts

_Filled when the generator runs._
