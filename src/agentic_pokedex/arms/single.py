"""The one-call arms: A0 closed-book, A1 single-shot, A2 fixed pipeline.

Each builds one chat message from a prompt of ``prompts/`` and, for A1 and A2,
the evidence its retrieval delivers. Prompts carry ``{question}`` and
``{evidence}`` placeholders, filled by plain replacement (the prompts hold JSON
braces, so ``str.format`` is never used).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from agentic_pokedex.arms.typed_expansion import World, expand
from agentic_pokedex.tools.contract import UNIT_SEPARATOR, TokenCounter
from agentic_pokedex.tools.search import search

CLOSED_BOOK_PROMPT = "answer_closed_book_v0"
EVIDENCE_PROMPT = "answer_with_evidence_v0"
SINGLE_SHOT_K = 5
"""A1's k in the pilot (untuned; the Phase 4 sweep tunes it on dev)."""


def fill(template: str, **slots: str) -> str:
    """Replace ``{name}`` placeholders with their values."""
    text = template
    for name, value in slots.items():
        text = text.replace("{" + name + "}", value)
    return text


def user_messages(text: str) -> list[dict[str, str]]:
    """One user message: the filled prompt."""
    return [{"role": "user", "content": text}]


@dataclass(frozen=True)
class Evidence:
    """What a retrieval arm puts before the model.

    Attributes:
        units: Distinct unit ids, in delivery order.
        tokens: Evidence tokens the tools returned (B's accounting).
        text: The units' texts, joined.
    """

    units: tuple[str, ...]
    tokens: int
    text: str


def evidence_of(
    units: Sequence[str], tokens: int, texts: Mapping[str, str]
) -> Evidence:
    """Evidence from delivered units."""
    text = UNIT_SEPARATOR.join(texts[u] for u in units)
    return Evidence(tuple(units), tokens, text)


def single_shot(
    world: World, question: str, counter: TokenCounter, k: int = SINGLE_SHOT_K
) -> Evidence:
    """A1: one ``search`` with the question text."""
    result = search(world.index, question, k, counter=counter)
    return evidence_of(result.unit_ids, result.tokens, world.texts)


def fixed_pipeline(world: World, question: str, counter: TokenCounter) -> Evidence:
    """A2's retrieval: E-002's pipeline at its frozen configuration (k = 5)."""
    delivery = expand(world, question, k=5, counter=counter)
    return evidence_of(delivery.units, delivery.tokens, world.texts)


def closed_book_text(prompt: str, question: str) -> str:
    """A0's message."""
    return fill(prompt, question=question)


def evidence_text(prompt: str, question: str, evidence: Evidence) -> str:
    """A1's or A2's message."""
    return fill(prompt, question=question, evidence=evidence.text)
