"""Archiwum / Baza wiedzy (T17): BM25 search over past cases and uploaded laws/orders, imports that the next search uses."""
from __future__ import annotations

import json
import re
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import services, store
from app.common import render
from udip import learning
from udip.ingest import IngestError, guess_date
from udip.search import Archive

router = APIRouter()

PARA = re.compile(r"(?m)^[ \t]*§[ \t]*(\d+[a-z]?)\.?")


def law_chunks(law: dict) -> list[dict]:
    """One searchable record per § of a law/order (the whole text when it has no §), as Archive records."""
    text = law.get("text") or law.get("request_text") or ""
    marks = list(PARA.finditer(text))
    parts: list[tuple[str, str]] = []
    if marks:
        head = text[:marks[0].start()].strip()
        if head:
            parts.append(("", head))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            parts.append((m.group(1), text[m.start():end].strip()))
    else:
        words = text.split()
        parts = [("", " ".join(words[i:i + 200])) for i in range(0, len(words), 200)] or [("", "")]
    lid = str(law["id"])
    return [{"id": f"{lid}#{n or i}", "law_id": lid, "para": n, "title": f"{law['title']}{' § ' + n if n else ''}",
             "request_text": "", "response_text": body, "date": (law.get("created_at") or "")[:10], "departments": []}
            for i, (n, body) in enumerate(parts)]


@lru_cache(maxsize=4)
def _law_index(key: tuple) -> tuple[Archive, dict]:
    chunks = [c for law in store.law_records() for c in law_chunks(law)]
    return Archive(chunks), {c["id"]: c for c in chunks}


def law_index() -> tuple[Archive, dict]:
    laws = store.law_records()
    return _law_index(tuple((str(x["id"]), len(x.get("text") or "")) for x in laws))


def search_cases(q: str, year: int | None, dep: str, k: int = 10) -> list[dict]:
    arch = services.archive()
    if q:
        res = arch.search(q, k=len(arch.records) or 1)
    else:
        res = [{"id": r["id"], "date": r.get("date"), "title": r.get("title"), "departments": r.get("departments") or [],
                "score": None, "matched_terms": [], "response_excerpt": (r.get("response_text") or "")[:300]}
               for r in sorted(arch.records, key=lambda r: r.get("date") or "", reverse=True)]
    if year:
        res = [r for r in res if str(r.get("date") or "")[:4] == str(year)]
    if dep:
        res = [r for r in res if dep in (r.get("departments") or [])]
    return res[:k] if q else res


def search_laws(q: str, k: int = 5) -> list[dict]:
    if not q:
        return []
    idx, by_id = law_index()
    out = []
    for r in idx.search(q, k=k):
        c = by_id[r["id"]]
        out.append({**r, "law_id": c["law_id"], "para": c["para"], "text": c["response_text"]})
    return out


def _years() -> list[int]:
    return sorted({int(str(r.get("date"))[:4]) for r in store.archive_records() if str(r.get("date") or "")[:4].isdigit()}, reverse=True)


def _page(request: Request, q: str = "", rok: str = "", wydzial: str = "", **extra):
    year = int(rok) if rok.isdigit() else None
    laws = store.law_records()
    return render(request, "archiwum.html", title="Archiwum", q=q, rok=year, wydzial=wydzial,
                  cases=search_cases(q, year, wydzial), law_hits=search_laws(q), years=_years(),
                  departments=services.departments(), n_cases=len(store.archive_records()), laws=laws,
                  n_chunks=sum(len(law_chunks(x)) for x in laws), memory=learning.memory_stats(), **extra)


@router.get("/archiwum")
def archiwum(request: Request, q: str = "", rok: str = "", wydzial: str = "", dodano: str = ""):
    return _page(request, q.strip(), rok, wydzial, added=[x for x in dodano.split(",") if x])


@router.get("/archiwum/sprawa/{case_id:path}")
def archive_case(request: Request, case_id: str):
    rec = next((r for r in store.archive_records() if r["id"] == case_id), None)
    if rec is None:
        raise HTTPException(404)
    in_register = store.case_by_number(case_id)
    return render(request, "archiwum_sprawa.html", title=case_id, rec=rec, names=services.department_names(), in_register=in_register)


@router.get("/archiwum/przepis/{law_id}")
def law_page(request: Request, law_id: str):
    law = next((x for x in store.law_records() if str(x["id"]) == law_id), None)
    if law is None:
        raise HTTPException(404)
    return render(request, "archiwum_przepis.html", title=law["title"], law=law, chunks=law_chunks(law))


