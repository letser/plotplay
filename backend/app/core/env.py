"""Shared runtime paths and environment loading."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Resolve important directories once so other modules can import them.
BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent

ENV_FILE_PATH = BACKEND_DIR / ".env"
DEFAULT_GAMES_PATH = (REPO_ROOT / "games").resolve()

# Populate os.environ for native runs while remaining a no-op when the file is missing.
if ENV_FILE_PATH.exists():
    load_dotenv(ENV_FILE_PATH, override=False)
