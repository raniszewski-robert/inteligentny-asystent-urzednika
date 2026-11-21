"""Wczytywanie dokumentów urzędnika: PDF, DOCX, ODT, TXT → czysty tekst (+ OCR dla skanów).

Zależności (licencje): pdfplumber (MIT), pypdf (BSD-3), python-docx (MIT), pypdfium2 (Apache-2.0/BSD-3, render stron do OCR),
Tesseract CLI z językiem `pol` (Apache-2.0). Bez PyMuPDF (AGPL) i bez pdftoppm (Poppler, GPL).

CLI i selftest: .claude/skills/udip-dane-i-zrodla/scripts/ingest.py
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

MIN_CHARS_PER_PAGE = 40  # mniej → strona prawdopodobnie jest skanem


class IngestError(RuntimeError):
    pass


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("­", "").replace("\xa0", " ")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)        # dzielenie wyrazów na końcu linii
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ocr_pdf(path: Path, lang: str = "pol") -> str:
    if not shutil.which("tesseract"):
        raise IngestError("PDF wygląda na skan, a tesseract nie jest zainstalowany (apt install tesseract-ocr tesseract-ocr-pol).")
    try:
        import pypdfium2 as pdfium
    except ImportError as e:
        raise IngestError("Do OCR potrzebny jest pypdfium2 (pip install pypdfium2).") from e
    pdf = pdfium.PdfDocument(str(path))
    out = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(len(pdf)):
            img = pdf[i].render(scale=2).to_pil()  # ok. 144 dpi × 2
            png = Path(td) / f"p{i}.png"
            img.save(png)
            r = subprocess.run(["tesseract", str(png), "-", "-l", lang], capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                raise IngestError(f"tesseract: {r.stderr.strip()[:200]}")
            out.append(r.stdout)
    return "\n\n".join(out)


def read_pdf(path: Path, ocr: str = "auto") -> tuple[str, dict]:
    from pypdf import PdfReader
    try:
        reader = PdfReader(str(path))
    except Exception as e:  # uszkodzony PDF
        raise IngestError(f"Nie da się otworzyć PDF: {e}") from e
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as e:
            raise IngestError("PDF jest zaszyfrowany hasłem.") from e
    try:  # pdfplumber (MIT) lepiej skleja litery rozstrzelone przez kerning („Komunik acji”); pypdf jako zapas
        import pdfplumber
        with pdfplumber.open(str(path)) as pl:
            pages = [(pg.extract_text(x_tolerance=1.5) or "") for pg in pl.pages]
    except Exception:
        pages = [(p.extract_text() or "") for p in reader.pages]
    meta = {"pages": len(pages), "ocr": False}
    weak = sum(1 for t in pages if len(t.strip()) < MIN_CHARS_PER_PAGE)
    if ocr == "always" or (ocr == "auto" and pages and weak / len(pages) > 0.5):
        meta["ocr"] = True
        return ocr_pdf(path), meta
    return "\n\n".join(pages), meta


def read_docx(path: Path) -> tuple[str, dict]:
    import docx
    try:
        d = docx.Document(str(path))
    except Exception as e:
        raise IngestError(f"Nie da się otworzyć DOCX: {e}") from e
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(parts), {"paragraphs": len(d.paragraphs), "tables": len(d.tables)}


def read_odt(path: Path) -> tuple[str, dict]:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("content.xml"))
    ns = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
    paras = ["".join(el.itertext()) for el in root.iter() if el.tag in (ns + "p", ns + "h")]
    return "\n".join(paras), {"paragraphs": len(paras)}


def text_quality(text: str) -> float:
    """Udział tokenów wyglądających na słowa lub liczby. Rękopis po OCR daje ok. 0.0–0.2, pisma urzędowe > 0.6."""
    toks = re.findall(r"\S+", text)
    if not toks:
        return 0.0
    word = re.compile(r"[(„\"]?[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]{2,}[.,;:?!)”\"]*")
    num = re.compile(r"[(]?[\d.,/:-]+[).,;:]?")

    def ok(t: str) -> bool:
        if num.fullmatch(t):
            return True
        if not word.fullmatch(t) or not re.search(r"[aeiouyąęóAEIOUYĄĘÓ]", t):
            return False
        return not re.search(r"(.)\1\1", t)  # „EEEE”, „HHHH” = śmieci OCR
    return round(sum(map(ok, toks)) / len(toks), 2)


def read_any(path: Path, ocr: str = "auto") -> dict:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        text, meta = read_pdf(path, ocr)
    elif ext == ".docx":
        text, meta = read_docx(path)
    elif ext == ".odt":
        text, meta = read_odt(path)
    elif ext in (".txt", ".md", ".eml"):
        raw = path.read_bytes()
        for enc in ("utf-8", "cp1250", "iso-8859-2"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        meta = {"encoding": enc}
    elif ext == ".doc":
        raise IngestError("Stary format .doc: zapisz jako .docx albo PDF (albo: soffice --headless --convert-to docx).")
    else:
        raise IngestError(f"Nieobsługiwany format {ext}")
    text = clean(text)
    if not text:
        raise IngestError("Pusty dokument po odczycie.")
    q = text_quality(text)
    warn = None
    if q < 0.5:  # próg z danych UMB: rękopis 0.36, pisma 0.78–0.90
        warn = ("Niska jakość tekstu (prawdopodobnie rękopis lub słaby skan): wpisz treść wniosku ręcznie "
                "albo użyj modelu z obsługą obrazu. Nie przekazuj tego tekstu dalej bez sprawdzenia.")
    return {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16], "chars": len(text), **meta,
            "quality": q, "warning": warn, "text": text, "security": _security(path, text)}


def _security(path: Path, text: str) -> dict:
    """udip.security.scan (T26); a scanner error never stops reading the file."""
    try:
        from . import security
        return security.scan(path, text)
    except Exception as e:
        return {"hidden_text": [], "images": [], "injection": [], "notes": [f"Kontrola bezpieczeństwa pominięta ({type(e).__name__})."]}


DATE_RX = re.compile(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b")
MONTHS = {"stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5, "czerwca": 6, "lipca": 7, "sierpnia": 8,
          "września": 9, "października": 10, "listopada": 11, "grudnia": 12}
DATE_WORDS = re.compile(r"\b(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})")


def guess_date(text: str) -> str | None:
    head = text[:600]
    for rx, conv in ((DATE_WORDS, lambda m: (int(m[3]), MONTHS[m[2]], int(m[1]))), (DATE_RX, lambda m: (int(m[3]), int(m[2]), int(m[1])))):
        m = rx.search(head)
        if m:
            try:
                return date(*conv(m)).isoformat()
            except ValueError:
                pass
    return None


def import_archive(folder: Path, out: Path) -> int:
    """Katalog archiwum: pary <id>_wniosek.* i <id>_odpowiedz.* albo pojedyncze pliki. Plik meta.json (opcjonalny)
    {"<id>": {"departments": [...], "date": "...", "title": "..."}} uzupełnia metadane."""
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8")) if (folder / "meta.json").exists() else {}
    groups: dict[str, dict] = {}
    errors = 0
    for f in sorted(folder.iterdir()):
        if f.name == "meta.json" or f.is_dir() or f.name.startswith("."):
            continue
        m = re.match(r"(.+?)[_-](wniosek|odpowiedz|odpowiedź|request|response)$", f.stem, re.I)
        key, role = (m.group(1), "response" if m.group(2).lower().startswith(("odp", "resp")) else "request") if m else (f.stem, "request")
        try:
            doc = read_any(f)
        except IngestError as e:
            print(f"POMINIĘTO {f.name}: {e}", file=sys.stderr)
            errors += 1
            continue
        g = groups.setdefault(key, {"id": key})
        g[f"{role}_text"] = doc["text"]
        g.setdefault("files", []).append(f.name)
        if role == "request" and "date" not in g:
            g["date"] = guess_date(doc["text"])
    with out.open("w", encoding="utf-8") as fh:
        for key, g in groups.items():
            g.update(meta.get(key, {}))
            g.setdefault("title", (g.get("request_text") or "")[:120].replace("\n", " "))
            fh.write(json.dumps(g, ensure_ascii=False) + "\n")
    print(f"Zaimportowano {len(groups)} spraw do {out} (błędów: {errors})", file=sys.stderr)
    return len(groups)
