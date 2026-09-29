"""The fact → units registry: which evidence units state which graph facts.

The sufficiency label is a pure function over this registry (ADR-002): a state
is sufficient when the units seen cover a minimal sufficient set of facts. So
the registry must be **exact** — every in-scope fact in at least one unit, every
copy of a fact known — and it is checked, not assumed (``render.check_world``).

A fact id carries its full content, so two renderings agree on a fact only if
they agree on its value::

    evo:{species}:{parent}                      species evolves from parent
    form:{pokemon}:{species}                    a non-default entry of species
    ptype:{pokemon}:{slot}:{type}
    pability:{pokemon}:{ability}:{hidden|regular}
    mtype:{move}:{type}    mpower:{move}:{power}    mcat:{move}:{category}
    eff:{attacker}:{defender}:{factor}          damage factor, percent
    learn:{pokemon}:{move}:{version_group}:{method}[:{level}]

Ability ids are **canonical**: abilities sharing an English name ("As One") are
one page and one id, the smallest.

The registry is naming-independent: the twin and the real world share it; only
unit text differs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

Fields = dict[str, Any]


def evo_id(species: int, parent: int) -> str:
    """Fact: ``species`` evolves from ``parent``."""
    return f"evo:{species}:{parent}"


def form_id(pokemon: int, species: int) -> str:
    """Fact: ``pokemon`` is a non-default entry (form) of ``species``."""
    return f"form:{pokemon}:{species}"


def ptype_id(pokemon: int, slot: int, type_id: int) -> str:
    """Fact: ``pokemon`` has ``type_id`` in ``slot``."""
    return f"ptype:{pokemon}:{slot}:{type_id}"


def pability_id(pokemon: int, ability: int, hidden: bool) -> str:
    """Fact: ``pokemon`` has ``ability`` (canonical id), hidden or regular."""
    return f"pability:{pokemon}:{ability}:{'hidden' if hidden else 'regular'}"


def mtype_id(move: int, type_id: int) -> str:
    """Fact: ``move`` has type ``type_id``."""
    return f"mtype:{move}:{type_id}"


def mpower_id(move: int, power: int) -> str:
    """Fact: ``move`` has base power ``power``."""
    return f"mpower:{move}:{power}"


def mcat_id(move: int, category: str) -> str:
    """Fact: ``move`` is physical, special or status."""
    return f"mcat:{move}:{category}"


def eff_id(attacker: int, defender: int, factor: int) -> str:
    """Fact: ``attacker`` deals ``factor`` percent damage to ``defender``."""
    return f"eff:{attacker}:{defender}:{factor}"


def learn_id(
    pokemon: int, move: int, version_group: str, method: str, level: int | None
) -> str:
    """Fact: ``pokemon`` learns ``move`` in ``version_group`` by ``method``."""
    base = f"learn:{pokemon}:{move}:{version_group}:{method}"
    return base if level is None else f"{base}:{level}"


@dataclass
class UnitMeta:
    """One evidence unit: where it sits and what it states.

    Attributes:
        id: Stable unit id, e.g. ``species/6/learnset/level-up/x-y/0``.
        page: Page kind: ``species``, ``move``, ``ability`` or ``type``.
        key: Id of the page's entity (canonical id for abilities).
        section: Section title (``Profile``, ``Learnset``, ``Form``, ``Notes``,
            ``Learned by``, ``Holders``, ``Matchups``).
        method: Learn method, for learnset sections.
        version_group: Version-group identifier, for versioned sections.
        form: Pokémon id of the form, for ``Form`` sections.
        chunk: 0-based position of the unit among units with the same header.
        chunks: Number of units sharing the header.
        free_text: Prose outside the registry (Pokédex notes).
        withheld: Left out of the index (S4); still registered.
        facts: Ids of the facts the unit states.
    """

    id: str
    page: str
    key: int
    section: str
    method: str | None = None
    version_group: str | None = None
    form: int | None = None
    chunk: int = 0
    chunks: int = 1
    free_text: bool = False
    withheld: bool = False
    facts: list[str] = field(default_factory=list)


@dataclass
class Registry:
    """Facts, units, and the index from each fact to every unit stating it."""

    facts: dict[str, Fields]
    units: dict[str, UnitMeta]
    version_scope: tuple[str, ...]
    withheld_pairs: list[tuple[int, str]]

    def __post_init__(self) -> None:
        index: dict[str, list[str]] = defaultdict(list)
        for unit in self.units.values():
            for fact in unit.facts:
                index[fact].append(unit.id)
        self._fact_units = dict(index)

    def fact_units(self, fact: str, *, indexed_only: bool = False) -> list[str]:
        """Every unit stating ``fact`` (only indexed ones if asked)."""
        units = self._fact_units.get(fact, [])
        if indexed_only:
            return [u for u in units if not self.units[u].withheld]
        return list(units)

    def indexed_units(self) -> list[str]:
        """Ids of the units the index serves (withheld ones excluded)."""
        return [u.id for u in self.units.values() if not u.withheld]

    def uncovered_facts(self) -> list[str]:
        """Facts no unit states — must be empty."""
        return sorted(f for f in self.facts if f not in self._fact_units)

    def unknown_facts(self) -> list[str]:
        """Facts stated by a unit but absent from the fact table — must be empty."""
        return sorted(f for f in self._fact_units if f not in self.facts)

    def save(self, path: Path) -> None:
        """Write the registry as JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version_scope": list(self.version_scope),
            "withheld_pairs": [list(p) for p in self.withheld_pairs],
            "facts": self.facts,
            "units": [asdict(u) for u in self.units.values()],
        }
        path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Registry:
        """Read a registry written by ``save``."""
        payload = json.loads(path.read_text(encoding="utf-8"))
        units = {u["id"]: UnitMeta(**u) for u in payload["units"]}
        return cls(
            facts=payload["facts"],
            units=units,
            version_scope=tuple(payload["version_scope"]),
            withheld_pairs=[(int(p), str(g)) for p, g in payload["withheld_pairs"]],
        )
