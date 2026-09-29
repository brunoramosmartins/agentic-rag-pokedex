"""The counterfactual twin: every name renamed, every fact intact (ADR-003).

Species, forms, moves, abilities, types, version names and the word "Pokémon"
get pronounceable pseudo-words, drawn from a seeded generator **independently
of the real name**, so a twin name carries no trace of the entity it replaces.
Numbers (levels, power) are never touched.

A candidate pseudo-word is rejected when it:

- is a real name or identifier in any language PokéAPI lists, or a franchise
  term (regions, "poke");
- is an English word (the pinned ``words_alpha.txt`` list);
- looks like an English real name: same first or last four letters, one edit
  away (a shared single-deletion neighbour), or contains one of five letters
  or more;
- is already taken by another twin name, of any kind.

Form names keep their shape: the species part is replaced by the species' twin
name and every other word by a consistent pseudo-word ("Mega Charizard X" →
"<mega> <twin> X"). Version-group names are rebuilt from their versions' twin
names ("Scarlet/Violet" → "<twin>/<twin>").

Free text (Pokédex flavor) is rewritten with the same map: every Title-case or
upper-case occurrence of a real name is replaced. Lower-case prose ("spits
fire") is left alone; it is the leak surface the identity probe measures (G2).

The map is written to ``data/world/twin_map.json`` (gitignored); only
``TWIN_SEED`` is versioned. Round trip — real → twin → real — is identity for
every name of every kind.

Usage::

    python -m agentic_pokedex.world.twin
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from agentic_pokedex.config import REPO_ROOT
from agentic_pokedex.world.download import DEFAULT_RAW_DIR, WORDLIST_MANIFEST
from agentic_pokedex.world.pokeapi import WorldTables, read_csv, read_world

TWIN_SEED = 20260929
DEFAULT_MAP_PATH = REPO_ROOT / "data" / "world" / "twin_map.json"
WORDLIST_FILE = next(iter(WORDLIST_MANIFEST))

KINDS = (
    "species",
    "pokemon",
    "form_word",
    "type",
    "ability",
    "move",
    "version",
    "version_group",
    "term",
)
"""Every kind of name the twin maps. ``form_word`` holds the words of form
names other than the species ("Mega", "Alolan"); ``term`` holds "Pokémon"."""

TEXT_KINDS = ("species", "pokemon", "term", "type", "ability", "move")
"""Kinds rewritten in free text, in priority order when two kinds share a name
("Psychic" is a type and a move). Version names stay out: flavor text never
names a game, and "X", "Y", "Sun" or "Moon" would be rewritten in plain prose."""

POKEMON_TERM = "Pokémon"
POKEMON_TERM_VARIANTS = ("Pokémon", "POKéMON", "POKÉMON", "Pokemon", "POKEMON")

FRANCHISE_TERMS = frozenset(
    {
        "poke", "pokemon", "pokedex", "pokeball", "nintendo", "gamefreak",
        "kanto", "johto", "hoenn", "sinnoh", "unova", "kalos", "alola", "galar",
        "paldea", "hisui", "kitakami", "orre", "fiore", "almia", "oblivia",
    }
)
"""Franchise words no twin name may equal (normalized: ASCII letters, lower)."""

NAME_FILES = (
    ("pokemon_species_names.csv", ("name",)),
    ("pokemon_form_names.csv", ("form_name", "pokemon_name")),
    ("move_names.csv", ("name",)),
    ("ability_names.csv", ("name",)),
    ("type_names.csv", ("name",)),
    ("version_names.csv", ("name",)),
)
"""Name columns read in every language for the exact-match filter."""

IDENTIFIER_FILES = (
    "pokemon_species.csv",
    "pokemon.csv",
    "moves.csv",
    "abilities.csv",
    "types.csv",
    "versions.csv",
    "version_groups.csv",
)

# Phonotactics: onset + nucleus + optional coda, two or three syllables.
ONSETS = (
    "b", "br", "d", "dr", "f", "fl", "g", "gr", "h", "k", "kr", "l", "m", "n",
    "p", "pr", "r", "s", "sk", "sl", "st", "t", "tr", "v", "z", "th", "sh",
)
NUCLEI = ("a", "e", "i", "o", "u", "a", "e", "o", "ai", "ou", "ei")
CODAS = ("", "", "", "", "n", "r", "l", "s", "k", "m", "x")
SYLLABLES = (2, 2, 3)
WORD_LENGTH = (4, 9)
"""Accepted length of one pseudo-word, in letters."""
CONSONANT_RUN = re.compile(r"[^aeiou]{3,}")
"""Three consonants in a row read badly ("nzothh"); such candidates are redrawn."""
BLOCKED_SUBSTRINGS = (
    "shit", "fuck", "cunt", "dick", "cock", "piss", "slut", "whor", "fag",
    "nig", "rape", "anal", "porn", "cum", "sex", "nazi", "kkk",
)
"""Profanity and slurs no pseudo-word may contain."""
TWO_WORD_SHARE = 0.4
"""Share of move and ability twin names made of two pseudo-words."""

MAX_ATTEMPTS = 10_000

_LETTERS = re.compile(r"[a-z]+")
_WORD = re.compile(r"[^\W\d_]{2,}")
_SPECIES_SLOT = "\x00"


def normalize(name: str) -> str:
    """Fold a name to ASCII lower-case letters ("Farfetch’d" → "farfetchd")."""
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    )
    return "".join(_LETTERS.findall(ascii_name.lower()))


def single_deletions(word: str) -> set[str]:
    """The word and every string obtained by deleting one character."""
    return {word} | {word[:i] + word[i + 1 :] for i in range(len(word))}


# --- Filters ----------------------------------------------------------------


@dataclass
class NameFilter:
    """Decides whether a candidate pseudo-word is acceptable.

    Args:
        forbidden: Normalized strings no candidate may equal (real names in
            every language, identifiers, franchise terms).
        dictionary: Normalized English words.
        english_names: Normalized English real names and their words, for the
            look-alike tests.
    """

    forbidden: set[str]
    dictionary: set[str]
    english_names: set[str]
    _prefixes: set[str] = field(init=False)
    _suffixes: set[str] = field(init=False)
    _neighbours: set[str] = field(init=False)
    _long: list[str] = field(init=False)

    def __post_init__(self) -> None:
        names = {n for n in self.english_names if len(n) >= 4}
        self._prefixes = {n[:4] for n in names if len(n) >= 5}
        self._suffixes = {n[-4:] for n in names if len(n) >= 5}
        self._neighbours = set().union(*(single_deletions(n) for n in names))
        self._long = sorted(n for n in names if len(n) >= 5)

    def reason(self, candidate: str) -> str | None:
        """Why ``candidate`` is rejected, or ``None`` if it is acceptable."""
        word = normalize(candidate)
        if word in self.forbidden or word in FRANCHISE_TERMS:
            return "real-name"
        if word in self.dictionary:
            return "dictionary"
        if word[:4] in self._prefixes or word[-4:] in self._suffixes:
            return "prefix-suffix"
        if single_deletions(word) & self._neighbours:
            return "one-edit"
        if any(name in word for name in self._long):
            return "contains-name"
        return None


def real_names(raw_dir: Path) -> tuple[set[str], set[str]]:
    """Every real name, normalized: all languages, and English only.

    Returns:
        ``(forbidden, english)``. ``forbidden`` holds names in every language,
        their words, and PokéAPI identifiers; ``english`` holds English names
        and their words, for the look-alike tests.
    """
    english_id = next(
        int(r["id"]) for r in read_csv(raw_dir, "languages.csv")
        if r["identifier"] == "en"
    )
    forbidden: set[str] = set()
    english: set[str] = set()
    for file, columns in NAME_FILES:
        for row in read_csv(raw_dir, file):
            for column in columns:
                name = row[column]
                pieces = {normalize(name)} | {normalize(w) for w in name.split()}
                pieces.discard("")
                forbidden |= pieces
                if int(row["local_language_id"]) == english_id:
                    english |= pieces
    for file in IDENTIFIER_FILES:
        for row in read_csv(raw_dir, file):
            ident = row["identifier"]
            forbidden |= {normalize(ident)} | {normalize(p) for p in ident.split("-")}
    forbidden.discard("")
    return forbidden, english


def load_dictionary(path: Path) -> set[str]:
    """Normalized words of a one-word-per-line list."""
    with path.open(encoding="utf-8") as handle:
        return {w for line in handle if (w := normalize(line))}


# --- Generation -------------------------------------------------------------


class PseudoWordGenerator:
    """Seeded pseudo-words that pass a ``NameFilter`` and never repeat."""

    def __init__(self, seed: int, name_filter: NameFilter) -> None:
        self.rng = random.Random(seed)
        self.filter = name_filter
        self.used: set[str] = set()
        self.rejected: dict[str, int] = {}

    def _candidate(self) -> str:
        syllables = self.rng.choice(SYLLABLES)
        word = "".join(
            self.rng.choice(ONSETS) + self.rng.choice(NUCLEI) + self.rng.choice(CODAS)
            for _ in range(syllables)
        )
        return word.capitalize()

    def word(self) -> str:
        """Return a fresh acceptable pseudo-word, capitalized."""
        for _ in range(MAX_ATTEMPTS):
            candidate = self._candidate()
            key = normalize(candidate)
            reason: str | None
            if key in self.used:
                reason = "taken"
            elif not WORD_LENGTH[0] <= len(key) <= WORD_LENGTH[1]:
                reason = "length"
            elif CONSONANT_RUN.search(key):
                reason = "consonant-run"
            elif any(b in key for b in BLOCKED_SUBSTRINGS):
                reason = "blocked"
            else:
                reason = self.filter.reason(candidate)
            if reason:
                self.rejected[reason] = self.rejected.get(reason, 0) + 1
                continue
            self.used.add(key)
            return candidate
        raise RuntimeError(f"no acceptable pseudo-word in {MAX_ATTEMPTS} attempts")

    def name(self, two_word_share: float = 0.0) -> str:
        """One pseudo-word, or two with probability ``two_word_share``."""
        if self.rng.random() < two_word_share:
            return f"{self.word()} {self.word()}"
        return self.word()


# --- The map ----------------------------------------------------------------


@dataclass
class TwinMap:
    """Real name ↔ twin name, per kind."""

    seed: int
    names: dict[str, dict[str, str]]
    _inverse: dict[str, dict[str, str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._inverse = {}
        for kind, mapping in self.names.items():
            inverse: dict[str, str] = {}
            for real, twin in mapping.items():
                if twin in inverse and inverse[twin] != real:
                    raise ValueError(f"{kind}: {twin!r} maps back to two names")
                inverse[twin] = real
            self._inverse[kind] = inverse

    def to_twin(self, kind: str, real: str) -> str:
        """Twin name of a real name."""
        return self.names[kind][real]

    def to_real(self, kind: str, twin: str) -> str:
        """Real name of a twin name."""
        return self._inverse[kind][twin]

    def save(self, path: Path) -> None:
        """Write the map as JSON (gitignored location)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"seed": self.seed, "names": self.names}
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> TwinMap:
        """Read a map written by ``save``."""
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(seed=payload["seed"], names=payload["names"])


