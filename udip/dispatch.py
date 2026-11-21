"""Przekazanie pytań do wydziału (CONTRACTS §2): termin wewnętrzny, pakiet (treść wiadomości + formularz DOCX),
odczyt odpowiedzi z oznaczeniami „Ad N” (tier 1 przypisania zdań w udip.draft).

Odwzorowuje praktykę UMB (Zarządzenie Prezydenta Miasta Bydgoszczy z 2024 r., § 11): BKS przekazuje wydziałowi
jego pytania z terminem, wydział odsyła projekt odpowiedzi w swojej części (ust. 1), zanonimizowany (ust. 8);
gdy nie ma informacji – wskazuje podmiot właściwy (ust. 3).

Dni wolne: soboty, niedziele i dni ustawowo wolne z udip.deadlines (tabela office_days_off nie jest jeszcze czytana).
Zależności: python-docx (MIT). Reszta: biblioteka standardowa.
"""
from __future__ import annotations

import io
import json
import re
from datetime import date, timedelta

from .deadlines import deadline_days, is_working_day

INTERNAL_MARGIN = 3  # dni robocze między terminem wydziału a terminem ustawowym (czas BKS na złożenie pisma)
MIN_LEAD = 2         # najkrótszy termin dla wydziału, w dniach roboczych od dziś
BKS_MAIL = "bip@um.bydgoszcz.pl"
_MONTHS = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października",
           "listopada", "grudnia"]


def _pl(d: date) -> str:
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year} r."


def _as_date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def add_working_days(d: date, n: int) -> date:
    """d przesunięte o n dni roboczych (n < 0: wstecz). Dzień d się nie liczy."""
    step = 1 if n >= 0 else -1
    left = abs(n)
    while left:
        d += timedelta(days=step)
        if is_working_day(d):
            left -= 1
    return d


def sub_deadline(received: date, today: date, due: date | None = None) -> date:
    """Termin dla wydziału = max(dziś + 2 dni robocze, termin ustawowy − 3 dni robocze).

    due: termin ustawowy, gdy inny niż 14 dni (przedłużenie z art. 13 ust. 2); domyślnie deadlines.deadline_days(received).
    Wynik może wypaść po terminie ustawowym, gdy sprawa przyszła do wydziału za późno – packet() wtedy ostrzega.
    """
    legal = due or deadline_days(_as_date(received))
    return max(add_working_days(_as_date(today), MIN_LEAD), add_working_days(legal, -INTERNAL_MARGIN))


def _dept(department: str) -> dict:
    from .analyze import load_departments
    for d in load_departments():
        if d["id"] == department:
            return d
    return {"id": department, "name": department, "type": "wydzial"}


def _qs(questions: list[dict]) -> list[tuple[int, str]]:
    out = []
    for i, q in enumerate(questions, 1):
        if isinstance(q, dict):
            out.append((int(q.get("no") or i), re.sub(r"\s+", " ", str(q.get("text") or "")).strip()))
        else:
            out.append((i, re.sub(r"\s+", " ", str(q)).strip()))
    return out


def message_text(case: dict, department: str, questions: list[dict], *, today: date | None = None,
                 due: date | None = None) -> tuple[str, str, date, date]:
    """(temat, treść, termin wydziału, termin ustawowy) wiadomości do wydziału."""
    from . import config
    received = _as_date(case["received"])
    legal = due or (_as_date(case["extension_until"]) if case.get("extension_until") else deadline_days(received))
    sub = sub_deadline(received, today or config.today(), legal)
    d = _dept(department)
    number = case.get("number") or "[numer sprawy]"
    subject = f"{number} – prośba o materiał do odpowiedzi na wniosek o udostępnienie informacji publicznej (termin: {_pl(sub)})"
    qs = _qs(questions)
    lines = [d["name"], "",
             f"Przekazuję wniosek o udostępnienie informacji publicznej zarejestrowany pod numerem {number}, "
             f"który wpłynął {_pl(received)}."]
    if (case.get("summary") or "").strip():
        lines += [f"Przedmiot wniosku: {case['summary'].strip()}"]
    lines += ["", "Proszę o przygotowanie materiału do odpowiedzi na następujące pytania wnioskodawcy:", ""]
    lines += [f"[Ad {n}] {t}" for n, t in qs] or ["[brak pytań przypisanych tej komórce – uzupełnij]"]
    lines += ["",
              f"Materiał proszę przekazać na adres {BKS_MAIL} do {_pl(sub)}. "
              f"Termin ustawowy udzielenia odpowiedzi wnioskodawcy upływa {_pl(legal)}.",
              "Odpowiedź proszę wpisać w załączonym formularzu pod oznaczeniem właściwego pytania, bez zmiany numeracji „Ad”.",
              "Materiał zawierający dane osobowe lub inne informacje podlegające ochronie proszę przekazać w wersji "
              "zanonimizowanej (§ 11 ust. 8 zarządzenia Prezydenta Miasta Bydgoszczy w sprawie udostępniania informacji publicznej).",
              "Jeżeli komórka nie posiada tej informacji, proszę wskazać podmiot właściwy (§ 11 ust. 3).",
              "", "Biuro Komunikacji Społecznej", "Urząd Miasta Bydgoszczy"]
    if sub >= legal:
        lines.insert(0, f"[UWAGA: termin dla komórki ({_pl(sub)}) nie wyprzedza terminu ustawowego ({_pl(legal)}) – "
                        "rozważ powiadomienie o przedłużeniu (art. 13 ust. 2 UDIP)]")
    return subject, "\n".join(lines), sub, legal


