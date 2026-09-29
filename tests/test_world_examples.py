"""Example pages for the docs: twin-side, notes elided."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_pokedex.world.examples import elide, main, page_markdown
from agentic_pokedex.world.index import Unit, load_units
from agentic_pokedex.world.registry import Registry


@pytest.fixture(scope="module")
def twin_units(fixture_world_dir: Path) -> list[Unit]:
    registry = Registry.load(fixture_world_dir / "registry.json")
    return load_units(fixture_world_dir / "pages" / "twin.jsonl", registry)


def test_elide_replaces_notes_only() -> None:
    notes = Unit("species/1/notes", "T", "Notes", "Species: T · Section: Notes\nA.\nB.")
    assert elide(notes) == (
        "Species: T · Section: Notes\n[flavor text — 2 texts, local only]"
    )
    one = Unit("species/1/notes", "T", "Notes", "Species: T · Section: Notes\nA.")
    assert elide(one).endswith("[flavor text — 1 text, local only]")
    profile = Unit("species/1/profile", "T", "Profile", "Species: T\nTypes: [[X]]")
    assert elide(profile) == profile.text


def test_species_page_markdown(twin_units: list[Unit]) -> None:
    text = page_markdown(twin_units, "species:1")
    assert text.startswith("#### Species page: ")
    assert "(3 units)" in text  # profile, notes, gamma learnset (alpha-beta withheld)
    assert text.count("```") == 6
    assert "A tiny seed" not in text
    assert "[flavor text — 1 text, local only]" in text


def test_single_unit_page(twin_units: list[Unit]) -> None:
    assert "(1 unit)" in page_markdown(twin_units, "type:1")


def test_unknown_page(twin_units: list[Unit]) -> None:
    with pytest.raises(ValueError, match="species:99"):
        page_markdown(twin_units, "species:99")


def test_examples_are_twin_only(fixture_world_dir: Path) -> None:
    assert main(["--world-dir", str(fixture_world_dir), "--pages", "real"]) == 1
