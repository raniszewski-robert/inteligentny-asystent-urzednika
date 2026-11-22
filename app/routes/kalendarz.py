"""Kalendarz (T04): register of requests ordered oldest → newest, urgency colours, status changes, import, export."""
from __future__ import annotations

import csv
import io
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response

from app import store
from app.common import clerk, is_htmx, render, today
from udip.register import STATUSES, URGENCY_LABEL, rows as register_rows

router = APIRouter()

LEGEND = ["overdue", "today", "tomorrow", "soon", "ok", "done"]

URGENCY_SHORT = {
    "overdue": "Po terminie",
    "today": "Termin dziś",
    "tomorrow": "Jutro",
    "soon": "Do 3 dni",
    "ok": "W terminie",
    "done": "Zakończony",
}

BOARD_STAGES = [
    ("a", "a) Brak działań", ("a_brak_dzialan",), "a_brak_dzialan"),
    ("b", "b) Zapytania w wydziałach", ("b_zapytania_wyslane",), "b_zapytania_wyslane"),
    ("c", "c) Kwerenda / przedłużenie", ("c_kwerenda",), "c_kwerenda"),
    ("de", "d–e) Gotowe i wysłane", ("d_odpowiedz_przygotowana", "e_odpowiedz_wyslana"), "d_odpowiedz_przygotowana"),
]


def _uklad(uklad: str | None) -> str:
    return "tabela" if uklad == "tabela" else "tablica"


def _year(rok: str | None) -> int | None:
    if rok is None or rok == "":
        return today().year if today().year in store.years() else None
    if rok == "wszystkie":
        return None
    try:
        return int(rok)
    except ValueError:
        return None


def register(year: int | None, uklad: str = "tablica") -> dict:
    cases = store.list_cases(year)
    by_number = {c["number"]: c for c in cases}
    rs = register_rows([store.to_request(c) for c in cases], today(), None)
    last = store.last_changes()
    for r in rs:
        c = by_number[r["number"]]
        r["id"] = c["id"]
        r["applicant_label"] = c.get("applicant_label") or ""
        r["is_demo"] = bool(c.get("is_demo"))
        r["extension_days"] = c.get("extension_days")
        r["last"] = last.get(c["id"])
        r["urgency_short"] = URGENCY_SHORT.get(r["urgency"], r["urgency_label"])
        r["dept_list"] = [d.strip() for d in (r.get("departments") or "").split(",") if d.strip()]
    counts = {k: sum(1 for r in rs if r["urgency"] == k) for k in URGENCY_LABEL}
    board_columns = [
        {
            "key": key,
            "title": title,
            "drop_status": drop_status,
            "cards": [r for r in rs if r["status"] in statuses],
        }
        for key, title, statuses, drop_status in BOARD_STAGES
    ]
    return {"rows": rs, "counts": counts, "year": year, "uklad": _uklad(uklad), "board_columns": board_columns,
            "statuses": STATUSES, "urgency_label": URGENCY_LABEL, "legend": LEGEND,
            "any_demo": any(r["is_demo"] for r in rs) or any(c.get("is_demo") for c in store.list_cases())}


def _page(request: Request, year: int | None, uklad: str | None = None, **extra):
    return render(request, "kalendarz.html", title="Kalendarz", years=store.years(), **register(year, _uklad(uklad)), **extra)


@router.get("/kalendarz")
def kalendarz(request: Request, rok: str | None = None, uklad: str | None = None):
    return _page(request, _year(rok), uklad=uklad)


def _archive_sent_letter(case_id: int) -> bool:
    """Status e: the approved, anonymized letter goes to the archive (lane B2, T08). No-op without a final draft
    or before app/b2_store.py is merged."""
    try:
        from app.b2_store import archive_sent_letter
    except ImportError:
        return False
    return bool(archive_sent_letter(case_id))


