"""SQLite storage (CONTRACTS §4): cases with status history, documents, letter drafts, archive, laws.

Plain sqlite3, one file: $UDIP_DATA_DIR/udip.sqlite (path read on every connect(), so tests can point
UDIP_DATA_DIR at a temp dir). The schema below is the contract; extra helpers after the contract ones are
additive. JSON columns (departments, analysis, spans, report) are stored as JSON text and returned decoded.
Seeding from the UMB data: seed() here, CLI in scripts/seed.py.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path

from . import config
from .register import STATUSES

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, number TEXT UNIQUE, received TEXT, summary TEXT, applicant_label TEXT,
  initials TEXT, status TEXT DEFAULT 'a_brak_dzialan', extension_days INTEGER, extension_until TEXT, answered TEXT,
  departments TEXT DEFAULT '[]', analysis TEXT, is_demo INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS status_history (id INTEGER PRIMARY KEY, case_id INTEGER, from_status TEXT, to_status TEXT, at TEXT, by TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, case_id INTEGER, kind TEXT CHECK(kind IN ('request','dept_answer','letter','law','archive','other')),
  filename TEXT, department TEXT, text TEXT, quality REAL, path TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS drafts (id INTEGER PRIMARY KEY, case_id INTEGER, version INTEGER, ltype TEXT, text TEXT, spans TEXT, report TEXT,
  final_to_send TEXT, final_anonymized TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS archive (id TEXT PRIMARY KEY, date TEXT, title TEXT, request_text TEXT, response_text TEXT, departments TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS laws (id INTEGER PRIMARY KEY, title TEXT, filename TEXT, text TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS department_dispatches (id INTEGER PRIMARY KEY, case_id INTEGER, department TEXT, questions TEXT,
  sub_deadline TEXT, sent_at TEXT, answered_at TEXT);
CREATE TABLE IF NOT EXISTS legal_chunks (id INTEGER PRIMARY KEY, law_title TEXT, ref TEXT, text TEXT, source_file TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS learned_pii_rules (id INTEGER PRIMARY KEY, phrase TEXT, normalized_phrase TEXT, action TEXT CHECK(action IN ('allow','redact')),
  category TEXT, source_case_id INTEGER, created_by TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS routing_feedback (id INTEGER PRIMARY KEY, question_text TEXT, tokens_json TEXT, predicted_dept TEXT, confirmed_dept TEXT,
  case_id INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS security_events (id INTEGER PRIMARY KEY, case_id INTEGER, kind TEXT, detail TEXT, raw TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS ix_history_case ON status_history(case_id);
CREATE INDEX IF NOT EXISTS ix_documents_case ON documents(case_id);
CREATE INDEX IF NOT EXISTS ix_drafts_case ON drafts(case_id);
CREATE INDEX IF NOT EXISTS ix_dispatches_case ON department_dispatches(case_id);
"""
CASE_FIELDS = ("number", "received", "summary", "applicant_label", "initials", "status", "extension_days", "extension_until",
               "answered", "departments", "analysis", "is_demo", "created_at")
DOC_KINDS = ("request", "dept_answer", "letter", "law", "archive", "other")
UMB = config.REPO / "data-partner" / "umb"
SYNTHETIC = [config.REPO / "data-samples" / "syntetyczne" / "archiwum.jsonl",
             config.REPO / "data-samples" / "syntetyczne_umb" / "archiwum.jsonl"]  # drugi: lane C (T14), gdy istnieje


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def db_path() -> Path:
    return config.data_dir() / "udip.sqlite"


