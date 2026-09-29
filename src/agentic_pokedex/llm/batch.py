"""The OpenAI Batch API: build requests, submit them, read the results.

Registered runs use the Batch API (ADR-008): a JSONL file of chat requests is
uploaded, processed within 24 hours at half price, and its output file read
back. Request building and output parsing are pure functions, tested without a
network; ``submit`` and ``fetch`` take an OpenAI client (``llm`` extra).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_pokedex.observability.tokens import Usage

CHAT_ENDPOINT = "/v1/chat/completions"
COMPLETION_WINDOW = "24h"


def chat_request(
    custom_id: str,
    *,
    model: str,
    messages: Sequence[Mapping[str, str]],
    max_completion_tokens: int,
    reasoning_effort: str | None = None,
    response_format: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One line of a Batch input file for the Chat Completions endpoint."""
    body: dict[str, Any] = {
        "model": model,
        "messages": [dict(m) for m in messages],
        "max_completion_tokens": max_completion_tokens,
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    if response_format:
        body["response_format"] = dict(response_format)
    return {
        "custom_id": custom_id, "method": "POST", "url": CHAT_ENDPOINT, "body": body
    }


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    """Write rows as JSON lines; return how many were written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSON lines, skipping blank lines."""
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@dataclass(frozen=True)
class BatchResult:
    """One parsed output line.

    Attributes:
        custom_id: The request's id.
        content: The assistant message, when the call succeeded.
        finish_reason: ``stop``, ``length``, … (``length`` means truncated).
        usage: API-reported usage, when present.
        error: A description of the failure, or ``None``.
    """

    custom_id: str
    content: str | None
    finish_reason: str | None
    usage: Usage | None
    error: str | None

    @property
    def ok(self) -> bool:
        """A complete answer came back."""
        return self.error is None and self.content is not None and (
            self.finish_reason == "stop"
        )


def parse_output_line(row: Mapping[str, Any]) -> BatchResult:
    """Parse one line of a Batch output (or error) file."""
    custom_id = row["custom_id"]
    if row.get("error"):
        return BatchResult(custom_id, None, None, None, json.dumps(row["error"]))
    response = row.get("response") or {}
    body = response.get("body") or {}
    usage = Usage.from_api(body["usage"]) if body.get("usage") else None
    if response.get("status_code") != 200:
        detail = body.get("error") or {"status": response.get("status_code")}
        return BatchResult(custom_id, None, None, usage, json.dumps(detail))
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return BatchResult(
        custom_id, message.get("content"), choice.get("finish_reason"), usage, None
    )


def submit(
    client: Any, path: Path, *, metadata: Mapping[str, str] | None = None
) -> str:
    """Upload a Batch input file and create the batch; return its id."""
    with path.open("rb") as handle:
        uploaded = client.files.create(file=handle, purpose="batch")
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint=CHAT_ENDPOINT,
        completion_window=COMPLETION_WINDOW,
        metadata=dict(metadata or {}),
    )
    return batch.id


def fetch(client: Any, batch_id: str) -> tuple[str, list[dict[str, Any]]]:
    """Status of a batch and, once it has ended, every output and error line."""
    batch = client.batches.retrieve(batch_id)
    rows: list[dict[str, Any]] = []
    for file_id in (batch.output_file_id, batch.error_file_id):
        if file_id:
            text = client.files.content(file_id).text
            rows += [json.loads(line) for line in text.splitlines() if line.strip()]
    return batch.status, rows
