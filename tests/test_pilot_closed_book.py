"""E-004 and E-005 runners: sampling, rounds, decisions (no network)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from agentic_pokedex.arms import agent
from agentic_pokedex.evaluation import batchrun, closed_book, pilot
from agentic_pokedex.evaluation.grader import GoldAnswer
from agentic_pokedex.llm.batch import BatchResult
from agentic_pokedex.observability.tokens import Usage

# --- Batch rounds -------------------------------------------------------------


def test_custom_id_round_trip() -> None:
    cid = batchrun.custom_id("e004", "A3", "q-0123456789", 2, 1)
    assert cid == "e004.A3.q-0123456789.r2.t1"
    assert batchrun.parse_custom_id(cid) == ("e004", "A3", "q-0123456789", 2, 1)


def test_rounds_and_unsent(tmp_path: Path) -> None:
    run = batchrun.RunDir(tmp_path)
    assert run.write_round([]) is None and run.next_round() == 0
    first = run.write_round([{"custom_id": "a"}])
    second = run.write_round([{"custom_id": "b"}])
    assert [p.name for p in run.rounds()] == ["requests-r0.jsonl", "requests-r1.jsonl"]
    run.save("batches.json", [{"id": "b1", "file": first.name, "collected": True}])
    assert run.unsent() == [second]


def entry(arm: str = "A0", question: str = "q-1") -> dict:
    return {"arm": arm, "question": question, "attempt": 0, "status": "pending",
            "messages": [{"role": "user", "content": "hi"}]}


def ok(cid: str, content: str = '{"answer": "3", "abstain": false}') -> BatchResult:
    return BatchResult(cid, content, "stop", Usage(10, 0, 5, 3), None)


def failed(cid: str) -> BatchResult:
    return BatchResult(cid, None, None, None, "server")


def test_apply_single_success_and_retries() -> None:
    e = entry()
    assert batchrun.apply_single("e004", e, ok("x"), 0) is None
    assert e["status"] == "done" and e["usage"]["reasoning_tokens"] == 3
    e = entry()
    for attempt in range(1, batchrun.MAX_TRIES + 1):
        line = batchrun.apply_single("e004", e, failed("x"), attempt)
        assert line["custom_id"].endswith(f".t{attempt}")
        assert line["body"]["max_completion_tokens"] == 4_000
        assert line["body"]["reasoning_effort"] == "low"
    assert batchrun.apply_single("e004", e, failed("x"), 9) is None
    assert e["status"] == "failed"
    assert batchrun.apply_single("e004", e, ok("x"), 10) is None  # stays failed


# --- E-004 ---------------------------------------------------------------------


def records() -> list[dict]:
    out = []
    for s, n in (("S0", 30), ("S1", 30), ("S2", 30), ("S3", 30), ("S4", 30)):
        for i in range(n):
            out.append({"id": f"{s}-A1:x={i}", "stratum": s, "template": f"{s}-A1",
                        "slots": {"X": i % 10, "M": i % 6, "V": "x-y"},
                        "gold_facts": []})
    return out


def test_agent_sample_is_stratified_seeded_and_spread_over_clusters() -> None:
    recs = records()
    ids = pilot.sample_agent_questions(recs)
    assert len(ids) == 30 and len(set(ids)) == 30
    by = {r["id"]: r for r in recs}
    per = Counter(by[q]["stratum"] for q in ids)
    assert "S0" not in per and sorted(per.values()) == [7, 7, 8, 8]
    s3 = [pilot.cluster_key(by[q]) for q in ids if by[q]["stratum"] == "S3"]
    assert len(set(s3)) == min(len(s3), 6)  # 6 moves: every cluster before repeats
    assert pilot.sample_agent_questions(recs) == ids


def test_apply_results_folds_both_kinds() -> None:
    a0 = entry("A0", "q-1")
    st = agent.start("q-2", "Which?", "Q: {question}")
    state = {"single": {"A0|q-1": a0},
             "agent": {"q-2": {"local": "x", "attempt": 0, "state": st.to_dict()}}}
    results = [ok("e004.A0.q-1.r0.t0"),
               ok("e004.A3.q-2.r0.t0", '{"answer": null, "abstain": true}')]
    nxt = pilot.apply_results(state, results, world=None, counter=len,
                              final_prompt="final", round_=1)
    assert nxt == [] and a0["status"] == "done"
    assert state["agent"]["q-2"]["state"]["done"]


def test_an_agent_failure_is_resent() -> None:
    st = agent.start("q-2", "Which?", "Q: {question}")
    state = {"single": {},
             "agent": {"q-2": {"local": "x", "attempt": 0, "state": st.to_dict()}}}
    nxt = pilot.apply_results(state, [failed("e004.A3.q-2.r0.t0")], world=None,
                              counter=len, final_prompt="final", round_=1)
    assert len(nxt) == 1 and nxt[0]["custom_id"] == "e004.A3.q-2.r1.t1"
    assert "tools" in nxt[0]["body"]


def test_describe_prints_no_grade() -> None:
    a0 = entry("A0", "q-1")
    pilot_state = {"single": {"A0|q-1": a0}, "agent": {}}
    batchrun.apply_single("e004", a0, ok("x"), 0)
    out = pilot.describe(pilot_state)
    assert out["arms"]["A0"]["calls"] == 1
    text = str(out).lower()
    assert "cost_usd" in text and "correct" not in text and "'c'" not in text


# --- E-005 ---------------------------------------------------------------------


def test_closed_book_sample_skips_excluded_and_caps_per_template() -> None:
    recs = records()
    excluded = {r["id"] for r in recs[:5]}
    ids = closed_book.sample(recs, excluded, per_template=20)
    assert not set(ids) & excluded
    by = {r["id"]: r for r in recs}
    assert set(Counter(by[q]["template"] for q in ids).values()) == {20}
    assert closed_book.sample(recs, excluded, per_template=20) == ids


def test_chance_is_majority_never_below_uniform() -> None:
    report = {"S0-A3": {"cap": {"values": 3, "majority_after": 0.40}},
              "S0-A1": {"cap": {"values": 162, "majority_after": 0.0257}},
              "S0-B1": {"cap": {"values": 2, "majority_after": 0.38}}}
    assert closed_book.chance("S0-A3", report, []) == 0.40
    assert closed_book.chance("S0-A1", report, []) == 0.0257
    assert closed_book.chance("S0-B1", report, []) == 0.5  # uniform floor
    golds = [GoldAnswer("level", "abstain", v) for v in (3, 3, 5, 7)]
    assert closed_book.chance("S4-A1", {}, golds) == 0.5


def test_correct_for_g2() -> None:
    js = '{"answer": "9", "abstain": false}'
    abstain = '{"answer": null, "abstain": true}'
    s4 = GoldAnswer("level", "abstain", 9)
    assert closed_book.correct_for_g2(js, s4)  # states the withheld value
    assert not closed_book.correct_for_g2(abstain, s4)
    s0 = GoldAnswer("level", "answer", 9)
    assert closed_book.correct_for_g2(js, s0)
    assert not closed_book.correct_for_g2(abstain, s0)


def reading(template: str, naming: str, k: int, chance: float = 0.1):
    return closed_book.read_template(template, naming, [True] * k + [False] * (50 - k),
                                     chance)


def test_the_rule_reads_the_wilson_lower_limit() -> None:
    assert not reading("S0-A1", "twin", 10).above  # 20%: lower ≈ 11%
    assert reading("S0-A1", "twin", 15).above  # 30%: lower ≈ 19% > 15%


def test_decide() -> None:
    control = [reading(t, "real", 40) for t in closed_book.CONTROL_TEMPLATES]
    clean = [reading(t, "twin", 3) for t in ("S0-A1", "S1-A1", "S2-A1")]
    assert closed_book.decide(control + clean)["verdict"] == "pass"
    leak = clean + [reading("S2-B1", "twin", 30)]
    out = closed_book.decide(control + leak)
    assert out["verdict"] == "fail" and out["failing"] == ["S2-B1"]
    weak = [reading(t, "real", 5) for t in closed_book.CONTROL_TEMPLATES[:2]] + \
        control[2:]
    assert closed_book.decide(weak + clean)["verdict"].startswith("not evaluated")
