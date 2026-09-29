"""Shared fixtures: the fictional world rendered once, and a fake embedder."""

from __future__ import annotations

import re
import zlib
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

FIXTURE_RAW = Path(__file__).parent / "fixtures" / "pokeapi_mini"
FIXTURE_SCOPE = ("alpha-beta", "gamma")
FIXTURE_WITHHELD = [(1, "alpha-beta")]


class FakeEmbedder:
    """Hashed bag of words: deterministic, no model, counts its passage calls."""

    name = "fake-bag-of-words"

    def __init__(self, dims: int = 32) -> None:
        self.dims = dims
        self.passage_calls = 0
        self.embedded: list[str] = []

    def _vector(self, text: str) -> np.ndarray:
        v = np.zeros(self.dims, dtype=np.float32)
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            v[zlib.crc32(word.encode()) % self.dims] += 1.0
        norm = np.linalg.norm(v)
        return v / norm if norm else v

    def passages(self, texts: Sequence[str]) -> np.ndarray:
        self.passage_calls += 1
        self.embedded += list(texts)
        return np.stack([self._vector(t) for t in texts])

    def query(self, text: str) -> np.ndarray:
        return self._vector(text)


@pytest.fixture()
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture(scope="session")
def fixture_world_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Registry and real-name page files (main and cue) of the fixture world."""
    from agentic_pokedex.world import render
    from agentic_pokedex.world.pokeapi import iter_learnsets, read_world

    tables = read_world(FIXTURE_RAW)
    world = render.build_world(
        tables, list(iter_learnsets(FIXTURE_RAW, tables)), FIXTURE_SCOPE
    )
    units = render.build_units(world, FIXTURE_WITHHELD)
    out = tmp_path_factory.mktemp("world")
    render.build_registry(world, units, FIXTURE_WITHHELD).save(out / "registry.json")
    names = render.Names.real(world)
    for label, cues in (("real", False), ("real-cues", True)):
        texts = [render.render_text(u, world, names, cues=cues) for u in units]
        render.write_units(out / "pages" / f"{label}.jsonl", units, texts)
    twin_names = render.Names.twin(world, fixture_twin_map())
    texts = [render.render_text(u, world, twin_names) for u in units]
    render.write_units(out / "pages" / "twin.jsonl", units, texts)
    return out


def fixture_twin_map():
    """The fixture world's twin map, drawn with the default seed."""
    from agentic_pokedex.world.pokeapi import read_world
    from agentic_pokedex.world.twin import (
        NameFilter,
        build_twin,
        load_dictionary,
        real_names,
    )

    forbidden, english = real_names(FIXTURE_RAW)
    name_filter = NameFilter(
        forbidden, load_dictionary(FIXTURE_RAW / "words_alpha.txt"), english
    )
    return build_twin(read_world(FIXTURE_RAW), name_filter)[0]
