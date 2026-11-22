"""Projekt pisma (T07): letter draft from department answers, report panel, 'Ad' editor, letter types, versions."""
from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import b2_redact as rd
from app import jobs
from app.routes.model import context as model_context
from app import b2_store as store
from app.common import render, today
from udip.analyze import split_questions
from udip.draft import LETTER_TYPES, check_numbers, make_draft

router = APIRouter()

LTYPES = {k: v["label"] for k, v in LETTER_TYPES.items() if not k.startswith("_")}
# Type-specific fields: name -> (label, letter types that use it). Every type also takes scope and sign.
TYPE_FIELDS = {
    "entity": ("Właściwy podmiot", ["odeslanie_art_4_ust_3"]),
    "entity_contact": ("Adres i e-mail podmiotu", ["odeslanie_art_4_ust_3"]),
    "bip_url": ("Adres strony w BIP", ["odeslanie_bip"]),
    "until": ("Nowy termin odpowiedzi", ["przedluzenie", "doprecyzowanie"]),
    "reason": ("Uzasadnienie", ["przedluzenie", "doprecyzowanie", "przetworzona"]),
}
PARAMS = ["ltype", "scope", "sign", *TYPE_FIELDS]
DEFAULT_SIGN = "[podpis]"


def _case_or_404(case_id: int) -> dict:
    c = store.get_case(case_id)
    if c is None:
        raise HTTPException(404)
    return c


def _received(case: dict) -> date:
    try:
        return date.fromisoformat(str(case.get("received"))[:10])
    except ValueError:
        return today()


def generate(case: dict, params: dict, assignments: dict | None = None) -> tuple[int, dict]:
    """make_draft for the case with the form parameters; saves a new version. Returns (version, result).
    The clerk's sentence assignments (report["assignments"]) carry over from the latest version; `assignments` adds to them."""
    inp = store.case_inputs(case)
    latest = store.get_draft(case["id"])
    asg = dict((latest or {}).get("report", {}).get("assignments") or {}) | (assignments or {})
    ltype = params.get("ltype") if params.get("ltype") in LTYPES else "udostepnienie"
    until = date.fromisoformat(params["until"]) if params.get("until") else None
    from app import settings
    mode = "llm" if params.get("mode") == "llm" and ltype == "udostepnienie" and settings.llm_on() else "template"
    res = make_draft(inp["request"], inp["answers"], _received(case), ltype, number=inp["number"], today=today(),
                     mode=mode, provider=settings.provider_arg(), sign=params.get("sign") or DEFAULT_SIGN, extension_until=until,
                     reason=params.get("reason", ""), scope=params.get("scope", ""), entity=params.get("entity", ""),
                     entity_contact=params.get("entity_contact", ""), bip_url=params.get("bip_url", ""), assignments=asg or None)
    report = dict(res["report"], params={k: params.get(k, "") for k in PARAMS} | {"ltype": ltype}, assignments=asg)
    v = store.save_draft(case["id"], ltype, res["text"], res["spans"], report)
    return v, res


AD_START = re.compile(r"(?m)^\s*Ad\s+\d{1,3}\b")
AD_END = re.compile(r"(?m)^\s*(Łączę wyrazy|Z poważaniem|\[podpis\]|Podstawa prawna)")


def _ad_part(text: str) -> str:
    """The answer paragraphs only (first „Ad N” up to the closing formula): the number check does not look at the
    addressee header (flat numbers, postal codes) or the signature and legal basis."""
    m = AD_START.search(text)
    if not m:
        return text
    end = AD_END.search(text, m.end())
    return text[m.start():end.start() if end else len(text)]


def save_edit(case: dict, base: dict, text: str) -> int | None:
    """Clerk's edited text as a new version (None when nothing changed). Spans re-detected, decisions kept,
    numbers that are new in this edit and absent from the department answers are reported."""
    text = text.replace("\r\n", "\n").strip("\n")
    if text == base["text"].strip("\n"):
        return None
    spans = rd.redetect(base["text"], base["spans"], text, letter=True)
    report = dict(base["report"])
    answers = [a for _, a in store.case_inputs(case)["answers"]]
    if answers and base["ltype"] == "udostepnienie":
        before = set(check_numbers([_ad_part(base["text"])], answers))
        report["number_check_edit"] = [n for n in check_numbers([_ad_part(text)], answers) if n not in before]
    report.update(edited=True, based_on=base["version"], anonymization_suggestions=len(spans))
    return store.save_draft(case["id"], base["ltype"], text, spans, report)


def _llm_on() -> bool:
    from app import settings
    return settings.llm_on()


def _view(request: Request, case: dict, draft: dict, *, saved: int | None = None, unchanged: bool = False,
          error: str = "", form: dict | None = None, job: dict | None = None):
    inp = store.case_inputs(case)
    rep = draft["report"]
    params = {k: "" for k in PARAMS} | (rep.get("params") or {}) | {"ltype": draft["ltype"]} | (form or {})
    params["sign"] = params.get("sign") or DEFAULT_SIGN
    num_bad = list(rep.get("number_check") or []) + list(rep.get("number_check_template") or []) + list(rep.get("number_check_edit") or [])
    return render(request, "projekt.html", title=f"Projekt pisma {case.get('number', '')}", case=case, draft=draft,
                  report=rep, versions=store.list_drafts(case["id"]), ltypes=LTYPES, type_fields=TYPE_FIELDS,
                  params=params, questions=split_questions(inp["request"]) if inp["request"] else [],
                  answers=inp["answers"], num_bad=num_bad, saved=saved, unchanged=unchanged, error=error,
                  undecided=len(rd.undecided(draft["spans"])), llm_on=_llm_on(), **model_context(job))


