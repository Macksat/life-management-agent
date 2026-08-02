"""Helpers for loading OpenAI-related environment from the repository .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal environments
    load_dotenv = None

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv_fallback(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            import os

            os.environ.setdefault(key, value)


@lru_cache(maxsize=1)
def load_repo_dotenv() -> None:
    """Load the repository root .env once if it exists."""

    dotenv_path = REPO_ROOT / ".env"
    if load_dotenv is not None:
        load_dotenv(dotenv_path=dotenv_path, override=False)
        return
    _load_dotenv_fallback(dotenv_path)