def _form_name(
    real: str, species_real: str, species_twin: str, forms: dict[str, str],
    generator: PseudoWordGenerator,
) -> str:
    """Twin name of a non-default Pokémon entry, keeping the name's shape."""
    templated = real.replace(species_real, _SPECIES_SLOT)

    def rename(match: re.Match[str]) -> str:
        word = match.group(0)
        key = word.lower()
        if key not in forms:
            forms[key] = generator.word()
        twin = forms[key]
        return twin.upper() if word.isupper() else twin

    return _WORD.sub(rename, templated).replace(_SPECIES_SLOT, species_twin)


def build_twin(
    tables: WorldTables, name_filter: NameFilter, seed: int = TWIN_SEED
) -> tuple[TwinMap, PseudoWordGenerator]:
    """Draw the twin names of every entity, in a fixed order.

    Entities are visited by kind in ``KINDS`` order and by id within a kind,
    so the same seed and tables always give the same map.

    Args:
        tables: Records from ``pokeapi.read_world``.
        name_filter: The acceptance test for pseudo-words.
        seed: Generator seed.

    Returns:
        The map, and the generator (for its rejection counts).
    """
    gen = PseudoWordGenerator(seed, name_filter)
    names: dict[str, dict[str, str]] = {kind: {} for kind in KINDS}

    species_by_id = {s["id"]: s for s in sorted(tables.species, key=lambda r: r["id"])}
    for s in species_by_id.values():
        if s["name"] not in names["species"]:
            names["species"][s["name"]] = gen.word()

    forms = names["form_word"]
    for p in sorted(tables.pokemon, key=lambda r: r["id"]):
        species_real = species_by_id[p["species_id"]]["name"]
        species_twin = names["species"][species_real]
        if p["name"] in names["pokemon"]:
            continue
        if p["name"] == species_real:
            names["pokemon"][p["name"]] = species_twin
        else:
            names["pokemon"][p["name"]] = _form_name(
                p["name"], species_real, species_twin, forms, gen
            )

    for kind, records, share in (
        ("type", tables.types, 0.0),
        ("ability", tables.abilities, TWO_WORD_SHARE),
        ("move", tables.moves, TWO_WORD_SHARE),
        ("version", tables.versions, 0.0),
    ):
        for r in sorted(records, key=lambda r: r["id"]):
            if r["name"] not in names[kind]:
                names[kind][r["name"]] = gen.name(share)

    versions_by_group: dict[int, list[tuple[int, str]]] = {}
    for v in tables.versions:
        versions_by_group.setdefault(v["version_group_id"], []).append(
            (v["id"], names["version"][v["name"]])
        )
    for g in sorted(tables.version_groups, key=lambda r: r["id"]):
        twins = [t for _, t in sorted(versions_by_group.get(g["id"], []))]
        names["version_group"][g["name"]] = "/".join(twins) if twins else gen.word()

    names["term"][POKEMON_TERM] = gen.word()
    return TwinMap(seed=seed, names=names), gen


