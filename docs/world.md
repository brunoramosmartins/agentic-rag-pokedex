# World v1

The world is built from PokéAPI at a pinned commit (`docs/data-sources.md`),
loaded into Neo4j as the examiner's graph (ADR-007), renamed into a
counterfactual twin (ADR-003) and rendered as sectioned pages whose sections are
the evidence units (ADR-002). This document records what the world contains and
the numbers behind every scope decision. Sections are added as each part is
built.

## Scope

**In:** species and forms; the 18 battle types and their efficacy table;
evolution chains (structure only); moves with type, power and category;
abilities with the hidden flag; level-up and other learnsets per version group.

**Pokédex flavor text is not in world v1.** It is loaded into the graph, but the
pages carry no notes: the identity probe (E-003) found that the renamed flavor
text still names the species — the twin was recognized in 27 of 50 pages
with notes and in 1 of 50 without — so G2's exit was taken
(`docs/contingency.md`). On the no-notes world, a fresh sample of 50 species
passes the probe (twin 1 of 50, control 48; E-003 run 2). `render --notes`
restores the notes, for research only.

**Out (parked):** encounters and locations, items, battle stats, evolution
conditions, genus, height and weight, the trading card game. Each would add
chain shapes and one more source to validate.

## Build

```bash
python -m agentic_pokedex.world.download     # 23 CSVs + word list, SHA-256 checked
python -m agentic_pokedex.world.load_graph   # replaces the Neo4j database
python -m agentic_pokedex.world.coverage     # learnset coverage report
python -m agentic_pokedex.world.twin         # twin map → data/world/twin_map.json
python -m agentic_pokedex.world.render       # pages + registry → data/world/
python -m agentic_pokedex.world.answer_space # values per answer slot
python -m agentic_pokedex.world.examples     # example pages (twin only)
```

## Graph

The graph holds the **real** world; the twin is a renaming layer built on top.

```
(:Species {id, identifier, name, generation, evolution_chain_id,
           is_baby, is_legendary, is_mythical})
(:Pokemon {id, identifier, name, is_default})-[:FORM_OF]->(:Species)
(:Species)-[:EVOLVES_FROM]->(:Species)
(:Pokemon)-[:HAS_TYPE {slot}]->(:Type {id, identifier, name})
(:Type)-[:DAMAGE {factor}]->(:Type)                 attacker → defender, percent
(:Pokemon)-[:HAS_ABILITY {slot, hidden}]->(:Ability {id, identifier, name})
(:Move {id, identifier, name, power, category})-[:OF_TYPE]->(:Type)
(:Pokemon)-[:LEARNS {version_group, method, level}]->(:Move)
(:Version {id, identifier, name})-[:IN_GROUP]->
    (:VersionGroup {id, identifier, name, generation, order})
(:Species)-[:HAS_FLAVOR]->(:FlavorText {key, text})-[:IN_VERSION]->(:Version)
```

### Filters

| Table | Kept | Rule |
|---|---|---|
| Types | 18 of 21 | Types with efficacy rows; drops `unknown`, `shadow`, Tera-only `stellar` |
| Moves | 833 of 937 | Learned by some Pokémon, battle type; drops shadow, Z- and Max-move variants |
| Abilities | 314 of 374 | Main series only |
| Names | English | `languages.identifier = en` |
| Flavor text | 14,496 of 68,220 | English only; whitespace collapsed |
| Learnsets | 638,321 (all) | Every version group and learn method; the version scope applies at render time |

### Load statistics (2026-09-29)

`LOAD CHECK: PASS` — every node and relationship count equals the number of
records written.

| Node | Count | | Relationship | Count |
|---|---:|---|---|---:|
| Species | 1,025 | | FORM_OF | 1,351 |
| Pokemon | 1,351 | | EVOLVES_FROM | 484 |
| Type | 18 | | HAS_TYPE | 2,116 |
| Ability | 314 | | DAMAGE | 324 |
| Move | 833 | | HAS_ABILITY | 2,943 |
| Version | 53 | | OF_TYPE | 833 |
| VersionGroup | 32 | | LEARNS | 638,321 |
| FlavorText | 14,496 | | IN_GROUP | 53 |
| | | | HAS_FLAVOR | 14,496 |
| | | | IN_VERSION | 14,496 |

