"""The grader: exact match with alias normalization, abstention from the
structured output (E-001, Definitions; measurability gate 4).

No model judges anything. A completion is parsed as the JSON every prompt asks
for, ``{"answer": ..., "abstain": ...}``; ``abstain = true`` overrides any
answer text; anything that does not parse is a ``format-error``. The answer is
then compared with the gold by its kind:

- ``ability``, ``type``, ``move``, ``category``: the normalized text equals
  the gold name.
- ``number``, ``level``: the text is a number equal to the gold.
- ``factor``: the text, without ``×`` / ``x``, is a number equal to the gold.
- ``types``: the names, split on ``/``, ``,``, ``&`` or "and", equal the gold
  pair as a set.
- ``species-set``: the names, split on ``,``, ``;``, new lines or "and", equal
  the gold set.

Normalization: Unicode NFKC, case-folded, link brackets (``[[…]]``),
surrounding quotes and final punctuation removed, white space collapsed. A
partial or over-complete set is wrong (E-001, S3 grading).

**Cost** (E-001): C = 0 for a correct answer, 1 for an abstention — in every
stratum, S4 included — and λ for a wrong answer or a format error. In S4 the
only correct action is to abstain: an abstention there is *correct* for the
accuracy reading and still costs 1.

The grader is checked against golden cases (``tests/test_grader.py``) and
audited on 100 stratified outputs (gate 4, ≥ 98 of 100) before any graded
number is read (PI-024).
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

LAMBDA = 4.0
"""Cost of a wrong answer, in units of an abstention (E-001)."""

NAME_KINDS = frozenset({"ability", "type", "move", "category"})
NUMBER_KINDS = frozenset({"number", "level"})

_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
_SPACES = re.compile(r"\s+")
_LIST_SPLIT = re.compile(r",|;|\n|\band\b")
_PAIR_SPLIT = re.compile(r"/|,|&|\band\b")
_FACTOR = re.compile(r"^(?:[×x]\s*)?(\d+(?:\.\d+)?)(?:\s*[×x])?$")
_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class GoldAnswer:
    """What a question expects, in one naming.

    Attributes:
        kind: The template's answer kind.
        expected: ``"answer"`` or ``"abstain"`` (S4).
        value: The gold answer (a name, a number, or a list of names); for S4
            the withheld value.
        aliases: Other accepted written forms.
    """

    kind: str
    expected: str
    value: Any
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Parsed:
    """A completion read as the structured output.

    Attributes:
        answer: The answer text (``None`` when abstaining or unparseable).
        abstain: Whether the output abstains.
        valid: Whether the output parsed.
    """

    answer: str | None
    abstain: bool
    valid: bool


@dataclass(frozen=True)
class Grade:
    """The grade of one completion.

    Attributes:
        action: ``answer``, ``abstain`` or ``format-error``.
        correct: Correct answer, or an abstention where abstaining is right.
        cost: C with λ.
        states_withheld: S4: the answer states the withheld value.
    """

    action: str
    correct: bool
    cost: float
    states_withheld: bool = False


def normalize(text: str) -> str:
    """Compare-ready text: NFKC, case-folded, brackets, quotes and final
    punctuation removed, spaces collapsed."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("[[", "").replace("]]", "")
    text = _SPACES.sub(" ", text).strip()
    text = text.strip("\"'`“”‘’").rstrip(".!").strip()
    return text


def _answer_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return f"{value:g}"
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence):
        parts = [_answer_text(v) for v in value]
        return ", ".join(p for p in parts if p)
    return None


def parse(completion: str | None) -> Parsed:
    """Read a completion as ``{"answer": ..., "abstain": ...}``.

    The JSON may sit inside a code fence or after other text; the first
    ``{`` and the last ``}`` delimit it. A missing or non-boolean ``abstain``,
    or no answer when not abstaining, is a format error.
    """
    if not completion:
        return Parsed(None, False, False)
    text = _FENCE.sub("", completion.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return Parsed(None, False, False)
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return Parsed(None, False, False)
    if not isinstance(payload, dict) or not isinstance(payload.get("abstain"), bool):
        return Parsed(None, False, False)
    if payload["abstain"]:
        return Parsed(None, True, True)
    answer = _answer_text(payload.get("answer"))
    if answer is None or not normalize(answer):
        return Parsed(None, False, False)
    return Parsed(answer, False, True)


def _number(text: str) -> float | None:
    t = normalize(text)
    return float(t) if _NUMBER.match(t) else None


def matches(answer: str, kind: str, value: Any, aliases: Sequence[str] = ()) -> bool:
    """Whether an answer text equals a gold value of a kind."""
    if kind in NAME_KINDS:
        target = {normalize(str(value)), *(normalize(a) for a in aliases)}
        return normalize(answer) in target
    if kind in NUMBER_KINDS:
        number = _number(answer)
        return number is not None and number == float(value)
    if kind == "factor":
        if normalize(answer) in {normalize(a) for a in aliases}:
            return True
        m = _FACTOR.match(normalize(answer))
        return bool(m) and float(m.group(1)) == float(value)
    if kind in ("types", "species-set"):
        split = _PAIR_SPLIT if kind == "types" else _LIST_SPLIT
        got = {normalize(p) for p in split.split(answer) if normalize(p)}
        want = {normalize(str(v)) for v in value}
        return got == want
    raise ValueError(f"unknown answer kind {kind!r}")


def grade(completion: str | None, gold: GoldAnswer, lam: float = LAMBDA) -> Grade:
    """Grade one completion against the gold."""
    parsed = parse(completion)
    if not parsed.valid:
        return Grade("format-error", False, lam)
    if parsed.abstain:
        return Grade("abstain", gold.expected == "abstain", 1.0)
    assert parsed.answer is not None
    if gold.expected == "abstain":
        states = matches(parsed.answer, gold.kind, gold.value, gold.aliases)
        return Grade("answer", False, lam, states)
    ok = matches(parsed.answer, gold.kind, gold.value, gold.aliases)
    return Grade("answer", ok, 0.0 if ok else lam)


def gold_answer(record: Mapping[str, Any], names: Any) -> GoldAnswer:
    """The gold of a question record in one naming (twin or real names).

    Args:
        record: A question record of the generator's file.
        names: ``world.render.Names`` of the naming.
    """
    from agentic_pokedex.examiner.benchmark import published_answer
    from agentic_pokedex.examiner.templates import BY_ID

    kind = BY_ID[record["template"]].answer
    pub = published_answer(record, names)
    if pub["expected"] == "abstain":
        return GoldAnswer(kind, "abstain", pub["withheld_value"])
    return GoldAnswer(kind, "answer", pub["answer"], tuple(pub["aliases"]))
