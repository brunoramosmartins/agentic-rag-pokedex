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
abilities with the hidden flag; level-up and other learnsets per version group;
Pokédex flavor text (local only, never published).

**Out (parked):** encounters and locations, items, battle stats, evolution
conditions, genus, height and weight, the trading card game. Each would add
chain shapes and one more source to validate.

## Build

```bash
python -m agentic_pokedex.world.download     # 23 CSVs, SHA-256 checked
python -m agentic_pokedex.world.load_graph   # replaces the Neo4j database
python -m agentic_pokedex.world.coverage     # learnset coverage report
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