`LEARNS` rows span 26 of the 32 version groups. The six without rows are the
four DLC groups (their moves are folded into the base group) and `legends-za`
and `mega-dimension`, not yet filled in at the pinned commit.

Four English Pokémon names are shared by two entries ("10% Zygarde",
"Koraidon", "Miraidon", "Mega Meowstic"). The graph keys on the PokéAPI
identifier, which is unique; page titles are disambiguated by the renderer.

## Version scope

**Frozen on 2026-09-29: `x-y`, `ultra-sun-ultra-moon`, `scarlet-violet`**
(generations 6, 7 and 9). `VERSION_SCOPE` in `world/pokeapi.py`.

What the choice has to buy is stratum S2 (wrong version): "at what level does X
learn Y in V?", where the same learnset in another version group of the corpus
gives a **different** level. Definitions, on level-up moves of default Pokémon
entries:

- a **pair** is (Pokémon, move);
- a pair is **answerable** in a group when it has exactly one level there and
  that level is ≥ 1 (level 0 means "on evolution");
- a pair is **S2-usable** for group g within a set G when it is answerable in
  g, another group of G lists it, and no other group of G lists it at g's
  level.

### Candidate groups

The seven base groups with near-complete learnsets (G1). The graph and the raw
CSVs give identical tables.

| Version group | Gen | Pokémon | Pairs | Answerable |
|---|---:|---:|---:|---:|
| x-y | 6 | 721 | 10,376 | 9,523 |
| omega-ruby-alpha-sapphire | 6 | 721 | 10,572 | 9,751 |
| sun-moon | 7 | 802 | 11,941 | 10,850 |
| ultra-sun-ultra-moon | 7 | 807 | 12,047 | 10,966 |
| sword-shield | 8 | 664 | 9,949 | 9,776 |
| brilliant-diamond-shining-pearl | 8 | 488 | 7,482 | 7,176 |
| scarlet-violet | 9 | 733 | 10,739 | 10,530 |

### Level differences

Pairs answerable in both groups, and how many have a different level. Within
the chosen scope:

| Group A | Group B | Shared | Level differs | Rate |
|---|---|---:|---:|---:|
| x-y | ultra-sun-ultra-moon | 9,241 | 2,249 | 24% |
| ultra-sun-ultra-moon | scarlet-violet | 6,115 | 3,428 | 56% |
| x-y | scarlet-violet | 5,293 | 3,354 | 63% |

Near-duplicates, which is why no two groups of the same era are combined:

| Group A | Group B | Shared | Level differs | Rate |
|---|---|---:|---:|---:|
| sun-moon | ultra-sun-ultra-moon | 10,848 | 39 | 0% |
| sword-shield | brilliant-diamond-shining-pearl | 4,846 | 18 | 0% |
| sword-shield | scarlet-violet | 5,924 | 67 | 1% |

The full 21-row table and all 28 candidate sets are regenerated by
`world.coverage` into `data/world/coverage.md`.

### Candidate sets compared

| Set | S2-usable per group | Weakest | Pokémon in all | Pokémon in any |
|---|---|---:|---:|---:|
| **x-y, ultra-sun-ultra-moon, scarlet-violet** | 2,386 · 2,383 · 3,581 | **2,383** | **486** | **999** |
| x-y, ultra-sun-ultra-moon, sword-shield | 2,379 · 3,232 · 5,654 | 2,379 | 498 | 898 |
| ultra-sun-ultra-moon, sword-shield, scarlet-violet | 5,694 · 2,397 · 315 | 315 | 355 | 1,025 |
| x-y, ultra-sun-ultra-moon, brilliant-diamond-shining-pearl, scarlet-violet | 2,381 · 2,209 · 1,107 · 1,678 | 1,107 | 348 | 999 |
| x-y, ultra-sun-ultra-moon, sword-shield, scarlet-violet | 2,377 · 2,793 · 2,387 · 313 | 313 | 311 | 1,025 |

*Pokémon in all / in any:* default entries with a level-up learnset in every /
some group of the set.

### Why this set

