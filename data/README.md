# data/

| Directory | Versioned | Contents |
|---|---|---|
| `raw/` | **No** (gitignored) | PokéAPI CSVs, downloaded by `world/download.py` with SHA-256 checks |
| `world/` | **No** (gitignored) | Graph export, twin map, rendered pages, index — regenerable from the seed |
| `splits/` | Yes | Opaque question ids per split and `manifest.json` (seed, allocation, hashes, distributions) — never question text or answers |

Raw PokéAPI data and Pokédex text are never committed: names and game text are
intellectual property of Nintendo, Creatures Inc. and GAME FREAK inc. See
[`docs/data-sources.md`](../docs/data-sources.md) for licenses and the
published-benchmark decision.
