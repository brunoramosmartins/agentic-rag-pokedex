"""The one-call arms and the agent loop (no network)."""

from __future__ import annotations

import json

import pytest

from agentic_pokedex.arms import agent
from agentic_pokedex.arms.single import (
    Evidence,
    closed_book_text,
    evidence_of,
    evidence_text,
    fill,
    fixed_pipeline,
    single_shot,
    user_messages,
)
from agentic_pokedex.arms.typed_expansion import World
from agentic_pokedex.llm.batch import BatchResult
from agentic_pokedex.observability.tokens import Usage
from agentic_pokedex.prompts import load_prompt
from agentic_pokedex.tools.open_page import Pages
from agentic_pokedex.world.index import HybridIndex, Unit


def chars(text: str) -> int:
    """A test token counter: one token per four characters."""
    return len(text) // 4


UNITS = [
    Unit("s/kedros/profile", "Kedros", "Profile",
         "Species: Kedros · Section: Profile\nHidden ability: [[Blazor]]\n"
         "Evolves into: [[Tarnlet]]"),
    Unit("s/tarnlet/profile", "Tarnlet", "Profile",
         "Species: Tarnlet · Section: Profile\nHidden ability: [[Blazor]]\n"
         "Evolves into: —"),
    Unit("a/blazor/holders", "Blazor", "Holders",
         "Ability: Blazor · Section: Holders\n[[Kedros]] (hidden)\n[[Tarnlet]]"),
]


@pytest.fixture()
def world() -> World:
    return World(HybridIndex(UNITS), Pages(UNITS), {u.id: u.text for u in UNITS},
                 {"s/kedros/profile": "Profile", "s/tarnlet/profile": "Profile",
                  "a/blazor/holders": "Holders"},
                 {"Kedros": "species", "Tarnlet": "species", "Blazor": "ability"})


# --- Prompts and one-call arms --------------------------------------------------


def test_the_cost_and_format_paragraphs_are_shared_verbatim() -> None:
    prompts = [load_prompt(n).text for n in ("answer_closed_book_v0",
                                             "answer_with_evidence_v0", "agent_v0")]
    cost = next(line for line in prompts[0].splitlines() if line.startswith("Costs:"))
    fmt = next(line for line in prompts[0].splitlines()
               if line.startswith("Reply with JSON only"))
    assert all(cost in p and fmt in p for p in prompts)
    assert all("{question}" in p for p in prompts)


def test_fill_leaves_json_braces_alone() -> None:
    text = fill('Q: {question} {"answer": null}', question="Why?")
    assert text == 'Q: Why? {"answer": null}'


def test_closed_book_and_evidence_messages() -> None:
    assert closed_book_text("Q: {question}", "Why?") == "Q: Why?"
    ev = evidence_of(["s/kedros/profile"], 20, {u.id: u.text for u in UNITS})
    text = evidence_text("Q: {question}\nE:\n{evidence}", "Why?", ev)
    assert text.endswith(UNITS[0].text)
    assert user_messages("hi") == [{"role": "user", "content": "hi"}]


def test_retrieval_arms(world: World) -> None:
    a1 = single_shot(world, "Kedros evolves", chars, k=1)
    assert a1.units == ("s/kedros/profile",) and a1.tokens > 0
    a2 = fixed_pipeline(world, "Kedros evolves", chars)
    assert set(a1.units) <= set(a2.units) and a2.tokens >= a1.tokens
    assert isinstance(a2, Evidence)


# --- Agent loop ---------------------------------------------------------------


def tool_call(name: str, args: dict | str, call_id: str = "c1") -> dict:
    arguments = args if isinstance(args, str) else json.dumps(args)
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": arguments}}


def turn(*calls: dict, content: str | None = None) -> BatchResult:
    return BatchResult("x", content, "tool_calls" if calls else "stop",
                       Usage(100, 0, 50, 40), None, tuple(calls))


