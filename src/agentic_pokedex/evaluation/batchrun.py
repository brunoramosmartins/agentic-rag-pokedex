"""A run made of Batch API rounds, kept in one directory.

``runs/<run>/`` holds the manifest, the state, one request file per round
(``requests-r<n>.jsonl``), the batches submitted (``batches.json``) and every
output line fetched (``outputs.jsonl``), so a run can be resumed and audited.
A question's request is re-sent at most ``MAX_TRIES`` times after an API
failure, on the same id, never re-drawn (E-001).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentic_pokedex.llm.batch import (
    BatchResult,
    chat_request,
    fetch,
    parse_output_line,
    read_jsonl,
    submit,
    write_jsonl,
)

MODEL = "gpt-5-mini"
REASONING_EFFORT = "low"
MAX_COMPLETION_TOKENS = 4_000
"""Headroom for reasoning (PI-014): E-003 hit a 1,000-token cap 28 times in 100."""

REASONING = {"central": 600, "pessimistic": 1_200}
"""Reasoning tokens per call for the estimates: E-003's twin medians were
512–576 at low effort (PI-014); the pessimistic case doubles them."""

VISIBLE_OUTPUT = 40
"""Visible output per call: the JSON answer."""

MAX_TRIES = 3
ENDED = ("completed", "failed", "expired", "cancelled")


def custom_id(
    experiment: str, arm: str, question: str, round_: int, attempt: int
) -> str:
    """``e004.A1.q-1a2b3c4d5e.r0.t0``: unique per request."""
    return f"{experiment}.{arm}.{question}.r{round_}.t{attempt}"


def parse_custom_id(value: str) -> tuple[str, str, str, int, int]:
    """Back from ``custom_id``."""
    experiment, arm, question, r, t = value.split(".")
    return experiment, arm, question, int(r[1:]), int(t[1:])


@dataclass
class RunDir:
    """The files of one run."""

    path: Path

    def __post_init__(self) -> None:
        self.path = Path(self.path)

    # --- State ------------------------------------------------------------------

    def load(self, name: str) -> Any:
        """A JSON file of the run."""
        return json.loads((self.path / name).read_text(encoding="utf-8"))

    def save(self, name: str, data: Any) -> None:
        """Write a JSON file of the run."""
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / name).write_text(
            json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # --- Rounds -----------------------------------------------------------------

    def rounds(self) -> list[Path]:
        """Request files, in round order."""
        return sorted(self.path.glob("requests-r*.jsonl"),
                      key=lambda p: int(p.stem.split("-r")[1]))

    def next_round(self) -> int:
        """Index of the next request file."""
        return len(self.rounds())

    def write_round(self, rows: Iterable[Mapping[str, Any]]) -> Path | None:
        """Write the next request file (nothing when ``rows`` is empty)."""
        rows = list(rows)
        if not rows:
            return None
        path = self.path / f"requests-r{self.next_round()}.jsonl"
        write_jsonl(path, rows)
        return path

    def batches(self) -> list[dict[str, Any]]:
        """Batches submitted so far."""
        path = self.path / "batches.json"
        return self.load("batches.json") if path.is_file() else []

    def unsent(self) -> list[Path]:
        """Request files no batch was created for."""
        sent = {b["file"] for b in self.batches()}
        return [p for p in self.rounds() if p.name not in sent]

    def submit_unsent(self, client: Any, experiment: str) -> list[str]:
        """Submit every request file not yet sent; return the batch ids."""
        batches, ids = self.batches(), []
        for path in self.unsent():
            batch_id = submit(client, path, metadata={"experiment": experiment,
                                                      "file": path.name})
            batches.append({"id": batch_id, "file": path.name, "collected": False,
                            "submitted_at": datetime.now(UTC).isoformat()})
            ids.append(batch_id)
        self.save("batches.json", batches)
        return ids

    def collect(self, client: Any) -> tuple[list[BatchResult], list[str]]:
        """Fetch every ended, uncollected batch; return its results and the
        batches still running. Raw output lines are appended to
        ``outputs.jsonl``."""
        batches = self.batches()
        results: list[BatchResult] = []
        running: list[str] = []
        for b in batches:
            if b.get("collected"):
                continue
            status, rows = fetch(client, b["id"])
            if status not in ENDED:
                running.append(f"{b['id']} ({status})")
                continue
            with (self.path / "outputs.jsonl").open("a", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            results += [parse_output_line(row) for row in rows]
            sent = {r["custom_id"] for r in read_jsonl(self.path / b["file"])}
            got = {r.custom_id for r in results}
            # A request with no output line failed silently: report it as such.
            results += [BatchResult(c, None, None, None, f"no output ({status})")
                        for c in sorted(sent - got)]
            b["collected"] = True
            b["status"] = status
        self.save("batches.json", batches)
        return results, running


# --- One-call requests --------------------------------------------------------


def single_request(experiment: str, entry: Mapping[str, Any], round_: int) -> dict:
    """The Batch line of a one-call entry (``arm``, ``question``, ``attempt``,
    ``messages``)."""
    return chat_request(
        custom_id(experiment, entry["arm"], entry["question"], round_,
                  entry["attempt"]),
        model=MODEL, messages=entry["messages"],
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        reasoning_effort=REASONING_EFFORT,
    )


def apply_single(
    experiment: str, entry: dict[str, Any], result: BatchResult, round_: int
) -> dict[str, Any] | None:
    """Fold one result into a one-call entry; return a re-send line or ``None``.

    Success records the completion and usage. An API failure is re-sent on the
    same question up to ``MAX_TRIES`` times, then the entry is ``failed``
    (scored C = λ, never excluded).
    """
    if entry["status"] != "pending":
        return None
    if result.error is not None:
        entry["attempt"] += 1
        if entry["attempt"] > MAX_TRIES:
            entry["status"] = "failed"
            entry["error"] = result.error
            return None
        return single_request(experiment, entry, round_)
    entry.update(status="done", completion=result.content,
                 finish_reason=result.finish_reason,
                 usage=asdict(result.usage) if result.usage else None)
    return None
