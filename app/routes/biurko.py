"""Biurko: ekran startowy. Po lewej teczki otwartych spraw z pieczątką terminu, po prawej otwarta teczka:
ostatni projekt pisma na kartce (propozycje i zaczernienia jak w anonimizacji) i uwagi na marginesie."""
from __future__ import annotations

import html
import re
from datetime import date

from fastapi import APIRouter, Request
from markupsafe import Markup

from app import b2_redact as rd
from app import b2_store, store
from app.common import render, today
from app.routes.kalendarz import register
from udip.draft import NUM, _norm_num, numbers

router = APIRouter()

PREFIX = "BKS.IV.1431."
ORDER = {"overdue": 0, "today": 1, "tomorrow": 2, "soon": 3, "ok": 4}
FOLDER = {"overdue": "manila", "today": "manila", "tomorrow": "manila", "soon": "blue", "ok": "grey"}
WEEKDAYS = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
MONTHS = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
          "października", "listopada", "grudnia"]


def plural(n: int, one: str, few: str, many: str) -> str:
    if n == 1:
        return one
    return few if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else many


def stamp(r: dict) -> str:
    u = r["urgency"]
    if u == "overdue":
        return "Po terminie"
    if u == "today":
        return "Dziś"
    if u == "tomorrow":
        return "Jutro"
    n = r.get("working_days_left")
    return f"{n} {plural(n, 'dzień', 'dni', 'dni')}" if isinstance(n, int) else r.get("urgency_short", "")


def folders() -> list[dict]:
    rows = [r for r in register(None)["rows"] if r["urgency"] != "done"]
    rows.sort(key=lambda r: (ORDER.get(r["urgency"], 9), r["due"], r["number"]))
    out = []
    for r in rows:
        d = date.fromisoformat(r["due"])
        out.append({**r, "short": r["number"].removeprefix(PREFIX), "stamp": stamp(r), "folder": FOLDER.get(r["urgency"], "grey"),
                    "due_short": d.strftime("%d.%m"), "depts": r.get("departments") or "bez wydziału"})
    return out


def _spans_for(spans: list[dict], version: str) -> list[dict]:
    """Rozłączne fragmenty do pokazania; w wersji do wysyłki adresat zostaje jawny."""
    flat = sorted(rd.flatten(spans), key=lambda s: (s["start"], -(s["end"] - s["start"])))
    out: list[dict] = []
    for s in flat:
        if s["status"] == "rejected" or (version == "wysylka" and s.get("addressee")):
            continue
        if out and s["start"] < out[-1]["end"]:
            continue
        out.append(s)
    return out


def _plain(seg: str, offset: int, ad_from: int, verified: set[str]) -> str:
    """Zwykły tekst: liczby zgodne z odpowiedziami wydziałów podkreślone, nagłówki „Ad N” pogrubione."""
    parts, pos = [], 0
    for m in NUM.finditer(seg):
        raw = m.group().strip()
        if offset + m.start() < ad_from or len(re.sub(r"\D", "", raw)) < 2 or re.fullmatch(r"(19|20)\d\d", raw):
            continue
        if _norm_num(raw) not in verified:
            continue
        st = m.start() + (len(m.group()) - len(m.group().lstrip()))
        parts.append(html.escape(seg[pos:st]))
        parts.append(f'<span class="num-ok" title="Liczba zgodna z odpowiedzią wydziału">{html.escape(raw)}</span>')
        pos = st + len(raw)
    parts.append(html.escape(seg[pos:]))
    return re.sub(r"(?m)^(Ad \d{1,3})\s*$", r"<strong>\1</strong>", "".join(parts))


