"""Renderer and registry on the fictional fixture world.

Scope for the fixture: its two version groups. Withheld: Sprig's level-up
learnset in alpha-beta.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agentic_pokedex.world import render
from agentic_pokedex.world.pokeapi import iter_learnsets, read_world
from agentic_pokedex.world.registry import Registry, learn_id
from agentic_pokedex.world.render import (
    Names,
    build_registry,
    build_units,
    build_world,
    check_world,
    choose_withheld,
    render_text,
    stats,
    world_facts,
    write_units,
)
from agentic_pokedex.world.twin import (
    NameFilter,
    build_twin,
    load_dictionary,
    real_names,
)

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"
SCOPE = ("alpha-beta", "gamma")
WITHHELD = [(1, "alpha-beta")]


@pytest.fixture(scope="module")
def world() -> render.World:
    tables = read_world(RAW)
    return build_world(tables, list(iter_learnsets(RAW, tables)), SCOPE)


@pytest.fixture(scope="module")
def units(world: render.World) -> list[render.Unit]:
    return build_units(world, WITHHELD)


@pytest.fixture(scope="module")
def registry(world: render.World, units: list[render.Unit]) -> Registry:
    return build_registry(world, units, WITHHELD)


@pytest.fixture(scope="module")
def real(world: render.World) -> Names:
    return Names.real(world)


@pytest.fixture(scope="module")
def twin(world: render.World) -> Names:
    forbidden, english = real_names(RAW)
    name_filter = NameFilter(
        forbidden, load_dictionary(RAW / "words_alpha.txt"), english
    )
    return Names.twin(world, build_twin(read_world(RAW), name_filter)[0])


def texts_by_id(units: list[render.Unit], world: render.World, names: Names) -> dict:
    return {u.meta.id: render_text(u, world, names) for u in units}


# --- World model ------------------------------------------------------------


def test_world_keeps_default_entries_and_the_four_methods(world: render.World) -> None:
    assert len(world.learnsets) == 7
    assert dict(world.dropped) == {"form learnset rows": 2}
    assert {r["method"] for r in world.learnsets} == {"level-up", "machine"}


def test_notes_are_selected_per_species(world: render.World) -> None:
    assert world.notes == {
        1: ["A tiny seed that wakes at dawn."],
        4: ["Its tail flickers in the rain."],
    }


def test_world_facts(world: render.World) -> None:
    kinds: dict[str, int] = {}
    for fact in world_facts(world).values():
        kinds[fact["kind"]] = kinds.get(fact["kind"], 0) + 1
    assert kinds == {
        "evo": 2, "form": 2, "ptype": 8, "pability": 8,
        "mtype": 3, "mcat": 3, "mpower": 2, "eff": 9, "learn": 7,
    }


def test_choose_withheld(world: render.World) -> None:
    pairs = choose_withheld(world, per_group=1, seed=3)
    assert sorted(g for _, g in pairs) == ["alpha-beta", "gamma"]
    assert {p for p, _ in pairs} == {1, 4}  # the only species in both groups
    assert choose_withheld(world, per_group=1, seed=3) == pairs
    with pytest.raises(ValueError, match="eligible"):
        choose_withheld(world, per_group=2)


# --- Units and registry -----------------------------------------------------


def test_unit_inventory(units: list[render.Unit]) -> None:
    ids = [u.meta.id for u in units]
    assert len(ids) == len(set(ids)) == 28
    assert "species/3/form/10002" in ids
    assert "species/1/notes" in ids
    assert "species/3/learnset/machine/alpha-beta/0" in ids
    assert not any(i.startswith("move/3/learned-by") for i in ids)  # status move


def test_registry_is_complete(registry: Registry) -> None:
    assert registry.uncovered_facts() == []
    assert registry.unknown_facts() == []


def test_redundant_facts_are_registered_in_every_copy(registry: Registry) -> None:
    fact = learn_id(2, 1, "alpha-beta", "level-up", 1)
    assert sorted(registry.fact_units(fact)) == [
        "move/1/learned-by/alpha-beta/0",
        "species/2/learnset/level-up/alpha-beta/0",
    ]


def test_withheld_facts_are_in_no_indexed_unit(registry: Registry) -> None:
    fact = learn_id(1, 1, "alpha-beta", "level-up", 1)
    assert registry.fact_units(fact) == ["species/1/learnset/level-up/alpha-beta/0"]
    assert registry.fact_units(fact, indexed_only=True) == []
    assert registry.units["species/1/learnset/level-up/alpha-beta/0"].withheld
    assert "species/1/learnset/level-up/alpha-beta/0" not in registry.indexed_units()


def test_a_fact_is_listed_once_per_unit(units: list[render.Unit]) -> None:
    for unit in units:
        assert len(unit.meta.facts) == len(set(unit.meta.facts)), unit.meta.id


def test_registry_save_and_load(tmp_path: Path, registry: Registry) -> None:
    path = tmp_path / "registry.json"
    registry.save(path)
    loaded = Registry.load(path)
    assert loaded.facts == registry.facts
    assert loaded.units == registry.units
    assert loaded.withheld_pairs == WITHHELD


# --- Text -------------------------------------------------------------------


def test_species_profile(units, world, real) -> None:
    text = texts_by_id(units, world, real)["species/3/profile"]
    assert text == (
        "Species: Sproutree · Section: Profile\n"
        "Types: [[Moss]] / [[Tide]]\n"
        "Abilities: [[Thicket]] · Hidden ability: [[Undertow]]\n"
        "Evolution: [[Sprig]] → [[Sprout]]; [[Sprout]] → [[Sproutree]]\n"
        "Forms: [[Sproutree (Tidal Form)]]"
    )


def test_species_without_evolution(units, world, real) -> None:
    text = texts_by_id(units, world, real)["species/4/profile"]
    assert "Evolution: does not evolve" in text


def test_learnsets(units, world, real) -> None:
    texts = texts_by_id(units, world, real)
    assert texts["species/3/learnset/level-up/alpha-beta/0"] == (
        "Species: Sproutree · Section: Learnset · Method: level-up · "
        "Version: Alpha/Beta\n"
        "On evolution: [[Vine Lash]]"
    )
    assert texts["species/3/learnset/machine/alpha-beta/0"].endswith(
        "Method: machine · Version: Alpha/Beta\nMoves: [[Soak]]"
    )


def test_hub_leaves_out_withheld_entries_and_shows_types(units, world, real) -> None:
    text = texts_by_id(units, world, real)["move/1/learned-by/alpha-beta/0"]
    assert text == (
        "Move: Vine Lash · Section: Learned by · Version: Alpha/Beta\n"
        "[[Sprout]] (Moss) — level 1\n"
        "[[Sproutree]] (Moss/Tide) — on evolution"
    )


def test_move_profile_without_power(units, world, real) -> None:
    text = texts_by_id(units, world, real)["move/3/profile"]
    assert text.endswith("Type: [[Tide]] · Category: status · Power: —")


def test_holders(units, world, real) -> None:
    text = texts_by_id(units, world, real)["ability/3/holders/0"]
    assert text.split("\n")[1:] == [
        "[[Sprig]] (hidden)",
        "[[Sproutree]] (hidden)",
        "[[Sproutree (Tidal Form)]]",
    ]


def test_matchups(units, world, real) -> None:
    text = texts_by_id(units, world, real)["type/1/matchups"]
    assert text.split("\n")[1:] == [
        "Attacking — super effective against: [[Moss]]",
        "Attacking — not very effective against: [[Ember]], [[Tide]]",
        "Defending — weak to: [[Tide]]",
        "Defending — resists: [[Ember]], [[Moss]]",
    ]


def test_notes_are_free_text(units, world, real) -> None:
    unit = next(u for u in units if u.meta.id == "species/1/notes")
    assert unit.meta.free_text and unit.meta.facts == []
    assert render_text(unit, world, real).endswith("A tiny seed that wakes at dawn.")


def test_no_notes_option(world: render.World) -> None:
    ids = [u.meta.id for u in build_units(world, WITHHELD, notes=False)]
    assert not any(i.endswith("/notes") for i in ids)


# --- The registry check -----------------------------------------------------


@pytest.mark.parametrize("naming", ["real", "twin"])
def test_text_parses_back_to_the_registry(
    naming, units, registry, world, real, twin
) -> None:
    names = {"real": real, "twin": twin}[naming]
    texts = [render_text(u, world, names) for u in units]
    assert check_world(registry, units, texts, world, names) == []


def test_check_catches_a_wrong_value(units, registry, world, real) -> None:
    texts = [render_text(u, world, real) for u in units]
    i = next(i for i, u in enumerate(units) if u.meta.id == "move/1/learned-by/gamma/0")
    texts[i] = texts[i].replace("level 5", "level 6")
    problems = check_world(registry, units, texts, world, real)
    assert len(problems) == 1 and problems[0].startswith("move/1/learned-by/gamma/0")


def test_check_catches_a_missing_line(units, registry, world, real) -> None:
    texts = [render_text(u, world, real) for u in units]
    i = next(i for i, u in enumerate(units) if u.meta.id == "species/3/profile")
    texts[i] = "\n".join(t for t in texts[i].split("\n") if not t.startswith("Forms"))
    problems = check_world(registry, units, texts, world, real)
    assert problems == [
        "species/3/profile: missing ['form:10002:3'], extra []"
    ]


def test_twin_text_names_no_real_entity(units, world, twin) -> None:
    real_names_ = [
        *(s["name"] for s in world.species.values()),
        *(m["name"] for m in world.moves.values()),
        *(t["name"] for t in world.types.values()),
        *world.abilities.values(),
    ]
    pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(map(re.escape, real_names_)) + r")(?!\w)"
    )
    for unit_id, text in texts_by_id(units, world, twin).items():
        assert not pattern.search(text), (unit_id, text)


# --- Split units and cues ---------------------------------------------------


def test_split_hubs_share_a_header_without_markers(
    monkeypatch: pytest.MonkeyPatch, world: render.World, real: Names
) -> None:
    monkeypatch.setattr(render, "HUB_CHUNK", 1)
    parts = [
        u for u in build_units(world, WITHHELD)
        if u.meta.id.startswith("move/1/learned-by/alpha-beta/")
    ]
    assert [u.meta.chunks for u in parts] == [2, 2]
    heads = [render_text(u, world, real).split("\n")[0] for u in parts]
    assert heads[0] == heads[1] == (
        "Move: Vine Lash · Section: Learned by · Version: Alpha/Beta"
    )
    cued = [render_text(u, world, real, cues=True).split("\n")[0] for u in parts]
    assert cued[0].endswith("· Part 1/2") and cued[1].endswith("· Part 2/2")


# --- Names, output, stats ---------------------------------------------------


def test_duplicate_display_names_are_numbered() -> None:
    names = Names(
        species={}, pokemon={10: "Twin", 11: "Twin", 12: "Other"}, types={},
        moves={}, abilities={}, groups={}, rewrite=lambda t: t,
    )
    assert names.pokemon == {10: "Twin", 11: "Twin (2)", 12: "Other"}
    assert names.lookup("pokemon", "Twin (2)") == 11


def test_rendering_is_idempotent(tmp_path: Path, world, real) -> None:
    digests = []
    for run in range(2):
        units = build_units(world, WITHHELD)
        texts = [render_text(u, world, real) for u in units]
        digests.append(write_units(tmp_path / f"run{run}.jsonl", units, texts))
    assert digests[0] == digests[1]


def test_stats(units, world, real) -> None:
    texts = [render_text(u, world, real) for u in units]
    s = stats(units, texts)
    assert (s["units"], s["indexed"], s["withheld"], s["free_text"]) == (28, 27, 1, 2)
    assert s["by_section"]["species/Learnset/level-up"] == 6
