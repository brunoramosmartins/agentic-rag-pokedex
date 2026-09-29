"""Hybrid index: BM25, dense cache, rank fusion, indexed units only."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from agentic_pokedex.world.index import (
    Bm25Index,
    Hit,
    HybridIndex,
    Unit,
    build_index,
    cached_vectors,
    load_units,
    rrf,
    split_header,
    tokenize,
)
from agentic_pokedex.world.registry import Registry


def unit(uid: str, text: str) -> Unit:
    return Unit(uid, uid, "Profile", text)


def test_tokenize_keeps_words_and_numbers() -> None:
    tokens = tokenize("Level 30: [[Vine Lash]] of the X")
    assert tokens == ["level", "30", "vine", "lash"]
    assert tokenize("Porygon-Z's") == ["porygon-z's"]


def test_bm25_ranks_by_term_frequency_and_breaks_ties_by_id() -> None:
    index = Bm25Index(
        ["a", "b", "c", "d"],
        [
            "sprig learns vine lash",
            "blaze learns cinder",
            "sprig sprig profile",
            "sprig learns vine lash",
        ],
    )
    hits = index.search("sprig", 4)
    assert [h.unit_id for h in hits] == ["c", "a", "d"]
    assert hits[1].score == hits[2].score  # identical texts, ordered by id
    assert index.match_count("sprig") == 3
    assert index.match_count("nothing here") == 0


def test_rrf_fuses_ranks_not_scores() -> None:
    fused = rrf(
        [[Hit("a", 100.0), Hit("b", 50.0)], [Hit("b", 0.9), Hit("c", 0.8)]], k=60
    )
    assert [h.unit_id for h in fused] == ["b", "a", "c"]
    assert fused[0].score == 1 / 62 + 1 / 61


def test_split_header() -> None:
    assert split_header("Species: Type: Null · Section: Profile\nTypes: x") == (
        "Type: Null",
        "Profile",
    )
    assert split_header(
        "Move: Vine Lash · Section: Learned by · Version: Alpha/Beta"
    ) == ("Vine Lash", "Learned by · Version: Alpha/Beta")


def test_cached_vectors_reuse_the_file(tmp_path: Path, fake_embedder) -> None:
    texts = ["sprig learns vine lash", "blaze learns cinder"]
    first = cached_vectors(texts, fake_embedder, tmp_path)
    second = cached_vectors(texts, fake_embedder, tmp_path)
    assert fake_embedder.passage_calls == 1
    assert np.array_equal(first, second)
    cached_vectors([*texts, "new text"], fake_embedder, tmp_path)
    assert fake_embedder.passage_calls == 2


def test_the_cache_is_per_unit(tmp_path: Path, fake_embedder) -> None:
    cached_vectors(["a text", "b text", "c text"], fake_embedder, tmp_path)
    fake_embedder.embedded.clear()
    # A re-rendered corpus: one unit gone, one new, order changed.
    vectors = cached_vectors(["c text", "d text", "a text"], fake_embedder, tmp_path)
    assert fake_embedder.embedded == ["d text"]
    order = ("c text", "d text", "a text")
    expected = np.stack([fake_embedder._vector(t) for t in order])
    assert np.allclose(vectors, expected)


def test_a_whole_corpus_cache_file_is_imported(tmp_path: Path, fake_embedder) -> None:
    from agentic_pokedex.world.index import _corpus_key

    texts = ["a text", "b text"]
    legacy = np.stack([fake_embedder._vector(t) for t in texts])
    np.save(tmp_path / f"{_corpus_key(fake_embedder.name, texts)}.npy", legacy)
    vectors = cached_vectors(texts, fake_embedder, tmp_path)
    assert fake_embedder.embedded == []  # nothing re-embedded
    assert np.allclose(vectors, legacy)
    assert (tmp_path / "store.npz").is_file()


def test_no_cache_dir_embeds_everything(fake_embedder) -> None:
    cached_vectors(["a", "b"], fake_embedder, None)
    assert fake_embedder.embedded == ["a", "b"]


def test_hybrid_search_is_deterministic(fake_embedder) -> None:
    units = [
        unit("a", "Species: Sprig · Section: Profile\nTypes: [[Moss]]"),
        unit("b", "Species: Blaze · Section: Profile\nTypes: [[Ember]]"),
        unit("c", "Move: Cinder · Section: Profile\nType: [[Ember]]"),
    ]
    index = HybridIndex(units, fake_embedder)
    first = index.search("Ember type", 2)
    assert len(first) == 2
    assert index.search("Ember type", 2) == first
    assert {h.unit_id for h in first} <= {"a", "b", "c"}


def test_lexical_only_index() -> None:
    index = HybridIndex([unit("a", "sprig"), unit("b", "blaze")])
    assert index.dense is None
    assert [h.unit_id for h in index.search("blaze", 5)] == ["b"]


def test_withheld_units_are_not_indexed(fixture_world_dir: Path) -> None:
    registry = Registry.load(fixture_world_dir / "registry.json")
    units = load_units(fixture_world_dir / "pages" / "real.jsonl", registry)
    ids = [u.id for u in units]
    assert len(ids) == 27
    assert "species/1/learnset/level-up/alpha-beta/0" not in ids
    assert ids[0] == "species/1/profile"  # page order is kept


def test_build_index_from_the_world_dir(fixture_world_dir: Path, fake_embedder) -> None:
    index = build_index(fixture_world_dir, "real", fake_embedder)
    assert len(index.units) == 27
    assert (fixture_world_dir / "index" / "real").is_dir()  # vectors cached
    hits = index.search("Vine Lash learned by", 5)
    assert all(h.unit_id in index.units for h in hits)


def test_fast_embedder_sorts_by_length_and_restores_the_order() -> None:
    from agentic_pokedex.world.index import FastEmbedder

    class FakeModel:
        def __init__(self) -> None:
            self.seen: list[str] = []

        def passage_embed(self, texts, batch_size):
            self.seen = list(texts)
            for text in texts:
                yield np.array([len(text), 1.0], dtype=np.float32)

    embedder = FastEmbedder.__new__(FastEmbedder)
    embedder._model = FakeModel()
    texts = ["ccc", "a", "bb"]
    vectors = embedder.passages(texts)
    assert embedder._model.seen == ["a", "bb", "ccc"]  # shortest first
    expected = np.array([[3, 1], [1, 1], [2, 1]], dtype=np.float32)
    expected /= np.linalg.norm(expected, axis=1, keepdims=True)
    assert np.allclose(vectors, expected)  # back in the caller's order