@router.get("/sprawy/{case_id}/projekt")
def projekt(request: Request, case_id: int, wersja: int | None = None, zapisano: int | None = None, bez_zmian: int = 0,
            ltype: str = "", bielik: str = ""):
    case = _case_or_404(case_id)
    job = jobs.get(bielik) if bielik else None
    if job and job["status"] == "done" and (job.get("result") or {}).get("target"):
        return RedirectResponse(job["result"]["target"], status_code=303)
    if ltype and wersja is None:
        # "Generuj projekt" on the case page: a new version unless the latest one already has this type
        latest = store.get_draft(case_id)
        if latest is not None and latest["ltype"] == ltype:
            return RedirectResponse(f"/sprawy/{case_id}/projekt?wersja={latest['version']}", status_code=303)
        v, _ = generate(case, {"ltype": ltype})
        return RedirectResponse(f"/sprawy/{case_id}/projekt?wersja={v}&zapisano={v}", status_code=303)
    if not store.list_drafts(case_id):
        generate(case, {"ltype": "udostepnienie"})
    draft = store.get_draft(case_id, wersja)
    if draft is None:
        raise HTTPException(404)
    return _view(request, case, draft, saved=zapisano, unchanged=bool(bez_zmian), job=job)


@router.post("/sprawy/{case_id}/projekt")
def projekt_post(request: Request, case_id: int, action: str = Form("zapisz"), text: str = Form(""),
                 base_version: int | None = Form(None), ltype: str = Form("udostepnienie"), scope: str = Form(""),
                 sign: str = Form(""), entity: str = Form(""), entity_contact: str = Form(""), bip_url: str = Form(""),
                 until: str = Form(""), reason: str = Form(""), mode: str = Form("template")):
    case = _case_or_404(case_id)
    url = f"/sprawy/{case_id}/projekt"
    if mode == "llm":
        action = "generuj"
    if action == "generuj":
        form = {"ltype": ltype, "scope": scope.strip(), "sign": sign.strip(), "entity": entity.strip(),
                "entity_contact": entity_contact.strip(), "bip_url": bip_url.strip(), "until": until.strip(), "reason": reason.strip(), "mode": mode}
        if ltype not in LTYPES:
            form["ltype"] = "udostepnienie"
        if form["until"]:
            try:
                date.fromisoformat(form["until"])
            except ValueError:
                draft = store.get_draft(case_id) or store.get_draft(case_id, generate(case, {"ltype": "udostepnienie"})[0])
                return _view(request, case, draft, error="Nowy termin podaj jako datę (RRRR-MM-DD).", form=form)
        if form.get("mode") == "llm" and _llm_on():
            from app import settings

            def work() -> dict:
                v, res = generate(store.get_case(case_id) or case, form)
                return {"target": f"{url}?wersja={v}&zapisano={v}",
                        "message": f"{settings.model_name()} zredagował akapity." if res["report"].get("mode_used") == "llm" else
                                   f"{settings.model_name()} nie dał poprawnych akapitów – nowa wersja z szablonu."}
            jid = jobs.submit(f"projekt:{case_id}", "odswiez", work)
            latest = store.get_draft(case_id)
            return RedirectResponse(f"{url}?bielik={jid}" + (f"&wersja={latest['version']}" if latest else ""), status_code=303)
        v, _ = generate(case, form)
        return RedirectResponse(f"{url}?wersja={v}&zapisano={v}", status_code=303)
    base = store.get_draft(case_id, base_version) if base_version else store.get_draft(case_id)
    if base is None:
        raise HTTPException(404)
    v = save_edit(case, base, text)
    if v is None:
        return RedirectResponse(f"{url}?wersja={base['version']}&bez_zmian=1", status_code=303)
    return RedirectResponse(f"{url}?wersja={v}&zapisano={v}", status_code=303)


@router.post("/sprawy/{case_id}/projekt/przypisz")
def projekt_assign(case_id: int, zdanie: str = Form(...), ad: str = Form(...), base_version: int | None = Form(None)):
    """The clerk picks the 'Ad' for a sentence the rules left unassigned ('plik#nr' -> question; 0 = leave the sentence out).
    Regenerates the draft with the parameters of the base version."""
    case = _case_or_404(case_id)
    base = store.get_draft(case_id, base_version) if base_version else store.get_draft(case_id)
    if base is None:
        raise HTTPException(404)
    if not ad.strip().isdigit():
        return RedirectResponse(f"/sprawy/{case_id}/projekt?wersja={base['version']}", status_code=303)
    params = dict(base["report"].get("params") or {}, ltype=base["ltype"])
    v, _ = generate(case, params, {zdanie: int(ad)})
    return RedirectResponse(f"/sprawy/{case_id}/projekt?wersja={v}&zapisano={v}", status_code=303)
