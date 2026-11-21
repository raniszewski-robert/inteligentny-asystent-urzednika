"""Data access for the Projekt pisma and Anonimizacja screens (lane B2): a thin layer over `udip.db` (T02).

Drafts use the contract `drafts` table (one row per version). Standalone anonymization documents (no case)
are JSON files in `$UDIP_DATA_DIR/anonimizacja/`; the raw upload is not kept.
"""
from __future__ import annotations

import json
import re
import secrets
from contextlib import closing
from datetime import datetime
from pathlib import Path

from udip import config, db

get_case = db.get_case
documents = db.documents
set_status = db.set_status
add_archive = db.add_archive
archive_records = db.archive_records


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def add_document(case_id: int, kind: str, filename: str, text: str, department: str | None = None) -> int:
    return db.add_document(case_id, kind, filename, text, department=department)


def case_inputs(case: dict) -> dict:
    """What make_draft needs: request text, department answers [(file, text)], number, received."""
    reqs = [d for d in documents(case["id"], "request") if (d.get("text") or "").strip()]
    if reqs:
        req_text = reqs[-1]["text"]
    else:
        arch = next((r for r in archive_records() if r["id"] == case.get("number") and (r.get("request_text") or "").strip()), None)
        req_text = arch["request_text"] if arch else (case.get("summary") or "")
    answers = [(d["filename"] or f"odpowiedz_{d['id']}.txt", d["text"] or "") for d in documents(case["id"], "dept_answer")]
    return {"request": req_text, "answers": answers,
            "number": case.get("number") or "BKS.IV.1431.___.2026", "received": case.get("received")}


# ---- drafts ----------------------------------------------------------------------------------------------------

def list_drafts(case_id: int) -> list[dict]:
    with closing(db.connect()) as con:
        return [dict(r) for r in con.execute(
            "SELECT id, case_id, version, ltype, created_at, final_anonymized IS NOT NULL AS finalized "
            "FROM drafts WHERE case_id=? ORDER BY version", (case_id,)).fetchall()]


def get_draft(case_id: int, version: int | None = None) -> dict | None:
    d = db.get_draft(case_id, version)
    if d is not None and isinstance(d.get("spans"), dict):  # tolerate {"spans": [...]}
        d["spans"] = d["spans"].get("spans", [])
    return d


def save_draft(case_id: int, ltype: str, text: str, spans: list, report: dict,
               final_to_send: str | None = None, final_anonymized: str | None = None) -> int:
    """New version (max + 1). Returns the version number."""
    did = db.save_draft(case_id, ltype, text, spans, report, final_to_send, final_anonymized)
    with closing(db.connect()) as con:
        return con.execute("SELECT version FROM drafts WHERE id=?", (did,)).fetchone()[0]


def set_spans(draft_id: int, spans: list, final_to_send: str | None = None, final_anonymized: str | None = None) -> None:
    """Store decisions on the draft; without finals the draft counts as not finalized (exports need a new approval)."""
    db.set_draft_finals(draft_id, final_to_send, final_anonymized, spans)


# ---- standalone anonymization documents --------------------------------------------------------------------------

TOKEN = re.compile(r"^[a-f0-9]{16}$")


def _doc_dir() -> Path:
    d = config.data_dir() / "anonimizacja"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_doc(filename: str, text: str, spans: list, keep: list[str]) -> str:
    doc_id = secrets.token_hex(8)  # random id of a standalone document (not a credential)
    save_doc(doc_id, {"filename": filename, "text": text, "spans": spans, "keep": keep, "created_at": _now(), "finalized": False})
    return doc_id


def get_doc(token: str) -> dict | None:
    if not TOKEN.match(token or ""):
        return None
    p = _doc_dir() / f"{token}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_doc(token: str, doc: dict) -> None:
    if not TOKEN.match(token):
        raise ValueError("bad token")
    (_doc_dir() / f"{token}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def delete_doc(token: str) -> bool:
    if not TOKEN.match(token or ""):
        return False
    p = _doc_dir() / f"{token}.json"
    if p.exists():
        p.unlink()
        return True
    return False


def archive_sent_letter(case_id: int, by: str = "") -> bool:
    """Put the case's finalized letter (anonymized) and its anonymized request into the archive table, so it feeds
    future searches, and keep the 'do wysyłki' text as a letter document. Call when the status becomes
    e_odpowiedz_wyslana. Returns False when the latest draft is not finalized."""
    from app import b2_redact as rd
    from app.common import today
    case = get_case(case_id)
    d = get_draft(case_id)
    if case is None or d is None or not d.get("final_anonymized") or rd.undecided(d["spans"]):
        return False
    req = case_inputs(case)["request"]
    rs = [dict(s, status="accepted") for s in rd.detect_spans(req)]
    add_archive(case["number"], today().isoformat(), case.get("summary") or case["number"], rd.export_text(req, rs, "zanonimizowana"),
                rd.export_text(d["text"], d["spans"], "zanonimizowana"),
                list(case.get("departments") or d["report"].get("departments") or []), "asystent")
    if not any(x["filename"] == f"{case['number']}_odpowiedz.txt" for x in documents(case_id, "letter")):
        add_document(case_id, "letter", f"{case['number']}_odpowiedz.txt", rd.export_text(d["text"], d["spans"], "do_wysylki"))
    return True
