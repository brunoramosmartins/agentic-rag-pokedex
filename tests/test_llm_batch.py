"""Batch API helpers: request lines and output parsing (no network)."""

from __future__ import annotations

from pathlib import Path

from agentic_pokedex.llm.batch import (
    CHAT_ENDPOINT,
    chat_request,
    parse_output_line,
    read_jsonl,
    write_jsonl,
)


def test_chat_request_line() -> None:
    line = chat_request(
        "e003-twin-1",
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_completion_tokens=100,
        reasoning_effort="low",
        response_format={"type": "json_object"},
    )
    assert line["custom_id"] == "e003-twin-1"
    assert (line["method"], line["url"]) == ("POST", CHAT_ENDPOINT)
    assert line["body"] == {
        "model": "gpt-5-mini",
        "messages": [{"role": "user", "content": "hi"}],
        "max_completion_tokens": 100,
        "reasoning_effort": "low",
        "response_format": {"type": "json_object"},
    }


def test_optional_fields_are_left_out() -> None:
    body = chat_request("x", model="m", messages=[], max_completion_tokens=5)["body"]
    assert "reasoning_effort" not in body and "response_format" not in body


def test_jsonl_round_trip(tmp_path: Path) -> None:
    rows = [{"a": 1}, {"b": "é"}]
    assert write_jsonl(tmp_path / "x.jsonl", rows) == 2
    assert read_jsonl(tmp_path / "x.jsonl") == rows


def output(finish: str = "stop", status: int = 200) -> dict:
    return {
        "custom_id": "e003-twin-1",
        "response": {
            "status_code": status,
            "body": {
                "choices": [
                    {"message": {"content": '{"guess": "x"}'}, "finish_reason": finish}
                ],
                "usage": {
                    "prompt_tokens": 500,
                    "completion_tokens": 120,
                    "completion_tokens_details": {"reasoning_tokens": 100},
                },
            },
        },
        "error": None,
    }


def test_parse_a_successful_line() -> None:
    result = parse_output_line(output())
    assert result.ok
    assert result.content == '{"guess": "x"}'
    assert (result.usage.input_tokens, result.usage.reasoning_tokens) == (500, 100)


def test_a_truncated_answer_is_not_ok() -> None:
    result = parse_output_line(output(finish="length"))
    assert not result.ok and result.error is None


def test_an_http_error_is_not_ok() -> None:
    row = output(status=500)
    row["response"]["body"] = {"error": {"message": "server"}}
    result = parse_output_line(row)
    assert not result.ok and "server" in result.error


def test_an_error_line_is_not_ok() -> None:
    row = {"custom_id": "e003-twin-1", "response": None,
           "error": {"code": "batch_expired"}}
    result = parse_output_line(row)
    assert not result.ok and "batch_expired" in result.error
