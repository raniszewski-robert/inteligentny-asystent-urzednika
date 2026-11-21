"""Nowy wniosek (T05): upload → text (quality check) → analysis → confirm → case in the register."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app import services, store
from app.common import clerk, render, today
from udip import learning, security
from udip.ingest import IngestError, guess_date

router = APIRouter()


def _summary(an: dict, text: str) -> str:
    if an.get("summary"):
        return an["summary"]
    first = (an.get("questions") or [{"text": text}])[0]["text"]
    first = " ".join(first.split())
    return first if len(first) <= 160 else first[:157].rsplit(" ", 1)[0] + "…"


def _form_defaults(an: dict, text: str, request: Request) -> dict:
    received = guess_date(text) or today().isoformat()
    try:
        year = date.fromisoformat(received).year
    except ValueError:
        year = today().year
    return {"number": store.next_number(year), "received": received, "initials": clerk(request),
            "summary": _summary(an, text), "applicant_label": "", "status": "a_brak_dzialan"}


def _security(doc: dict, text: str) -> dict:
    """T26 scan of the stored upload (re-done on every analysis, so it follows the current text); pasted text gets
    the instruction check only. Never raises."""
    if doc.get("security") is not None and doc.get("text") == text:
        return doc["security"]  # fresh upload: ingest already scanned it
    try:
        p = services.upload_path(doc.get("stored") or "")
        if p:
            return security.scan(p, text)
        return {**security.empty(), "injection": security.find_injection(text)}
    except Exception:
        return security.empty()


def _pages(nums) -> str:
    nums = sorted({n for n in nums if n})
    return ", ".join(str(n) for n in nums)


def security_lines(sec: dict | None) -> list[str]:
    """Plain-Polish lines for the 'Kontrola bezpieczeństwa pliku' note; [] = nothing to show."""
    if not sec:
        return []
    out = []
    for h in sec.get("hidden_text") or []:
        out.append(f"Tekst niewidoczny po otwarciu pliku ({h.get('where')}; {h.get('reason')}): „{h.get('text')}”.")
    imgs = sec.get("images") or []
    if imgs:
        pages = _pages(im.get("page") for im in imgs)
        hints = sorted({im["hint"] for im in imgs if im.get("hint")})
        line = f"Obrazy w pliku: {len(imgs)}" + (f" (strony {pages})" if pages else "") + (f", w tym: {', '.join(hints)}" if hints else "")
        out.append(line + ". Sprawdź, czy zawierają podpis, pieczęć lub dane osobowe.")
    for i in sec.get("injection") or []:
        out.append(f"Fragment wygląda na polecenie dla programu: „{i.get('text')}”. Nie jest przekazywany do modelu językowego.")
    for n in sec.get("notes") or []:
        out.append(n)
    return out


def _page(request: Request, **ctx):
    if "doc" in ctx and "text" in ctx and ctx.get("doc") is not None:
        ctx.setdefault("security_lines", security_lines(_security(ctx["doc"], ctx["text"])))
        try:  # T25: laws and rulings added in Archiwum, searchable at once
            ctx.setdefault("legal", learning.legal_hits(ctx["text"]))
        except Exception:
            ctx.setdefault("legal", [])
    return render(request, "wniosek_nowy.html", title="Nowy wniosek", names=services.department_names(), **ctx)


@router.get("/wniosek/nowy")
def form(request: Request):
    return _page(request)


@router.post("/wniosek/nowy")
async def submit(request: Request):
    f = await request.form()
    akcja = str(f.get("akcja") or "analizuj")
    text = str(f.get("tekst") or "").strip()
    doc = {"file": str(f.get("plik_nazwa") or ""), "stored": str(f.get("plik_zapis") or ""), "quality": None, "warning": None}
    up = f.get("plik")
    if up is not None and getattr(up, "filename", ""):
        data = await up.read()
        if data:
            try:
                doc = services.read_upload(up.filename, data)
            except IngestError as e:
                return _page(request, error=str(e), text=text)
            text = doc["text"]
    elif f.get("jakosc"):
        try:
            doc["quality"] = float(str(f.get("jakosc")))
        except ValueError:
            pass
    if not text:
        return _page(request, error="Dodaj plik wniosku albo wpisz jego treść.")

    if akcja == "zapisz":
        return _save(request, f, text, doc)

    an = services.run_analysis(text)
    return _page(request, text=text, doc=doc, analysis=an, form=_form_defaults(an, text, request),
                 chosen={q["no"]: [q["routing"][0]["department"]] if q["routing"] else [] for q in an["questions"]})


def _save(request: Request, f, text: str, doc: dict):
    number = str(f.get("number") or "").strip()
    received = str(f.get("received") or "").strip()
    an = services.run_analysis(text)
    chosen = {q["no"]: [str(v) for v in f.getlist(f"dep_{q['no']}")] for q in an["questions"]}
    form = {k: str(f.get(k) or "").strip() for k in ("number", "received", "initials", "summary", "applicant_label", "status")}
    errors = []
    if not number:
        errors.append("Podaj numer sprawy.")
    elif store.case_by_number(number):
        errors.append(f"Sprawa {number} jest już w rejestrze.")
    try:
        date.fromisoformat(received)
    except ValueError:
        errors.append("Podaj datę wpływu.")
    if form["status"] not in ("a_brak_dzialan", "b_zapytania_wyslane"):
        form["status"] = "a_brak_dzialan"
    if errors:
        return _page(request, text=text, doc=doc, analysis=an, form=form, chosen=chosen, error=" ".join(errors))
    deps: list[str] = []
    for no in sorted(chosen):
        for d in chosen[no]:
            if d not in deps:
                deps.append(d)
    an["chosen_departments"] = {str(k): v for k, v in chosen.items()}
    an["source_file"] = doc.get("file") or ""
    cid = store.create_case(number=number, received=received, summary=form["summary"], applicant_label=form["applicant_label"],
                            initials=form["initials"] or clerk(request), status="a_brak_dzialan", departments=deps, analysis=an)
    if form["status"] != "a_brak_dzialan":
        store.set_status(cid, form["status"], clerk(request), "przy rejestracji wniosku")
    _log_routing(an, chosen, cid)
    sec = _security(doc, text)
    if security.count(sec):
        security.log_scan(sec, cid)
    stored = services.upload_path(doc.get("stored") or "")
    store.add_document(cid, "request", doc.get("file") or "wniosek.txt", text, quality=doc.get("quality"),
                       path=str(stored) if stored else None)
    return RedirectResponse(f"/sprawy/{cid}", status_code=303)


def _log_routing(an: dict, chosen: dict, case_id: int) -> None:
    """T25: every department the clerk confirmed per question; a different one than proposed is a correction."""
    try:
        for q in an["questions"]:
            predicted = q["routing"][0]["department"] if q.get("routing") else ""
            for dep in chosen.get(q["no"], []):
                learning.log_routing(q["text"], predicted, dep, case_id)
    except Exception:
        pass
