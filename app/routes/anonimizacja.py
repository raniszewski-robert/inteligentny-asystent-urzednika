"""Anonimizacja (T08): span editor, approval, DOCX/TXT exports; for a case letter and for any uploaded file.

Case mode:       GET/POST /sprawy/{id}/anonimizacja, GET /sprawy/{id}/eksport/{do_wysylki|zanonimizowana}.{docx|txt}
Standalone mode: GET/POST /anonimizacja (upload), GET/POST /anonimizacja/{token}, GET /anonimizacja/{token}/eksport/zanonimizowana.{docx|txt}

Exports are refused while any span is undecided, and every file is checked for accepted text before it is sent.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response

from app import b2_redact as rd
from app import b2_store as store
from app import jobs, services
from app.routes.model import context as model_context
from app.common import clerk, render
from udip import config, security
from udip.ingest import IngestError, read_any

router = APIRouter()

STATUSES = {"suggested", "review", "accepted", "rejected"}
UPLOAD_EXT = {".txt", ".md", ".eml", ".docx", ".odt", ".pdf"}
MAX_UPLOAD = 15 * 1024 * 1024
SENT = "e_odpowiedz_wyslana"
MIME = {"docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "txt": "text/plain; charset=utf-8"}


# ---- shared form handling ------------------------------------------------------------------------------------------

def _prepare(spans: list[dict]) -> list[dict]:
    for s in spans:
        s.setdefault("orig", s["status"] if s["status"] in rd.UNDECIDED else "review")
    return spans


def model_spans(text: str, spans: list[dict], keep: list[str]) -> list[dict]:
    """Extra fragments from the language model (udip.anonymize.detect hook): always "review", never overlapping
    a fragment that is already there, marked source="llm". No model available → spans unchanged."""
    from app import settings
    from udip.anonymize import detect
    if not settings.llm_on():
        return spans
    taken = [(s["start"], s["end"]) for s in spans]
    n = sum(1 for s in spans if str(s.get("id", "")).startswith("m"))
    for sp in detect(text, keep=keep, provider=settings.provider_arg()):
        if not str(sp.reason).startswith("model:") or any(sp.start < e and b < sp.end for b, e in taken):
            continue
        n += 1
        spans.append({"start": sp.start, "end": sp.end, "text": text[sp.start:sp.end], "type": sp.type, "confidence": sp.confidence,
                      "reason": sp.reason, "status": "review", "orig": "review", "id": f"m{n}", "source": "llm"})
        taken.append((sp.start, sp.end))
    spans.sort(key=lambda s: (s["start"], -s["end"]))
    return spans


def _apply_form(text: str, spans: list[dict], form, action: str, *, letter: bool, keep: list[str]) -> tuple[str, list[dict], bool]:
    """Decisions from the form, then the bulk action. Returns (text, spans, text_changed)."""
    for s in spans:
        v = form.get(f"st_{s['id']}")
        if v in STATUSES:
            s["status"] = v
    act, _, sid = str(form.get("pamiec") or "").partition(":")  # T25: a remembered fragment gets the matching decision
    for s in spans:
        if sid and s["id"] == sid and act in ("allow", "redact", "tajemnica"):
            s["status"] = "rejected" if act == "allow" else "accepted"
    manual = [x for x in str(form.get("manual", "")).splitlines() if x.strip()]
    edited = form.get("edited")
    changed = False
    if edited is not None:
        edited = str(edited).replace("\r\n", "\n").strip("\n")
        if edited.strip() and edited != text.strip("\n"):
            spans = rd.redetect(text, spans, edited, letter=letter, keep=keep)
            text, changed = edited, True
    spans = _prepare(rd.add_manual(text, spans, manual))
    if action == "model":  # w tle: start_model_spans() po zapisaniu decyzji
        pass
    elif action == "akceptuj":
        for s in spans:
            if s["status"] == "suggested":
                s["status"] = "accepted"
    elif action == "wszystkie":
        for s in spans:
            if s["status"] in rd.UNDECIDED:
                s["status"] = "accepted"
    return text, spans, changed


def _finals(text: str, spans: list[dict], versions: list[str]) -> tuple[dict[str, str], list[str]]:
    """Final texts per version and any leak found in the TXT or DOCX output (must be empty)."""
    out, found = {}, []
    for v in versions:
        txt = rd.export_text(text, spans, v)
        found += rd.leaks(txt, text, spans, v)
        found += rd.leaks(rd.docx_text(rd.export_docx(text, spans, v)), text, spans, v)
        found += [h["secret"] for h in rd.audit(text, spans, v)["hits"]]
        out[v] = txt
    return out, sorted(set(found))


def _file(text: str, spans: list[dict], version: str, ext: str, stem: str, initials: str = "") -> Response:
    if rd.undecided(spans):
        raise HTTPException(409, "Najpierw zdecyduj o wszystkich zaznaczonych fragmentach i zatwierdź anonimizację.")
    if ext == "docx":
        data = rd.export_docx(text, spans, version, initials)
        check = rd.docx_text(data)
        if not rd.audit_bytes(data, text, spans, version)["ok"]:
            raise HTTPException(500, "Kontrola XML zatrzymała eksport. Zgłoś to administratorowi.")
    else:
        check = rd.export_text(text, spans, version)
        data = check.encode("utf-8")
    if rd.leaks(check, text, spans, version):
        raise HTTPException(500, "Kontrola wycieków zatrzymała eksport. Zgłoś to administratorowi.")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{stem}_{version}")[:120] + "." + ext
    return Response(data, media_type=MIME[ext], headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _split_name(name: str) -> tuple[str, str]:
    m = re.fullmatch(r"(do_wysylki|zanonimizowana)\.(docx|txt)", name)
    if not m:
        raise HTTPException(404)
    return m.group(1), m.group(2)


def _page(request: Request, *, mode: str, heading: str, base: str, action_url: str, text: str, spans: list[dict], finalized: bool,
          versions: list[str], warnings: list[str], message: str = "", error: str = "", **extra):
    from app import settings
    spans = sorted(spans, key=lambda s: (s["start"], -(s["end"] - s["start"])))
    extra.setdefault("llm_on", settings.llm_on())
    extra.setdefault("llm_count", sum(1 for s in spans if s.get("source") == "llm"))
    extra.setdefault("audits", {v: rd.audit(text, spans, v) for v in versions} if finalized and not rd.undecided(spans) else {})
    return render(request, "anonimizacja.html", title=heading, mode=mode, heading=heading, base=base, action_url=action_url, text=text,
                  marked=rd.marked_html(text, spans), spans=spans, undecided=len(rd.undecided(spans)), finalized=finalized,
                  versions={v: rd.VERSIONS[v] for v in versions}, warnings=warnings, message=message, error=error,
                  manual="\n".join(rd.manual_phrases(spans)), type_label=rd.type_label, status_label=rd.STATUS_LABEL, **extra)


def _model_msg(before: int, after: int) -> str:
    from app import settings
    n, who = after - before, settings.model_name()
    return (f"{who} dodał {n} fragm. do decyzji (fioletowa ramka)." if n > 0 else
            f"{who} nie znalazł nic ponad reguły.")


def start_case_model(case_id: int) -> str | None:
    if not settings_llm_on():
        return None

    def work() -> dict:
        draft = store.get_draft(case_id)
        spans = _prepare(draft["spans"])
        before = len(spans)
        spans = model_spans(draft["text"], spans, [])
        if store.get_draft(case_id)["id"] == draft["id"]:  # nikt w międzyczasie nie zapisał nowej wersji
            store.set_spans(draft["id"], spans)
        return {"message": _model_msg(before, len(spans)), "target": f"/sprawy/{case_id}/anonimizacja"}

    return jobs.submit(f"anon:{case_id}", "odswiez", work)


def start_doc_model(token: str) -> str | None:
    if not settings_llm_on():
        return None

    def work() -> dict:
        doc = store.get_doc(token)
        spans = _prepare(doc["spans"])
        before = len(spans)
        doc["spans"] = model_spans(doc["text"], spans, doc.get("keep", []))
        store.save_doc(token, doc)
        return {"message": _model_msg(before, len(doc["spans"])), "target": f"/anonimizacja/{token}"}

    return jobs.submit(f"anon-doc:{token}", "odswiez", work)


def settings_llm_on() -> bool:
    from app import settings
    return settings.llm_on()


# ---- case mode ----------------------------------------------------------------------------------------------------

def _case_draft(case_id: int) -> tuple[dict, dict]:
    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(404)
    return case, store.get_draft(case_id)


def _case_page(request: Request, case: dict, draft: dict, **kw):
    spans = _prepare(draft["spans"])
    return _page(request, mode="sprawa", heading=f"Anonimizacja {case['number']}", base=f"/sprawy/{case['id']}", action_url=f"/sprawy/{case['id']}/anonimizacja",
                 text=draft["text"], spans=spans, finalized=bool(draft.get("final_anonymized")) and not rd.undecided(spans),
                 versions=["do_wysylki", "zanonimizowana"], warnings=rd.legal_warnings(draft["text"], spans),
                 case=case, draft=draft, sent=case.get("status") == SENT, **kw)


@router.get("/sprawy/{case_id}/anonimizacja")
def case_anon(request: Request, case_id: int, msg: str = "", bielik: str = ""):
    case, draft = _case_draft(case_id)
    if draft is None:
        return RedirectResponse(f"/sprawy/{case_id}/projekt", status_code=303)
    return _case_page(request, case, draft, message=MESSAGES.get(msg, ""), **model_context(jobs.get(bielik)))


MESSAGES = {
    "zapisano": "Zapisano decyzje.",
    "zatwierdzono": "Anonimizacja zatwierdzona. Pliki są gotowe do pobrania.",
    "wyslano": "Status sprawy: odpowiedź wysłana. Pismo dodano do archiwum.",
    "zapamietano": "Zapamiętano. Przy kolejnych dokumentach asystent zastosuje tę decyzję (lista w Archiwum, Pamięć instytucjonalna).",
    "nowa": "Treść się zmieniła: zapisano nową wersję pisma, fragmenty wykryto od nowa.",
}


@router.post("/sprawy/{case_id}/anonimizacja")
async def case_anon_post(request: Request, case_id: int):
    case, draft = _case_draft(case_id)
    if draft is None:
        raise HTTPException(404)
    form = await request.form()
    action = str(form.get("action", "zapisz"))
    url = f"/sprawy/{case_id}/anonimizacja"
    if action == "wyslano":
        if not draft.get("final_anonymized") or rd.undecided(draft["spans"]):
            return _case_page(request, case, draft, error="Najpierw zatwierdź anonimizację.")
        if case.get("status") != SENT:
            store.set_status(case_id, SENT, clerk(request), "odpowiedź wysłana (ekran anonimizacji)")
        store.archive_sent_letter(case_id)
        return RedirectResponse(f"{url}?msg=wyslano", status_code=303)
    text, spans, changed = _apply_form(draft["text"], _prepare(draft["spans"]), form, action, letter=True, keep=[])
    if changed:
        report = dict(draft["report"], edited=True, based_on=draft["version"])
        store.save_draft(case_id, draft["ltype"], text, spans, report)
        draft = store.get_draft(case_id)
    if action == "zatwierdz":
        if rd.undecided(spans):
            store.set_spans(draft["id"], spans)
            draft = store.get_draft(case_id)
            return _case_page(request, case, draft, error=f"Bez decyzji: {len(rd.undecided(spans))} fragm. Zdecyduj o każdym "
                              "fragmencie albo użyj przycisku „Zaczernij wszystkie bez decyzji”.")
        finals, found = _finals(text, spans, ["do_wysylki", "zanonimizowana"])
        if found:
            store.set_spans(draft["id"], spans)
            return _case_page(request, case, store.get_draft(case_id), error="Kontrola wycieków zatrzymała eksport: " + "; ".join(found))
        store.set_spans(draft["id"], spans, finals["do_wysylki"], finals["zanonimizowana"])
        return RedirectResponse(f"{url}?msg=zatwierdzono", status_code=303)
    store.set_spans(draft["id"], spans)
    if action == "model":
        jid = start_case_model(case_id)
        return RedirectResponse(f"{url}?bielik={jid}" if jid else url, status_code=303)
    return RedirectResponse(f"{url}?msg={'nowa' if changed else 'zapamietano' if form.get('pamiec') else 'zapisano'}", status_code=303)


@router.get("/sprawy/{case_id}/eksport/{name}")
def case_export(request: Request, case_id: int, name: str):
    version, ext = _split_name(name)
    case, draft = _case_draft(case_id)
    if draft is None or not draft.get("final_anonymized"):
        raise HTTPException(409, "Najpierw zatwierdź anonimizację na ekranie Anonimizacja.")
    return _file(draft["text"], draft["spans"], version, ext, case["number"], clerk(request))


# ---- standalone mode -------------------------------------------------------------------------------------------------

def _doc_or_404(token: str) -> dict:
    doc = store.get_doc(token)
    if doc is None:
        raise HTTPException(404)
    return doc


def _doc_page(request: Request, token: str, doc: dict, **kw):
    spans = _prepare(doc["spans"])
    return _page(request, mode="plik", heading=f"Anonimizacja: {doc['filename']}", base=f"/anonimizacja/{token}", action_url=f"/anonimizacja/{token}",
                 text=doc["text"], spans=spans, finalized=bool(doc.get("finalized")) and not rd.undecided(spans),
                 versions=["zanonimizowana"], warnings=[doc["warning"]] if doc.get("warning") else [],
                 security_lines=doc.get("security_lines") or [], doc=doc, **kw)


@router.get("/anonimizacja")
def upload_form(request: Request):
    return render(request, "anonimizacja.html", title="Anonimizacja", mode="upload", error="", keep="")


@router.post("/anonimizacja")
async def upload(request: Request):
    form = await request.form()
    keep = [x.strip() for x in str(form.get("jawne", "")).splitlines() if x.strip()]
    pasted = str(form.get("tekst", "")).replace("\r\n", "\n").strip()
    up = form.get("plik")

    def fail(msg: str):
        return render(request, "anonimizacja.html", title="Anonimizacja", mode="upload", error=msg, keep="\n".join(keep),
                      status_code=400)

    warning = None
    sec = None
    if isinstance(up, UploadFile) or (hasattr(up, "filename") and hasattr(up, "read")):
        if up.filename:
            ext = Path(up.filename).suffix.lower()
            if ext not in UPLOAD_EXT:
                return fail("Obsługiwane pliki: TXT, DOCX, ODT, PDF. Plik .doc zapisz najpierw jako DOCX.")
            data = await up.read(MAX_UPLOAD + 1)
            if len(data) > MAX_UPLOAD:
                return fail("Plik jest większy niż 15 MB.")
            tmp = config.data_dir() / "tmp"
            tmp.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=tmp, suffix=ext, delete=False) as f:
                f.write(data)
            try:
                res = read_any(Path(f.name))
            except (IngestError, Exception) as e:  # noqa: BLE001  any parser error ends as a message, not a 500
                return fail(f"Nie udało się odczytać pliku: {e}")
            finally:
                Path(f.name).unlink(missing_ok=True)  # the upload is not kept, only its text
            text, name, warning, sec = res["text"], Path(up.filename).name, res.get("warning"), res.get("security")
        else:
            text, name = "", ""
    else:
        text, name = "", ""
    if not text:
        if not pasted:
            return fail("Wybierz plik albo wklej tekst.")
        text, name = pasted, "tekst wklejony"
        sec = {**security.empty(), "injection": security.find_injection(text)}
    if security.count(sec):
        security.log_scan(sec, None)
    sec_lines = services.security_lines(sec)
    doc_id = store.new_doc(name, text, _prepare(rd.detect_spans(text, keep)), keep)
    if warning or sec_lines:
        doc = store.get_doc(doc_id)
        if warning:
            doc["warning"] = warning
        if sec_lines:
            doc["security_lines"] = sec_lines
        store.save_doc(doc_id, doc)
    return RedirectResponse(f"/anonimizacja/{doc_id}", status_code=303)


@router.get("/anonimizacja/{token}")
def doc_anon(request: Request, token: str, msg: str = "", bielik: str = ""):
    return _doc_page(request, token, _doc_or_404(token), message=MESSAGES.get(msg, ""), **model_context(jobs.get(bielik)))


@router.post("/anonimizacja/{token}")
async def doc_anon_post(request: Request, token: str):
    doc = _doc_or_404(token)
    form = await request.form()
    action = str(form.get("action", "zapisz"))
    if action == "usun":
        store.delete_doc(token)
        return RedirectResponse("/anonimizacja", status_code=303)
    text, spans, changed = _apply_form(doc["text"], _prepare(doc["spans"]), form, action, letter=False, keep=doc.get("keep", []))
    doc.update(text=text, spans=spans, finalized=False)
    if action == "zatwierdz":
        if rd.undecided(spans):
            store.save_doc(token, doc)
            return _doc_page(request, token, doc, error=f"Bez decyzji: {len(rd.undecided(spans))} fragm. Zdecyduj o każdym "
                             "fragmencie albo użyj przycisku „Zaczernij wszystkie bez decyzji”.")
        _, found = _finals(text, spans, ["zanonimizowana"])
        if found:
            store.save_doc(token, doc)
            return _doc_page(request, token, doc, error="Kontrola wycieków zatrzymała eksport: " + "; ".join(found))
        doc["finalized"] = True
        store.save_doc(token, doc)
        return RedirectResponse(f"/anonimizacja/{token}?msg=zatwierdzono", status_code=303)
    store.save_doc(token, doc)
    if action == "model":
        jid = start_doc_model(token)
        return RedirectResponse(f"/anonimizacja/{token}?bielik={jid}" if jid else f"/anonimizacja/{token}", status_code=303)
    return RedirectResponse(f"/anonimizacja/{token}?msg={'nowa' if changed else 'zapamietano' if form.get('pamiec') else 'zapisano'}",
                            status_code=303)


# ---- T25: remember a decision for next documents --------------------------------------------------------------------

BACK = re.compile(r"/sprawy/(\d+)/anonimizacja|/anonimizacja/([\w-]+)")


@router.post("/pamiec")
async def remember(request: Request):
    """Button „Zapamiętaj …” of one fragment (pamiec = allow|redact|tajemnica:<span id>, powrot = screen URL). Stores the
    rule in udip.learning, then saves the whole form on that screen as „Zapisz decyzje” does."""
    from udip import learning
    form = await request.form()
    m = BACK.fullmatch(str(form.get("powrot") or ""))
    act, _, sid = str(form.get("pamiec") or "").partition(":")
    if not m or act not in ("allow", "redact", "tajemnica"):
        raise HTTPException(400, "Nieprawidłowe żądanie.")
    case_id = int(m.group(1)) if m.group(1) else None
    if case_id is not None:
        _, draft = _case_draft(case_id)
        spans = (draft or {}).get("spans") or []
    else:
        spans = _doc_or_404(m.group(2))["spans"]
    span = next((s for s in spans if s.get("id") == sid), None)
    if span is None:
        raise HTTPException(404, "Nie ma takiego fragmentu. Odśwież stronę.")
    category = "TAJEMNICA" if act == "tajemnica" else span.get("type") or ""
    learning.remember(span["text"], "allow" if act == "allow" else "redact", category, case_id, clerk(request))
    if case_id is not None:
        return await case_anon_post(request, case_id)
    return await doc_anon_post(request, m.group(2))


@router.get("/anonimizacja/{token}/eksport/{name}")
def doc_export(request: Request, token: str, name: str):
    version, ext = _split_name(name)
    if version != "zanonimizowana":
        raise HTTPException(404)
    doc = _doc_or_404(token)
    if not doc.get("finalized"):
        raise HTTPException(409, "Najpierw zatwierdź anonimizację.")
    return _file(doc["text"], doc["spans"], version, ext, Path(doc["filename"]).stem or "dokument", clerk(request))
