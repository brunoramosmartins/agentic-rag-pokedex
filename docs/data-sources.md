# Data Sources and Licenses

**Status:** G1 evaluated 2026-09-24 — **pass**. Every source has a verdict
below; the evidence (license files, pinned commit, SHA-256 hashes, coverage
counts) was collected the same day. See [`contingency.md`](contingency.md) for
the gate definition.

---

## Summary

| Source | Content | Role | License | G1 verdict |
|---|---|---|---|---|
| PokéAPI (CSV) | Species, forms, types, type efficacy, moves, abilities, evolution chains, learnsets per version group | World + gold | BSD-3-Clause (code and data files) | **ok-with-restriction** |
| Pokédex flavor text (inside PokéAPI) | Game prose per species and version | Corpus realism | Game text copyrighted by Nintendo / Creatures / GAME FREAK | **ok-with-restriction** |
| English word list (`dwyl/english-words`) | 370,105 English words | Filter for twin names (Phase 1) | Unlicense (public domain) | **ok** |
| MuSiQue v1.0 | Multi-hop QA with answerable / unanswerable pairs | External calibration (v1.2) | CC BY 4.0 | **ok** |
| Generated benchmark (this project's output) | Twin questions, answers, gold chains, step labels | Publishable asset | MIT (this repo) for what is published — see below | Decided below |

**Standing restriction for every PokéAPI-derived file:** raw CSVs, the rendered
world and Pokédex text are **never committed**. `data/raw/` and `data/world/`
are gitignored; everything arrives through a download script with hash checks.

---

## PokéAPI

- **Repository:** <https://github.com/PokeAPI/pokeapi>, data in `data/v2/csv/`.
- **License:** BSD-3-Clause (`LICENSE.md`, SPDX `BSD-3-Clause` per the GitHub
  license API). The license file itself states that Pokémon and character
  names are trademarks of Nintendo.
- **Pinned commit:** `6bbd96bb8ef7356963b833074ca25672d23e41c4` (master,
  2026-09-24), confirmed in Phase 1. `world/download.py` fetches from this
  commit, not from `master`, so the world is reproducible. Its `MANIFEST` is
  the source of truth for every hash below.

**SHA-256 of the files sampled for G1** (at the pinned commit):

| File | SHA-256 |
|---|---|
| `abilities.csv` | `74c3588ad48e08e54ff01f432899a4028c3e91508bbd53201df85e1f6b9e9ef3` |
| `evolution_chains.csv` | `5159f0481eaa786f2b08e58356bcc6271e0982dceeb69746aaac4637d5a47125` |
| `moves.csv` | `8aafd37bf78f19471495c05b201545180f50f0a08a2a2a844d69f9837dd39ac9` |
| `pokemon.csv` | `16c81c33188b0eac403aa2f759fcbe9e42c611f722d263f5b5a6a5bff9f8ce6b` |
| `pokemon_abilities.csv` | `4a79ee53d386a8ad3a89657483ddfd31594e05a5d52400fe131e5e4dfd7ec04a` |
| `pokemon_move_methods.csv` | `78b75acfcf6dca4c82da9d4851357cbbd65e61b08154eddfc2ace0efd00e408e` |
| `pokemon_moves.csv` | `22a807cef26891eeac0d0c900bd363e66baf421f7ee795bc7bc3e718f23b939e` |
| `pokemon_species.csv` | `e66e2eeb25fd3836b0ebab6bf87bbf01960aa3c0555e2bac495fa8393c5e0c45` |
| `pokemon_species_flavor_text.csv` | `c341e602ab623084fef4c44ca4a174938e617802cfcf2deec830d824f688dc69` |
| `pokemon_types.csv` | `f1fc4bfd657a034ea3bf6972423b10276424aa068577b304a78a08996425ba05` |
| `type_efficacy.csv` | `cdd7de4066680414d0a2433af805f139f425d6350cbf998ecab559a0fe8ff587` |
| `types.csv` | `37f039c8d722f47d51ba1c5c5ecf9b7007235b1a9a1af2827645c777b70307c8` |
| `version_groups.csv` | `28da8d89d8eb4966941f81a9e62b3990510ed4d76dd774158246551a8e7707a7` |
| `versions.csv` | `70083465865a6a69a9aad2be3fc3915078c6ff740f14a090b1367d8ec9cfc3cd` |

**Added in Phase 1** (English names, move categories, forms), same commit. The
14 hashes above were re-checked on 2026-09-29 and all match.

| File | SHA-256 |
|---|---|
| `ability_names.csv` | `8acb80c42210f86ae747dc3347b060d69cd2574a9dbfaf74774ae632ca6348da` |
| `languages.csv` | `fbb60019a6a461783d5671a995d5f590db61792a273e90faa0ed630d102a19b8` |
| `move_damage_classes.csv` | `b7101ceca4dff152537a2fb5c439ca4030b05f86442c643812c0b7b6ccf16f1b` |
| `move_names.csv` | `99e23ee38ea53d1473474d463b87651deac3cd4928750f8186feae66da45c147` |
| `pokemon_form_names.csv` | `f496066d02fab12c18d10cce0af2f748d09cb7e296ecc784cc8682f8c4da8625` |
| `pokemon_forms.csv` | `99bf8f7ad4dc1f2e291357a090cef6a575623ec3cbf9030d0e33656e6e608ae2` |
| `pokemon_species_names.csv` | `820cde17074cdb1c2b0595c997fb8f998e773bd5da3bb525dec85703c86c5fd9` |
| `type_names.csv` | `685230c51074cf2f723debcf827a4df4c36ab0ec7e929c806ad65a3e40958705` |
| `version_names.csv` | `23e3e9062f98e1f83d475b9eeac57ddff4375b46c175948a65c4fe8d3e1d87b4` |

**Added in Phase 2** (which form must evolve; PI-019), same commit.

| File | SHA-256 |
|---|---|
| `pokemon_evolution.csv` | `66495e349599befb48ef677e2c34c3d1aa0288e83b99277d944bbf495a743341` |

### Learnset coverage by version group

At the pinned commit: 1,025 species, 1,351 Pokémon entries (forms included),
32 version groups. Counts of `pokemon_moves.csv` rows and of Pokémon entries
with a learnset, for the candidate groups:

| Version group | Gen | Learnset rows | Entries with a learnset | Entries with level-up moves | Species covered |
|---|---:|---:|---:|---:|---:|
| scarlet-violet | 9 | 54,658 | 867 | 867 | 733 |
| sword-shield | 8 | 44,204 | 750 | 750 | 664 |
| brilliant-diamond-shining-pearl | 8 | 24,797 | 491 | 491 | 488 |
| ultra-sun-ultra-moon | 7 | 62,019 | 959 | 959 | 807 |
| sun-moon | 7 | 49,542 | 944 | 944 | 802 |
| omega-ruby-alpha-sapphire | 6 | 54,392 | 811 | 811 | 721 |
| x-y | 6 | 42,886 | 784 | 784 | 721 |

**Findings that constrain Phase 1 (version scope) and Phase 2 (generator):**

1. **DLC version groups are empty.** `the-isle-of-armor`, `the-crown-tundra`,
   `the-teal-mask` and `the-indigo-disk` have 0 learnset rows; their moves are
   folded into the base group. Scope uses base groups only.
2. **Adjacent generations barely differ.** Among level-up (species, move) pairs
   present in both groups, the level differs in **3%** for scarlet-violet vs
   sword-shield (210 of 6,971), **59%** for scarlet-violet vs
   ultra-sun-ultra-moon (4,545 of 7,688) and **82%** for sword-shield vs
   ultra-sun-ultra-moon (6,615 of 8,096). Stratum S2 (wrong version) needs the
   near-certain section to give a **different** answer, otherwise answering from
   the wrong version is correct by accident. Consequences: (a) the 3–4 version
   groups chosen in Phase 1 should span generations, not be adjacent; (b) the
   S2 generator keeps only pairs whose level differs between the asked version
   and **every other version group in the corpus** — otherwise answering from a
   third version is correct by accident (a filter with an N-of-M count in
   `docs/examiner.md`).
3. **Pokédex text does not follow learnset coverage.** English flavor text
   exists for 721 species in x-y / omega-ruby-alpha-sapphire, 609 in
   sword-shield, but only **120** in scarlet / violet. Flavor text is attached
   per species from whichever version has it, independent of the learnset
   version groups.

**Verdict: ok-with-restriction.** BSD-3 confirmed, CSV available at a pinned
commit, complete learnsets for the candidate base groups. Restrictions: names
and game text are third-party IP (never committed; trademark notice in README
and demo), and the version scope must satisfy finding 2.

---

## Pokédex flavor text

- Source: `pokemon_species_flavor_text.csv` in PokéAPI (hash above).
- The file is distributed with PokéAPI, but the text itself is game prose
  whose copyright belongs to Nintendo, Creatures Inc. and GAME FREAK inc. The
  BSD-3 license of the repository does not grant rights over it.
- Used **only in the local corpus**, renamed through the twin map. It is also
  the first suspect for identity leakage (G2) and the first thing removed if the
  twin leaks.
- **Not in world v1 (2026-09-29).** The identity probe (E-003) confirmed the
  leak: renamed flavor text still let the model name the species. The pages
  carry no notes; the file is still downloaded, to reproduce E-003 and for the
  renderer's research option `--notes`.

**Verdict: ok-with-restriction** — local use only; never committed, never
published, in real or renamed form.

---

## English word list (twin filter)

- Source: `words_alpha.txt` from <https://github.com/dwyl/english-words>, pinned
  at commit `8179fe68775df3f553ef19520db065228e65d1d3` (last change to the file
  on 2025-01-05). SHA-256
  `3ed0c94610d8bcf7c11bbb49c56aa49c7234d32b66824df91f554169e572da48`.
- License: Unlicense (public domain).
- Use: no twin pseudo-word may be an English word (`world/twin.py`). It is
  fetched by `world/download.py` with the CSVs. A system dictionary would make
  the twin depend on the machine; pinned, the published seed rebuilds the same
  twin everywhere.

**Verdict: ok.**

---

## MuSiQue v1.0

- **Repository:** <https://github.com/StonyBrookNLP/musique>. **License:**
  CC BY 4.0 (`LICENSE`, SPDX `CC-BY-4.0`); the README states the same.
  Attribution to Trivedi et al. (TACL 2022) is required wherever results on it
  are published.
- **Archive:** `musique_v1.0.zip` from the Google Drive link in the README
  (id `1tGdADlNjWFaHLeZZGShh2IRcpO6Lv24h`), 272,049,578 bytes, SHA-256
  `98f839bf2fd5319f5c688aed77901a6d5c30b3b9f9f691ab9a8ecafb045ee0cd`.
- `musique_full_v1.0_dev.jsonl`: SHA-256
  `8cab31d56a3a1c4ef491b205a8dab3f1ac9c66e472098c6cf1de4e20294f7a4a`;
  **4,834 questions = 2,417 answerable + 2,417 unanswerable**, with answers,
  aliases, paragraphs and decompositions (2-hop 2,504; 3-hop 1,520; 4-hop 810).
- **The Full test split has no labels** (`id`, `paragraphs`, `question` only).
  The v1.2 calibration sample (30 answerable + 30 unanswerable counterparts)
  is therefore drawn from **dev**, with a registered seed.
- The README's leakage caution concerns training on MuSiQue's seed single-hop
  datasets. This project trains nothing on them, so it does not apply.

**Verdict: ok.**

---

## Published benchmark — what goes out

Decision (Phase 0): the published benchmark contains **only twin-side,
fact-level material**, and the corpus is rebuilt locally.

| Published (JSONL + generator code) | Not published |
|---|---|
| Question id, stratum, template id, twin-side question text | Real-name question text |
| Canonical answer and aliases (twin names, numbers) | The twin → real name map |
| Gold chain as fact ids; minimal sufficient sets, near-certain and withheld units as unit ids | Rendered pages or any unit text |
| Split ids and seeds; the pinned PokéAPI commit; the twin seed | Pokédex text, real or renamed |
| Per-step labels of published trajectories (unit ids only) | Raw PokéAPI CSVs |

Anyone can reproduce the corpus with the pinned commit + the generator + the
seeds. Twin names are seeded pseudo-words filtered against real names, which
also keeps trademarks out of the published files.

**Documentation examples (amended 2026-09-29).** Docs and the README may show
a few twin-side rendered pages or units as examples (`docs/world.md` shows one
page per entity type; later phases render cases of prompt, evidence and
completion). Every flavor-text unit in them is elided and replaced by a marker
such as `[flavor text — 2 units, local only]`. What remains is PokéAPI fact
content under twin names. Real-name pages, the twin → real name map and
Pokédex text, real or renamed, are never shown. The benchmark files themselves
still carry unit ids only.

---

## LLM prices (verified 2026-09-24)

Source: OpenAI API pricing page (<https://developers.openai.com/api/docs/pricing>),
per million tokens. Registered runs use the **Batch** tier. Reasoning tokens are
billed as output.

| Model | Tier | Input | Cached input | Output |
|---|---|---:|---:|---:|
| gpt-5-mini | Standard | US$ 0.25 | US$ 0.025 | US$ 2.00 |
| gpt-5-mini | **Batch** | **US$ 0.125** | US$ 0.0125 | **US$ 1.00** |
| gpt-4o-mini | Standard | US$ 0.15 | US$ 0.075 | US$ 0.60 |
| gpt-4o-mini | **Batch** | **US$ 0.075** | — | **US$ 0.30** |

Prices change without notice. They are re-checked before every registered run
and the value used is written in that run's registry entry, next to the
measured cost. Budget caps per release are in
[ADR-008](adr/adr-008-models-gpt5mini-primary-4omini-replication.md).

---

## Trademark notice (README and demo)

> Pokémon and all related names are trademarks of Nintendo, Creatures Inc. and
> GAME FREAK inc. This is an unofficial, non-commercial fan project, not
> affiliated with or endorsed by them. Game data from PokéAPI (BSD-3-Clause).
