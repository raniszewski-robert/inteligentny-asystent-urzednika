"""Sprawa (T06): one case – deadlines, questions with departments, similar cases, department answers, drafts, history."""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

from app import jobs, services, store
from app.routes.model import context as model_context
from app.common import clerk, render, today
from udip import db, dispatch, learning, security
from udip.ingest import IngestError
from udip.register import STATUSES, URGENCY_LABEL, rows as register_rows

router = APIRouter()


def _case_or_404(case_id: int) -> dict:
    c = store.get_case(case_id)
    if c is None:
        raise HTTPException(404)
    return c


def _request_text(c: dict) -> tuple[str, str]:
    """(text, source): the stored request document, else the request text of the same number in the archive."""
    docs = store.documents(c["id"], "request")
    if docs and (docs[-1].get("text") or "").strip():
        return docs[-1]["text"], "document"
    for r in store.archive_records():
        if r["id"] == c["number"] and (r.get("request_text") or "").strip():
            return r["request_text"], "archive"
    return "", ""


def _questions(c: dict) -> list[dict]:
    an = c.get("analysis") or {}
    chosen = an.get("chosen_departments") or {}
    names = services.department_names()
    out = []
    for q in an.get("questions") or []:
        ids = chosen.get(str(q["no"])) or ([q["routing"][0]["department"]] if q.get("routing") else [])
        out.append({"no": q["no"], "text": q["text"], "departments": [(d, names.get(d, d)) for d in ids],
                    "alternatives": [r for r in q.get("routing") or [] if r["department"] not in ids]})
    return out


def _dispatch_blocks(c: dict) -> list[dict]:
    """One block per routed department: copy-ready message, sub-deadline, and whether it was marked as sent (T24)."""
    names = services.department_names()
    sent = {d["department"]: d for d in db.dispatches(c["id"])}
    out = []
    if not c.get("received"):
        return out
    for dep, qs in dispatch.dispatch_questions(c).items():
        subject, text, sub, legal = dispatch.message_text(c, dep, qs, today=today())
        out.append({"department": dep, "name": names.get(dep, dep), "questions": qs, "subject": subject,
                    "message": f"Temat: {subject}\n\n{text}", "sub_deadline": sub, "legal_due": legal, "sent": sent.get(dep)})
    return out


def _page(request: Request, c: dict, **extra):
    row = register_rows([store.to_request(c)], today())[0]
    docs = store.documents(c["id"])
    text, source = _request_text(c)
    legal = []
    if text:
        try:
            legal = learning.legal_hits(text)
        except Exception:
            legal = []
    return render(request, "sprawa.html", title=c["number"], case=c, row=row, statuses=STATUSES, urgency_label=URGENCY_LABEL,
                  questions=_questions(c), analysis=c.get("analysis") or {}, request_docs=[d for d in docs if d["kind"] == "request"],
                  answers=[d for d in docs if d["kind"] == "dept_answer"], other_docs=[d for d in docs if d["kind"] not in ("request", "dept_answer")],
                  history=store.history(c["id"]), drafts=store.drafts(c["id"]), letter_types=services.letter_types(),
                  departments=services.departments(), names=services.department_names(), can_analyze=bool(text),
                  request_source=source, dispatches=_dispatch_blocks(c), legal=legal,
                  **(model_context(jobs.running(f"sprawa-analiza:{c['id']}")) | extra))


@router.get("/sprawy/{case_id}")
def case_page(request: Request, case_id: int):
    return _page(request, _case_or_404(case_id))


@router.post("/sprawy/{case_id}/analiza")
def analyze_case(request: Request, case_id: int):
    c = _case_or_404(case_id)
    text, source = _request_text(c)
    if not text:
        return _page(request, c, error="Brak treści wniosku. Dodaj wniosek przez ekran „Nowy wniosek”.")
    an = services.run_analysis(text, exclude_id=c["number"])
    an["chosen_departments"] = {str(q["no"]): [q["routing"][0]["department"]] for q in an["questions"] if q.get("routing")}
    if source == "archive":
        store.add_document(case_id, "request", f"{c['number']} – wniosek (archiwum)", text)
    fields: dict = {"analysis": an}
    if not c.get("departments"):
        deps: list[str] = []
        for ids in an["chosen_departments"].values():
            deps += [d for d in ids if d not in deps]
        fields["departments"] = deps
    store.update_case(case_id, **fields)
    services.start_case_analysis(case_id, text, exclude_id=c["number"])
    return RedirectResponse(f"/sprawy/{case_id}", status_code=303)