- **S2 material does not bind.** Every one-group-per-generation set has more
  than 300 S2-usable pairs in its weakest group; the evaluation splits need a
  few hundred S2 questions in total. The choice rests on balance and species
  coverage.
- **Balanced.** Each chosen group carries at least 2,383 S2-usable pairs.
- **Coverage.** 486 Pokémon have a learnset in all three groups (the base for
  S2 and S4, where other versions must remain); 999 of 1,025 have one in at
  least one group, generation 9 included.
- **Rejected:** x-y + ultra-sun-ultra-moon + sword-shield (more S2 pairs,
  11,265 in total, but about a hundred species, generation 9, without any
  learnset); any set pairing sword-shield with scarlet-violet (1% differ, the
  weakest group falls to ~315); four-group sets (every one adds a
  near-duplicate, about a third more learnset units, and fewer Pokémon in all
  groups).

Pokédex flavor text is attached per species from whichever version has it,
independently of the version scope (`docs/data-sources.md`).

## Counterfactual twin

`world/twin.py`, seed `TWIN_SEED = 20260929`. The map real → twin lives in
`data/world/twin_map.json` (gitignored); only the seed is versioned.

**What is renamed.** Species, Pokémon entries (forms), types, abilities, moves,
versions, version groups and the word "Pokémon". Numbers are never touched.

**How names are drawn.** Each name is a pronounceable pseudo-word (two or three
syllables, 4–9 letters, never three consonants in a row) drawn from a seeded
generator, independently of the real name it replaces. Moves and abilities get
two words in about 40% of cases. A candidate is redrawn when it:

| Test | Against |
|---|---|
| Real name | Every name PokéAPI lists in any language, their words, every identifier, and franchise terms (regions, "poke") |
| Dictionary | 370,105 English words (`docs/data-sources.md`) |
| Look-alike | English real names: same first or last four letters, one edit away, or containing one of five letters or more |
| Profanity | A short blocklist of substrings |
| Taken | Every twin word already drawn, of any kind |

**Shapes kept.** A form name keeps its structure: the species part becomes the
species' twin and every other word a consistent pseudo-word ("Mega Charizard
X" → "<mega> <species> X"). A version-group name is rebuilt from its versions'
twins ("Scarlet/Violet" → "<version>/<version>").

**Free text.** Flavor text is rewritten at render time: every Title-case or
upper-case occurrence of a species, form, type, ability or move name, or of
"Pokémon", is replaced; when two kinds share a name ("Psychic"), the type wins
over the move. Version names are not rewritten in prose ("X", "Sun"). Lower-case
prose ("spits fire") is left as it is: that was the leak surface the identity
probe measured, and it leaked — the reason world v1 has no notes (E-003).

### Build (2026-09-29)

| Kind | Distinct real names | Note |
|---|---:|---|
| species | 1,025 | |
| pokemon | 1,343 | 1,351 entries; a few forms share an English name |
| form_word | 156 | words of form names other than the species |
| type | 18 | |
| ability | 313 | 314 abilities; "As One" names two |
| move | 833 | 479 one-word, 354 two-word twins |
| version | 51 | 53 versions; two names repeat across regions |
| version_group | 32 | rebuilt from versions |
| term | 1 | "Pokémon" |

- **Round trip** real → twin → real: identity for every name of every kind.
- **Unique words:** no pseudo-word is shared by two names.
- **Flavor text:** 5,797 of 14,496 English texts change; after rewriting, **0**
  still name a real species, in any case. Renaming the names was not enough:
  the descriptions themselves identify the species (E-003).

## Pages and evidence units

`world/render.py` and `world/registry.py`. One page per species, move, ability
and type; every section is an evidence unit whose first line is a metadata
header. The examples below use made-up twin names.

```
Species: Kedros · Section: Profile
Types: [[Ranze]] / [[Sonzu]]
Abilities: [[Thalso]], [[Vihom]] · Hidden ability: [[Daikpil]]
Evolves into: [[Nemzaiva]], [[Resbas]]
Forms: [[Poukzai Kedros]]
```
```
Species: Kedros · Section: Learnset · Method: level-up · Version: Diprok/Kastoxgi
Level 1: [[Kresto]], [[Polvun]]
On evolution: [[Fleilavu]]
Level 16: [[Laikpan Naisgol]]
```
```
Move: Kresto · Section: Learned by · Version: Diprok/Kastoxgi
[[Floupei]] (Ranze/Sonzu) — level 12
[[Skahis]] (Dasme) — level 30
```

