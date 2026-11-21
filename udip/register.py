"""Rejestr (kalendarz) wniosków UDIP: model danych, statusy, sortowanie, podświetlenia, eksport.

Pola z treści zadania (pkt 3): liczba porządkowa, nr wniosku, skrócony opis, inicjały,
data wpływu, termin odpowiedzi, data udzielenia odpowiedzi, status (a–e), kwerenda + liczba dni,
wybór roku. Lista od najstarszego do najnowszego.

CLI: .claude/skills/udip-kalendarz-terminy/scripts/register.py. Tylko biblioteka standardowa.
"""
from __future__ import annotations

import csv
import html
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

from .deadlines import deadline_days, deadline_extended, deadline_safe, urgency, working_days_left

# Statusy z „uproszczonej instrukcji” w treści zadania (pkt 11).
STATUSES = {
    "a_brak_dzialan": "a) brak działań",
    "b_zapytania_wyslane": "b) zapytania wysłane do wydziałów",
    "c_kwerenda": "c) kwerenda (przedłużenie)",
    "d_odpowiedz_przygotowana": "d) przygotowana odpowiedź",
    "e_odpowiedz_wyslana": "e) odpowiedź wysłana",
}
URGENCY_LABEL = {
    "overdue": "PO TERMINIE",
    "today": "termin DZIŚ",
    "tomorrow": "termin jutro / następny dzień roboczy",
    "soon": "do 3 dni roboczych",
    "ok": "w terminie",
    "done": "zakończony",
}
URGENCY_COLOR = {  # tło wiersza; kontrast tekstu sprawdzony dla czarnego tekstu
    "overdue": "#f4a6a6",
    "today": "#f8c4c4",
    "tomorrow": "#ffd8a8",
    "soon": "#fff3bf",
    "ok": "#ffffff",
    "done": "#d3f9d8",
}


@dataclass
class Request:
    number: str                      # nr wniosku, np. BKS.1431.12.2026
    received: str                    # data wpływu RRRR-MM-DD
    summary: str                     # skrócony opis tematu
    initials: str = ""               # inicjały osoby prowadzącej
    status: str = "a_brak_dzialan"
    extension_days: int | None = None   # kwerenda: +N dni
    extension_months: int | None = None  # albo przedłużenie w miesiącach
    answered: str | None = None      # data udzielenia odpowiedzi
    departments: list[str] = field(default_factory=list)
    channel: str = ""                # e-mail, ePUAP, papier
    notes: str = ""
    history: list[dict] = field(default_factory=list)

    @property
    def received_date(self) -> date:
        return date.fromisoformat(self.received)

    def due(self) -> tuple[date, list[str]]:
        if self.status == "c_kwerenda" or self.extension_days is not None or self.extension_months is not None:
            if self.extension_days is None and self.extension_months is None:
                return deadline_extended(self.received_date, months=2)
            return deadline_extended(self.received_date, self.extension_days, self.extension_months)
        return deadline_days(self.received_date), []

    def set_status(self, status: str, when: str | None = None, who: str = "") -> None:
        if status not in STATUSES:
            raise ValueError(f"Nieznany status {status}; dozwolone: {', '.join(STATUSES)}")
        self.history.append({"from": self.status, "to": status, "at": when or datetime.now().isoformat(timespec="minutes"), "by": who})
        self.status = status
        if status == "e_odpowiedz_wyslana" and not self.answered:
            self.answered = (when or date.today().isoformat())[:10]


def load(path: Path) -> list[Request]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw["requests"] if isinstance(raw, dict) else raw
    return [Request(**r) for r in items]


def save(reqs: list[Request], path: Path) -> None:
    path.write_text(json.dumps({"requests": [asdict(r) for r in reqs]}, ensure_ascii=False, indent=2), encoding="utf-8")


