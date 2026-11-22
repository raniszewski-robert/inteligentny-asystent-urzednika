"""Zadania modelu w tle. Strona odpowiada od razu wynikiem reguł, a Bielik dokłada swoje, gdy skończy.

Jeden wątek roboczy (lokalny model i tak liczy po kolei). Zadanie ma klucz: drugie zlecenie z tym samym kluczem,
gdy pierwsze jeszcze trwa, dostaje to samo zadanie. Stan jest w pamięci procesu – po restarcie aplikacji
zadania znikają, a strony wracają do samych reguł. UDIP_JOBS_SYNC=1 wykonuje zadania od razu (testy).
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

log = logging.getLogger("udip.jobs")

_EXEC = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bielik")
_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}
_KEYS: dict[str, str] = {}
KEEP = 200  # ile zakończonych zadań pamiętamy


def _sync() -> bool:
    return os.environ.get("UDIP_JOBS_SYNC", "").strip() in ("1", "true", "tak")


def _set(jid: str, **kw) -> None:
    with _LOCK:
        if jid in _JOBS:
            _JOBS[jid].update(kw)


def submit(key: str, kind: str, fn: Callable[..., Any], *args, **kwargs) -> str:
    """Zleca fn(*args, **kwargs); zwraca id zadania. kind mówi stronie, jak pokazać wynik."""
    with _LOCK:
        jid = _KEYS.get(key)
        if jid and _JOBS.get(jid, {}).get("status") == "running":
            return jid
        jid = uuid.uuid4().hex[:12]
        _JOBS[jid] = {"id": jid, "key": key, "kind": kind, "status": "running", "result": None, "error": "",
                      "started": time.time(), "finished": None}
        _KEYS[key] = jid
        done = [j for j in _JOBS.values() if j["status"] != "running"]
        for old in sorted(done, key=lambda j: j["started"])[:max(0, len(done) - KEEP)]:
            _JOBS.pop(old["id"], None)

    def run() -> None:
        try:
            res = fn(*args, **kwargs)
            _set(jid, status="done", result=res, finished=time.time())
        except Exception as e:  # noqa: BLE001 – błąd modelu nigdy nie psuje strony: zostają reguły
            log.exception("zadanie %s (%s) nie powiodło się", jid, key)
            _set(jid, status="error", error=f"{type(e).__name__}: {e}"[:300], finished=time.time())

    if _sync():
        run()
    else:
        _EXEC.submit(run)
    return jid


def get(jid: str | None) -> dict | None:
    if not jid:
        return None
    with _LOCK:
        j = _JOBS.get(jid)
        return dict(j) if j else None


def by_key(key: str) -> dict | None:
    with _LOCK:
        jid = _KEYS.get(key)
        j = _JOBS.get(jid) if jid else None
        return dict(j) if j else None


def running(key: str) -> dict | None:
    j = by_key(key)
    return j if j and j["status"] == "running" else None


def elapsed(job: dict) -> int:
    return int((job.get("finished") or time.time()) - job["started"])