| Page | Sections (units) |
|---|---|
| Species | `Profile` (types, abilities, the species it evolves into — forward links only, "—" for a final form — and forms); one `Form` per non-default entry (types, abilities); one `Learnset` per learn method and version group; `Notes` (up to 2 Pokédex texts, free text) only with `--notes` — off in world v1 |
| Move | `Profile` (type, category, power); `Learned by` per version group, level-up only, each entry with the learner's types, split every 20 entries |
| Ability | `Holders`, split every 20 entries, hidden ones marked |
| Type | `Matchups`: attacking and defending, by damage factor |

**Design decisions** (journal, 2026-09-29):

1. **Every learn method on species pages** — level-up, machine, egg and tutor,
   one unit per method and version group. A machine unit that lists a move
   is plausible, insufficient evidence for a question about its level (a
   wrong-method distractor, beside the wrong-version one). Hubs stay level-up
   only: a machine hub would list most of the corpus.
2. **Non-default forms** carry types and abilities only; their learnsets are
   out of v1, and hubs list default entries only.
3. **Hub entries show the learner's types**, so S3 ("which T-type learn M by
   level-up in V?") is a gather-and-filter over the hub's units.
4. **120 withheld pairs** (species, version group), 40 per group, seeded
   (`WITHHELD_SEED`), among the species with a level-up learnset in all three
   groups; a species is withheld in one group at most. Their level-up
   `Learnset` unit leaves the index **and their entries leave that group's
   hubs**, so no indexed unit states the withheld levels. Their machine, egg
   and tutor units stay. Examiner consequence: S3 templates avoid hubs whose
   gold set includes a withheld species.