async def _read(up) -> dict:
    data = await up.read()
    return services.read_upload(up.filename, data)


@router.post("/archiwum/import")
async def import_cases(request: Request):
    """Either one case (id, date, title, departments, request/response as files or text) or many files named
    <id>_wniosek.* / <id>_odpowiedz.* (a whole folder)."""
    f = await request.form()
    files = [u for u in f.getlist("pliki") if getattr(u, "filename", "")]
    if files:
        return await _import_folder(request, files)
    cid = str(f.get("id") or "").strip()
    req_text, resp_text = str(f.get("request_text") or "").strip(), str(f.get("response_text") or "").strip()
    try:
        for field, target in (("request_file", "req"), ("response_file", "resp")):
            up = f.get(field)
            if up is not None and getattr(up, "filename", ""):
                t = (await _read(up))["text"]
                req_text, resp_text = (t, resp_text) if target == "req" else (req_text, t)
    except IngestError as e:
        return _page(request, import_error=str(e))
    if not cid or not (req_text or resp_text):
        return _page(request, import_error="Podaj numer sprawy i treść wniosku albo odpowiedzi.")
    deps = [d.strip().upper() for d in re.split(r"[,; ]+", str(f.get("departments") or "")) if d.strip()]
    known = {d["id"].upper(): d["id"] for d in services.departments()}
    deps = [known.get(d, d) for d in deps]
    date_ = str(f.get("date") or "").strip() or guess_date(resp_text or req_text) or ""
    title = str(f.get("title") or "").strip() or " ".join((req_text or resp_text).split())[:120]
    store.add_archive(cid, date_, title, req_text, resp_text, deps, "urzędnik")
    return RedirectResponse(f"/archiwum?q={quote(title[:80])}&dodano={quote(cid)}", status_code=303)


async def _import_folder(request: Request, files):
    from udip.ingest import import_archive
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "archiwum"
        folder.mkdir()
        for up in files:
            name = Path(up.filename).name
            if name == "meta.json" or name.lower().endswith(services.ALLOWED):
                (folder / name).write_bytes(await up.read())
        out = Path(tmp) / "out.jsonl"
        import_archive(folder, out)
        recs = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    for r in recs:
        store.add_archive(r["id"], r.get("date") or "", r.get("title") or r["id"], r.get("request_text", ""),
                          r.get("response_text", ""), r.get("departments") or [], "import")
    if not recs:
        return _page(request, import_error="Nie zaimportowano żadnej sprawy. Pliki: <numer>_wniosek.pdf i <numer>_odpowiedz.pdf (PDF, DOCX, ODT, TXT).")
    return RedirectResponse(f"/archiwum?dodano={quote(','.join(r['id'] for r in recs))}", status_code=303)


@router.post("/archiwum/przepisy")
async def import_law(request: Request):
    f = await request.form()
    up = f.get("plik")
    if up is None or not getattr(up, "filename", ""):
        return _page(request, law_error="Wybierz plik aktu (PDF, DOCX, ODT, TXT).")
    try:
        doc = await _read(up)
    except IngestError as e:
        return _page(request, law_error=str(e))
    title = str(f.get("title") or "").strip() or Path(up.filename).stem
    lid = store.add_law(title, doc["file"], doc["text"])
    learning.add_law(doc["text"], title, source_file=doc["file"])  # T25: legal_hits on the case screens
    n = len(law_chunks({"id": lid, "title": title, "text": doc["text"]}))
    return _page(request, law_added={"id": lid, "title": title, "chunks": n, "warning": doc.get("warning")})


RESET = {"pii": "Zapomniano decyzje o danych osobowych.", "routing": "Zapomniano korekty wydziałów.",
         "legal": "Usunięto przepisy z podpowiedzi do spraw.", "all": "Wyczyszczono całą pamięć instytucjonalną."}


@router.post("/archiwum/pamiec/reset")
async def memory_reset(request: Request):
    """T25: forget one kind of learned memory (pii, routing, legal, all)."""
    f = await request.form()
    kind = str(f.get("rodzaj") or "")
    if kind not in RESET:
        raise HTTPException(400, "Nieznany rodzaj pamięci.")
    learning.reset(kind)
    return _page(request, memory_message=RESET[kind])