@router.post("/sprawy/{case_id}/status")
def change_status(request: Request, case_id: int, status: str = Form(...), extension_days: str = Form(""),
                  note: str = Form(""), rok: str = Form(""), widok: str = Form("kalendarz"),
                  uklad: str = Form("tablica")):
    if store.get_case(case_id) is None:
        raise HTTPException(404)
    if status not in STATUSES:
        raise HTTPException(400, "Nieznany status.")
    ext = None
    if extension_days.strip():
        try:
            ext = max(0, min(int(extension_days), 366))
        except ValueError:
            raise HTTPException(400, "Liczba dni przedłużenia musi być liczbą.")
    c = store.get_case(case_id)
    if c["status"] != status or note.strip():
        store.set_status(case_id, status, clerk(request), note.strip() or None, extension_days=ext)
        if status == "e_odpowiedz_wyslana":
            _archive_sent_letter(case_id)
    elif ext is not None and status == "c_kwerenda":
        store.update_case(case_id, extension_days=ext)
    if is_htmx(request) and widok == "kalendarz":
        return render(request, "kalendarz_tabela.html", **register(_year(rok or "wszystkie"), uklad=_uklad(uklad)))
    if widok == "sprawa":
        back = f"/sprawy/{case_id}"
    else:
        back = f"/kalendarz?rok={rok or ''}" + ("&uklad=tabela" if _uklad(uklad) == "tabela" else "")
    if is_htmx(request):
        return Response(status_code=204, headers={"HX-Redirect": back})
    return RedirectResponse(back, status_code=303)


@router.post("/kalendarz/import")
async def import_xlsx(request: Request, plik: UploadFile = File(...), demo: str = Form("")):
    from udip.importer import convert, demo_shift
    name = plik.filename or "arkusz.xlsx"
    if not name.lower().endswith((".xlsx", ".xlsm")):
        return _page(request, _year(None), import_error="Wybierz arkusz Excel (.xlsx) w układzie kalendarium UMB.")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "arkusz.xlsx"
        p.write_bytes(await plik.read())
        try:
            recs, issues = convert(p)
        except Exception as e:  # noqa: BLE001 – wrong layout, damaged file
            return _page(request, _year(None), import_error=f"Nie udało się odczytać arkusza ({type(e).__name__}). Sprawdź, czy ma kolumnę „Numer sprawy”.")
    if demo:
        recs = demo_shift(recs, today())
    res = store.import_records(recs, demo=bool(demo), replace=bool(demo))
    return _page(request, None, import_result={"file": name, "issues": issues, **res, "demo": bool(demo)})


@router.post("/kalendarz/demo")
def demo(request: Request, akcja: str = Form(...)):
    if akcja == "wczytaj":
        store.load_demo(today())
        return RedirectResponse("/kalendarz?rok=wszystkie", status_code=303)
    if akcja == "usun":
        store.clear_demo()
    return RedirectResponse("/kalendarz", status_code=303)


EXPORT_COLS = [("lp", "L.p."), ("number", "Numer sprawy"), ("applicant_label", "Wnioskodawca"), ("summary", "Przedmiot zapytania"),
               ("received", "Data wpływu"), ("initials", "Osoba odpowiedzialna"), ("status_label", "Status"), ("extension", "Kwerenda"),
               ("due", "Termin odpowiedzi"), ("due_safe", "Termin bezpieczny"), ("answered", "Data odpowiedzi"),
               ("working_days_left", "Pozostało dni roboczych"), ("urgency_label", "Pilność"), ("departments", "Wydziały")]


@router.get("/kalendarz/eksport.csv")
def export_csv(rok: str | None = None):
    rs = register(_year(rok))["rows"]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([h for _, h in EXPORT_COLS])
    for r in rs:
        w.writerow([r.get(k, "") for k, _ in EXPORT_COLS])
    data = "\ufeff" + buf.getvalue()  # BOM: Excel reads Polish characters
    return Response(data.encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="kalendarz_udip.csv"'})


def _ics_text(s: str) -> str:
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", " ")


@router.get("/kalendarz/eksport.ics")
def export_ics(rok: str | None = None):
    rs = register(_year(rok))["rows"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//asystent-udip//PL", "CALSCALE:GREGORIAN"]
    for r in rs:
        if r["urgency"] == "done":
            continue
        lines += ["BEGIN:VEVENT", f"UID:{r['number']}@asystent-udip", f"DTSTAMP:{stamp}",
                  f"DTSTART;VALUE=DATE:{r['due_safe'].replace('-', '')}",
                  f"SUMMARY:{_ics_text(('Termin UDIP ' + r['number'] + ': ' + r['summary'])[:200])}",
                  f"DESCRIPTION:{_ics_text('Termin ustawowy ' + r['due'] + ', termin bezpieczny ' + r['due_safe'])}",
                  "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", "DESCRIPTION:Jutro termin UDIP", "END:VALARM", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines) + "\r\n", media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="terminy_udip.ics"'})
