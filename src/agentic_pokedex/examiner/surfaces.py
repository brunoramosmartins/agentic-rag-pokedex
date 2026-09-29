"""Hand-written surface forms: three per template (`docs/examiner.md`).

No LLM paraphrase in v1: a paraphrase can change what a question asks, and a
correct gold answer to a changed question is a wrong gold answer. S4 reuses
S2's forms, so the wording never reveals whether an answer exists.

Placeholders: ``{X}`` species, ``{M}`` move, ``{A}`` / ``{B}`` / ``{T}``
types, ``{V}`` version group, ``{L}`` level, ``{TERM}`` the world's word for
"Pokémon" (twin: a pseudo-word), singular and plural alike, as "Pokémon".
"""

from __future__ import annotations

import random
from collections.abc import Mapping

SURFACES: Mapping[str, tuple[str, str, str]] = {
    "S0-A1": (
        "What is {X}'s hidden ability?",
        "Which ability does {X} have as its hidden ability?",
        "Name the hidden ability of {X}.",
    ),
    "S0-A2": (
        "What is the base power of {M}?",
        "How much power does the move {M} have?",
        "What power does {M} have?",
    ),
    "S0-A3": (
        "Is {M} a physical, special or status move?",
        "What damage category does {M} belong to?",
        "Which category is the move {M}: physical, special or status?",
    ),
    "S0-A4": (
        "What type is the move {M}?",
        "Which type does {M} belong to?",
        "{M} is a move of which type?",
    ),
    "S0-B1": (
        "How effective is a {A}-type attack against a {B}-type target?",
        "What damage multiplier does {A} deal to {B}?",
        "Against a {B}-type defender, how effective is a {A}-type attack?",
    ),
    "S1-A1": (
        "What is the hidden ability of the final form of {X}'s evolution line?",
        "{X} eventually reaches a final evolution. What is that form's hidden "
        "ability?",
        "Which hidden ability does the last evolution of {X} have?",
    ),
    "S1-A2": (
        "What types does the final form of {X}'s evolution line have?",
        "{X} eventually reaches a final evolution. What are its types?",
        "Which types does the last evolution of {X} have?",
    ),
    "S1-A3": (
        "What is the hidden ability of the species {X} evolves into?",
        "{X} evolves into another species. What is that species' hidden ability?",
        "Which hidden ability does {X}'s evolution have?",
    ),
    "S1-B1": (
        "How effective is {M} against {X}?",
        "If {M} hits {X}, what is its type damage multiplier?",
        "What type-effectiveness multiplier does {M} get against {X}?",
    ),
    "S2-A1": (
        "At what level does {X} learn {M} in {V}?",
        "In {V}, at which level does {X} learn {M}?",
        "{X} learns {M} by leveling up in {V}. At what level?",
    ),
    "S2-A2": (
        "Which move does {X} learn at level {L} in {V}?",
        "In {V}, what move does {X} learn upon reaching level {L}?",
        "Name the move {X} learns at level {L} in {V}.",
    ),
    "S2-B1": (
        "What is the last move {X} learns by leveling up in {V}?",
        "In {V}, which move does {X} learn at the highest level?",
        "Which level-up move does {X} learn last in {V}?",
    ),
    "S3-A1": (
        "Which {T}-type {TERM} learn {M} by leveling up in {V}?",
        "List every {T}-type {TERM} that learns {M} by level-up in {V}.",
        "In {V}, which {TERM} of type {T} learn {M} by leveling up?",
    ),
    "S3-B1": (
        "Which {T}-type {TERM} learn {M} by leveling up in {V} at or below "
        "level {L}?",
        "List every {T}-type {TERM} that learns {M} by level {L} or earlier "
        "in {V}.",
        "In {V}, which {TERM} of type {T} learn {M} by leveling up no later "
        "than level {L}?",
    ),
}
SURFACES = {**SURFACES, "S4-A1": SURFACES["S2-A1"], "S4-B1": SURFACES["S2-A2"]}


def surface_index(question_id: str, seed: int) -> int:
    """Which of the three forms a question uses: seeded by its id, so stable."""
    return random.Random(f"{seed}:{question_id}").randrange(3)


def render(template: str, index: int, slots: Mapping[str, str]) -> str:
    """Fill one surface form's placeholders.

    Raises:
        KeyError: A placeholder has no value.
    """
    return SURFACES[template][index].format(**slots)
