"""Download the PokéAPI CSVs and the word list at pinned commits, SHA-256 checked.

The world is built from PokéAPI's ``data/v2/csv/`` at ``POKEAPI_COMMIT``, never
from ``master``, so that every rebuild starts from the same bytes. Every file is
checked against ``MANIFEST`` before it is kept; a mismatch aborts.

The files land in ``data/raw/`` (gitignored). Raw CSVs and Pokédex text are
third-party material and are never committed (``docs/data-sources.md``).

Usage::

    python -m agentic_pokedex.world.download            # fetch what is missing
    python -m agentic_pokedex.world.download --check    # verify only, no network
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path

from agentic_pokedex.config import REPO_ROOT

POKEAPI_COMMIT = "6bbd96bb8ef7356963b833074ca25672d23e41c4"
"""PokéAPI master on 2026-09-24; recorded in ``docs/data-sources.md``."""

CSV_URL = (
    "https://raw.githubusercontent.com/PokeAPI/pokeapi/{commit}/data/v2/csv/{name}"
)

DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"

MANIFEST: Mapping[str, str] = {
    # Sampled for G1 (Phase 0).
    "abilities.csv":
        "74c3588ad48e08e54ff01f432899a4028c3e91508bbd53201df85e1f6b9e9ef3",
    "evolution_chains.csv":
        "5159f0481eaa786f2b08e58356bcc6271e0982dceeb69746aaac4637d5a47125",
    "moves.csv":
        "8aafd37bf78f19471495c05b201545180f50f0a08a2a2a844d69f9837dd39ac9",
    "pokemon.csv":
        "16c81c33188b0eac403aa2f759fcbe9e42c611f722d263f5b5a6a5bff9f8ce6b",
    "pokemon_abilities.csv":
        "4a79ee53d386a8ad3a89657483ddfd31594e05a5d52400fe131e5e4dfd7ec04a",
    "pokemon_move_methods.csv":
        "78b75acfcf6dca4c82da9d4851357cbbd65e61b08154eddfc2ace0efd00e408e",
    "pokemon_moves.csv":
        "22a807cef26891eeac0d0c900bd363e66baf421f7ee795bc7bc3e718f23b939e",
    "pokemon_species.csv":
        "e66e2eeb25fd3836b0ebab6bf87bbf01960aa3c0555e2bac495fa8393c5e0c45",
    "pokemon_species_flavor_text.csv":
        "c341e602ab623084fef4c44ca4a174938e617802cfcf2deec830d824f688dc69",
    "pokemon_types.csv":
        "f1fc4bfd657a034ea3bf6972423b10276424aa068577b304a78a08996425ba05",
    "type_efficacy.csv":
        "cdd7de4066680414d0a2433af805f139f425d6350cbf998ecab559a0fe8ff587",
    "types.csv":
        "37f039c8d722f47d51ba1c5c5ecf9b7007235b1a9a1af2827645c777b70307c8",
    "version_groups.csv":
        "28da8d89d8eb4966941f81a9e62b3990510ed4d76dd774158246551a8e7707a7",
    "versions.csv":
        "70083465865a6a69a9aad2be3fc3915078c6ff740f14a090b1367d8ec9cfc3cd",
    # Added in Phase 1: English names, move categories and forms.
    "ability_names.csv":
        "8acb80c42210f86ae747dc3347b060d69cd2574a9dbfaf74774ae632ca6348da",
    "languages.csv":
        "fbb60019a6a461783d5671a995d5f590db61792a273e90faa0ed630d102a19b8",
    "move_damage_classes.csv":
        "b7101ceca4dff152537a2fb5c439ca4030b05f86442c643812c0b7b6ccf16f1b",
    "move_names.csv":
        "99e23ee38ea53d1473474d463b87651deac3cd4928750f8186feae66da45c147",
    "pokemon_form_names.csv":
        "f496066d02fab12c18d10cce0af2f748d09cb7e296ecc784cc8682f8c4da8625",
    "pokemon_forms.csv":
        "99bf8f7ad4dc1f2e291357a090cef6a575623ec3cbf9030d0e33656e6e608ae2",
    "pokemon_species_names.csv":
        "820cde17074cdb1c2b0595c997fb8f998e773bd5da3bb525dec85703c86c5fd9",
    "type_names.csv":
        "685230c51074cf2f723debcf827a4df4c36ab0ec7e929c806ad65a3e40958705",
    "version_names.csv":
        "23e3e9062f98e1f83d475b9eeac57ddff4375b46c175948a65c4fe8d3e1d87b4",
}
"""File name → SHA-256 at ``POKEAPI_COMMIT``. The single source of truth."""

WORDLIST_COMMIT = "8179fe68775df3f553ef19520db065228e65d1d3"
"""``dwyl/english-words`` (Unlicense), last change to the file on 2025-01-05."""

WORDLIST_URL = "https://raw.githubusercontent.com/dwyl/english-words/{commit}/{name}"

WORDLIST_MANIFEST: Mapping[str, str] = {
    "words_alpha.txt":
        "3ed0c94610d8bcf7c11bbb49c56aa49c7234d32b66824df91f554169e572da48",
}
"""English words the twin's pseudo-words must avoid (``world/twin.py``). Pinned
like the CSVs, so the twin is the same on every machine."""

Fetcher = Callable[[str], bytes]


class HashMismatchError(RuntimeError):
    """A downloaded file does not match its manifest hash."""


def sha256_bytes(data: bytes) -> str:
    """Return the hex SHA-256 of a byte string."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_url(url: str) -> bytes:
    """Fetch a URL over HTTPS and return its body."""
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def verify(
    raw_dir: Path = DEFAULT_RAW_DIR, manifest: Mapping[str, str] = MANIFEST
) -> dict[str, str]:
    """Check every manifest file on disk.

    Args:
        raw_dir: Directory holding the CSVs.
        manifest: File name → expected SHA-256.

    Returns:
        File name → ``"ok"``, ``"missing"`` or ``"mismatch"``.
    """
    status: dict[str, str] = {}
    for name, expected in sorted(manifest.items()):
        path = raw_dir / name
        if not path.is_file():
            status[name] = "missing"
        elif sha256_file(path) != expected:
            status[name] = "mismatch"
        else:
            status[name] = "ok"
    return status


