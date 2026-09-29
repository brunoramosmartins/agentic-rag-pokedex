"""E-003, the identity probe: the identity half of G2 (``docs/contingency.md``).

Can the primary model name the real species behind a twin page? A positive
control — the real page with the species' own name masked — shows the probe can
detect identification at all. A third condition, the twin page without its
Pokédex notes, attributes a leak to the flavor text. Everything here is pure;
``scripts/identity_probe.py`` runs it through the Batch API.

The registry entry (``experiments/registry.md``, E-003) governs; the constants
below restate it.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from agentic_pokedex.evaluation.intervals import wilson
from agentic_pokedex.tools.contract import TOKEN_CAP, TokenCounter, pack
from agentic_pokedex.world.index import Unit
from agentic_pokedex.world.render import World
from agentic_pokedex.world.twin import normalize

PROBE_SEED = 20260929
QUOTAS: Mapping[int, int] = {1: 6, 2: 6, 3: 6, 4: 6, 5: 6, 6: 5, 7: 5, 8: 5, 9: 5}
"""Species per generation: 50 in total."""

CONTROL, TWIN, TWIN_NO_NOTES = "control", "twin", "twin_no_notes"
CONDITIONS = (CONTROL, TWIN, TWIN_NO_NOTES)
MASK = "[MASKED]"

CONTROL_MIN_RATE = 0.50
"""Below this, the probe is broken, not the twin safe."""
TWIN_MAX_RATE = 0.10
"""Above this, G2 fails."""

MODEL = "gpt-5-mini"
REASONING_EFFORT = "low"
MAX_COMPLETION_TOKENS = 4_000
"""Output cap, reasoning included. 1,000 in the first run; 28 of 100 twin calls
spent it all on reasoning (amendment of 2026-09-29)."""
VISIBLE_OUTPUT_TOKENS = 25
RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "identity_guess",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "guess": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["guess", "confidence"],
            "additionalProperties": False,
        },
    },
}


# --- Sample -----------------------------------------------------------------


def eligible_species(world: World) -> list[int]:
    """Species whose default entry has a level-up learnset in the scope."""
    species = {
        world.pokemon[r["pokemon_id"]]["species_id"]
        for r in world.learnsets
        if r["method"] == "level-up"
    }
    return sorted(species)


def sample_species(
    world: World, quotas: Mapping[int, int] = QUOTAS, seed: int = PROBE_SEED
) -> list[int]:
    """Draw the probe's species, stratified by generation.

    Raises:
        ValueError: A generation has fewer eligible species than its quota.
    """
    by_generation: dict[int, list[int]] = defaultdict(list)
    for sid in eligible_species(world):
        by_generation[world.species[sid]["generation"]].append(sid)
    rng = random.Random(seed)
    chosen: list[int] = []
    for generation in sorted(quotas):
        pool = by_generation.get(generation, [])
        if len(pool) < quotas[generation]:
            raise ValueError(
                f"generation {generation}: {len(pool)} eligible, "
                f"{quotas[generation]} needed"
            )
        chosen += sorted(rng.sample(pool, quotas[generation]))
    return chosen


# --- Pages ------------------------------------------------------------------


def species_units(units: Iterable[Unit], sid: int) -> list[Unit]:
    """The indexed units of a species page, in page order."""
    prefix = f"species/{sid}/"
    return [u for u in units if u.id.startswith(prefix)]


def mask_name(text: str, name: str) -> str:
    """Replace every whole-word occurrence of ``name``, in any case."""
    return re.sub(rf"(?<!\w){re.escape(name)}(?!\w)", MASK, text, flags=re.IGNORECASE)


def serve(units: Sequence[Unit], counter: TokenCounter, cap: int = TOKEN_CAP) -> str:
    """The page as ``open_page(title)`` returns it: from the top, under the cap."""
    return pack(units, counter, cap).text


def condition_page(
    condition: str,
    sid: int,
    world: World,
    real_units: Sequence[Unit],
    twin_units: Sequence[Unit],
    counter: TokenCounter,
) -> str:
    """The text the model sees for one species in one condition.

    - control: the real page, the species' own name masked in every unit
      (forms containing it are masked too), then served;
    - twin: the twin page, served;
    - twin, no notes: the twin page without its ``Notes`` unit, served.
    """
    if condition == CONTROL:
        name = world.species[sid]["name"]
        units = [
            Unit(u.id, MASK, u.section, mask_name(u.text, name))
            for u in species_units(real_units, sid)
        ]
    elif condition == TWIN:
        units = species_units(twin_units, sid)
    elif condition == TWIN_NO_NOTES:
        units = [u for u in species_units(twin_units, sid) if u.section != "Notes"]
    else:
        raise ValueError(f"unknown condition {condition!r}")
    if not units:
        raise ValueError(f"species {sid} has no indexed unit")
    return serve(units, counter)


def custom_id(condition: str, sid: int) -> str:
    """Stable request id: ``e003-{condition}-{species}``."""
    return f"e003-{condition}-{sid}"


def parse_custom_id(value: str) -> tuple[str, int]:
    """Inverse of ``custom_id``."""
    _, rest = value.split("-", 1)
    condition, sid = rest.rsplit("-", 1)
    return condition, int(sid)


# --- Grading ----------------------------------------------------------------


def accepted_names(world: World, sid: int) -> tuple[set[str], set[str]]:
    """Normalized real names that count as identifying ``sid``.

    Returns:
        ``(line, exact)``: every species and form of the evolution line (the
        governing rule), and the species with its own forms (descriptive).
    """

    def names_of(species: Iterable[int]) -> set[str]:
        wanted = set(species)
        names = {world.species[s]["name"] for s in wanted}
        names |= {
            p["name"] for p in world.pokemon.values() if p["species_id"] in wanted
        }
        return {normalize(n) for n in names} - {""}

    chain = world.chains[world.species[sid]["evolution_chain_id"]]
    return names_of(chain), names_of([sid])


def parse_guess(content: str | None) -> tuple[str, float] | None:
    """``(guess, confidence)`` from a structured answer, or ``None`` if invalid."""
    if content is None:
        return None
    try:
        data = json.loads(content)
        guess, confidence = data["guess"], float(data["confidence"])
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(guess, str):
        return None
    return guess, confidence


@dataclass(frozen=True)
class ProbeRow:
    """One graded answer."""

    species_id: int
    generation: int
    condition: str
    guess: str
    confidence: float
    identified: bool
    exact: bool


def grade(
    world: World, condition: str, sid: int, guess: str, confidence: float
) -> ProbeRow:
    """Grade one guess; "unknown" and anything outside the line are misses."""
    line, exact = accepted_names(world, sid)
    key = normalize(guess)
    return ProbeRow(
        species_id=sid,
        generation=world.species[sid]["generation"],
        condition=condition,
        guess=guess,
        confidence=confidence,
        identified=key in line,
        exact=key in exact,
    )


# --- Summary and decision ---------------------------------------------------


@dataclass(frozen=True)
class ConditionSummary:
    """Counts of one condition, N-of-M over its valid answers."""

    condition: str
    valid: int
    identified: int
    exact: int
    unknown: int
    by_generation: dict[int, tuple[int, int]]

    @property
    def rate(self) -> float:
        """Identified share of valid answers."""
        return self.identified / self.valid if self.valid else 0.0

    @property
    def interval(self) -> tuple[float, float]:
        """Wilson 95% interval of ``rate``."""
        return wilson(self.identified, self.valid)


def summarize(rows: Iterable[ProbeRow]) -> dict[str, ConditionSummary]:
    """Per-condition counts, with per-generation identified-of-valid."""
    grouped: dict[str, list[ProbeRow]] = defaultdict(list)
    for row in rows:
        grouped[row.condition].append(row)
    summary = {}
    for condition, items in grouped.items():
        by_gen: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        for r in items:
            by_gen[r.generation][0] += r.identified
            by_gen[r.generation][1] += 1
        summary[condition] = ConditionSummary(
            condition=condition,
            valid=len(items),
            identified=sum(r.identified for r in items),
            exact=sum(r.exact for r in items),
            unknown=sum(normalize(r.guess) == "unknown" for r in items),
            by_generation={g: (k, n) for g, (k, n) in sorted(by_gen.items())},
        )
    return summary


def decide(summary: Mapping[str, ConditionSummary]) -> str:
    """Apply E-003's decision rule.

    Returns:
        ``"probe broken"``, ``"pass"``, ``"fail: notes"`` (the twin leaks, the
        no-notes condition does not) or ``"fail: structural"``.
    """
    if summary[CONTROL].rate < CONTROL_MIN_RATE:
        return "probe broken"
    if summary[TWIN].rate <= TWIN_MAX_RATE:
        return "pass"
    if summary[TWIN_NO_NOTES].rate <= TWIN_MAX_RATE:
        return "fail: notes"
    return "fail: structural"


def _with_invalid(
    s: ConditionSummary, invalid: int, identified: bool
) -> ConditionSummary:
    return ConditionSummary(
        condition=s.condition,
        valid=s.valid + invalid,
        identified=s.identified + (invalid if identified else 0),
        exact=s.exact,
        unknown=s.unknown,
        by_generation=s.by_generation,
    )


def decide_bounded(
    summary: Mapping[str, ConditionSummary], invalid: Mapping[str, int]
) -> str:
    """The decision rule when some answers stayed invalid (amendment 2026-09-29).

    Invalid answers are not missing at random — they are the calls where the
    model reasoned longest — so they are counted both ways. **Worst case for
    the twin:** every invalid twin answer identified, every invalid control
    answer a miss; best case: the opposite. A verdict both cases share is
    taken; otherwise the result reads "undetermined: worst / best".
    """
    worst = {
        c: _with_invalid(s, invalid.get(c, 0), identified=(c != CONTROL))
        for c, s in summary.items()
    }
    best = {
        c: _with_invalid(s, invalid.get(c, 0), identified=(c == CONTROL))
        for c, s in summary.items()
    }
    low, high = decide(worst), decide(best)
    return low if low == high else f"undetermined: {low} / {high}"