def connect() -> sqlite3.Connection:
    """New connection to the shared database (schema ensured). Rows are sqlite3.Row; close it after use."""
    p = db_path()
    con = sqlite3.connect(p, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=10000")
    con.executescript(SCHEMA)
    return con


def init() -> None:
    """Create the tables if missing (idempotent)."""
    with closing(connect()):
        pass


def _q(sql: str, args=()) -> list[dict]:
    with closing(connect()) as con:
        return [dict(r) for r in con.execute(sql, args).fetchall()]


def _x(sql: str, args=()) -> int:
    with closing(connect()) as con, con:
        return con.execute(sql, args).lastrowid


def _dumps(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def _loads(v, default):
    if v is None or v == "":
        return default
    if not isinstance(v, str):
        return v
    try:
        return json.loads(v)
    except ValueError:
        return default


def _as_json(v, default) -> str | None:
    """Accept a Python value or already-encoded JSON text (the UI store passes both)."""
    if v is None:
        return None if default is None else _dumps(default)
    if isinstance(v, str):
        return v
    return _dumps(list(v) if isinstance(v, tuple) else v)


def _case(r: dict) -> dict:
    r["departments"] = _loads(r.get("departments"), [])
    r["analysis"] = _loads(r.get("analysis"), None)
    return r


# ---------------------------------------------------------------- cases


def list_cases(year: int | None = None) -> list[dict]:
    """Cases from the oldest to the newest (by date received, then number); year filters on the date received."""
    sql, args = "SELECT * FROM cases", ()
    if year:
        sql, args = sql + " WHERE substr(received, 1, 4) = ?", (f"{int(year):04d}",)
    return [_case(r) for r in _q(sql + " ORDER BY received, number", args)]


def get_case(id: int) -> dict | None:
    r = _q("SELECT * FROM cases WHERE id = ?", (id,))
    return _case(r[0]) if r else None


def create_case(**f) -> int:
    """Insert a case; keys are cases columns (departments: list or JSON text, analysis: dict or JSON text). Returns its id."""
    bad = set(f) - set(CASE_FIELDS)
    if bad:
        raise TypeError(f"Nieznane pola sprawy: {', '.join(sorted(bad))}")
    if not f.get("number"):
        raise ValueError("Sprawa musi mieć numer")
    f.setdefault("status", "a_brak_dzialan")
    if f["status"] not in STATUSES:
        raise ValueError(f"Nieznany status {f['status']}; dozwolone: {', '.join(STATUSES)}")
    f["departments"] = _as_json(f.get("departments"), [])
    if "analysis" in f:
        f["analysis"] = _as_json(f["analysis"], None)
    f.setdefault("created_at", _now())
    cols = list(f)
    return _x(f"INSERT INTO cases ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", [f[c] for c in cols])


def set_status(id: int, status: str, by: str, note: str | None = None, *, at: str | None = None) -> None:
    """Change the status and record it in status_history. Status e sets `answered` (date of `at`, else config.today())
    when the case has no answer date yet. KeyError: no such case; ValueError: unknown status."""
    if status not in STATUSES:
        raise ValueError(f"Nieznany status {status}; dozwolone: {', '.join(STATUSES)}")
    answered = (at or config.today().isoformat())[:10]
    at = at or _now()
    with closing(connect()) as con, con:
        row = con.execute("SELECT status, answered FROM cases WHERE id = ?", (id,)).fetchone()
        if row is None:
            raise KeyError(id)
        con.execute("INSERT INTO status_history (case_id, from_status, to_status, at, by, note) VALUES (?, ?, ?, ?, ?, ?)",
                    (id, row["status"], status, at, by, note))
        con.execute("UPDATE cases SET status = ? WHERE id = ?", (status, id))
        if status == "e_odpowiedz_wyslana" and not row["answered"]:
            con.execute("UPDATE cases SET answered = ? WHERE id = ?", (answered, id))


def add_document(case_id: int, kind: str, filename: str, text: str, department: str | None = None, quality: float | None = None,
                 path: str | None = None) -> int:
    if kind not in DOC_KINDS:
        raise ValueError(f"Nieznany rodzaj dokumentu {kind}; dozwolone: {', '.join(DOC_KINDS)}")
    return _x("INSERT INTO documents (case_id, kind, filename, department, text, quality, path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (case_id, kind, filename, department, text, quality, None if path is None else str(path), _now()))


def save_draft(case_id: int, ltype: str, text: str, spans: list, report: dict, final_to_send: str | None = None,
               final_anonymized: str | None = None) -> int:
    """New draft version for the case (1, 2, …). spans: dicts or Span objects. Returns the draft id."""
    sp = [asdict(s) if is_dataclass(s) else s for s in (spans or [])]
    with closing(connect()) as con, con:
        v = con.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM drafts WHERE case_id = ?", (case_id,)).fetchone()[0]
        return con.execute("INSERT INTO drafts (case_id, version, ltype, text, spans, report, final_to_send, final_anonymized, created_at)"
                           " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (case_id, v, ltype, text, _dumps(sp), _dumps(report or {}), final_to_send, final_anonymized, _now())).lastrowid


def add_dispatch(case_id: int, department: str, questions: list, sub_deadline: str | date | None, sent_at: str | None = None) -> int:
    """Record that the case's questions went to a department (T24). One row per case and department: sending again
    updates the questions, sub-deadline and sent_at of that row. questions: [{no, text}] or [no, …]. Returns the row id."""
    sent_at = sent_at or _now()
    sub = sub_deadline.isoformat() if isinstance(sub_deadline, date) else sub_deadline
    with closing(connect()) as con, con:
        row = con.execute("SELECT id FROM department_dispatches WHERE case_id = ? AND department = ?", (case_id, department)).fetchone()
        if row:
            con.execute("UPDATE department_dispatches SET questions = ?, sub_deadline = ?, sent_at = ? WHERE id = ?",
                        (_dumps(questions or []), sub, sent_at, row["id"]))
            return row["id"]
        return con.execute("INSERT INTO department_dispatches (case_id, department, questions, sub_deadline, sent_at) VALUES (?, ?, ?, ?, ?)",
                           (case_id, department, _dumps(questions or []), sub, sent_at)).lastrowid


def dispatches(case_id: int) -> list[dict]:
    """Departments the case was sent to, in the order sent; questions decoded."""
    return [dict(r, questions=_loads(r.get("questions"), [])) for r in
            _q("SELECT * FROM department_dispatches WHERE case_id = ? ORDER BY id", (case_id,))]


def set_dispatch_answered(case_id: int, department: str, answered_at: str | None = None) -> None:
    """Mark the department's part as answered (first answer counts; later calls keep the first date)."""
    _x("UPDATE department_dispatches SET answered_at = COALESCE(answered_at, ?) WHERE case_id = ? AND department = ?",
       (answered_at or _now(), case_id, department))


def _arch(r: dict) -> dict:
    v = r.get("departments")
    r["departments"] = _loads(v, [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else [])
    return r


def archive_records() -> list[dict]:
    """Archive cases in the format udip.search.Archive takes (id, date, title, request_text, response_text, departments, source)."""
    return [_arch(r) for r in _q("SELECT * FROM archive ORDER BY date, id")]


def add_archive(id: str, date: str, title: str, request_text: str, response_text: str, departments: list[str], source: str) -> None:
    """Insert or replace an archive case by id."""
    _x("INSERT OR REPLACE INTO archive (id, date, title, request_text, response_text, departments, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
       (id, date, title, request_text or "", response_text or "", _as_json(departments, []), source))


def add_law(title: str, filename: str, text: str) -> int:
    return _x("INSERT INTO laws (title, filename, text, created_at) VALUES (?, ?, ?, ?)", (title, filename, text, _now()))


def law_records() -> list[dict]:
    """Laws in the Archive record format too (id as str, title, request_text = text) plus filename."""
    return [dict(r, id=str(r["id"]), request_text=r["text"], response_text="", departments=[], date=(r["created_at"] or "")[:10])
            for r in _q("SELECT * FROM laws ORDER BY id")]


# ---------------------------------------------------------------- additive helpers (not in CONTRACTS §4)


def log_security_event(case_id: int | None, kind: str, detail: str, raw: str) -> int:
    """One row in security_events (lane E, T26): a scanner finding or a quarantined prompt-injection span."""
    return _x("INSERT INTO security_events (case_id, kind, detail, raw, created_at) VALUES (?, ?, ?, ?, ?)",
              (case_id, kind, detail, raw, _now()))


def security_events(case_id: int | None = None) -> list[dict]:
    if case_id is None:
        return _q("SELECT * FROM security_events ORDER BY id")
    return _q("SELECT * FROM security_events WHERE case_id = ? ORDER BY id", (case_id,))


def case_by_number(number: str) -> dict | None:
    r = _q("SELECT * FROM cases WHERE number = ?", (number,))
    return _case(r[0]) if r else None


def update_case(id: int, **f) -> None:
    """Plain field update (no history: use set_status for the status)."""
    bad = set(f) - (set(CASE_FIELDS) - {"status"})
    if bad:
        raise TypeError(f"Pola niedozwolone w update_case: {', '.join(sorted(bad))}")
    if not f:
        return
    if "departments" in f:
        f["departments"] = _as_json(f["departments"], [])
    if "analysis" in f:
        f["analysis"] = _as_json(f["analysis"], None)
    _x(f"UPDATE cases SET {', '.join(k + ' = ?' for k in f)} WHERE id = ?", [*f.values(), id])


def history(case_id: int) -> list[dict]:
    """Status changes of a case in the order they were recorded."""
    return _q("SELECT * FROM status_history WHERE case_id = ? ORDER BY id", (case_id,))


def documents(case_id: int, kind: str | None = None) -> list[dict]:
    if kind:
        return _q("SELECT * FROM documents WHERE case_id = ? AND kind = ? ORDER BY id", (case_id, kind))
    return _q("SELECT * FROM documents WHERE case_id = ? ORDER BY id", (case_id,))


def _draft(r: dict) -> dict:
    r["spans"] = _loads(r.get("spans"), [])
    r["report"] = _loads(r.get("report"), {})
    return r


def get_draft(case_id: int, version: int | None = None) -> dict | None:
    """One draft version (default: the latest), spans and report decoded."""
    if version is None:
        r = _q("SELECT * FROM drafts WHERE case_id = ? ORDER BY version DESC LIMIT 1", (case_id,))
    else:
        r = _q("SELECT * FROM drafts WHERE case_id = ? AND version = ?", (case_id, version))
    return _draft(r[0]) if r else None


def set_draft_finals(draft_id: int, final_to_send: str | None, final_anonymized: str | None, spans: list | None = None) -> None:
    """Store the finalized versions (and the decided spans) on an existing draft."""
    sets, args = ["final_to_send = ?", "final_anonymized = ?"], [final_to_send, final_anonymized]
    if spans is not None:
        sets.append("spans = ?")
        args.append(_dumps([asdict(s) if is_dataclass(s) else s for s in spans]))
    _x(f"UPDATE drafts SET {', '.join(sets)} WHERE id = ?", [*args, draft_id])


def delete_case(id: int) -> None:
    """Remove a case with its history, documents, drafts and department dispatches."""
    with closing(connect()) as con, con:
        for t, col in (("status_history", "case_id"), ("documents", "case_id"), ("drafts", "case_id"),
                       ("department_dispatches", "case_id"), ("cases", "id")):
            con.execute(f"DELETE FROM {t} WHERE {col} = ?", (id,))


# ---------------------------------------------------------------- seed


def _jsonl(path: Path) -> list[dict]:
    from .search import load_archive
    return load_archive(path) if Path(path).is_file() else []


def seed(xlsx: Path | None = None, archive: Path | None = None, demo_today: date | None = None, with_synthetic: bool = False,
         reset: bool = False) -> dict:
    """Load the UMB calendar sheet into cases and the UMB archive (and optionally the synthetic archives) into archive.

    Idempotent: archive rows are replaced by id; a case whose number already exists is left as it is (the clerk's
    status changes survive), unless reset=True, which deletes it with its history and re-imports it.
    demo_today: dates shifted around that day (importer.demo_shift) and is_demo=1, so the calendar shows every urgency.
    Returns {cases_added, cases_skipped, cases_replaced, archive, issues}.
    """
    from .importer import convert, demo_shift, extension_to_days, fill_departments
    xlsx = Path(xlsx or UMB / "kalendarium_umb.xlsx")
    archive = Path(archive or UMB / "archiwum_umb.jsonl")
    init()
    arch = _jsonl(archive)
    n_arch = 0
    for src, recs in [("umb", arch)] + ([("syntetyczne", _jsonl(p)) for p in SYNTHETIC] if with_synthetic else []):
        for r in recs:
            add_archive(r["id"], r.get("date"), r.get("title", ""), r.get("request_text", ""), r.get("response_text", ""),
                        r.get("departments") or [], r.get("source") or src)
            n_arch += 1
    recs, issues = convert(xlsx)
    fill_departments(recs, arch)
    if demo_today:
        recs = demo_shift(recs, demo_today)
    until = {r["number"]: r.get("extension_until") for r in recs}
    extension_to_days(recs)
    added, skipped, replaced = [], [], []
    for r in recs:
        old = case_by_number(r["number"])
        if old and not reset:
            skipped.append(r["number"])
            continue
        if old:
            delete_case(old["id"])
            replaced.append(r["number"])
        else:
            added.append(r["number"])
        create_case(number=r["number"], received=r["received"], summary=r.get("summary", ""), applicant_label=r.get("applicant_label", ""),
                    initials=r.get("initials", ""), status=r.get("status", "a_brak_dzialan"), extension_days=r.get("extension_days"),
                    extension_until=until.get(r["number"]), answered=r.get("answered"), departments=r.get("departments") or [],
                    is_demo=1 if demo_today else 0)
    return {"cases_added": added, "cases_skipped": skipped, "cases_replaced": replaced, "archive": n_arch, "issues": issues}
