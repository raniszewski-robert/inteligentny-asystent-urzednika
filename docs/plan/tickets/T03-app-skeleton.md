# T03 – FastAPI + Jinja2 + htmx skeleton and visual base

**Lane:** B1 – UI: case flow · **Status:** done · **Estimate:** 45 min · **Blocked by:** T00

**Owns:** `app/main.py`, `app/templates/base.html`, `app/static/app.css`, `app/static/htmx.min.js`

## Goal

A runnable app with navigation for every screen and a plain official look.

## Scope

- Header as text „Urząd Miasta Bydgoszczy · Biuro Komunikacji Społecznej”; nav to every route in CONTRACTS §5; clerk dropdown (cookie); **mode pill** slot showing `udip.llm.mode()` (Offline – reguły / Offline – Bielik / Cloud demo – Claude).
- Render from `tests/fixtures/` until T01/T02 are on `main`.
- unslop-ui pass with `--surface`.

## Acceptance criteria

- [ ] `uvicorn app.main:app` serves `/` with layout, no external requests.
- [ ] unslop-ui counts recorded.
