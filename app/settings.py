"""App settings kept under UDIP_DATA_DIR (not in .env): the clerk's choice of language model.

Default = UDIP_PROVIDER from .env (empty → auto in udip.llm.provider_for). The *effective* provider is what
udip.llm.provider_for() returns for that choice: "rules" whenever the model cannot be used (no key, budget spent).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from udip import config, llm

CHOICES = [  # (value, label)
    ("rules", "Tylko reguły (bez modelu językowego)"),
    ("openai_compat", "Model lokalny – Bielik (Ollama, offline)"),
]


def _file() -> Path:
    return config.data_dir() / "settings.json"


def _read() -> dict:
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _local_only(value: str) -> str:
    value = value.strip()
    if value == "openai_compat":
        return "openai_compat:" + (os.environ.get("LLM_MODEL") or "local")
    if value == "rules" or value.startswith("openai_compat:"):
        return value
    return "rules"


def provider_choice() -> str:
    """Stored choice, else UDIP_PROVIDER; only local modes (rules or openai_compat:*) are permitted."""
    raw = str(_read().get("provider") or os.environ.get("UDIP_PROVIDER", "")).strip()
    if not raw:
        return "rules"
    return _local_only(raw)


def set_provider(value: str) -> str:
    value = _local_only(value)
    data = _read() | {"provider": value}
    _file().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return value


def provider_arg() -> str | None:
    """What to pass as provider= to udip.analyze / detect / make_draft."""
    return provider_choice()


def effective() -> str:
    p = provider_arg()
    if p and p.startswith("openai_compat:") and not llm.available(p):
        return "rules"
    return llm.provider_for(p)


def llm_on() -> bool:
    return effective() != "rules"
