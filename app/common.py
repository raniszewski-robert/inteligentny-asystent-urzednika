"""Shared helpers for every screen router: templates, render(), today, the clerk cookie, date filters.

Lane B2 screens use the same helpers: `from app.common import render, today, clerk`.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from urllib.parse import quote

from fastapi import Request
from fastapi.templating import Jinja2Templates

import udip  # noqa: F401  (loads UDIP_ENV_FILE)

APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

CLERK_COOKIE = "urzednik"
DEFAULT_CLERKS = ["Pracownik 1", "Pracownik 2", "Pracownik 3"]

NAV = [  # (path, label) – every top-level screen in CONTRACTS §5
    ("/biurko", "Biurko"),
    ("/wniosek/nowy", "Nowy wniosek"),
    ("/archiwum", "Archiwum"),
    ("/anonimizacja", "Anonimizacja"),
]

MONTHS = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
          "października", "listopada", "grudnia"]


def today() -> date:
    """Working date of the app. UDIP_TODAY=RRRR-MM-DD fixes it (demo, tests); default: the system date."""
    v = os.environ.get("UDIP_TODAY", "").strip()
    return date.fromisoformat(v) if v else date.today()


def clerks() -> list[str]:
    v = os.environ.get("UDIP_CLERKS", "").strip()
    return [c.strip() for c in v.split(",") if c.strip()] if v else list(DEFAULT_CLERKS)


def clerk(request: Request) -> str:
    """Initials of the clerk chosen in the header dropdown (cookie), default the first one."""
    c = request.cookies.get(CLERK_COOKIE, "")
    return c if c else clerks()[0]


def dmy(value) -> str:
    """2026-11-22 → 22.11.2026; empty stays empty."""
    if not value:
        return ""
    s = str(value)[:10]
    try:
        d = date.fromisoformat(s)
    except ValueError:
        return str(value)
    return d.strftime("%d.%m.%Y")


def pl_long(value) -> str:
    """2026-11-22 → 22 listopada 2026 r."""
    if not value:
        return ""
    d = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    return f"{d.day} {MONTHS[d.month - 1]} {d.year} r."


templates.env.filters["dmy"] = dmy
templates.env.filters["pl_long"] = pl_long
templates.env.filters["urlq"] = lambda s: quote(str(s), safe="")


def render(request: Request, name: str, status_code: int = 200, **ctx):
    """TemplateResponse with the layout context every page needs (nav, clerk, today)."""
    path = request.url.path
    base = {
        "nav": NAV,
        "active": "/biurko" if path.startswith("/kalendarz") else next((p for p, _ in NAV if path == p or path.startswith(p + "/")), ""),
        "clerk": clerk(request),
        "clerks": clerks(),
        "today": today(),
    }
    base.update(ctx)
    return templates.TemplateResponse(request, name, base, status_code=status_code)


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"
