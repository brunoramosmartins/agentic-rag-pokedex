"""The two tools: the contract every arm shares (ADR-009)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_pokedex.tools.contract import NO_MORE, NO_RESULTS, ToolConfig, pack
from agentic_pokedex.tools.open_page import Pages, open_page
from agentic_pokedex.tools.search import search
from agentic_pokedex.world.index import HybridIndex, Unit, build_index


def chars(text: str) -> int:
    """A test token counter: one token per four characters."""
    return len(text) // 4


def unit(uid: str, text: str, title: str = "T", section: str = "Profile") -> Unit:
    return Unit(uid, title, section, text)


@pytest.fixture(scope="module")
def index(fixture_world_dir: Path) -> HybridIndex:
    return build_index(fixture_world_dir, "real")


@pytest.fixture(scope="module")
def pages(index: HybridIndex) -> Pages:
    return Pages(index.units.values())


# --- Packing ----------------------------------------------------------------


def test_pack_stops_at_the_first_unit_that_does_not_fit() -> None:
    units = [unit("a", "x" * 400), unit("b", "x" * 400), unit("c", "x" * 40)]
    result = pack(units, chars, cap=150)
    assert result.unit_ids == ("a",)  # b does not fit; c is not tried
    assert result.tokens == chars(result.text)


def test_pack_always_returns_the_first_unit() -> None:
    result = pack([unit("a", "x" * 4000)], chars, cap=10)
    assert result.unit_ids == ("a",)


def test_pack_counts_the_preamble() -> None:
    units = [unit("a", "x" * 200), unit("b", "x" * 200)]
    assert pack(units, chars, cap=110).unit_ids == ("a", "b")
    assert pack(units, chars, cap=110, preamble="y" * 40).unit_ids == ("a",)


# --- search -----------------------------------------------------------------


def test_search_returns_units_with_headers(index: HybridIndex) -> None:
    result = search(index, "Sproutree hidden ability", 5, counter=chars)
    assert "species/3/profile" in result.unit_ids
    assert result.text.startswith(index.units[result.unit_ids[0]].text)


def test_search_clamps_k(index: HybridIndex) -> None:
    assert len(search(index, "level", 50, counter=chars).unit_ids) <= 5
    assert len(search(index, "level", 0, counter=chars).unit_ids) == 1


def test_search_main_condition_shows_no_count(index: HybridIndex) -> None:
    result = search(index, "Vine Lash", 5, counter=chars)
    assert "matching units" not in result.text


def test_search_cue_condition_states_the_count(fixture_world_dir: Path) -> None:
    cue_index = build_index(fixture_world_dir, "real-cues")
    result = search(cue_index, "Vine Lash", 5, counter=chars,
                    config=ToolConfig(cues=True))
    first_line = result.text.split("\n")[0]
    assert first_line == f"{cue_index.match_count('Vine Lash')} matching units."


def test_search_never_returns_withheld_units(index: HybridIndex) -> None:
    result = search(index, "Sprig Level 1 Vine Lash Alpha/Beta learnset", 5,
                    counter=chars)
    assert "species/1/learnset/level-up/alpha-beta/0" not in result.unit_ids


def test_search_with_no_match(index: HybridIndex) -> None:
    result = search(index, "zzzz qqqq", 5, counter=chars)
    assert (result.text, result.unit_ids) == (NO_RESULTS, ())


def test_search_respects_the_token_cap(index: HybridIndex) -> None:
    result = search(index, "level", 5, counter=chars, config=ToolConfig(token_cap=30))
    assert len(result.unit_ids) == 1


# --- open_page --------------------------------------------------------------


def test_open_page_reads_from_the_top(pages: Pages) -> None:
    result = open_page(pages, "Blaze", counter=chars)
    assert result.unit_ids == (
        "species/4/profile",
        "species/4/form/10001",
        "species/4/notes",
        "species/4/learnset/level-up/alpha-beta/0",
        "species/4/learnset/level-up/gamma/0",
    )


def test_open_page_leaves_out_withheld_units(pages: Pages) -> None:
    result = open_page(pages, "Sprig", section="level-up", counter=chars)
    assert result.unit_ids == ("species/1/learnset/level-up/gamma/0",)


def test_open_page_section_filter(pages: Pages) -> None:
    result = open_page(pages, "Vine Lash", section="learned by", counter=chars)
    assert result.unit_ids == (
        "move/1/learned-by/alpha-beta/0",
        "move/1/learned-by/gamma/0",
    )
    one = open_page(pages, "Vine Lash", section="Learned by · Version: Gamma",
                    counter=chars)
    assert one.unit_ids == ("move/1/learned-by/gamma/0",)


def test_open_page_offset_continues_and_ends(pages: Pages) -> None:
    first = open_page(pages, "Blaze", counter=chars, config=ToolConfig(token_cap=40))
    assert len(first.unit_ids) < 5
    rest = open_page(pages, "Blaze", offset=len(first.unit_ids), counter=chars)
    assert first.unit_ids + rest.unit_ids == open_page(
        pages, "Blaze", counter=chars
    ).unit_ids
    end = open_page(pages, "Blaze", offset=5, counter=chars)
    assert (end.text, end.unit_ids) == (NO_MORE, ())


def test_open_page_main_condition_shows_no_count(pages: Pages) -> None:
    result = open_page(pages, "Blaze", counter=chars)
    assert "units in this selection" not in result.text


def test_open_page_cue_condition_states_the_count(pages: Pages) -> None:
    result = open_page(pages, "Blaze", counter=chars, config=ToolConfig(cues=True))
    assert result.text.split("\n")[0] == "5 units in this selection."


def test_open_page_unknown_title(pages: Pages) -> None:
    assert open_page(pages, "blaze", counter=chars).text == "No page titled 'blaze'."


def test_a_section_matching_nothing_serves_the_whole_page(pages: Pages) -> None:
    whole = open_page(pages, "Blaze", counter=chars)
    missing = open_page(pages, "Blaze", section="Matchups", counter=chars)
    assert (missing.text, missing.unit_ids) == (whole.text, whole.unit_ids)


def test_a_withheld_section_is_not_announced(pages: Pages) -> None:
    # S4: Sprig's level-up learnset in Alpha/Beta is withheld. Asking for it
    # returns the page, with the other version's learnset — the plausible,
    # insufficient evidence — and no word about the missing section.
    result = open_page(
        pages, "Sprig", section="level-up · Version: Alpha/Beta", counter=chars
    )
    assert "species/1/learnset/level-up/gamma/0" in result.unit_ids
    assert "species/1/learnset/level-up/alpha-beta/0" not in result.unit_ids
    assert "No section" not in result.text


@pytest.mark.parametrize("section", [None, "Profile", "level-up", "Matchups", "zzz"])
@pytest.mark.parametrize("title", ["Sprig", "Blaze", "Vine Lash", "Ember"])
def test_the_main_condition_never_states_an_absence(
    pages: Pages, title: str, section: str | None
) -> None:
    text = open_page(pages, title, section=section, counter=chars).text
    for cue in ("No section", "not found", "does not exist", "units in this selection"):
        assert cue not in text