def test_a_tool_call_runs_and_its_units_are_logged(world: World) -> None:
    st = agent.start("q-1", "Which?", "Q: {question}")
    msgs, offer = agent.turn_messages(st, "final")
    assert offer and msgs[0]["content"] == "Q: Which?"
    agent.advance(st, turn(tool_call("open_page", {"title": "Kedros"})), world, chars)
    assert st.calls == 1 and st.seen() == [["s/kedros/profile"]]
    assert st.messages[-1]["role"] == "tool"
    assert st.messages[-1]["content"] == UNITS[0].text
    assert st.messages[-2]["tool_calls"][0]["id"] == "c1"
    assert not st.done and st.turns[0]["usage"]["reasoning_tokens"] == 40


def test_a_reply_without_a_tool_ends_the_run(world: World) -> None:
    st = agent.start("q-1", "Which?", "Q: {question}")
    agent.advance(st, turn(content='{"answer": "Blazor", "abstain": false}'), world,
                  chars)
    assert st.done and st.final == '{"answer": "Blazor", "abstain": false}'
    assert agent.proposals(st) == ["answer"]


def test_t_max_then_a_last_turn_without_tools(world: World) -> None:
    st = agent.start("q-1", "Which?", "Q: {question}")
    for i in range(agent.T_MAX):
        agent.advance(st, turn(tool_call("search", {"query": "Kedros"}, f"c{i}")),
                      world, chars, budget=10**6)
    assert st.calls == agent.T_MAX and st.last_turn()
    msgs, offer = agent.turn_messages(st, "You have no tool calls left.")
    assert not offer and msgs[-1] == {"role": "user",
                                      "content": "You have no tool calls left."}
    agent.turn_messages(st, "You have no tool calls left.")
    assert sum(m["content"] == "You have no tool calls left." for m in st.messages) == 1
    agent.advance(st, turn(content='{"answer": null, "abstain": true}'), world, chars)
    assert st.done


def test_a_result_past_b_is_withheld_and_ends_the_tools(world: World) -> None:
    st = agent.start("q-1", "Which?", "Q: {question}")
    agent.advance(st, turn(tool_call("open_page", {"title": "Kedros"})), world, chars,
                  budget=5)
    assert st.budget_spent and st.seen() == [[]] and st.tokens == 0
    assert st.messages[-1]["content"] == agent.BUDGET_REACHED
    assert st.last_turn()


def test_invalid_calls_count_as_steps(world: World) -> None:
    st = agent.start("q-1", "Which?", "Q: {question}")
    agent.advance(st, turn(tool_call("open_page", "{not json")), world, chars)
    agent.advance(st, turn(tool_call("delete_page", {"title": "Kedros"}, "c2")),
                  world, chars)
    assert st.calls == 2 and all(m == [] for m in st.seen())
    assert st.messages[-1]["content"] == agent.INVALID_CALL


def test_search_and_open_page_arguments(world: World) -> None:
    st = agent.start("q-1", "Which?", "Q: {question}")
    agent.advance(st, turn(tool_call("search", {"query": "Kedros evolves", "k": 1})),
                  world, chars)
    agent.advance(st, turn(tool_call("open_page", {"title": "Blazor",
                                                   "section": "Holders",
                                                   "offset": 0}, "c2")),
                  world, chars)
    assert st.seen() == [["s/kedros/profile"], ["a/blazor/holders"]]
    assert agent.proposals(st) == ["search", "open_page"]


def test_api_failures_end_the_run_after_the_retries() -> None:
    st = agent.start("q-1", "Which?", "Q: {question}")
    for _ in range(3):
        agent.fail(st, 3)
    assert not st.done
    agent.fail(st, 3)
    assert st.done and st.failed and st.final is None


def test_state_round_trip(world: World) -> None:
    st = agent.start("q-1", "Which?", "Q: {question}")
    agent.advance(st, turn(tool_call("open_page", {"title": "Kedros"})), world, chars)
    back = agent.AgentState.from_dict(json.loads(json.dumps(st.to_dict())))
    assert back == st


def test_tools_are_the_contract() -> None:
    names = [t["function"]["name"] for t in agent.TOOLS]
    assert names == ["search", "open_page"]
    k = agent.TOOLS[0]["function"]["parameters"]["properties"]["k"]
    assert k["maximum"] == 5