@router.post("/sprawy/{case_id}/odpowiedzi")
async def upload_answers(request: Request, case_id: int):
    c = _case_or_404(case_id)
    f = await request.form()
    chosen = str(f.get("department") or "")
    known = {d["id"] for d in services.departments()}
    report = []
    files = [u for u in f.getlist("pliki") if getattr(u, "filename", "")]
    if not files:
        return _page(request, c, error="Wybierz co najmniej jeden plik odpowiedzi wydziału.")
    for up in files:
        data = await up.read()
        try:
            doc = services.read_upload(up.filename, data)
        except IngestError as e:
            report.append({"file": up.filename, "error": str(e)})
            continue
        dep = chosen if chosen in known else services.detect_department(up.filename, doc["text"])
        path = services.upload_path(doc["stored"])
        store.add_document(case_id, "dept_answer", doc["file"], doc["text"], department=dep or None,
                           quality=doc.get("quality"), path=str(path) if path else None)
        if dep:
            db.set_dispatch_answered(case_id, dep)
        sec = doc.get("security") or {}
        if security.count(sec):
            security.log_scan(sec, case_id)
        report.append({"file": doc["file"], "department": dep, "auto": not chosen, "warning": doc.get("warning"),
                       "security": services.security_lines(sec)})
    return _page(request, store.get_case(case_id), upload_report=report)


@router.post("/sprawy/{case_id}/dokumenty/{doc_id}/wydzial")
def set_document_department(case_id: int, doc_id: int, department: str = Form("")):
    """Correct the department of an uploaded answer."""
    _case_or_404(case_id)
    known = {d["id"] for d in services.departments()}
    dep = department if department in known else None
    store.set_document_department(case_id, doc_id, dep)
    if dep:
        db.set_dispatch_answered(case_id, dep)
    return RedirectResponse(f"/sprawy/{case_id}#odpowiedzi", status_code=303)


@router.post("/sprawy/{case_id}/trasowanie")
def set_question_department(case_id: int, question_no: int = Form(...), department: str = Form("")):
    """Change the routed department of one question and log the correction in udip.learning (CONTRACTS §5)."""
    c = _case_or_404(case_id)
    an = dict(c.get("analysis") or {})
    qs = an.get("questions") or []
    q = next((x for x in qs if int(x["no"]) == question_no), None)
    if q is None:
        raise HTTPException(404, "Nie ma takiego pytania w analizie sprawy.")
    known = {d["id"] for d in services.departments()}
    dep = department.strip()
    if dep and dep not in known:
        raise HTTPException(400, "Nieznany wydział.")
    chosen = dict(an.get("chosen_departments") or {})
    chosen[str(question_no)] = [dep] if dep else []
    an["chosen_departments"] = chosen
    deps: list[str] = []
    for item in qs:
        ids = chosen.get(str(item["no"]))
        if ids is None:
            ids = [item["routing"][0]["department"]] if item.get("routing") else []
        for d in ids:
            if d not in deps:
                deps.append(d)
    store.update_case(case_id, analysis=an, departments=deps)
    if dep:
        try:
            predicted = q["routing"][0]["department"] if q.get("routing") else ""
            learning.log_routing(q["text"], predicted, dep, case_id)
        except Exception:
            pass
    return RedirectResponse(f"/sprawy/{case_id}", status_code=303)


def _dispatch_or_404(case_id: int, dept: str) -> tuple[dict, list[dict]]:
    c = _case_or_404(case_id)
    groups = dispatch.dispatch_questions(c)
    if dept not in groups:
        raise HTTPException(404, "Ta komórka nie ma pytań w tej sprawie.")
    return c, groups[dept]


@router.get("/sprawy/{case_id}/przekazanie/{dept}.docx")
def dispatch_form(case_id: int, dept: str):
    """Reply form for one department: [Ad N] Pytanie / Odpowiedź wydziału blocks (tier 1 when uploaded back)."""
    c, qs = _dispatch_or_404(case_id, dept)
    p = dispatch.packet(c, dept, qs, today=today())
    return Response(p["reply_form_docx"], media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{p["filename"]}"'})


@router.get("/sprawy/{case_id}/przekazanie/{dept}")
def dispatch_message(case_id: int, dept: str):
    c, qs = _dispatch_or_404(case_id, dept)
    return PlainTextResponse(dispatch.packet(c, dept, qs, today=today())["message_text"])


@router.post("/sprawy/{case_id}/przekazane")
def dispatch_sent(request: Request, case_id: int, department: str = Form(...)):
    """Mark the department's questions as sent: records department_dispatches; a case with no action yet moves to status b."""
    c, qs = _dispatch_or_404(case_id, department)
    sub = dispatch.message_text(c, department, qs, today=today())[2]
    db.add_dispatch(case_id, department, qs, sub)
    if c.get("status") == "a_brak_dzialan":
        store.set_status(case_id, "b_zapytania_wyslane", clerk(request), note=f"Przekazano do {department}")
    return RedirectResponse(f"/sprawy/{case_id}#przekazanie", status_code=303)
