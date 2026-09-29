"""PokéAPI download: the manifest is the only gate, and no unchecked file lands."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agentic_pokedex.world.download import (
    MANIFEST,
    POKEAPI_COMMIT,
    HashMismatchError,
    download,
    sha256_bytes,
    verify,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pokeapi_mini"

FILES = {"a.csv": b"id\n1\n", "b.csv": b"id\n2\n"}
TEST_MANIFEST = {name: sha256_bytes(data) for name, data in FILES.items()}


class FakeFetch:
    """Serve ``FILES`` by URL basename and record every request."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        return self.files[url.rsplit("/", 1)[1]]


def test_manifest_is_well_formed() -> None:
    assert len(POKEAPI_COMMIT) == 40
    for name, digest in MANIFEST.items():
        assert name.endswith(".csv")
        assert re.fullmatch(r"[0-9a-f]{64}", digest), name


def test_manifest_covers_exactly_the_files_the_reader_uses() -> None:
    fixture_files = {p.name for p in FIXTURE_DIR.glob("*.csv")}
    assert fixture_files == set(MANIFEST)


def test_download_fetches_from_the_pinned_commit(tmp_path: Path) -> None:
    fetch = FakeFetch(FILES)
    fetched = download(tmp_path, manifest=TEST_MANIFEST, fetch=fetch)
    assert fetched == ["a.csv", "b.csv"]
    assert all(f"/{POKEAPI_COMMIT}/data/v2/csv/" in url for url in fetch.urls)
    assert (tmp_path / "a.csv").read_bytes() == FILES["a.csv"]
    assert verify(tmp_path, TEST_MANIFEST) == {"a.csv": "ok", "b.csv": "ok"}


def test_matching_files_are_not_fetched_again(tmp_path: Path) -> None:
    download(tmp_path, manifest=TEST_MANIFEST, fetch=FakeFetch(FILES))
    fetch = FakeFetch(FILES)
    assert download(tmp_path, manifest=TEST_MANIFEST, fetch=fetch) == []
    assert fetch.urls == []


def test_force_fetches_everything(tmp_path: Path) -> None:
    download(tmp_path, manifest=TEST_MANIFEST, fetch=FakeFetch(FILES))
    fetched = download(
        tmp_path, manifest=TEST_MANIFEST, fetch=FakeFetch(FILES), force=True
    )
    assert fetched == ["a.csv", "b.csv"]


def test_a_tampered_file_on_disk_is_replaced(tmp_path: Path) -> None:
    download(tmp_path, manifest=TEST_MANIFEST, fetch=FakeFetch(FILES))
    (tmp_path / "a.csv").write_bytes(b"tampered\n")
    assert verify(tmp_path, TEST_MANIFEST)["a.csv"] == "mismatch"
    assert download(tmp_path, manifest=TEST_MANIFEST, fetch=FakeFetch(FILES)) == [
        "a.csv"
    ]
    assert verify(tmp_path, TEST_MANIFEST)["a.csv"] == "ok"


def test_a_remote_mismatch_aborts_and_leaves_no_file(tmp_path: Path) -> None:
    bad = dict(FILES, **{"a.csv": b"id\n999\n"})
    with pytest.raises(HashMismatchError, match="a.csv"):
        download(tmp_path, manifest=TEST_MANIFEST, fetch=FakeFetch(bad))
    assert not (tmp_path / "a.csv").exists()
    assert not list(tmp_path.glob("*.part"))


def test_verify_reports_missing_files(tmp_path: Path) -> None:
    assert verify(tmp_path, TEST_MANIFEST) == {"a.csv": "missing", "b.csv": "missing"}


def test_download_follows_a_custom_url_template(tmp_path: Path) -> None:
    fetch = FakeFetch(FILES)
    download(
        tmp_path,
        manifest=TEST_MANIFEST,
        commit="abc123",
        url_template="https://example.org/{commit}/{name}",
        fetch=fetch,
    )
    assert fetch.urls == [
        "https://example.org/abc123/a.csv",
        "https://example.org/abc123/b.csv",
    ]


def test_word_list_is_pinned() -> None:
    from agentic_pokedex.world.download import WORDLIST_COMMIT, WORDLIST_MANIFEST

    assert len(WORDLIST_COMMIT) == 40
    assert set(WORDLIST_MANIFEST) == {"words_alpha.txt"}
    assert not set(WORDLIST_MANIFEST) & set(MANIFEST)