# --- Free text --------------------------------------------------------------


@dataclass
class TextRewriter:
    """Rewrite Title-case and upper-case real names in free text."""

    replacements: dict[str, str]
    pattern: re.Pattern[str]

    @classmethod
    def from_map(cls, twin: TwinMap) -> TextRewriter:
        """Build the rewriter from every kind in ``TEXT_KINDS``."""
        replacements: dict[str, str] = {}
        for kind in TEXT_KINDS:
            for real, name in twin.names[kind].items():
                for variant, target in ((real, name), (real.upper(), name.upper())):
                    replacements.setdefault(variant, target)
        term = twin.names["term"][POKEMON_TERM]
        for variant in POKEMON_TERM_VARIANTS:
            # "POKéMON" is upper case in the old games despite its "é".
            upper = sum(c.isupper() for c in variant) > len(variant) // 2
            replacements.setdefault(variant, term.upper() if upper else term)
        alternation = "|".join(
            re.escape(v) for v in sorted(replacements, key=len, reverse=True)
        )
        pattern = re.compile(rf"(?<!\w)(?:{alternation})(?!\w)")
        return cls(replacements, pattern)

    def rewrite(self, text: str) -> str:
        """Replace every known real name in ``text`` by its twin."""
        return self.pattern.sub(lambda m: self.replacements[m.group(0)], text)