def rows(reqs: list[Request], today: date, year: int | None = None) -> list[dict]:
    sel = [r for r in reqs if year is None or r.received_date.year == year]
    sel.sort(key=lambda r: (r.received, r.number))  # od najstarszego do najnowszego
    out = []
    for lp, r in enumerate(sel, 1):
        due, warn = r.due()
        done = r.status == "e_odpowiedz_wyslana"
        u = urgency(due, today, done)
        late = bool(done and r.answered and date.fromisoformat(r.answered) > due)
        out.append({
            "lp": lp, "number": r.number, "received": r.received, "summary": r.summary,
            "initials": r.initials, "status": r.status, "status_label": STATUSES[r.status],
            "extension": (f"+{r.extension_days} dni" if r.extension_days is not None else
                          f"+{r.extension_months} mies." if r.extension_months is not None else
                          "do 2 mies." if r.status == "c_kwerenda" else ""),
            "due": due.isoformat(), "due_safe": (deadline_safe(r.received_date).isoformat() if not warn else due.isoformat()),
            "answered": r.answered or "",
            "working_days_left": "" if done else working_days_left(due, today),
            "urgency": u, "urgency_label": URGENCY_LABEL[u] + (" (odpowiedź po terminie)" if late else ""),
            "departments": ", ".join(r.departments), "warnings": warn,
        })
    return out


def to_csv(rs: list[dict], path: Path) -> None:
    cols = ["lp", "number", "received", "summary", "initials", "status_label", "extension", "due", "due_safe", "answered", "working_days_left", "urgency_label", "departments"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # BOM: poprawne polskie znaki w Excelu
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", delimiter=";")
        w.writeheader()
        w.writerows(rs)


def to_html(rs: list[dict], path: Path, today: date, year: int | None) -> None:
    head = ["L.p.", "Nr wniosku", "Data wpływu", "Temat (skrót)", "Inicjały", "Status", "Kwerenda", "Termin", "Termin bezpieczny", "Data odpowiedzi", "Dni rob.", "Pilność", "Wydziały"]
    keys = ["lp", "number", "received", "summary", "initials", "status_label", "extension", "due", "due_safe", "answered", "working_days_left", "urgency_label", "departments"]
    body = []
    for r in rs:
        cells = "".join(f"<td>{html.escape(str(r[k]))}</td>" for k in keys)
        body.append(f'<tr class="{r["urgency"]}" style="background:{URGENCY_COLOR[r["urgency"]]}">{cells}</tr>')
    legend = "".join(f'<span style="background:{URGENCY_COLOR[k]};padding:2px 8px;margin-right:6px;border:1px solid #999">{v}</span>' for k, v in URGENCY_LABEL.items())
    counts = {k: sum(1 for r in rs if r["urgency"] == k) for k in URGENCY_LABEL}
    doc = f"""<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><title>Kalendarz wniosków UDIP</title>
<style>body{{font-family:system-ui,sans-serif;margin:24px;color:#111}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #888;padding:6px 8px;font-size:14px;text-align:left}}th{{background:#e9ecef}}
tr.overdue td,tr.today td{{font-weight:600}}</style></head><body>
<h1>Kalendarz wniosków o udostępnienie informacji publicznej</h1>
<p>Stan na {today.isoformat()}{f" · rok {year}" if year else ""} · wniosków: {len(rs)} ·
po terminie: {counts['overdue']} · dziś: {counts['today']} · jutro: {counts['tomorrow']}</p>
<p>{legend}</p>
<table><thead><tr>{''.join(f'<th>{h}</th>' for h in head)}</tr></thead><tbody>
{chr(10).join(body)}
</tbody></table>
<p style="font-size:12px;color:#444">Termin: art. 13 UDIP z przesunięciem wg art. 57 § 4 KPA. „Termin bezpieczny”: ostatni dzień roboczy przed 14. dniem, bo orzecznictwo nie przesądza stosowania art. 57 KPA w UDIP – planuj wysyłkę wg niego.
Narzędzie pomocnicze – ostateczną decyzję podejmuje urzędnik.</p></body></html>"""
    path.write_text(doc, encoding="utf-8")


def to_ics(rs: list[dict], path: Path) -> None:
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//asystent-udip//PL", "CALSCALE:GREGORIAN"]
    for r in rs:
        if r["urgency"] == "done":
            continue
        d = r["due"].replace("-", "")
        summ = f"Termin UDIP {r['number']}: {r['summary']}"[:200].replace(",", "\\,").replace(";", "\\;")
        lines += ["BEGIN:VEVENT", f"UID:{r['number']}@asystent-udip", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{d}",
                  f"SUMMARY:{summ}", "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", "DESCRIPTION:Jutro termin UDIP", "END:VALARM", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
