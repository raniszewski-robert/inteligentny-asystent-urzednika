"""Data access for the screens: a thin layer over udip.db (CONTRACTS §4) with what the screens need on top
(register rows, demo data, import, next case number). An empty database is seeded on first use with the UMB
archive and the 10 UMB cases in demo mode.
"""
from __future__ import annotations

import re
from contextlib import closing
from dataclasses import fields
from datetime import date

from udip import config, db
from udip.deadlines import deadline_days
from udip.register import STATUSES, Request

UMB = config.REPO / "data-partner" / "umb"

_ready: set[str] = set()


def ensure() -> None:
    """Create the schema and, for a database with no cases and no archive, load the UMB demo data."""
    key = str(db.db_path())
    if key in _ready:
        return
    db.init()
    if not db.list_cases() and not db.archive_records():
        from app.common import today
        db.seed(demo_today=today())
    _ready.add(key)


def reset_backend() -> None:
    """Tests: forget which databases were checked (after changing UDIP_DATA_DIR)."""
    _ready.clear()


def connect():
    ensure()
    return db.connect()


# ---- cases -------------------------------------------------------------------------------------------------

def list_cases(year: int | None = None) -> list[dict]:
    ensure()
    return db.list_cases(year)


def get_case(case_id: int) -> dict | None:
    ensure()
    return db.get_case(case_id)


def case_by_number(number: str) -> dict | None:
    ensure()
    return db.case_by_number(number)


def years() -> list[int]:
    return sorted({int(c["received"][:4]) for c in list_cases() if (c.get("received") or "")[:4].isdigit()}, reverse=True)


def create_case(**f) -> int:
    ensure()
    return db.create_case(**f)


def update_case(case_id: int, **f) -> None:
    db.update_case(case_id, **f)


def set_status(case_id: int, status: str, by: str, note: str | None = None, extension_days: int | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"Nieznany status: {status}")
    db.set_status(case_id, status, by, note)
    if status == "c_kwerenda" and extension_days is not None:
        db.update_case(case_id, extension_days=int(extension_days), extension_until=None)


def history(case_id: int) -> list[dict]:
    return db.history(case_id)


def last_changes() -> dict[int, dict]:
    with closing(db.connect()) as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM status_history ORDER BY id")]
    return {h["case_id"]: h for h in rows}


def to_request(c: dict) -> Request:
    """udip.register.Request for the register rows (extension_until → extension_days counted from the 14-day term)."""
    names = {f.name for f in fields(Request)}
    d = {k: c.get(k) for k in ("number", "received", "extension_days", "answered")}
    d.update(summary=c.get("summary") or "", initials=c.get("initials") or "", status=c.get("status") or "a_brak_dzialan",
             departments=list(c.get("departments") or []), notes="", history=[])
    if d["extension_days"] is None and c.get("extension_until"):
        base = deadline_days(date.fromisoformat(c["received"]))
        d["extension_days"] = max(0, (date.fromisoformat(c["extension_until"]) - base).days)
    return Request(**{k: v for k, v in d.items() if k in names})


def next_number(year: int) -> str:
    """Next BKS.IV.1431.N.YYYY after the highest N of that year in the register."""
    top = 0
    for c in list_cases():
        m = re.match(r"^BKS\.IV\.1431\.(\d+)\.(\d{4})$", c["number"] or "")
        if m and int(m.group(2)) == year:
            top = max(top, int(m.group(1)))
    return f"BKS.IV.1431.{top + 1}.{year}"


# ---- import of the calendar sheet ------------------------------------------------------------------------------

def import_records(recs: list[dict], demo: bool = False, replace: bool = False) -> dict:
    """Create cases from importer.convert()/demo_shift() records. Returns {added, skipped, replaced}."""
    from udip.importer import extension_to_days, fill_departments
    ensure()
    fill_departments(recs, db.archive_records())
    until = {r["number"]: r.get("extension_until") for r in recs}
    extension_to_days(recs)
    added, skipped, replaced = [], [], []
    for r in recs:
        old = db.case_by_number(r["number"])
        if old:
            if not replace:
                skipped.append(r["number"])
                continue
            db.delete_case(old["id"])
            replaced.append(r["number"])
        else:
            added.append(r["number"])
        db.create_case(number=r["number"], received=r["received"], summary=r.get("summary", ""),
                       applicant_label=r.get("applicant_label", ""), initials=r.get("initials", ""),
                       status=r.get("status", "a_brak_dzialan"), extension_days=r.get("extension_days"),
                       extension_until=until.get(r["number"]), answered=r.get("answered"),
                       departments=r.get("departments") or [], is_demo=1 if demo else 0)
    return {"added": added, "skipped": skipped, "replaced": replaced}


def clear_demo() -> int:
    ensure()
    demo = [c for c in db.list_cases() if c.get("is_demo")]
    for c in demo:
        db.delete_case(c["id"])
    return len(demo)


def load_demo(today: date) -> dict:
    """The 10 UMB cases with dates shifted around `today` (is_demo=1); replaces cases with the same numbers."""
    clear_demo()
    r = db.seed(demo_today=today, reset=True)
    return {"added": r["cases_added"], "replaced": r["cases_replaced"], "skipped": r["cases_skipped"]}


# ---- documents, drafts -------------------------------------------------------------------------------------------

def add_document(case_id: int, kind: str, filename: str, text: str, department: str | None = None,
                 quality: float | None = None, path: str | None = None) -> int:
    return db.add_document(case_id, kind, filename, text, department=department, quality=quality, path=path)


def documents(case_id: int, kind: str | None = None) -> list[dict]:
    return db.documents(case_id, kind)


def set_document_department(case_id: int, doc_id: int, department: str | None) -> None:
    with closing(db.connect()) as con, con:
        con.execute("UPDATE documents SET department=? WHERE id=? AND case_id=?", (department, doc_id, case_id))


def drafts(case_id: int) -> list[dict]:
    with closing(db.connect()) as con:
        return [dict(r) for r in con.execute("SELECT id, case_id, version, ltype, created_at FROM drafts WHERE case_id=? ORDER BY version",
                                             (case_id,))]


# ---- archive and laws --------------------------------------------------------------------------------------------

def archive_records() -> list[dict]:
    ensure()
    return db.archive_records()


def add_archive(id: str, date: str, title: str, request_text: str, response_text: str, departments: list[str], source: str) -> None:
    db.add_archive(id, date, title, request_text, response_text, departments, source)


def add_law(title: str, filename: str, text: str) -> int:
    ensure()
    return db.add_law(title, filename, text)


def law_records() -> list[dict]:
    ensure()
    return db.law_records()
