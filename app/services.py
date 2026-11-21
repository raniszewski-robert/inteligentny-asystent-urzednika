"""Calls into the core shared by the case screens: archive index, departments, analysis, file reading."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

from udip import config
from udip.analyze import analyze, load_departments
from udip.search import Archive

from app import store
from app.common import today

ALLOWED = (".pdf", ".docx", ".odt", ".txt")


@lru_cache(maxsize=1)
def departments() -> list[dict]:
    return load_departments()


def department_names() -> dict[str, str]:
    return {d["id"]: d["name"] for d in departments()}


_arch: tuple[tuple, Archive] | None = None


def archive() -> Archive:
    """BM25 index over the archive table; rebuilt when the archive changes."""
    global _arch
    recs = store.archive_records()
    key = tuple((r["id"], len(r.get("request_text") or ""), len(r.get("response_text") or "")) for r in recs)
    if _arch is None or _arch[0] != key:
        _arch = (key, Archive(recs))
    return _arch[1]


def run_analysis(text: str, exclude_id: str | None = None) -> dict:
    """Rules or LLM, as the Ustawienia choice decides (default UDIP_PROVIDER); the rule result is always the base."""
    from app import settings
    return analyze(text, archive(), departments(), today(), exclude_id=exclude_id, provider=settings.provider_arg())


def uploads_dir() -> Path:
    d = config.data_dir() / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


SAFE = re.compile(r"[^\w.\- ]+", re.UNICODE)


def save_upload(name: str, data: bytes) -> Path:
    """Keep the original file: uploads/<sha12>_<safe name>."""
    safe = SAFE.sub("_", Path(name).name)[:120] or "plik"
    p = uploads_dir() / f"{hashlib.sha256(data).hexdigest()[:12]}_{safe}"
    if not p.exists():
        p.write_bytes(data)
    return p


def upload_path(token: str) -> Path | None:
    """Resolve a stored upload name sent back by a form; None if it is not a file in uploads/."""
    if not token or "/" in token or "\\" in token or token.startswith("."):
        return None
    p = uploads_dir() / token
    return p if p.is_file() else None


def read_upload(name: str, data: bytes) -> dict:
    """ingest.read_any on an uploaded file. Raises udip.ingest.IngestError with a message for the clerk."""
    from udip.ingest import IngestError, read_any
    if not name.lower().endswith(ALLOWED):
        raise IngestError("Obsługiwane formaty: PDF, DOCX, ODT, TXT.")
    p = save_upload(name, data)
    doc = read_any(p)
    doc["stored"] = p.name
    doc["file"] = Path(name).name
    return doc


SIGN = re.compile(r"^\s*([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)\.\d", re.M)


def detect_department(filename: str, text: str) -> str:
    """Department of a department answer: from the file name (WGK.txt, 'odp WGK.pdf'), the file's reference sign
    in the header ('WGK.1431.77.2026'), or the department's full name in the text. '' when unknown."""
    ids = {d["id"].upper(): d["id"] for d in departments()}
    for tok in re.split(r"[^\wĄĆĘŁŃÓŚŹŻąćęłńóśźż]+", Path(filename).stem):
        if tok.upper() in ids:
            return ids[tok.upper()]
    for m in SIGN.finditer(text[:800]):
        if m.group(1).upper() in ids and m.group(1).upper() != "BKS":
            return ids[m.group(1).upper()]
    low = text.lower()
    hits = [(low.rfind(d["name"].lower()), d["id"]) for d in departments() if d["name"].lower() in low and d["id"] != "BKS"]
    return max(hits)[1] if hits else ""


def letter_types() -> list[tuple[str, str]]:
    from udip.letters import LETTER_TYPES
    return [(k, v.get("label", k)) for k, v in LETTER_TYPES.items() if not k.startswith("_") and isinstance(v, dict)]


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
