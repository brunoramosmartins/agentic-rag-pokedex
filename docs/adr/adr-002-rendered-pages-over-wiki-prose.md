# ADR-002 — Rendered Pages over Wiki Prose

**Status:** Accepted (Phase 0, 2026-09-25).

## Context

The agent needs a corpus to read. Two options exist:

1. **Real wiki prose** (e.g. Bulbapedia): realistic, messy text.
2. **Pages rendered from the graph**: every fact comes from PokéAPI, laid out as
   sectioned pages.

The thesis depends on a **per-step sufficiency label that is exact**: given the
units the agent has seen up to step t, is the evidence enough? That requires
knowing, for every fact in the gold chain, every unit of text that states it.
With free prose, that mapping is an annotation problem with its own error rate,
and the error lands directly in the mechanism metrics (detector precision and
recall per step). Bulbapedia is also licensed CC BY-NC-SA, which complicates
publishing a derived benchmark.

## Decision

The corpus is **rendered from the graph** (`world/render.py`):

- **One page per entity** (species, move, ability, type), split into **sections
  of ~100–400 tokens**. Each section is an **evidence unit** with a metadata
  header, like a wiki section title:
  `Species: Vexmoor · Section: Learnset · Version: Ambergleam`.
- **Typed links** inside the text (`Evolves into: [[Tarnlet]]`) form the implicit
  graph that the fixed pipeline expands and the agent can follow with
  `open_page`.
- **Controlled redundancy.** Some facts appear in two places (the learnset on
  the species page and "Learned by" on the move page). The **fact → units
  registry** (`world/registry.py`) knows every copy, so the label stays exact
  under redundancy.
- **Hubs split into units without truncation cues** (see ADR-009).
- **Withheld units** (for S4) leave the index and are recorded in the registry.
- Pokédex flavor text is kept (renamed through the twin map) for realism; it is
  the first thing removed if the twin leaks (G2, ADR-003).

## Consequences

- The sufficiency label is a **pure function** over the registry, tested
  against hand-built trajectories (measurability gate 7).
- Gate 7 check for the renderer: every graph fact appears in ≥ 1 unit and the
  fact → units registry is complete.
- **Free text is outside the registry.** Pokédex flavor text is prose; the
  registry cannot know whether a flavor unit states a gold fact (an evolution,
  a type). An unregistered unit that gives the answer away makes the label say
  `insufficient` while the agent holds the evidence, and the error lands in the
  detector's precision and recall — it looks like a detector mistake and is a
  labeler mistake. The labeler's golden trajectories cannot catch this: they
  take the registry as given.
- **Shortcut scan** (`examiner/`, gate 7), run on every generated question: any
  unit that mentions the question's anchor entity **together with** the answer
  (name or alias) and is not registered as carrying a gold-chain fact flags the
  question. For numeric answers, the scan looks for the number in units of the
  entity that owns the attribute (a bare "42" matches everywhere). Flagged
  questions are inspected and re-labelled or discarded, with N-of-M published
  in `docs/examiner.md`. The scan is itself checked on **planted leaks**,
  including one in flavor text, before it is trusted.
- The scan is lexical and misses paraphrase ("it grows into a fearsome
  dragon"), so the G3 audit also reads the flavor text of the entities on
  every audited chain.
- **Declared limitation:** rendered text is cleaner than real documents — no
  contradictions, no internal jargon. Exactness of the label is chosen over
  realism. Real prose is parked as an external-validity idea (open-ideas).
- The benchmark can be regenerated locally from the generator + seeds, which
  helps the publication decision in `docs/data-sources.md`.

## Updates

### 2026-09-29 — Pokédex flavor text removed from world v1

The decision above kept the flavor text for realism and named it the first
thing to remove if the twin leaked. It leaked (E-003; ADR-003, Updates), so
world v1 has no notes. Consequences here: every unit of the corpus is now
generated from registered facts, so no free text sits outside the registry;
the shortcut scan loses its flavor-text case and the G3 audit its flavor read
(plan impact PI-013). The declared limitation grows: the rendered corpus is
cleaner still, with no prose at all.

### 2026-09-29 — Profiles link forward only

Species Profiles first showed the whole evolution line, as wikis do. Designing
the examiner's templates showed the cost: the final form's Profile named the
anchor of every evolution-based S1 question and held its answer, so one unit
answered a question built to need two, and the single-unit shortcut filter
discarded all of them. Profiles now show only the species a species evolves
into, and a final form states "Evolves into: —" — a registered fact, so an
agent that reaches it has evidence that the line ends there. To find a
pre-evolution, the agent searches. The corpus is shaped for question validity
here, and says so (PI-017).

### 2026-09-29 — The shortcut scan reads statements, not units

The scan above flags "any unit that mentions the anchor together with the
answer". Built on the rendered pages, that reads two facts on different lines
as one: a pre-evolution's Profile names the anchor ("Evolves into") and its own
hidden ability, and the unit-level scan flagged 2,064 questions, the extra 778
all of that kind. The scan now reads **statements** — a body line with its
unit's header, or a whole free-text unit, so prose is still read as a block —
and scans the twin pages, since real names collide lexically. Flags are
resolved by class with a written verdict; the first scan flagged 1,286
questions in 18 classes, all coincidences, and discarded none. Every run plants
leaks first, one of them in prose, and requires all flagged
(`docs/examiner.md`, "Shortcut scan").

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Bulbapedia prose | NC-SA license; fact alignment error-prone; label no longer exact |
| Rendered pages with no redundancy | Unrealistically clean: one fact, one place. Redundancy is bought at no loss of exactness through the registry |
| One unit per page | Pages too long for B = 4,000; the unit of evidence must be finer than the page for the label to mean anything |

## References

- [`measurability-gate.md`](../measurability-gate.md) — gate 7, renderer check
- [`notes/ho-2020-2wikimultihopqa.md`](../../notes/ho-2020-2wikimultihopqa.md) — §5.4, Wikipedia × Wikidata mismatches
- ADR-003 (twin), ADR-009 (no truncation cues)
