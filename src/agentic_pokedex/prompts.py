"""Prompts live in ``prompts/`` and are loaded by name; their hash is logged.

A prompt is a Markdown file whose whole content, stripped, is the prompt text.
The SHA-256 of that text goes into every run's manifest, so a result can always
be traced to the exact wording that produced it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from agentic_pokedex.config import REPO_ROOT

PROMPTS_DIR = REPO_ROOT / "prompts"


@dataclass(frozen=True)
class Prompt:
    """A loaded prompt and the hash of its text."""

    name: str
    text: str
    sha256: str


def load_prompt(name: str, directory: Path = PROMPTS_DIR) -> Prompt:
    """Load ``{directory}/{name}.md``.

    Args:
        name: Prompt name, without extension.
        directory: Where prompts live.

    Returns:
        The prompt, with the SHA-256 of its stripped text.
    """
    text = (directory / f"{name}.md").read_text(encoding="utf-8").strip()
    return Prompt(name, text, hashlib.sha256(text.encode("utf-8")).hexdigest())