# --- Checks -----------------------------------------------------------------


def round_trip_failures(twin: TwinMap, tables: WorldTables) -> list[str]:
    """Real names whose round trip real → twin → real is not the identity."""
    real_by_kind: dict[str, Iterable[str]] = {
        "species": (s["name"] for s in tables.species),
        "pokemon": (p["name"] for p in tables.pokemon),
        "type": (t["name"] for t in tables.types),
        "ability": (a["name"] for a in tables.abilities),
        "move": (m["name"] for m in tables.moves),
        "version": (v["name"] for v in tables.versions),
        "version_group": (g["name"] for g in tables.version_groups),
        "term": (POKEMON_TERM,),
    }
    failures = []
    for kind, reals in real_by_kind.items():
        for real in reals:
            try:
                back = twin.to_real(kind, twin.to_twin(kind, real))
            except KeyError:
                failures.append(f"{kind}: {real!r} has no twin")
                continue
            if back != real:
                failures.append(f"{kind}: {real!r} came back as {back!r}")
    return failures


def collisions(twin: TwinMap) -> list[str]:
    """Generated words used by two different names (across every kind)."""
    owners: dict[str, str] = {}
    problems = []
    generated = ("species", "form_word", "type", "ability", "move", "version", "term")
    for kind in generated:
        for real, name in twin.names[kind].items():
            for word in name.split():
                key = normalize(word)
                owner = f"{kind}:{real}"
                if key in owners and owners[key] != owner:
                    problems.append(f"{word!r}: {owners[key]} and {owner}")
                owners.setdefault(key, owner)
    return problems


