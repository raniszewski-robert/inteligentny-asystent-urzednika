"""Model językowy: domyślnie same reguły. Lokalny Bielik (Ollama, offline) włącza się tylko wpisem w .env.

Nie ma wyboru w interfejsie. Konfiguracja w .env:
- UDIP_PROVIDER=openai_compat:bielik – reguły + Bielik; wyniki modelu przechodzą przez te same kontrole co reguły,
  a gdy serwer modelu nie odpowiada, aplikacja po cichu zostaje przy regułach;
- LLM_BASE_URL (domyślnie http://localhost:11434/v1, Ollama) i LLM_MODEL – gdzie jest Bielik.
Każda inna wartość (albo brak) = same reguły; modeli spoza komputera nie da się włączyć.
"""
from __future__ import annotations

import os
import time
import urllib.request

from udip import llm

DEFAULT_PROVIDER = "rules"
DEFAULT_BASE_URL = "http://localhost:11434/v1"
PING_TTL = 30.0   # s: jak długo pamiętamy, czy serwer modelu odpowiada
PING_TIMEOUT = 0.8
_ping: dict = {"base": None, "at": 0.0, "up": False}


def provider_choice() -> str:
    """Same reguły, chyba że .env wskazuje model lokalny (UDIP_PROVIDER=openai_compat:<nazwa>)."""
    raw = os.environ.get("UDIP_PROVIDER", "").strip()
    return raw if raw.startswith("openai_compat:") else DEFAULT_PROVIDER


def base_url() -> str:
    return (os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def _server_up() -> bool:
    """Czy serwer modelu odpowiada (GET /models), z pamięcią na PING_TTL sekund."""
    if llm.TRANSPORT is not None:  # testy podstawiają własny transport
        return True
    base, now = base_url(), time.monotonic()
    if _ping["base"] == base and now - _ping["at"] < PING_TTL:
        return _ping["up"]
    try:
        with urllib.request.urlopen(base + "/models", timeout=PING_TIMEOUT) as r:  # noqa: S310 – adres z .env, lokalny
            up = 200 <= r.status < 300
    except Exception:  # noqa: BLE001 – brak serwera = reguły
        up = False
    _ping.update(base=base, at=now, up=up)
    return up


def effective() -> str:
    """Dostawca na to wywołanie: Bielik, gdy odpowiada, inaczej reguły."""
    p = provider_choice()
    if p == "rules" or not _server_up():
        return "rules"
    os.environ.setdefault("LLM_BASE_URL", base_url())  # udip.llm uznaje model za dostępny, gdy adres jest ustawiony
    return llm.provider_for(p)


def provider_arg() -> str | None:
    """Co przekazać jako provider= do udip.analyze / detect / make_draft."""
    return effective()


def llm_on() -> bool:
    return effective() != "rules"
