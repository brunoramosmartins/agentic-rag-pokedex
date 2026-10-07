"""The grader: golden completions with known grades (PI-024, gate 4)."""

from __future__ import annotations

import pytest

from agentic_pokedex.evaluation.grader import (
    LAMBDA,
    GoldAnswer,
    gold_answer,
    grade,
    matches,
    normalize,
    parse,
)

ABILITY = GoldAnswer("ability", "answer", "Hairrur Stobireis")
LEVEL = GoldAnswer("level", "answer", 3)
NUMBER = GoldAnswer("number", "answer", 40)
CATEGORY = GoldAnswer("category", "answer", "physical")
FACTOR = GoldAnswer("factor", "answer", 0.5, ("×0.5", "x0.5", "0.5"))
TYPES = GoldAnswer("types", "answer", ["Slomdei", "Stikrar"])
SET = GoldAnswer("species-set", "answer", ["Baiflaim", "Dordol", "Haski"])
S4_LEVEL = GoldAnswer("level", "abstain", 9)
S4_MOVE = GoldAnswer("move", "abstain", "Thagrir")


def js(answer: object, abstain: bool = False) -> str:
    import json

    return json.dumps({"answer": answer, "abstain": abstain}, ensure_ascii=False)


# (name, completion, gold, action, correct, cost)
GOLDEN = [
    ("exact name", js("Hairrur Stobireis"), ABILITY, "answer", True, 0.0),
    ("case and spaces", js("  hairrur   STOBIREIS "), ABILITY, "answer", True, 0.0),
    ("link brackets and a period", js("[[Hairrur Stobireis]]."), ABILITY, "answer",
     True, 0.0),
    ("a different name", js("Hairrur"), ABILITY, "answer", False, LAMBDA),
    ("level as digits", js("3"), LEVEL, "answer", True, 0.0),
    ("level as a number", js(3), LEVEL, "answer", True, 0.0),
    ("level with a word", js("level 3"), LEVEL, "answer", False, LAMBDA),
    ("power", js("40"), NUMBER, "answer", True, 0.0),
    ("category, capitalized", js("Physical"), CATEGORY, "answer", True, 0.0),
    ("factor ×0.5", js("×0.5"), FACTOR, "answer", True, 0.0),
    ("factor 0.5x", js("0.5x"), FACTOR, "answer", True, 0.0),
    ("factor .50 as a number", js(0.5), FACTOR, "answer", True, 0.0),
    ("factor ×2", js("×2"), FACTOR, "answer", False, LAMBDA),
    ("type pair, other order", js("Stikrar / Slomdei"), TYPES, "answer", True, 0.0),
    ("type pair with 'and'", js("Slomdei and Stikrar"), TYPES, "answer", True, 0.0),
    ("one type of two", js("Slomdei"), TYPES, "answer", False, LAMBDA),
    ("set, any order", js("Haski, Baiflaim, Dordol"), SET, "answer", True, 0.0),
    ("set as a JSON list", js(["Dordol", "Haski", "Baiflaim"]), SET, "answer",
     True, 0.0),
    ("set with 'and'", js("Baiflaim, Dordol and Haski"), SET, "answer", True, 0.0),
    ("partial set", js("Baiflaim, Dordol"), SET, "answer", False, LAMBDA),
    ("over-complete set", js("Baiflaim, Dordol, Haski, Nouta"), SET, "answer",
     False, LAMBDA),
    ("abstain", js(None, True), ABILITY, "abstain", False, 1.0),
    ("abstain overrides the answer", js("Hairrur Stobireis", True), ABILITY,
     "abstain", False, 1.0),
    ("S4 abstain is correct, still costs 1", js(None, True), S4_LEVEL, "abstain",
     True, 1.0),
    ("S4 answered", js("9"), S4_LEVEL, "answer", False, LAMBDA),
    ("fenced JSON", "```json\n" + js("3") + "\n```", LEVEL, "answer", True, 0.0),
    ("JSON after text", "Here it is: " + js("3"), LEVEL, "answer", True, 0.0),
    ("not JSON", "The answer is 3.", LEVEL, "format-error", False, LAMBDA),
    ("abstain missing", '{"answer": "3"}', LEVEL, "format-error", False, LAMBDA),
    ("abstain as a string", '{"answer": "3", "abstain": "false"}', LEVEL,
     "format-error", False, LAMBDA),
    ("no answer, not abstaining", js(None), LEVEL, "format-error", False, LAMBDA),
    ("empty answer", js("  "), LEVEL, "format-error", False, LAMBDA),
    ("empty completion", "", LEVEL, "format-error", False, LAMBDA),
]


@pytest.mark.parametrize(("name", "completion", "gold", "action", "correct", "cost"),
                         GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden(name: str, completion: str, gold: GoldAnswer, action: str,
                correct: bool, cost: float) -> None:
    g = grade(completion, gold)
    assert (g.action, g.correct, g.cost) == (action, correct, cost), name


def test_s4_records_whether_the_withheld_value_was_stated() -> None:
    assert grade(js("9"), S4_LEVEL).states_withheld
    assert not grade(js("12"), S4_LEVEL).states_withheld
    assert grade(js("thagrir"), S4_MOVE).states_withheld
    assert not grade(js(None, True), S4_MOVE).states_withheld


def test_normalize() -> None:
    assert normalize(' "[[Mr. Mime]]." ') == "mr. mime"
    assert normalize("Farfetch'd") == "farfetch'd"
    assert normalize("ＡＢＣ") == "abc"  # full-width, NFKC


def test_parse_keeps_the_answer_text() -> None:
    assert parse(js("Haski")).answer == "Haski"
    assert parse(js(["A", "B"])).answer == "A, B"
    assert parse(js(None, True)).abstain


def test_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown answer kind"):
        matches("x", "colour", "x")


class FakeNames:
    """The name tables ``published_answer`` reads."""

    abilities = {3: "Undertow"}
    types = {1: "Ember", 2: "Tide"}
    moves = {1: "Vine Lash"}
    species: dict[int, str] = {}


def test_gold_answer_from_a_record() -> None:
    names = FakeNames()
    record = {"template": "S0-A1", "stratum": "S0", "answer": 3}
    assert gold_answer(record, names) == GoldAnswer("ability", "answer", "Undertow")
    s4 = {"template": "S4-B1", "stratum": "S4", "answer": 1}
    assert gold_answer(s4, names) == GoldAnswer("move", "abstain", "Vine Lash")
    pair = {"template": "S1-A2", "stratum": "S1", "answer": [2, 1]}
    assert gold_answer(pair, names).value == ["Ember", "Tide"]
