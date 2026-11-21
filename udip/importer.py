"""Import arkusza „WNIOSKI O UDOSTĘPNIANIE INFORMACJI PUBLICZNEJ.xlsx” (wzór kalendarium UMB) → rejestr JSON + raport niespójności.

Kolumny wzoru UMB (wiersz 2): Lp. | Numer sprawy | Wnioskodawca | Przedmiot zapytania | Data wpływu | Termin odpowiedzi |
Data odpowiedzi | Osoba odpowiedzialna | Pozostało dni. Nagłówki rozpoznawane po nazwie, więc kolejność może się zmienić.

Kontrole (każda z przykładem z arkusza UMB z 21.11.2026):
- termin w arkuszu ≠ termin wyliczony (art. 13 UDIP + art. 57 § 4 KPA), np. formuła „=E11+14” bez przesunięcia z soboty;
- termin przed datą wpływu (literówka w roku), odpowiedź przed wpływem, numer sprawy niepasujący do roku wpływu;
- tekst zamiast daty (np. „19.08.2026/18.09.2026 - doprecyzowanie wniosku”) → zapis jako przedłużenie z datą z tekstu.

CLI: .claude/skills/udip-kalendarz-terminy/scripts/import_xlsx.py arkusz.xlsx --out rejestr.json [--report niespojnosci.md]
Zależność: openpyxl (MIT).
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from .deadlines import deadline_days, is_working_day, urgency, working_days_left

HEAD = {"lp": "lp", "numer sprawy": "number", "nr wniosku": "number", "wnioskodawca": "applicant", "przedmiot zapytania": "summary",
        "temat": "summary", "data wpływu": "received", "termin odpowiedzi": "due_sheet", "data odpowiedzi": "answered",
        "osoba odpowiedzialna": "initials", "inicjały": "initials", "pozostało dni": "left_sheet"}
DATE_TXT = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


def as_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    if len(parts) >= 2 and not parts[-1].isdigit():
        return "".join(p[0] for p in parts[:2]).upper()
    return (name or "").strip()  # „Pracownik 1” zostaje bez zmian


def convert(path: Path) -> tuple[list[dict], list[str]]:
    import openpyxl
    ws = openpyxl.load_workbook(path, data_only=False).active
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and any(isinstance(c, str) and c.strip().lower().startswith("numer sprawy") for c in r))
    cols = {}
    for j, h in enumerate(rows[hi]):
        key = (h or "").strip().lower().rstrip(".")
        if key in HEAD:
            cols[HEAD[key]] = j
    out, issues = [], []
    for r in rows[hi + 1:]:
        if not r or not r[cols["number"]]:
            continue
        g = lambda k: r[cols[k]] if k in cols else None  # noqa: E731
        num = str(g("number")).strip()
        rec_d = as_date(g("received"))
        if not rec_d:
            issues.append(f"{num}: brak poprawnej daty wpływu ({g('received')!r}) – pominięto")
            continue
        calc = deadline_days(rec_d)
        due_raw = g("due_sheet")
        item = {"number": num, "received": rec_d.isoformat(), "summary": str(g("summary") or "").strip(),
                "initials": initials(str(g("initials") or "")), "applicant_label": str(g("applicant") or "").strip(),
                "status": "a_brak_dzialan", "departments": [], "notes": ""}
        due_s = as_date(due_raw)
        if isinstance(due_raw, str) and due_raw.startswith("="):
            naive = rec_d.toordinal() + 14
            if naive != calc.toordinal():
                issues.append(f"{num}: termin to formuła {due_raw!r} = {date.fromordinal(naive)} (bez przesunięcia z soboty/święta); poprawnie {calc}")
        elif isinstance(due_raw, str):
            ds = [date(int(y), int(m), int(d)) for d, m, y in DATE_TXT.findall(due_raw)]
            if ds:
                item["extension_until"] = max(ds).isoformat()
                item["status"] = "c_kwerenda"
                item["notes"] = f"z arkusza: {due_raw}"
                issues.append(f"{num}: tekst w kolumnie terminu ({due_raw!r}) → przedłużenie do {max(ds)}")
        elif due_s:
            if due_s < rec_d:
                issues.append(f"{num}: termin {due_s} wcześniejszy niż wpływ {rec_d} (literówka w roku?); wyliczono {calc}")
            elif due_s != calc:
                issues.append(f"{num}: termin w arkuszu {due_s} ≠ wyliczony {calc} (art. 13 UDIP + art. 57 § 4 KPA)")
        ans = as_date(g("answered"))
        if ans:
            item["answered"] = ans.isoformat()
            item["status"] = "e_odpowiedz_wyslana"
            if ans < rec_d:
                issues.append(f"{num}: odpowiedź {ans} przed wpływem {rec_d} – sprawdź datę wpływu")
            limit = date.fromisoformat(item["extension_until"]) if "extension_until" in item else calc
            if ans > limit and "extension_until" not in item:
                issues.append(f"{num}: odpowiedź {ans} po terminie {calc} bez odnotowanego przedłużenia")
        m = re.search(r"\.(\d{4})$", num)
        if m and int(m.group(1)) != rec_d.year:
            issues.append(f"{num}: rok w numerze sprawy ≠ rok wpływu {rec_d.year}")
        out.append(item)
    return out, issues


def demo_shift(recs: list[dict], today: date) -> list[dict]:
    """Zachowuje tematy i kolejność, nadaje daty wpływu dające pełne spektrum pilności (po terminie, dziś, jutro…)."""
    from datetime import timedelta
    want = ["overdue", "today", "tomorrow", "soon", "soon", "ok", "ok", "ok", "ok", "ok"]
    status = ["b_zapytania_wyslane", "d_odpowiedz_przygotowana", "b_zapytania_wyslane", "b_zapytania_wyslane", "a_brak_dzialan",
              "a_brak_dzialan", "c_kwerenda", "a_brak_dzialan", "a_brak_dzialan", "e_odpowiedz_wyslana"]
    used: set[date] = set()
    out = []
    for i, r in enumerate(sorted(recs, key=lambda x: x["received"])):
        w = want[i % len(want)]
        pick = None
        fallback_pick = None
        for back in range(1, 60):
            d = today - timedelta(days=back)
            if d in used or not is_working_day(d):
                continue
            due = deadline_days(d)
            if urgency(due, today) == w:
                if w == "overdue" and working_days_left(due, today) >= 0:
                    fallback_pick = fallback_pick or d
                    continue
                pick = d
                break
        pick = pick or fallback_pick or next(today - timedelta(days=b) for b in range(1, 60) if today - timedelta(days=b) not in used and is_working_day(today - timedelta(days=b)))
        used.add(pick)
        r = {k: v for k, v in r.items() if k not in ("answered", "extension_until", "extension_days")}
        r["received"], r["status"] = pick.isoformat(), status[i % len(status)]
        if r["status"] == "c_kwerenda":
            r["extension_days"] = 30
        if r["status"] == "e_odpowiedz_wyslana":
            r["answered"] = today.isoformat()
        r["notes"] = (r.get("notes", "") + " [DEMO: daty przesunięte]").strip()
        out.append(r)
    return out


def fill_departments(recs: list[dict], archive: list[dict]) -> list[dict]:
    """Wydziały ze sprawy archiwalnej o tym samym numerze (bez podmiotów zewnętrznych ZEWN*)."""
    arch = {r["id"]: r for r in archive}
    for r in recs:
        if r["number"] in arch:
            r["departments"] = [d for d in arch[r["number"]].get("departments", []) if not d.startswith("ZEWN")]
    return recs


def extension_to_days(recs: list[dict]) -> list[dict]:
    """Przedłużenie z arkusza (data w polu extension_until) → extension_days zgodne z register.Request
    (liczone od terminu 14-dniowego). Usuwa extension_until."""
    for r in recs:
        if "extension_until" in r:
            base = deadline_days(date.fromisoformat(r["received"]))
            r["extension_days"] = max(0, (date.fromisoformat(r.pop("extension_until")) - base).days)
    return recs
