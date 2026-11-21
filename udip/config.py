"""Shared settings: loads the one .env every worktree reads (UDIP_ENV_FILE) and exposes repo/data paths.

Owned by lane A after T00. Imported by udip/__init__.py, so any `import udip.*` has the environment loaded.
Values already in os.environ win over the file (a shell export overrides .env).
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / ".claude" / "skills"
_loaded: Path | None = None


def env_file() -> Path:
    return Path(os.environ.get("UDIP_ENV_FILE") or REPO / ".env")


def load_env(path: Path | None = None) -> Path | None:
    """Read KEY=VALUE lines (no interpolation). Returns the file read, or None if it does not exist."""
    global _loaded
    p = Path(path) if path else env_file()
    if not p.is_file():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
    _loaded = p
    return p


def data_dir() -> Path:
    d = Path(os.environ.get("UDIP_DATA_DIR") or REPO / "var")
    d.mkdir(parents=True, exist_ok=True)
    return d


def llm_cache_dir() -> Path:
    d = Path(os.environ.get("UDIP_LLM_CACHE_DIR") or data_dir() / "llm_cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def llm_usage_file() -> Path:
    return data_dir() / "llm_usage.json"


def today() -> date:
    """Working date of the app. UDIP_TODAY=RRRR-MM-DD fixes it (demo, tests); default: the system date."""
    v = os.environ.get("UDIP_TODAY", "").strip()
    return date.fromisoformat(v) if v else date.today()