def reply_form_docx(case: dict, department: str, questions: list[dict], sub: date) -> bytes:
    """Formularz odpowiedzi: bloki „[Ad N] Pytanie: … / Odpowiedź wydziału:”. Wypełniony i wgrany z powrotem
    daje przypisanie zdań do pytań bez zgadywania (parse_reply)."""
    import docx
    from docx.shared import Pt
    d = _dept(department)
    doc = docx.Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    doc.add_paragraph().add_run("Formularz odpowiedzi komórki merytorycznej").bold = True
    doc.add_paragraph(f"Sprawa: {case.get('number') or '[numer sprawy]'}")
    doc.add_paragraph(f"Komórka: {d['id']} – {d['name']}")
    doc.add_paragraph(f"Termin przekazania materiału: {_pl(sub)}, na adres {BKS_MAIL}")
    doc.add_paragraph("Odpowiedź wpisz pod „Odpowiedź wydziału:” przy każdym pytaniu. Nie zmieniaj oznaczeń pytań. "
                      "Dane osobowe zanonimizuj przed odesłaniem (§ 11 ust. 8 zarządzenia).")
    for n, t in _qs(questions):
        p = doc.add_paragraph()
        p.add_run(f"[Ad {n}]").bold = True
        p.add_run(f" Pytanie: {t}")
        doc.add_paragraph("Odpowiedź wydziału:")
        doc.add_paragraph("")
    doc.add_paragraph("")
    doc.add_paragraph("Sprawę prowadzi:")
    buf = io.BytesIO()
    doc.save(buf)
    data = buf.getvalue()
    try:
        from .export import harden_docx
        data = harden_docx(data)
    except Exception:  # noqa: BLE001  (lane E; bez niej formularz i tak jest poprawny)
        pass
    return data


def packet(case: dict, department: str, questions: list[dict], *, today: date | None = None, due: date | None = None) -> dict:
    """{message_text, reply_form_docx, subject, sub_deadline, legal_due, filename} dla jednej komórki.

    case: number, received (+ summary, extension_until); questions: tylko pytania tej komórki [{no, text}] z numeracją wniosku.
    """
    subject, text, sub, legal = message_text(case, department, questions, today=today, due=due)
    safe = re.sub(r"[^\w.\-]+", "_", f"{case.get('number') or 'sprawa'}_{department}")
    return {"message_text": f"Temat: {subject}\n\n{text}", "subject": subject, "sub_deadline": sub, "legal_due": legal,
            "reply_form_docx": reply_form_docx(case, department, questions, sub), "filename": f"formularz_{safe}.docx",
            "questions": [{"no": n, "text": t} for n, t in _qs(questions)]}


# ------------------------------------------------------------------ odczyt odpowiedzi (tier 1)

# [Ad N] | Ad. N | Ad N. / Ad N: / Ad N) | „Ad N” sam w linii; zawsze na początku linii albo po białym znaku
MARK = re.compile(r"(?im)(?:^|(?<=\s))(?:\[\s*Ad\.?\s*(\d{1,3})\s*\]|Ad\.\s*(\d{1,3})\b[.:)]?|Ad\s+(\d{1,3})(?:\s*[.:)]|[ \t]*$))")
ANSWER_LABEL = re.compile(r"(?i)odpowied[zź]\s+wydzia[lł]u\s*:")
QUESTION_LABEL = re.compile(r"(?i)^\s*pytanie\s*:")
TAIL = re.compile(r"(?im)^\s*(Sprawę prowadzi|Sprawe prowadzi|Sporządził|Z poważaniem|Do wiadomości|Łączę wyrazy|Otrzymują)")


def markers(text: str) -> list[re.Match]:
    return list(MARK.finditer(text or ""))


def parse_reply(text: str) -> dict[int, str] | None:
    """Odpowiedź wydziału z oznaczeniami pytań → {nr pytania: treść}. None = brak oznaczeń (wtedy tier 2 w draft).

    Tekst przed pierwszym oznaczeniem (nagłówek pisma) jest pomijany; w bloku formularza pomija się „Pytanie: …”
    i bierze to, co po „Odpowiedź wydziału:”; stopka („Sprawę prowadzi”, „Z poważaniem”) jest odcinana.
    Puste odpowiedzi nie trafiają do wyniku, więc wgrany niewypełniony formularz daje {} (a nie None).
    """
    ms = markers(text)
    if not ms:
        return None
    out: dict[int, str] = {}
    for i, m in enumerate(ms):
        k = int(next(g for g in m.groups() if g))
        seg = text[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(text)]
        lab = ANSWER_LABEL.search(seg)
        if lab:
            seg = seg[lab.end():]
        elif QUESTION_LABEL.match(seg):
            seg = seg.split("\n", 1)[1] if "\n" in seg else ""
        seg = TAIL.split(seg)[0]
        clean = re.sub(r"\s+", " ", seg).strip(" \t\n–-:")
        if clean:
            out[k] = f"{out[k]} {clean}" if k in out else clean
    return out


def dispatch_questions(case: dict) -> dict[str, list[dict]]:
    """Pytania sprawy pogrupowane po komórkach (z analizy: chosen_departments, inaczej pierwsza propozycja trasowania)."""
    an = case.get("analysis") or {}
    if isinstance(an, str):
        an = json.loads(an or "{}")
    chosen = an.get("chosen_departments") or {}
    out: dict[str, list[dict]] = {}
    for q in an.get("questions") or []:
        ids = chosen.get(str(q["no"])) or ([q["routing"][0]["department"]] if q.get("routing") else [])
        for d in ids:
            out.setdefault(d, []).append({"no": q["no"], "text": q["text"]})
    for d in case.get("departments") or []:
        out.setdefault(d, [])
    return out
