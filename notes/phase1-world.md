# Phase 1 — The World: PokéAPI → Graph → Twin → Pages

**Objective.** Build world v1 to specification: the graph in Neo4j, the renamed
twin, sectioned pages whose sections are the evidence units, the fact → units
registry, the index and the two tools. Freeze the version scope from measured
coverage, not from preference.

**Dates.** Opened and closed 2026-09-29 · size L (8–11 partial working days,
as an estimate) · no calendar, no hard deadline.

**Ends with.** Tag `v0.2-world` (no release): world built and rebuilt
idempotently, twin round trip 100%, registry complete, preliminary G2 from the
identity probe, `docs/world.md` published.

---

## Download and graph load (`world/download.py`, `world/load_graph.py`)

23 PokéAPI CSVs at the pinned commit, each kept only if its SHA-256 matches the
manifest; the 14 hashed for G1 still matched. The graph holds the **real**
world (the twin is a renaming layer) with every version group, so the coverage
report and the examiner read the same data. Scope filters: the 18 battle types,
moves someone learns (833 of 937), main-series abilities, English only. The
load ends with a check that every node and relationship count equals the
records written — a `MATCH` that misses an endpoint fails silently otherwise.
`LOAD CHECK: PASS`, 638,321 learnset rows. Details: `docs/world.md`, Graph.

## Learnset coverage report and base version groups

Measured, per pair of groups, how often a (Pokémon, move) level differs, and
for every candidate set how many pairs can carry an S2 question. Adjacent
generations are near-duplicates (sword-shield vs scarlet-violet 1%, sun-moon vs
ultra-sun-ultra-moon 0%). S2 material does not bind any set; the author chose
**x-y, ultra-sun-ultra-moon, scarlet-violet** for balance (weakest group 2,383
S2 pairs) and coverage (generation 9 included). Graph and CSV computations
agree in every cell. Details: `docs/world.md`, Version scope.

## Counterfactual twin (`world/twin.py`)

Seeded pseudo-words (4–9 letters) drawn independently of the real names,
rejected when they equal a real name in any language, an English word (pinned
word list — a system dictionary would differ between machines), look like an
English real name, contain profanity, or repeat. The first draw produced
unreadable names and one profanity; the word shape was tightened. Form names
keep "<qualifier> <species>", version groups are rebuilt from their versions.
Round trip real → twin → real is identity for every name of every kind.

## Renderer and fact → units registry (`world/render.py`, `world/registry.py`)

One page per species, move, ability and type; each section is an evidence unit.
The page design was reviewed with the author before code: species pages carry
**every learn method** (the author's objection — a machine unit listing a move
is a wrong-method distractor), level-up hubs show each learner's types (for
S3), forms carry types and abilities only, and 120 (species, version) pairs are
withheld for S4, removed from the hubs too. Fact ids carry their full value,
and a parse-back check proves the registry exact: 144,861 facts, 12,452 units
(12,332 indexed) after the notes were removed. Details: `docs/world.md`, Pages.

## Index and tools (`world/index.py`, `tools/search.py`, `tools/open_page.py`)

BM25 adapted from the previous project plus `bge-small` through `fastembed`
(CPU; the GPU is not visible from WSL), fused by reciprocal rank. The first
embedding took 15 minutes because batches padded every unit to the longest
one (twin pseudo-words split into many word pieces); sorting by length and a
per-unit cache fixed it — a re-render re-embeds nothing that did not change.
Tools: at most 700 tokens per call, `open_page` from the top with `offset`. At
the close review, "No section matching …" was found to announce an S4 absence;
a section matching nothing now serves the whole page (ADR-009, Updates).

## Identity probe — preliminary G2

Registered as E-003. Run 1 (50 species × 3 conditions): control 48 of 50, twin
**with** Pokédex notes 27 of 50, without notes 1 of 50 — the renamed flavor
text still identified the species. 28 answers had been truncated at a
1,000-token output cap; an amendment raised it to 4,000 and counted residual
invalid answers both ways. G2's exit was taken: world v1 renders no notes.
Run 2 (fresh 50 species, no-notes world): control 48, twin **1 of 50** — the
identity half of G2 passes. The one hit was recognized from structure alone.
Total cost about US$ 0.22. Details: `experiments/registry.md`, E-003.

## Admissible answers per answer slot

Counted n values, uniform chance and the modal share per slot. Several slots
are skewed well beyond uniform (a move's type is Normal 22.6% of the time, a
learnable level is 1 in 21.3% of pairs), which would have failed G2's
closed-book rule with no leak. The rule now uses each template's
majority-answer rate, and generation caps it (PI-012). Details: `docs/world.md`,
Answer spaces; `docs/contingency.md`, G2.

## Idempotent rebuild

Rendering twice writes byte-identical page files in both namings, and the
no-notes world rendered on two occasions produced the same SHA-256 — the
build is reproducible from the pinned commit, the word list and the seeds.

## `docs/world.md` — statistics and one rendered page of each type

Published with scope, graph, twin, pages, registry, index, tools and answer
spaces. The example pages (a species with a form and a learnset split in two
units, a move hub, an ability, a type) are regenerated by `world/examples.py`,
twin-side only.

## Close review

Before the tag, every decision was stress-tested with an external review. The
main finding: in 82% of evolution lines the base and final forms share their
hidden ability, so S1 as first designed rarely tested the missing hop (PI-015:
material vs benign S1). Adopted also: no tool states an absence, the S3
mechanism is split, cost never changes the treatment. The plan was revised;
PI-010 to PI-016 are resolved in `docs/decision-journal.md`.

---

## Lessons Learned

* I initially treated version-group selection as a scope decision; after measuring coverage, I realized the choice should be a consequence of the data rather than a preference. The final set was determined by structural coverage and S2 diversity.
* I initially expected entity renaming to be enough to make the world semantically blinded. My preregistered prediction was that Pokédex Notes would matter little; the first probe gave 27/50 with Notes versus 1/50 without them. The preregistration made that failure visible and showed why the twin had to be validated experimentally, not merely constructed.
* The Gengar argument changed how I understood the evidence units: a page stating only that a Pokémon learns a move can create an artificial wrong-method distractor. This led me to keep every learn method on species pages, even though that increased the amount of information available to the examiner.
* The phase also showed me that reproducibility is not only a property of the code. The pinned commit, word list, seeds, cache, and idempotent rebuild became part of the definition of the world itself.
* Adversarial review exposed confounders that the initial tests did not capture, especially in S1, answer-slot distributions, and absence handling. I had to revise the architecture against the experimental objective, not just against the implementation.

## Failed Attempts

* I submitted once before the world was fully frozen and had to treat that version as provisional; this reinforced the need to separate build, validation, and freeze explicitly.
* The first twin-name generation produced unreadable pseudo-words and one profanity; the filters and shape constraints had to be tightened.
* The first embedding run took about 15 minutes because batches were padded to the longest unit; sorting by length and per-unit caching fixed the issue.
* The first identity probe was contaminated by Pokédex Notes: the twin remained identifiable in 27/50 cases. Removing the Notes reduced the result to 1/50.
* The 1,000-token output cap truncated 28 answers and made the initial G2 interpretation unreliable; the experiment was rerun with a 4,000-token cap, with residual invalid cases counted in both conditions.
* The initial G2 rule assumed a uniform distribution of admissible answers, but the data showed strong skew in several slots. I replaced it with the majority-answer rate for each template.
* The initial S1 design rarely tested the missing hop because base and final forms shared the same hidden ability in 82% of evolution lines; the mechanism was reclassified as material vs. benign and the plan was revised.

