"""Learning from clerk corrections (T25): three feedback loops, offline, stored in SQLite and visible to the clerk.

1. Personal data: remember(phrase, "allow"|"redact", ...) → learned_pii_rules. anonymize.detect_rules applies
   apply_rules(text) first: "allow" removes the rule spans on that phrase (e.g. an official's name), "redact" adds
   a suggested span with the reason REASON_PII.
2. Routing: log_routing(question, predicted, confirmed, case) → routing_feedback. analyze.route adds boost(): a
   department the clerk chose instead of the proposal, for a similar question, goes to the top with the reason
   "Wzmocnione przez N korekt urzędnika".
3. Law: add_law(file or text, title) splits a law, order or ruling into Art. / § / sygnatura chunks (legal_chunks),
   searchable at once through legal_hits(text).
memory_stats() and reset(kind) serve the "Pamięć instytucjonalna" panel.

Reading never creates the database: without a database file every loop is a no-op, so pure tests stay pure.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .textpl import norm, tokens

REASON_PII = "Wyuczone z korekty urzędnika"
ACTIONS = ("allow", "redact")
KINDS = ("pii", "routing", "legal", "all")
SIMILAR = 0.5        # Dice coefficient of question tokens from which a past correction counts
NEW_DAYS = 30        # a law added within this many days is shown as newly added


def _db():
    from . import db
    return db


def _has_db() -> bool:
    try:
        return _db().db_path().exists()
    except Exception:
        return False


def _rows(sql: str, args=()) -> list[dict]:
    if not _has_db():
        return []
    with closing(_db().connect()) as con:
        return [dict(r) for r in con.execute(sql, args).fetchall()]


def _exec(sql: str, args=()) -> int:
    with closing(_db().connect()) as con, con:
        return con.execute(sql, args).lastrowid


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------------ 1. personal data rules

def normalize_phrase(phrase: str) -> str:
    return re.sub(r"\s+", " ", norm(phrase or "")).strip(" .,;:")


def _word_rx(w: str) -> str:
    """One word of a remembered phrase, allowing Polish case endings (Bruski → Bruskiego, Kaskada → Kaskady)."""
    if re.search(r"\d", w) or not w.isalpha():
        return re.escape(w)
    if len(w) <= 4:
        return re.escape(w) + r"\w{0,3}"
    return re.escape(w[:max(3, len(w) - 2)]) + r"\w{0,5}"


def phrase_regex(phrase: str) -> re.Pattern:
    words = normalize_phrase(phrase).split(" ")
    return re.compile(r"(?<!\w)" + r"[\s\-]+".join(_word_rx(w) for w in words if w) + r"(?!\w)", re.I)


def remember(phrase: str, action: str, category: str = "", case_id: int | None = None, by: str = "") -> int:
    """Store (or update) a rule for this phrase; the latest decision on the same phrase wins. Returns the rule id."""
    phrase = re.sub(r"\s+", " ", phrase or "").strip()
    key = normalize_phrase(phrase)
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {ACTIONS}")
    if len(key) < 2:
        raise ValueError("phrase too short")
    _db().init()
    old = _rows("SELECT id FROM learned_pii_rules WHERE normalized_phrase = ?", (key,))
    if old:
        _exec("UPDATE learned_pii_rules SET phrase=?, action=?, category=?, source_case_id=?, created_by=?, created_at=? WHERE id=?",
              (phrase, action, category, case_id, by, _now(), old[0]["id"]))
        return old[0]["id"]
    return _exec("INSERT INTO learned_pii_rules (phrase, normalized_phrase, action, category, source_case_id, created_by, created_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?)", (phrase, key, action, category, case_id, by, _now()))


def rules() -> list[dict]:
    return _rows("SELECT * FROM learned_pii_rules ORDER BY id")


def apply_rules(text: str) -> list[dict]:
    """Occurrences of remembered phrases: [{start, end, text, action, category, rule_id, reason}] sorted by start."""
    if not text:
        return []
    out = []
    for r in rules():
        try:
            rx = phrase_regex(r["phrase"])
        except re.error:
            continue
        for m in rx.finditer(text):
            out.append({"start": m.start(), "end": m.end(), "text": m.group(), "action": r["action"], "category": r["category"] or "",
                        "rule_id": r["id"], "reason": REASON_PII})
    return sorted(out, key=lambda x: (x["start"], -x["end"]))


# ------------------------------------------------------------------ 2. routing feedback

def _toks(text: str) -> set[str]:
    return set(tokens(text or ""))


def log_routing(question: str, predicted: str | None, confirmed: str, case_id: int | None = None) -> None:
    """One clerk decision on one question. Only rows where confirmed != predicted count as corrections in boost()."""
    if not question or not confirmed:
        return
    _db().init()
    _exec("INSERT INTO routing_feedback (question_text, tokens_json, predicted_dept, confirmed_dept, case_id, created_at) "
          "VALUES (?, ?, ?, ?, ?, ?)", (question, json.dumps(sorted(_toks(question)), ensure_ascii=False), predicted or "",
                                        confirmed, case_id, _now()))


def _dice(a: set, b: set) -> float:
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def korekty(n: int) -> str:
    if n == 1:
        return "1 korektę"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} korekty"
    return f"{n} korekt"


def boost(question: str, scores: dict[str, float]) -> dict[str, tuple[float, str]]:
    """department → (extra score, reason). A department confirmed by the clerk instead of the proposal for a similar
    question (Dice ≥ SIMILAR, ≥ 2 shared words) gets enough to rank first: top score + summed similarity."""
    q = _toks(question)
    if len(q) < 2:
        return {}
    sims: dict[str, list[float]] = {}
    for r in _rows("SELECT tokens_json, predicted_dept, confirmed_dept FROM routing_feedback WHERE confirmed_dept != predicted_dept"):
        try:
            t = set(json.loads(r["tokens_json"] or "[]"))
        except ValueError:
            continue
        d = _dice(q, t)
        if d >= SIMILAR and len(q & t) >= 2:
            sims.setdefault(r["confirmed_dept"], []).append(d)
    if not sims:
        return {}
    top = max(scores.values(), default=0.0)
    return {dep: (round(top + sum(v), 2), f"Wzmocnione przez {korekty(len(v))} urzędnika") for dep, v in sims.items()}


# ------------------------------------------------------------------ 3. laws and rulings

HEAD = re.compile(r"(?m)^[ \t]*(?:(Art\.?[ \t]*\d+[a-z]?)\.?|(§[ \t]*\d+[a-z]?)\.?|((?:sygn\.?(?:[ \t]*akt)?|Sygnatura(?:[ \t]*akt)?)[ \t:]*"
                  r"[IVXL]+[ \t]+[A-Za-z]{2,4}(?:/[A-Za-z]{1,3})?[ \t]+\d+/\d{2,4}))", re.I)


def split_law(text: str) -> list[tuple[str, str]]:
    """(ref, text) per article, paragraph (§) or ruling signature; the preamble keeps ref ''. No headings → 200-word blocks."""
    text = (text or "").strip()
    marks = list(HEAD.finditer(text))
    if not marks:
        words = text.split()
        return [("", " ".join(words[i:i + 200])) for i in range(0, len(words), 200)]
    out = []
    head = text[:marks[0].start()].strip()
    if head:
        out.append(("", head))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        ref = re.sub(r"\s+", " ", next(g for g in m.groups() if g)).strip()
        ref = re.sub(r"^art", "Art", ref, flags=re.I).replace("Art ", "Art. ").replace("Art.", "Art. ").replace("Art.  ", "Art. ")
        ref = re.sub(r"§\s*", "§ ", ref)
        out.append((ref, text[m.start():end].strip()))
    return out


def add_law(path_or_text, title: str, source_file: str = "") -> int:
    """Split a law/order/ruling (file path or its text) into legal_chunks. Returns the number of chunks stored."""
    if isinstance(path_or_text, Path) or (isinstance(path_or_text, str) and len(path_or_text) < 500 and "\n" not in path_or_text
                                          and Path(path_or_text).suffix and Path(path_or_text).is_file()):
        from .ingest import read_any
        p = Path(path_or_text)
        text, source_file = read_any(p)["text"], source_file or p.name
    else:
        text = str(path_or_text or "")
    parts = [(r, t) for r, t in split_law(text) if t.strip()]
    if not parts:
        return 0
    _db().init()
    now = _now()
    with closing(_db().connect()) as con, con:
        con.executemany("INSERT INTO legal_chunks (law_title, ref, text, source_file, created_at) VALUES (?, ?, ?, ?, ?)",
                        [(title, r, t, source_file, now) for r, t in parts])
    return len(parts)


FUNC = set("""oraz jest się nie dla przez który która które których tym tego tej ten tak lub albo jak czy przy pod nad
też jego jej ich być było będzie może mogą wraz także tylko jeżeli jezeli gdy aby oraz pana pani proszę prosze wnoszę wnosze""".split())


def _fold(s: str) -> str:
    s = norm(s).replace("ł", "l")
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def _ltoks(text: str) -> set[str]:
    """Words for law search: accents folded (PDFs often lose them), the UDIP vocabulary kept, numbers kept."""
    return {t for t in tokens(_fold(text), keep_stop=True, keep_numbers=True)
            if (t.isdigit() or len(t) >= 3) and t not in FUNC}


def legal_hits(text: str, k: int = 3) -> list[dict]:
    """Chunks that share the most (IDF-weighted) words with the text: [{id, law_title, ref, text, score, matched,
    source_file, created_at, new}]; new = added within NEW_DAYS. Needs ≥ 2 shared words."""
    chunks = _rows("SELECT * FROM legal_chunks")
    q = _ltoks(text or "")
    if not chunks or not q:
        return []
    toks = [_ltoks(c["law_title"] + " " + c["text"]) for c in chunks]
    df = Counter(t for ts in toks for t in ts)
    n = len(chunks)
    since = (datetime.now() - timedelta(days=NEW_DAYS)).isoformat(timespec="seconds")
    scored = []
    for c, ts in zip(chunks, toks):
        common = q & ts
        if len(common) < 2:
            continue
        s = sum(math.log(1 + n / df[t]) for t in common) / math.sqrt(len(ts) or 1)
        scored.append((s, c, common))
    scored.sort(key=lambda x: -x[0])
    return [{"id": c["id"], "law_title": c["law_title"], "ref": c["ref"], "text": c["text"], "score": round(s, 3),
             "matched": sorted(common)[:8], "source_file": c["source_file"], "created_at": c["created_at"],
             "new": (c["created_at"] or "") >= since} for s, c, common in scored[:k]]


# ------------------------------------------------------------------ memory widget

def memory_stats() -> dict:
    def one(sql):
        r = _rows(sql)
        return r[0]["n"] if r else 0
    return {"pii_allow": one("SELECT COUNT(*) n FROM learned_pii_rules WHERE action='allow'"),
            "pii_redact": one("SELECT COUNT(*) n FROM learned_pii_rules WHERE action='redact'"),
            "routing": one("SELECT COUNT(*) n FROM routing_feedback WHERE confirmed_dept != predicted_dept"),
            "routing_all": one("SELECT COUNT(*) n FROM routing_feedback"),
            "legal_chunks": one("SELECT COUNT(*) n FROM legal_chunks"),
            "laws": one("SELECT COUNT(DISTINCT law_title) n FROM legal_chunks")}


def reset(kind: str) -> None:
    """Forget one kind of learned memory: pii, routing, legal or all."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if not _has_db():
        return
    tables = {"pii": ["learned_pii_rules"], "routing": ["routing_feedback"], "legal": ["legal_chunks"]}
    todo = [t for v in tables.values() for t in v] if kind == "all" else tables[kind]
    with closing(_db().connect()) as con, con:
        for t in todo:
            con.execute(f"DELETE FROM {t}")
