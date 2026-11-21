# T09 – Windows setup on D: + checkpoint 1

**Lane:** D – delivery · **Status:** done · **Estimate:** 45 min · **Blocked by:** T00

**Owns:** `setup.ps1`, `run.ps1`, `run.sh`, `docs/INSTALL_WINDOWS.md`

## Goal

You can run it on your laptop without touching C:.

## Scope

- `setup.ps1`: Python ≥ 3.11 and Git check, venv at `UDIP_VENV`, `PIP_CACHE_DIR`/`TEMP`/`UDIP_DATA_DIR` on D:, install, seed; optional Ollama hint with `OLLAMA_MODELS` on D:.
- `run.ps1`: uvicorn `app.main:app` on 127.0.0.1:8000 + browser; `TESSERACT_CMD` from `.env`.
- Start against a stub app; finish when T03/T02 are on `main`.

## Acceptance criteria

- [ ] Fresh clone on D: → setup → run shows Kalendarz.
- [ ] Nothing new on C: except Python.

> Checkpoint 1 after this ticket and T05 are merged