def letter_html(text: str, spans: list[dict], version: str, answers: list[str]) -> tuple[str, Markup]:
    """(linia z datą, treść pisma jako HTML)."""
    verified = numbers("\n".join(answers)) if answers else set()
    first, _, _ = text.partition("\n")
    date_line = first.strip() if first.strip().startswith("Bydgoszcz") else ""
    start = len(first) + 1 if date_line else 0
    m = re.search(r"(?m)^Ad \d", text)
    ad_from = m.start() if m else len(text)
    out, pos = [], start
    for s in _spans_for(spans, version):
        if s["end"] <= start:
            continue
        st = max(s["start"], start)
        out.append(_plain(text[pos:st], pos, ad_from, verified))
        frag = html.escape(text[st:s["end"]])
        tip = html.escape(f"{rd.type_label(s['type'])} ({rd.STATUS_LABEL.get(s['status'], s['status'])})")
        out.append(f'<mark class="sp sp-{html.escape(s["status"])}" title="{tip}">{frag}</mark>')
        pos = s["end"]
    out.append(_plain(text[pos:], pos, ad_from, verified))
    return date_line, Markup("".join(out).lstrip("\n"))


def margin_notes(case: dict, draft: dict | None) -> list[dict]:
    if draft is None:
        return [{"text": "projekt pisma powstanie z odpowiedzi wydziałów", "tone": "grey"}]
    notes = []
    answers = store.documents(case["id"], "dept_answer")
    rep = draft.get("report") or {}
    bad = list(rep.get("number_check") or []) + list(rep.get("number_check_template") or []) + list(rep.get("number_check_edit") or [])
    if bad:
        notes.append({"text": f"✗ liczby spoza odpowiedzi: {', '.join(bad[:3])}", "tone": "red"})
    elif answers and draft.get("ltype") == "udostepnienie":
        who = ", ".join(sorted({(d.get("department") or d.get("filename") or "").strip() for d in answers} - {""}))
        notes.append({"text": f"✓ liczby zgadzają się z odpowiedzią: {who}", "tone": "blue"})
    spans = draft.get("spans") or []
    for s in [s for s in spans if s["status"] == "review"][:2]:
        notes.append({"text": f"{rd.type_label(s['type']).lower()}: zaczernić czy jawne? (do decyzji)", "tone": "orange"})
    sugg = [s for s in spans if s["status"] == "suggested"]
    if sugg:
        kinds = ", ".join(sorted({rd.type_label(s["type"]).lower() for s in sugg}))
        notes.append({"text": f"{kinds} – {plural(len(sugg), 'propozycja', 'propozycje', 'propozycji')} zaczernienia", "tone": "grey"})
    if rep.get("unassigned"):
        n = len(rep["unassigned"])
        notes.append({"text": f"{n} {plural(n, 'zdanie', 'zdania', 'zdań')} bez przypisania do „Ad”", "tone": "orange"})
    return notes


@router.get("/biurko")
def biurko(request: Request, teczka: int | None = None, wersja: str = "bip"):
    version = "wysylka" if wersja == "wysylka" else "bip"
    fs = folders()
    case = store.get_case(teczka) if teczka else None
    if case is None:  # domyślnie teczka z najnowszym projektem pisma, inaczej pierwsza na stosie
        with_draft = [f for f in fs if b2_store.get_draft(f["id"]) is not None]
        pick = with_draft[0] if with_draft else (fs[0] if fs else None)
        case = store.get_case(pick["id"]) if pick else None
    draft = b2_store.get_draft(case["id"]) if case else None
    date_line, body, undecided = "", Markup(""), 0
    if draft is not None:
        answers = [d.get("text") or "" for d in store.documents(case["id"], "dept_answer")]
        date_line, body = letter_html(draft["text"], draft.get("spans") or [], version, answers)
        undecided = len(rd.undecided(draft.get("spans") or []))
    t = today()
    open_n = len(fs)
    return render(
        request, "biurko.html", title="Biurko",
        folders=fs,
        day_line=f"{WEEKDAYS[t.weekday()]}, {t.day} {MONTHS[t.month - 1]} {t.year}",
        open_line=f"{open_n} {plural(open_n, 'otwarta teczka', 'otwarte teczki', 'otwartych teczek')}",
        case=case, draft=draft, version=version, date_line=date_line, letter=body,
        notes=margin_notes(case, draft) if case else [],
        undecided=undecided,
        undecided_text=(f"{undecided} {plural(undecided, 'fragment czeka', 'fragmenty czekają', 'fragmentów czeka')} na decyzję"
                        " – eksport po rozstrzygnięciu" if undecided else "Każdy fragment ma decyzję – pismo można pobrać"),
    )
