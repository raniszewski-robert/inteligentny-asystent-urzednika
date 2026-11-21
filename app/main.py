"""Asystent UDIP – FastAPI app. Run: uvicorn app.main:app --port 8102

Screens live in app/routes/*.py; every module there that defines `router` is included automatically
(routes and templates: docs/plan/CONTRACTS.md §5).
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from urllib.parse import urlparse

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import routes
from .common import APP_DIR, CLERK_COOKIE, clerks, render

log = logging.getLogger("udip.app")

app = FastAPI(title="Asystent UDIP", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


def include_routers(application: FastAPI) -> list[str]:
    loaded = []
    for m in sorted(pkgutil.iter_modules(routes.__path__), key=lambda m: m.name):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{routes.__name__}.{m.name}")
        r = getattr(mod, "router", None)
        if r is not None:
            application.include_router(r)
            loaded.append(m.name)
    return loaded


ROUTERS = include_routers(app)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/kalendarz", status_code=303)


def _back(request: Request, fallback: str = "/kalendarz") -> str:
    ref = request.headers.get("referer", "")
    p = urlparse(ref)
    if ref and p.netloc == request.url.netloc:  # only same-site redirects
        return p.path + (f"?{p.query}" if p.query else "")
    return fallback


@app.post("/urzednik", include_in_schema=False)
def set_clerk(request: Request, urzednik: str = Form(...)):
    resp = RedirectResponse(_back(request), status_code=303)
    if urzednik in clerks():
        resp.set_cookie(CLERK_COOKIE, urzednik, max_age=60 * 60 * 24 * 365, samesite="lax")
    return resp


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return render(request, "blad.html", status_code=404, title="Nie znaleziono",
                      message="Nie ma takiej strony albo sprawy. Wróć do kalendarza.")
    return render(request, "blad.html", status_code=exc.status_code, title="Błąd",
                  message=str(exc.detail or "Nie udało się wykonać operacji."))
