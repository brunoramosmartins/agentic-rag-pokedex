"""The common agent loop (A3 in the pilot; A3, A3′, A4, A4p in Phase 5).

One Batch round per step: the loop's state is plain data, saved between
rounds. Each turn the model either calls one tool (``search`` or
``open_page``; parallel calls are off) or replies with its answer.

- **Step:** one tool call and its observation (E-001). At most ``T_MAX``.
- **B:** the tool results together hold at most ``EVIDENCE_BUDGET`` tokens. A
  result that would pass B is not shown: the call returns ``BUDGET_REACHED``
  and the budget is spent.
- **Last turn:** after ``T_MAX`` calls, or once B is spent, the request offers
  no tool and adds the ``agent_final_v0`` message; the agent answers or
  abstains (E-001: "search is not offered").
- A call the tools cannot run (unknown tool, arguments that do not parse)
  returns ``INVALID_CALL`` and counts as a step.

Every turn logs the full messages sent, the completion and the API usage; every
step logs the call, the units shown and their tokens, which the sufficiency
labeler reads.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from agentic_pokedex.arms.single import fill
from agentic_pokedex.arms.typed_expansion import World
from agentic_pokedex.llm.batch import BatchResult
from agentic_pokedex.tools.contract import MAX_K, TokenCounter, ToolResult
from agentic_pokedex.tools.open_page import open_page
from agentic_pokedex.tools.search import search

AGENT_PROMPT = "agent_v0"
FINAL_PROMPT = "agent_final_v0"
T_MAX = 6
EVIDENCE_BUDGET = 4_000
BUDGET_REACHED = "Evidence budget reached."
INVALID_CALL = "Invalid call."
NO_MORE_CALLS = "No more calls."

TOOLS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "search",
        "description": "The k best-matching page sections for a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "minimum": 1, "maximum": MAX_K},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }},
    {"type": "function", "function": {
        "name": "open_page",
        "description": ("A page by its exact title, from its top; section keeps "
                        "the sections whose header contains that text; offset "
                        "skips that many sections."),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "section": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0},
            },
            "required": ["title"],
            "additionalProperties": False,
        },
    }},
]


@dataclass
class AgentState:
    """One question's run of the loop, saved between Batch rounds.

    Attributes:
        question: Question id.
        messages: Every message sent so far, in order.
        steps: One entry per tool call: call, arguments, units, tokens.
        turns: One entry per model turn: completion, tool calls, usage.
        tokens: Evidence tokens shown.
        budget_spent: A result was withheld because it would pass B.
        final: The final completion text, once the agent has answered.
        done: The run has ended (answer, abstention or failure).
        failures: API failures on the current turn.
        final_asked: The last-turn message has been added.
        failed: The run ended on API failures (scored C = λ, never excluded).
    """

    question: str
    messages: list[dict[str, Any]]
    steps: list[dict[str, Any]] = field(default_factory=list)
    turns: list[dict[str, Any]] = field(default_factory=list)
    tokens: int = 0
    budget_spent: bool = False
    final: str | None = None
    done: bool = False
    failures: int = 0
    final_asked: bool = False
    failed: bool = False

    @property
    def calls(self) -> int:
        """Tool calls made (steps)."""
        return len(self.steps)

    def last_turn(self) -> bool:
        """No tool is offered any more."""
        return self.calls >= T_MAX or self.budget_spent

    def seen(self) -> list[list[str]]:
        """Units shown at each step, in order (for the labeler)."""
        return [list(s["units"]) for s in self.steps]

    def to_dict(self) -> dict[str, Any]:
        """Plain data for the state file."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AgentState:
        """Back from the state file."""
        return cls(**dict(data))


def start(question_id: str, question: str, prompt: str) -> AgentState:
    """A new run: the agent prompt with the question."""
    return AgentState(question_id, [{"role": "user",
                                     "content": fill(prompt, question=question)}])


def turn_messages(state: AgentState, final_prompt: str) -> tuple[list[dict], bool]:
    """Messages of the next request and whether tools are offered.

    On the last turn the final message is added once to the state.
    """
    if state.last_turn():
        if not state.final_asked:
            state.messages.append({"role": "user", "content": final_prompt})
            state.final_asked = True
        return state.messages, False
    return state.messages, True


def run_tool(
    world: World, name: str, arguments: str, counter: TokenCounter
) -> tuple[ToolResult | None, dict[str, Any]]:
    """Run one tool call; ``None`` when the call is invalid."""
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return None, {}
    if not isinstance(args, dict):
        return None, {}
    try:
        if name == "search" and isinstance(args.get("query"), str):
            k = int(args.get("k", MAX_K))
            return search(world.index, args["query"], k, counter=counter), args
        if name == "open_page" and isinstance(args.get("title"), str):
            section = args.get("section")
            section = section if isinstance(section, str) else None
            offset = int(args.get("offset", 0) or 0)
            return open_page(world.pages, args["title"], section, offset,
                             counter=counter), args
    except (TypeError, ValueError):
        return None, args
    return None, args


def advance(
    state: AgentState, result: BatchResult, world: World, counter: TokenCounter,
    budget: int = EVIDENCE_BUDGET,
) -> None:
    """Apply one model turn to the state.

    A tool call runs and its observation is appended; a reply without a tool
    call ends the run. The caller handles API failures (``result.error``)
    before calling this.
    """
    state.turns.append({
        "content": result.content, "tool_calls": list(result.tool_calls),
        "finish_reason": result.finish_reason,
        "usage": asdict(result.usage) if result.usage else None,
    })
    state.failures = 0
    if not result.tool_calls or state.last_turn():
        state.final = result.content
        state.done = True
        return
    state.messages.append({"role": "assistant", "content": result.content,
                           "tool_calls": [dict(c) for c in result.tool_calls]})
    for call in result.tool_calls:
        fn = call.get("function") or {}
        name, arguments = fn.get("name", ""), fn.get("arguments", "")
        if state.last_turn():
            reply, units, tokens = NO_MORE_CALLS, (), 0
        else:
            res, args = run_tool(world, name, arguments, counter)
            if res is None:
                reply, units, tokens = INVALID_CALL, (), counter(INVALID_CALL)
            elif state.tokens + res.tokens > budget:
                reply, units, tokens = BUDGET_REACHED, (), 0
                state.budget_spent = True
            else:
                reply, units, tokens = res.text, res.unit_ids, res.tokens
            state.tokens += tokens
            state.steps.append({"tool": name, "arguments": arguments,
                                "units": list(units), "tokens": tokens})
        state.messages.append({"role": "tool", "tool_call_id": call.get("id", ""),
                               "content": reply})


def fail(state: AgentState, max_failures: int = 3) -> None:
    """Count an API failure on the current turn; end the run after the last."""
    state.failures += 1
    if state.failures > max_failures:
        state.done = True
        state.failed = True
        state.final = None


def proposals(state: AgentState) -> Sequence[str]:
    """What the agent did each turn: ``search``, ``open_page`` or ``answer``."""
    out = []
    for turn in state.turns:
        calls = turn["tool_calls"]
        out.append((calls[0].get("function") or {}).get("name", "invalid")
                   if calls else "answer")
    return out
