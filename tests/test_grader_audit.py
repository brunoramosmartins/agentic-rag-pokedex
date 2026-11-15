"""Gate 4's audit: drawing, the sheet and the decision (no network)."""

from __future__ import annotations

from collections import Counter

from agentic_pokedex.evaluation.grader import GoldAnswer
from agentic_pokedex.evaluation.grader_audit import (
    THRESHOLD,
    Output,
    outputs_e004,
    outputs_e005,
    render_item,
    render_sheet,
    sample,
    score,
)
from agentic_pokedex.examiner.audit import read_verdicts, set_verdict

GOLD = GoldAnswer("level", "answer", 3)
ANSWER = '{"answer": "3", "abstain": false}'
ABSTAIN = '{"answer": null, "abstain": true}'


def outputs() -> list[Output]:
    out = []
    for stratum in ("S0", "S1", "S2", "S3", "S4"):
        for k, source in enumerate(("e004-A0", "e004-A1", "e005-twin")):
            for i in range(12):
                completion = (ABSTAIN if i % 2 else ANSWER) if i else "broken"
                out.append(Output(source, f"q-{stratum[1]}{k}{i:02d}abc",
                                  f"{stratum}-A1", "Q?", completion, GOLD))
    return out


def test_sample_is_stratified_and_seeded() -> None:
    items = sample(outputs())
    assert len(items) == 100
    assert set(Counter(o.stratum for o in items).values()) == {20}
    assert sample(outputs()) == items


def test_sample_takes_format_errors_then_answers_first() -> None:
    items = sample(outputs())
    s0 = [o for o in items if o.stratum == "S0"]
    # Each source: its one format error, its 5 answers, then abstentions.
    assert sum(o.completion == "broken" for o in s0) == 3
    assert sum(o.completion == ANSWER for o in s0) == 15
    assert sum(o.completion == ABSTAIN for o in s0) == 2


def test_item_shows_question_gold_completion_and_grade() -> None:
    text = render_item(1, Output("e004-A1", "q-0123456789", "S2-A1", "At what level?",
                                 ANSWER, GOLD))
    assert text.startswith("## 1. S2-A1/e004-A1 — q-0123456789")
    assert "**Gold (level):** 3" in text and "    " + ANSWER in text
    assert "**Grader:** answer · correct yes · C 0" in text
    s4 = render_item(2, Output("e005-real", "q-0123456789", "S4-A1", "At what level?",
                               ABSTAIN, GoldAnswer("level", "abstain", 9)))
    assert "abstain (withheld value: 9)" in s4 and "C 1" in s4


def test_sheet_round_trip_and_decision() -> None:
    items = sample(outputs())
    sheet = render_sheet(items)
    verdicts = read_verdicts(sheet)
    assert len(verdicts) == 100 and score(verdicts)["decision"] == "pending"
    for n in range(1, 101):
        sheet = set_verdict(sheet, n, "ok" if n > 100 - THRESHOLD else
                            "wrong — misread")
    result = score(read_verdicts(sheet))
    assert (result["ok"], result["wrong"], result["decision"]) == (98, 2, "pass")
    sheet = set_verdict(sheet, 50, "wrong — misread")
    assert score(read_verdicts(sheet))["decision"] == "fail"


def test_outputs_from_run_states() -> None:
    e005 = {"single": {"twin|q-1": {
        "arm": "twin", "question": "q-1", "template": "S0-A2", "status": "done",
        "messages": [{"role": "user", "content": "…\nQuestion: How much power?"}],
        "completion": ANSWER,
        "gold": {"kind": "number", "expected": "answer", "value": 3,
                 "aliases": []}}}}
    [o] = outputs_e005(e005)
    assert (o.source, o.text, o.gold.value) == ("e005-twin", "How much power?", 3)
    e004 = {"single": {"A1|q-2": {
        "arm": "A1", "question": "q-2", "local": "S2-A1:x", "status": "done",
        "messages": [{"role": "user",
                      "content": "…\nQuestion: At what level?\n\nEvidence:\nU"}],
        "completion": ANSWER}},
        "agent": {"q-3": {"local": "S1-A1:y", "state": {
            "question": "q-3", "final": ABSTAIN,
            "messages": [{"role": "user", "content": "…\nQuestion: Which?"}]}}}}
    outs = outputs_e004(e004, {"S2-A1:x": GOLD, "S1-A1:y": GOLD},
                        {"S2-A1:x": "S2-A1", "S1-A1:y": "S1-A1"})
    assert [(o.source, o.text) for o in outs] == [("e004-A1", "At what level?"),
                                                 ("e004-A3", "Which?")]
