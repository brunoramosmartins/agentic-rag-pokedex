"""Local configuration: environment variables, with `.env` as the fallback.

Variables already set in the environment always win; `.env` (gitignored, at
the repository root) only fills in what is missing. `docker compose` reads the
same file, so Neo4j credentials and the API key live in one place.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


def load_env(path: Path = DEFAULT_ENV_FILE) -> bool:
    """Load `.env` into the environment without overriding existing variables.

    Args:
        path: The env file to read.

    Returns:
        True if the file existed and was read.
    """
    if not path.is_file():
        return False
    return load_dotenv(path, override=False)