def download(
    raw_dir: Path = DEFAULT_RAW_DIR,
    *,
    manifest: Mapping[str, str] = MANIFEST,
    commit: str = POKEAPI_COMMIT,
    url_template: str = CSV_URL,
    fetch: Fetcher = fetch_url,
    force: bool = False,
) -> list[str]:
    """Fetch every manifest file that is missing or does not match its hash.

    A file is written through a ``.part`` file and renamed only after its hash
    matches, so ``raw_dir`` never holds an unchecked file under a final name.

    Args:
        raw_dir: Destination directory (created if needed).
        manifest: File name → expected SHA-256.
        commit: Commit to fetch from.
        url_template: URL with ``{commit}`` and ``{name}`` placeholders.
        fetch: Callable that returns the body of a URL (injected in tests).
        force: Re-fetch every file, even those that already match.

    Returns:
        Names of the files fetched, in manifest order.

    Raises:
        HashMismatchError: A fetched file does not match its manifest hash.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    fetched: list[str] = []
    for name, expected in sorted(manifest.items()):
        path = raw_dir / name
        if not force and path.is_file() and sha256_file(path) == expected:
            continue
        data = fetch(url_template.format(commit=commit, name=name))
        actual = sha256_bytes(data)
        if actual != expected:
            raise HashMismatchError(
                f"{name}: expected {expected}, got {actual} (commit {commit})"
            )
        part = path.with_name(path.name + ".part")
        part.write_bytes(data)
        os.replace(part, path)
        fetched.append(name)
    return fetched


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Download PokéAPI CSVs.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--check", action="store_true", help="verify only")
    parser.add_argument("--force", action="store_true", help="re-fetch all")
    args = parser.parse_args(argv)

    if not args.check:
        fetched = download(args.raw_dir, force=args.force)
        print(f"PokéAPI @ {POKEAPI_COMMIT[:12]}: fetched {len(fetched)} file(s)")
        fetched = download(
            args.raw_dir,
            manifest=WORDLIST_MANIFEST,
            commit=WORDLIST_COMMIT,
            url_template=WORDLIST_URL,
            force=args.force,
        )
        print(f"Word list @ {WORDLIST_COMMIT[:12]}: fetched {len(fetched)} file(s)")
    status = verify(args.raw_dir) | verify(args.raw_dir, WORDLIST_MANIFEST)
    bad = {name: s for name, s in status.items() if s != "ok"}
    for name, s in bad.items():
        print(f"  {s.upper():8} {name}")
    print(f"{len(status) - len(bad)} of {len(status)} files match the manifest")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