5. **Notes:** up to 2 distinct Pokédex texts per species, most recent versions
   first — **off in world v1** since E-003 (G2's exit); `--notes` restores
   them for research.
6. **Titles are unique:** abilities sharing a name ("As One") are one page;
   forms sharing a display name get " (2)".

Split units share one header with no pagination marker (ADR-009). The cue
variant for the S3 ablation (`--cues`) adds `Part k/N`.

**Out of v1, declared:** learnsets of non-default forms (23,098 rows in the
scope), and the rare learn methods (`light-ball-egg`, `form-change`,
`zygarde-cube`: 9 rows).

### Example pages (twin, as rendered)

One page of each kind, exactly as the renderer writes it and the index serves
it, regenerated with `python -m agentic_pokedex.world.examples`. World v1 has
no Pokédex notes; had a page any, the generator would elide them
(`docs/data-sources.md`). Everything shown is PokéAPI fact content under twin
names. The species page shows a form, three learn methods, and a
machine learnset split into two units that share one header with no
pagination marker (ADR-009). The move's hub shows each learner's types.

#### Species page: Humzam (6 units)

```
Species: Humzam · Section: Profile
Types: [[Laigrel]] / [[Lolmax]]
Abilities: [[Dralfas]], [[Dunuszaik]] · Hidden ability: [[Teipomde]]
Evolves into: [[Fesouk]]
Forms: [[Salleken Humzam]]
```

```
Species: Humzam · Section: Form · Form: Salleken Humzam
Types: [[Laigrel]] / [[Lolmax]]
Abilities: [[Dralfas]], [[Dunuszaik]] · Hidden ability: [[Teipomde]]
```

```
Species: Humzam · Section: Learnset · Method: level-up · Version: Karek/Zistamdu
Level 1: [[Lerkodok]], [[Zesleilge Vailnis]]
Level 6: [[Trenpa]]
Level 12: [[Faimteik Gamosix]]
Level 18: [[Goukpo]]
Level 24: [[Gaismes]]
Level 30: [[Grukvin Bommor]]
Level 36: [[Gakvur]]
Level 42: [[Dresvol]]
Level 48: [[Venlus Fleilon]]
Level 54: [[Dastesnou Krirsain]]
Level 60: [[Namdazun]]
Level 66: [[Kraknas Brirmos]]
```

```
Species: Humzam · Section: Learnset · Method: machine · Version: Karek/Zistamdu
Moves: [[Sheifam Pazox]], [[Koumlile Vartade]], [[Fixro Praxve]], [[Krapum]], [[Domgoul Stulsek]], [[Kraknas Brirmos]], [[Nomfei]], [[Koxme Gusgekram]], [[Gaisfai]], [[Drimse]], [[Fosdo]], [[Rekkes Slaihin]], [[Pairak Thokaxvar]], [[Begax]], [[Prondan]], [[Makroux]], [[Dimvouk]], [[Trourdes]], [[Zeishu Diksus]], [[Skaxtim]], [[Zesleilge Vailnis]], [[Bivolgoux Promon]], [[Lailul Naipofek]], [[Flikel]], [[Goukpo]], [[Gakvur]], [[Venlus Fleilon]], [[Shouvain]], [[Peprordei]], [[Loukmil]], [[Dadei Krakreis]], [[Dastesnou Krirsain]], [[Festei]], [[Kimpam]], [[Gratros]], [[Kraixrus]], [[Nemkotror]], [[Zosathem]], [[Grukvin Bommor]], [[Gese]]
```

```
Species: Humzam · Section: Learnset · Method: machine · Version: Karek/Zistamdu
Moves: [[Mouxtampe]], [[Gaismes]], [[Sokra]], [[Githai]], [[Feiskouvu]]
```

```
Species: Humzam · Section: Learnset · Method: egg · Version: Karek/Zistamdu
Moves: [[Druli Brolha]], [[Gramfem]], [[Brolek]]
```

#### Move page: Pramnulpu (2 units)

```
Move: Pramnulpu · Section: Profile
Type: [[Ranze]] · Category: physical · Power: 70
```

```
Move: Pramnulpu · Section: Learned by · Version: Karek/Zistamdu
[[Nepreisvo]] (Ranze) — level 44
[[Tukfer]] (Ranze) — level 49
[[Radahos]] (Shulkem/Laigrel) — level 47
[[Nosox]] (Shulkem/Laigrel) — level 47
[[Vudi]] (Shulkem/Laigrel) — level 47
```

#### Ability page: Slaire (1 unit)

```
Ability: Slaire · Section: Holders
[[Brendail]] (hidden)
[[Zugro]] (hidden)
[[Moushi]] (hidden)
```

#### Type page: Sonzu (1 unit)

```
Type: Sonzu · Section: Matchups
Attacking — super effective against: [[Bomgu]], [[Rexmok]]
Attacking — not very effective against: [[Stikrar]], [[Sonzu]], [[Lolmax]]
Attacking — no effect on: [[Thoba]]
Attacking — normal damage against: [[Dadeis]], [[Duszogaik]], [[Slomdei]], [[Shogeksas]], [[Ranze]], [[Tratreix]], [[Laigrel]], [[Dasme]], [[Dobem]], [[Krergak]], [[Paxrou]], [[Shulkem]]
Defending — weak to: [[Thoba]]
Defending — resists: [[Bomgu]], [[Laigrel]], [[Sonzu]]
Defending — normal damage from: [[Dadeis]], [[Duszogaik]], [[Slomdei]], [[Shogeksas]], [[Ranze]], [[Tratreix]], [[Dasme]], [[Rexmok]], [[Stikrar]], [[Dobem]], [[Krergak]], [[Lolmax]], [[Paxrou]], [[Shulkem]]
```

### The registry

A fact id carries its full content (`learn:{pokemon}:{move}:{group}:{method}:{level}`,
`ptype:{pokemon}:{slot}:{type}`, …; `world/registry.py`). Every body line is
generated from registered facts, and the check parses each unit's text back into
fact ids and compares them with the registry — so a wrong value, a missing line
or an extra line fails it. Pokédex notes, when rendered (`--notes`), are free
text outside the registry, marked as such.

### Build (2026-09-29, world v1: no notes)

| Section | Units |
|---|---:|
| species / Profile | 1,025 |
| species / Form | 326 |
| species / Learnset / level-up | 2,261 (120 withheld) |
| species / Learnset / machine | 2,914 |
| species / Learnset / egg | 1,054 |
| species / Learnset / tutor | 898 |
| move / Profile | 833 |
| move / Learned by | 2,761 |
| ability / Holders | 362 |
| type / Matchups | 18 |
| **Total** | **12,452** (12,332 indexed) |

- **Facts:** 145,429, every one stated by at least one unit; no unit states an
  unregistered fact; every unit's text parses back to exactly its registered
  facts, in the twin and in the real naming (`REGISTRY CHECK: PASS`).
- **Size** (indexed units, estimated as characters / 4): mean 94 tokens, p90
  180, max 223; about 1.16 million tokens in total. The largest unit is well
  under the ~700 tokens a tool call returns.
- **Idempotence:** a forced rebuild writes byte-identical page files (same
  SHA-256), in both namings.

## Index and tools

**Index** (`world/index.py`) — indexed units only; withheld units never enter.

- **BM25**, adapted from the previous project: `k1 = 1.2`, `b = 0.75`, ties by
  unit id. Twin names are pseudo-words no embedding model has seen, so the
  lexical half carries the names.
- **Dense:** `BAAI/bge-small-en-v1.5` through `fastembed` (ONNX, CPU, the
  `retrieval` extra), exact cosine search in numpy. Passage vectors are cached
  in `data/world/index/`, keyed by model and texts.
- **Fusion:** reciprocal rank fusion (`k = 60`) over the top 50 of each.

**Tools** (`tools/`) — the same for every arm.

| Call | Returns |
|---|---|
| `search(query, k ≤ 5)` | The best units, with headers |
| `open_page(title)` | The page from the top |
| `open_page(title, section)` | Units whose section line contains `section` (`"level-up"`, `"Learned by · Version: …"`); if none does, the whole page from the top, with no message |
| `open_page(title, section, offset)` | The same, skipping the first `offset` units; `"No more units."` past the end |

At most **700 tokens of units per call** (`o200k_base`), packed in rank or page
order, the first unit always. In the main condition nothing says how many units
matched or remain, or that a section does not exist — no tool hands over the
signal used to decide sufficiency (ADR-009, Updates); in the cue condition (S3 ablation) both tools state the
count, and the cue page file carries `Part k/N`. Every result records the ids
of the units it showed, for the labeler.

In the real naming a type and a move can share a name ("Psychic");
`open_page` then returns both pages, species before move before ability before
type. Twin titles are all unique.

## Answer spaces

`world/answer_space.py`. For each slot an answer can fill: how many values it
admits, the **uniform** chance of a blind guess (1 / n), and the **modal
share** — the score of always guessing the most common value, which needs no
leak at all. Populations are world-level, in scope; a template's own
population is known only once questions exist. Counts are the same in the twin
and in the real naming.

| Slot | Population | Values (n) | Uniform chance | Modal share | Space |
|---|---|---:|---:|---:|---|
| type of a Pokémon (primary) | Pokémon entries (1,351) | 18 | 5.6% | 11.8% | small |
| type of a Pokémon (any slot) | Pokémon type facts (2,116) | 18 | 5.6% | 9.1% | small |
| type of a move | moves (833) | 18 | 5.6% | 22.6% | small |
| move category | moves (833) | 3 | 33.3% | 40.3% | small |
| move power | moves with power (546) | 32 | 3.1% | 13.0% | open |
| damage factor | type pairs (324) | 4 | 25.0% | 63.0% | small |
| learn level | answerable level-up pairs in scope (31,019) | 96 | 1.0% | 21.3% | open |
| learn level (S2-usable) | S2-usable pairs in scope (8,350) | 93 | 1.1% | 4.4% | open |
| ability | Pokémon ability facts (2,943) | 312 | 0.3% | 1.6% | open |
| hidden ability | hidden-ability facts (988) | 166 | 0.6% | 2.5% | open |
| species | species (1,025) | 1,025 | 0.1% | 0.1% | open |
| move | moves (833) | 833 | 0.1% | 0.1% | open |

*Small* = at most 20 values. Several slots are skewed well beyond uniform
chance: a move's type is Normal 22.6% of the time, a damage factor is ×1 63% of
the time, and a learnable level is 1 in 21.3% of answerable pairs (4.4% among
S2-usable pairs, whose levels differ between groups by construction).

