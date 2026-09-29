"""Counterfactual twin: name filters, seeded generation, round trip, free text."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agentic_pokedex.world.pokeapi import read_world
from agentic_pokedex.world.twin import (
    KINDS,
    POKEMON_TERM,
    WORD_LENGTH,
    NameFilter,
    PseudoWordGenerator,
    TextRewriter,
    TwinMap,
    build_twin,
    collisions,
    load_dictionary,
    main,
    normalize,
    real_names,
    residual_names,
    round_trip_failures,
    single_deletions,
)

RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"


def small_filter() -> NameFilter:
    return NameFilter(
        forbidden={"sprig", "gloom"},
        dictionary={"table", "mirror"},
        english_names={"sprout", "blaze", "vinelash", "vine", "lash"},
    )


def fixture_filter() -> NameFilter:
    forbidden, english = real_names(RAW)
    return NameFilter(forbidden, load_dictionary(RAW / "words_alpha.txt"), english)


# --- Normalization and filters ----------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Farfetch’d", "farfetchd"),
        ("Nidoran♀", "nidoran"),
        ("Pokémon", "pokemon"),
        ("Mr. Mime", "mrmime"),
        ("Porygon2", "porygon"),
        ("ほのお", ""),
    ],
)
def test_normalize(name: str, expected: str) -> None:
    assert normalize(name) == expected


def test_single_deletions() -> None:
    assert single_deletions("abc") == {"abc", "bc", "ac", "ab"}


@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        ("Sprig", "real-name"),
        ("Kanto", "real-name"),  # franchise term
        ("Table", "dictionary"),
        ("Sproka", "prefix-suffix"),  # starts like "sprout"
        ("Kolash", "prefix-suffix"),  # ends like "vinelash"
        ("Blaxe", "one-edit"),  # one substitution from "blaze"
        ("Blze", "one-edit"),  # one deletion from "blaze"
        ("Korvinelashu", "contains-name"),
        ("Mirotu", None),
    ],
)
def test_name_filter(candidate: str, reason: str | None) -> None:
    assert small_filter().reason(candidate) == reason


def test_load_dictionary_normalizes_and_skips_blanks(tmp_path: Path) -> None:
    path = tmp_path / "words.txt"
    path.write_bytes(b"Apple\r\nbanana\n\n")
    assert load_dictionary(path) == {"apple", "banana"}


def test_real_names_cover_every_language_and_identifiers() -> None:
    forbidden, english = real_names(RAW)
    assert {"sprig", "megablaze", "vinelash", "vine", "lash", "gloom"} <= forbidden
    assert "tidal" in forbidden  # a word of the form name "Tidal Form"
    assert "sprig" in english
    assert "" not in forbidden


# --- Generator --------------------------------------------------------------


def test_generator_is_deterministic() -> None:
    a = PseudoWordGenerator(7, small_filter())
    b = PseudoWordGenerator(7, small_filter())
    assert [a.word() for _ in range(50)] == [b.word() for _ in range(50)]


def test_generated_words_are_unique_well_formed_and_accepted() -> None:
    gen = PseudoWordGenerator(3, small_filter())
    words = [gen.word() for _ in range(200)]
    keys = [normalize(w) for w in words]
    assert len(set(keys)) == len(keys)
    for word, key in zip(words, keys, strict=True):
        assert word[0].isupper()
        assert WORD_LENGTH[0] <= len(key) <= WORD_LENGTH[1]
        assert not re.search(r"[^aeiou]{3,}", key)
        assert small_filter().reason(word) is None


def test_two_word_names() -> None:
    gen = PseudoWordGenerator(11, small_filter())
    assert len(gen.name(two_word_share=1.0).split()) == 2
    assert len(gen.name(two_word_share=0.0).split()) == 1


def test_generator_gives_up_instead_of_looping_forever() -> None:
    class RejectAll(NameFilter):
        def reason(self, candidate: str) -> str | None:
            return "rejected"

    gen = PseudoWordGenerator(1, RejectAll(set(), set(), set()))
    with pytest.raises(RuntimeError, match="no acceptable pseudo-word"):
        gen.word()


# --- The map on the fixture world -------------------------------------------


@pytest.fixture(scope="module")
def twin() -> TwinMap:
    return build_twin(read_world(RAW), fixture_filter())[0]


def test_every_kind_is_mapped(twin: TwinMap) -> None:
    assert set(twin.names) == set(KINDS)
    assert len(twin.names["species"]) == 4
    assert len(twin.names["pokemon"]) == 6
    assert len(twin.names["type"]) == 3
    assert len(twin.names["move"]) == 3
    assert POKEMON_TERM in twin.names["term"]


def test_round_trip_is_identity(twin: TwinMap) -> None:
    assert round_trip_failures(twin, read_world(RAW)) == []


def test_no_word_is_shared_by_two_names(twin: TwinMap) -> None:
    assert collisions(twin) == []


def test_same_seed_same_map_other_seed_other_map() -> None:
    tables = read_world(RAW)
    first = build_twin(tables, fixture_filter(), seed=5)[0]
    again = build_twin(tables, fixture_filter(), seed=5)[0]
    other = build_twin(tables, fixture_filter(), seed=6)[0]
    assert first.names == again.names
    assert first.names != other.names


def test_twin_names_are_never_real_names(twin: TwinMap) -> None:
    forbidden, _ = real_names(RAW)
    for kind in ("species", "type", "ability", "move", "version", "term"):
        for name in twin.names[kind].values():
            for word in name.split():
                assert normalize(word) not in forbidden, (kind, name)


def test_default_entries_take_the_species_twin(twin: TwinMap) -> None:
    assert twin.to_twin("pokemon", "Sprig") == twin.to_twin("species", "Sprig")


def test_form_names_keep_their_shape(twin: TwinMap) -> None:
    blaze = twin.to_twin("species", "Blaze")
    sproutree = twin.to_twin("species", "Sproutree")
    words = twin.names["form_word"]
    assert twin.to_twin("pokemon", "Mega Blaze") == f"{words['mega']} {blaze}"
    assert twin.to_twin("pokemon", "Sproutree (Tidal Form)") == (
        f"{sproutree} ({words['tidal']} {words['form']})"
    )


def test_version_group_names_are_rebuilt_from_versions(twin: TwinMap) -> None:
    alpha = twin.to_twin("version", "Alpha")
    beta = twin.to_twin("version", "Beta")
    assert twin.to_twin("version_group", "Alpha/Beta") == f"{alpha}/{beta}"


def test_save_and_load(tmp_path: Path, twin: TwinMap) -> None:
    path = tmp_path / "twin.json"
    twin.save(path)
    loaded = TwinMap.load(path)
    assert loaded.names == twin.names
    assert loaded.seed == twin.seed


def test_a_map_that_is_not_invertible_is_refused() -> None:
    names = {kind: {} for kind in KINDS}
    names["species"] = {"Sprig": "Molva", "Sprout": "Molva"}
    with pytest.raises(ValueError, match="maps back to two names"):
        TwinMap(seed=0, names=names)


# --- Free text --------------------------------------------------------------


@pytest.fixture()
def rewriter() -> TextRewriter:
    names = {kind: {} for kind in KINDS}
    names["species"] = {"Sprig": "Molva", "Mr. Sprig": "Tarvo"}
    names["type"] = {"Psychic": "Rauk"}
    names["move"] = {"Psychic": "Zemo", "Vine Lash": "Kesso Dran"}
    names["term"] = {POKEMON_TERM: "Brenna"}
    return TextRewriter.from_map(TwinMap(seed=0, names=names))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Sprig grows fast.", "Molva grows fast."),
        ("SPRIG grows fast.", "MOLVA grows fast."),
        ("a sprig of leaves", "a sprig of leaves"),  # lower-case prose stays
        ("Sprigs everywhere", "Sprigs everywhere"),  # whole words only
        ("Mr. Sprig waves.", "Tarvo waves."),  # longest name wins
        ("It uses Vine Lash.", "It uses Kesso Dran."),
        ("Psychic power", "Rauk power"),  # type outranks move
        ("This POKéMON is a Pokémon.", "This BRENNA is a Brenna."),
    ],
)
def test_rewrite(rewriter: TextRewriter, text: str, expected: str) -> None:
    assert rewriter.rewrite(text) == expected


def test_residual_names() -> None:
    texts = ["Sprig is here", "a sprig", "SPRIG", "nothing"]
    assert residual_names(texts, ["Sprig"]) == {"title_or_upper": 2, "any_case": 3}


# --- CLI --------------------------------------------------------------------


def test_main_writes_the_map(tmp_path: Path) -> None:
    out = tmp_path / "twin_map.json"
    assert main(["--raw-dir", str(RAW), "--out", str(out)]) == 0
    assert TwinMap.load(out).names["species"].keys() == {
        "Sprig",
        "Sprout",
        "Sproutree",
        "Blaze",
    }
