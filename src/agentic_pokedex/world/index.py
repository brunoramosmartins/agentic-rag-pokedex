"""The retrieval index: BM25 + dense, fused by reciprocal rank.

Only **indexed** units are searchable: the registry's withheld units (S4) never
enter. One index per page file, so the twin, the real world and the cue variant
each get their own.

- **BM25** is adapted from the previous project's (`graphrag-mtg-rules`,
  ``evaluation/bm25.py``): standard ``k1 = 1.2``, ``b = 0.75``, IDF floored at
  zero, ties broken by id. Twin names are pseudo-words no embedding model has
  seen, so the lexical half carries the names; the dense half carries the
  section vocabulary ("learnset", "hidden ability", "super effective").
- **Dense:** ``BAAI/bge-small-en-v1.5`` through ``fastembed`` (ONNX, CPU; the
  ``retrieval`` extra). Exact cosine search in numpy — 13k vectors of 384
  dimensions need no approximate index. Passage vectors are cached on disk,
  keyed by the model and the SHA-256 of the indexed texts.
- **Fusion:** reciprocal rank fusion, ``1 / (RRF_K + rank)`` summed over the two
  rankings, each cut at ``CANDIDATES``. Scores of different retrievers are never
  compared, only ranks.

Usage::

    python -m agentic_pokedex.world.index --query "hidden ability of Kedros"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.world.registry import Registry

DENSE_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_BATCH = 64
RRF_K = 60
CANDIDATES = 50
K1 = 1.2
B = 0.75
DEFAULT_WORLD_DIR = REPO_ROOT / "data" / "world"

_WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")

STOPWORDS = frozenset(
    (
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "for",
        "with", "as", "by", "from", "if", "then", "than", "but", "so", "about",
        "into", "over", "under", "is", "are", "was", "were", "be", "been",
        "being", "it", "its", "this", "that", "these", "those", "there",
        "their", "they", "them", "what", "which", "does", "do", "did",
    )
)
"""Words with no retrieval signal. Short on purpose: "can", "learn", "level"
and "hidden" carry the question."""


def tokenize(text: str) -> list[str]:
    """Lower-case words and numbers, stopwords and one-letter tokens removed."""
    return [
        w for w in _WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 1
    ]


@dataclass(frozen=True)
class Hit:
    """One scored unit. Scores compare within one query and one retriever."""

    unit_id: str
    score: float


# --- Lexical ----------------------------------------------------------------


class Bm25Index:
    """An in-memory inverted index with BM25 scoring."""

    def __init__(self, unit_ids: Sequence[str], texts: Iterable[str]) -> None:
        self.unit_ids = list(unit_ids)
        self._postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self._lengths: list[int] = []
        for i, text in enumerate(texts):
            terms = Counter(tokenize(text))
            self._lengths.append(sum(terms.values()))
            for term, count in terms.items():
                self._postings[term].append((i, count))
        if len(self._lengths) != len(self.unit_ids):
            raise ValueError("texts and ids differ in length")
        n = len(self._lengths)
        self.average_length = sum(self._lengths) / n if n else 0.0

    def _idf(self, term: str) -> float:
        df = len(self._postings.get(term, ()))
        if not df:
            return 0.0
        n = len(self._lengths)
        return max(0.0, math.log((n - df + 0.5) / (df + 0.5) + 1.0))

    def scores(self, query: str) -> dict[int, float]:
        """Positive BM25 score of every unit matching a query term."""
        scores: dict[int, float] = defaultdict(float)
        for term, q in Counter(tokenize(query)).items():
            idf = self._idf(term)
            if not idf:
                continue
            for i, count in self._postings[term]:
                norm = K1 * (1 - B + B * self._lengths[i] / self.average_length)
                scores[i] += q * idf * count * (K1 + 1) / (count + norm)
        return scores

    def search(self, query: str, k: int) -> list[Hit]:
        """The ``k`` best units, ties broken by id."""
        ranked = sorted(
            self.scores(query).items(), key=lambda kv: (-kv[1], self.unit_ids[kv[0]])
        )
        return [Hit(self.unit_ids[i], s) for i, s in ranked[:k]]

    def match_count(self, query: str) -> int:
        """Units sharing at least one informative term with the query."""
        return len(self.scores(query))


# --- Dense ------------------------------------------------------------------


class Embedder(Protocol):
    """Turns passages and queries into L2-normalized vectors."""

    name: str

    def passages(self, texts: Sequence[str]) -> np.ndarray:
        """One row per text."""
        ...

    def query(self, text: str) -> np.ndarray:
        """One vector."""
        ...


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    return matrix / np.where(norms == 0, 1.0, norms)


class FastEmbedder:
    """``fastembed`` wrapper (requires the ``retrieval`` extra)."""

    def __init__(self, model: str = DENSE_MODEL, cache_dir: Path | None = None) -> None:
        from fastembed import TextEmbedding

        self.name = model
        self._model = TextEmbedding(
            model_name=model, cache_dir=str(cache_dir) if cache_dir else None
        )

    def passages(self, texts: Sequence[str]) -> np.ndarray:
        """Passage vectors, normalized, in the order of ``texts``.

        Texts are embedded shortest first, so each batch pads to a similar
        length: twin pseudo-words split into several word pieces ("res ##ko
        ##x ##dam"), units run from ~20 to ~435 pieces, and batches in page
        order padded most of their rows to the longest one.
        """
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        embedded = self._model.passage_embed(
            [texts[i] for i in order], batch_size=EMBED_BATCH
        )
        vectors = np.empty((len(texts), 0), dtype=np.float32)
        for position, vector in zip(order, embedded, strict=True):
            if vectors.shape[1] == 0:
                vectors = np.empty((len(texts), len(vector)), dtype=np.float32)
            vectors[position] = vector
        return _normalize(vectors)

    def query(self, text: str) -> np.ndarray:
        """Query vector (with the model's query prefix), normalized."""
        vector = next(iter(self._model.query_embed(text)))
        return _normalize(np.asarray(vector, dtype=np.float32))


class DenseIndex:
    """Exact cosine search over normalized passage vectors."""

    def __init__(
        self, unit_ids: Sequence[str], vectors: np.ndarray, embedder: Embedder
    ) -> None:
        if len(unit_ids) != len(vectors):
            raise ValueError("vectors and ids differ in length")
        self.unit_ids = list(unit_ids)
        self.vectors = vectors
        self.embedder = embedder

    def search(self, query: str, k: int) -> list[Hit]:
        """The ``k`` most similar units, ties broken by id."""
        if not self.unit_ids:
            return []
        sims = self.vectors @ self.embedder.query(query)
        order = sorted(
            range(len(sims)), key=lambda i: (-float(sims[i]), self.unit_ids[i])
        )
        return [Hit(self.unit_ids[i], float(sims[i])) for i in order[:k]]


STORE_FILE = "store.npz"


def text_key(model: str, text: str) -> str:
    """Cache key of one passage: model and text."""
    return hashlib.sha256(f"{model}\x00{text}".encode()).hexdigest()[:32]


def _corpus_key(model: str, texts: Sequence[str]) -> str:
    """Key of the earlier whole-corpus cache files (``{key}.npy``)."""
    digest = hashlib.sha256()
    digest.update(model.encode())
    for text in texts:
        digest.update(b"\x00" + text.encode("utf-8"))
    return digest.hexdigest()[:24]


def _load_store(path: Path) -> dict[str, np.ndarray]:
    if not path.is_file():
        return {}
    data = np.load(path)
    return dict(zip(data["keys"].tolist(), data["vectors"], strict=True))


def _save_store(path: Path, store: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted(store)
    np.savez(path, keys=np.array(keys), vectors=np.stack([store[k] for k in keys]))


def cached_vectors(
    texts: Sequence[str], embedder: Embedder, cache_dir: Path | None
) -> np.ndarray:
    """Passage vectors, embedding only the texts the cache does not hold.

    The cache is per passage (model + text), so re-rendering the world
    re-embeds only the units whose text changed. A whole-corpus file written
    by the earlier cache is imported when the corpus matches it.
    """
    if cache_dir is None:
        return embedder.passages(texts)
    store_path = cache_dir / STORE_FILE
    store = _load_store(store_path)
    keys = [text_key(embedder.name, t) for t in texts]
    legacy = cache_dir / f"{_corpus_key(embedder.name, texts)}.npy"
    if legacy.is_file() and any(k not in store for k in keys):
        store.update(zip(keys, np.load(legacy), strict=True))
        _save_store(store_path, store)
    missing = sorted({i for i, k in enumerate(keys) if k not in store})
    if missing:
        print(
            f"Embedding {len(missing):,} of {len(texts):,} units with "
            f"{embedder.name} (cached per unit; minutes on CPU the first time)...",
            file=sys.stderr,
            flush=True,
        )
        started = time.monotonic()
        vectors = embedder.passages([texts[i] for i in missing])
        print(f"Embedded in {time.monotonic() - started:.0f} s", file=sys.stderr)
        store.update(zip((keys[i] for i in missing), vectors, strict=True))
        _save_store(store_path, store)
    return np.stack([store[k] for k in keys]) if keys else np.empty((0, 0))


# --- Hybrid -----------------------------------------------------------------


def rrf(rankings: Sequence[Sequence[Hit]], k: int = RRF_K) -> list[Hit]:
    """Reciprocal rank fusion; ties broken by id."""
    fused: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            fused[hit.unit_id] += 1.0 / (k + rank)
    return [
        Hit(u, s) for u, s in sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


@dataclass(frozen=True)
class Unit:
    """An indexed unit: its id, page title, section line and full text."""

    id: str
    title: str
    section: str
    text: str


def split_header(text: str) -> tuple[str, str]:
    """Title and section part of a unit header.

    ``"Species: Kedros · Section: Learnset · Method: …"`` →
    ``("Kedros", "Learnset · Method: …")``.
    """
    head = text.split("\n", 1)[0]
    first, _, rest = head.partition(" · Section: ")
    return first.split(": ", 1)[1], rest


class HybridIndex:
    """BM25 and dense rankings over the indexed units, fused by RRF."""

    def __init__(self, units: Sequence[Unit], embedder: Embedder | None = None,
                 cache_dir: Path | None = None) -> None:
        self.units = {u.id: u for u in units}
        ids = [u.id for u in units]
        texts = [u.text for u in units]
        self.bm25 = Bm25Index(ids, texts)
        self.dense = (
            DenseIndex(ids, cached_vectors(texts, embedder, cache_dir), embedder)
            if embedder
            else None
        )

    def search(self, query: str, k: int) -> list[Hit]:
        """The ``k`` best units for a query."""
        rankings = [self.bm25.search(query, CANDIDATES)]
        if self.dense:
            rankings.append(self.dense.search(query, CANDIDATES))
        return rrf(rankings)[:k]

    def match_count(self, query: str) -> int:
        """Lexical match count, shown only in the cue condition."""
        return self.bm25.match_count(query)


def load_units(pages: Path, registry: Registry) -> list[Unit]:
    """Indexed units of a page file, in page order (withheld ones dropped)."""
    indexed = set(registry.indexed_units())
    units = []
    with pages.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["id"] in indexed:
                title, section = split_header(row["text"])
                units.append(Unit(row["id"], title, section, row["text"]))
    return units


def build_index(
    world_dir: Path = DEFAULT_WORLD_DIR,
    pages: str = "twin",
    embedder: Embedder | None = None,
) -> HybridIndex:
    """The hybrid index of ``pages/{pages}.jsonl`` in ``world_dir``."""
    registry = Registry.load(world_dir / "registry.json")
    units = load_units(world_dir / "pages" / f"{pages}.jsonl", registry)
    return HybridIndex(units, embedder, world_dir / "index" / pages)


def main(argv: list[str] | None = None) -> int:
    """CLI: build (or reuse) the index and print the top units for a query."""
    parser = argparse.ArgumentParser(description="Build and query the index.")
    parser.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--pages", default="twin", help="twin, real, twin-cues, …")
    parser.add_argument("--query", default="")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--lexical-only", action="store_true")
    args = parser.parse_args(argv)

    embedder = None
    if not args.lexical_only:
        embedder = FastEmbedder(cache_dir=args.world_dir / "models")
    index = build_index(args.world_dir, args.pages, embedder)
    print(f"{len(index.units):,} indexed units from pages/{args.pages}.jsonl")
    if args.query:
        for hit in index.search(args.query, args.k):
            print(f"\n[{hit.unit_id}]  rrf={hit.score:.4f}")
            print(index.units[hit.unit_id].text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