def residual_names(texts: Iterable[str], names: Iterable[str]) -> dict[str, int]:
    """Count rewritten texts that still contain a real name, by case.

    ``title_or_upper`` counts names written as given or in upper case (what the
    rewriter must have caught); ``any_case`` also counts lower-case mentions.
    """
    ordered = sorted(set(names), key=len, reverse=True)
    variants = sorted(
        {v for n in ordered for v in (n, n.upper())}, key=len, reverse=True
    )
    exact = re.compile(rf"(?<!\w)(?:{'|'.join(map(re.escape, variants))})(?!\w)")
    loose = re.compile(
        rf"(?<!\w)(?:{'|'.join(map(re.escape, ordered))})(?!\w)", re.IGNORECASE
    )
    counts = {"title_or_upper": 0, "any_case": 0}
    for text in texts:
        counts["title_or_upper"] += bool(exact.search(text))
        counts["any_case"] += bool(loose.search(text))
    return counts


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build the counterfactual twin.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_MAP_PATH)
    parser.add_argument("--seed", type=int, default=TWIN_SEED)
    args = parser.parse_args(argv)

    tables = read_world(args.raw_dir)
    forbidden, english = real_names(args.raw_dir)
    name_filter = NameFilter(
        forbidden, load_dictionary(args.raw_dir / WORDLIST_FILE), english
    )
    twin, gen = build_twin(tables, name_filter, args.seed)

    failures = round_trip_failures(twin, tables)
    clashes = collisions(twin)
    rewriter = TextRewriter.from_map(twin)
    rewritten = [rewriter.rewrite(f["text"]) for f in tables.flavor_texts]
    changed = sum(
        1 for f, r in zip(tables.flavor_texts, rewritten, strict=True) if f["text"] != r
    )
    residual = residual_names(rewritten, (s["name"] for s in tables.species))

    print(f"Twin seed {args.seed}")
    for kind in KINDS:
        print(f"  {kind:14} {len(twin.names[kind]):>6,}")
    print("Rejected candidates:", dict(sorted(gen.rejected.items())))
    print(f"Flavor texts rewritten: {changed:,} of {len(rewritten):,}")
    print(
        "Rewritten flavor texts still naming a real species: "
        f"{residual['title_or_upper']:,} (Title/UPPER), "
        f"{residual['any_case']:,} (any case)"
    )
    for line in failures[:20] + clashes[:20]:
        print("  FAIL", line)
    ok = not failures and not clashes and residual["title_or_upper"] == 0
    print("ROUND TRIP:", "PASS" if not failures else f"FAIL ({len(failures)})")
    print("UNIQUE NAMES:", "PASS" if not clashes else f"FAIL ({len(clashes)})")

    twin.save(args.out)
    print(f"Map written to {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
