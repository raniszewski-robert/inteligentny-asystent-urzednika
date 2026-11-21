"""Wczytywanie dokumentów urzędnika: PDF, DOCX, ODT, TXT → czysty tekst (+ OCR dla skanów).

Zależności (licencje): pdfplumber (MIT), pypdf (BSD-3), python-docx (MIT), pypdfium2 (Apache-2.0/BSD-3, render stron do OCR),
Tesseract CLI z językiem `pol` (Apache-2.0). Bez PyMuPDF (AGPL) i bez pdftoppm (Poppler, GPL).

CLI i selftest: .claude/skills/udip-dane-i-zrodla/scripts/ingest.py
"""
from __future__ import annotations

import hashlib
import json
import os
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


def _tesseract() -> str | None:
    """Tesseract CLI: TESSERACT_CMD from .env (Windows install outside PATH) or `tesseract` on PATH."""
    cmd = os.environ.get("TESSERACT_CMD", "").strip()
    if cmd and Path(cmd).is_file():
        return cmd
    return shutil.which("tesseract")


def _tesseract_langs(cmd: str) -> set[str]:
    try:
        r = subprocess.run([cmd, "--list-langs"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    lines = (r.stdout + "\n" + r.stderr).splitlines()
    return {ln.strip() for ln in lines if ln.strip() and " " not in ln.strip() and not ln.strip().endswith(":")}


def ocr_unavailable(lang: str = "pol") -> str | None:
    """None when OCR can run, otherwise the reason (shown to the clerk)."""
    cmd = _tesseract()
    if not cmd:
        return "Tesseract nie jest zainstalowany (Windows: winget install UB-Mannheim.TesseractOCR i TESSERACT_CMD w .env)."
    if lang not in _tesseract_langs(cmd):
        return f"Tesseract nie ma języka „{lang}” (doinstaluj dane języka polskiego)."
    try:
        import pypdfium2  # noqa: F401
    except ImportError:
        return "Do OCR potrzebny jest pypdfium2 (pip install pypdfium2)."
    return None


def ocr_pages(path: Path, pages: list[int], lang: str = "pol") -> dict[int, str]:
    """OCR of selected pages (0-based) → {page: text}."""
    reason = ocr_unavailable(lang)
    if reason:
        raise IngestError(reason)
    import pypdfium2 as pdfium
    cmd = _tesseract()
    pdf = pdfium.PdfDocument(str(path))
    out = {}
    with tempfile.TemporaryDirectory() as td:
        for i in pages:
            img = pdf[i].render(scale=2).to_pil()  # ok. 144 dpi × 2
            png = Path(td) / f"p{i}.png"
            img.save(png)
            r = subprocess.run([cmd, str(png), "-", "-l", lang], capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                raise IngestError(f"tesseract: {r.stderr.strip()[:200]}")
            out[i] = r.stdout
    return out


def ocr_pdf(path: Path, lang: str = "pol") -> str:
    from pypdf import PdfReader
    n = len(PdfReader(str(path)).pages)
    texts = ocr_pages(path, list(range(n)), lang)
    return "\n\n".join(texts[i] for i in range(n))


def read_pdf(path: Path, ocr: str = "auto") -> tuple[str, dict]:
    """Text layer per page; pages without one (scans) go through OCR one by one, so a mixed PDF keeps every page."""
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
    weak = [i for i, t in enumerate(pages) if len(t.strip()) < MIN_CHARS_PER_PAGE]
    targets = list(range(len(pages))) if ocr == "always" else (weak if ocr == "auto" else [])
    if targets:
        reason = ocr_unavailable()
        readable = [i for i in range(len(pages)) if i not in weak]
        if reason and (ocr == "always" or not readable):
            raise IngestError(f"PDF wygląda na skan, a OCR nie działa: {reason}")
        if reason:  # część stron ma tekst: oddaj go i nazwij strony, których nie odczytano
            meta["unread_pages"] = [i + 1 for i in weak]
            meta["ocr_problem"] = reason
        else:
            for i, t in ocr_pages(path, targets).items():
                if ocr == "always" or len(t.strip()) > len(pages[i].strip()):
                    pages[i] = t
            meta["ocr"] = True
            meta["ocr_pages"] = [i + 1 for i in targets]
    return "\n\n".join(t for t in pages if t.strip()), meta


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
_SKIP = {W_NS + "pPr", W_NS + "rPr", W_NS + "delText", W_NS + "instrText", MC_FALLBACK}


def _docx_blocks(container) -> list[str]:
    """Paragraphs and tables of a body, cell, header or text box, in document order."""
    out: list[str] = []
    for el in container:
        if el.tag == W_NS + "p":
            out.extend(_docx_paragraph(el))
        elif el.tag == W_NS + "tbl":
            out.extend(_docx_table(el))
        elif el.tag in (W_NS + "sdt", W_NS + "customXml"):  # pola formularza, kontrolki treści
            inner = el.find(W_NS + "sdtContent")
            out.extend(_docx_blocks(inner if inner is not None else el))
    return out


def _docx_paragraph(p) -> list[str]:
    parts: list[str] = []
    boxes: list[str] = []  # ramki tekstowe zakotwiczone w akapicie idą zaraz po nim

    def walk(el):
        for c in el:
            if c.tag in _SKIP:
                continue
            if c.tag == W_NS + "txbxContent":
                boxes.extend(_docx_blocks(c))
                continue
            if c.tag == W_NS + "t":
                parts.append(c.text or "")
            elif c.tag == W_NS + "tab":
                parts.append("\t")
            elif c.tag in (W_NS + "br", W_NS + "cr"):
                parts.append("\n")
            elif c.tag == W_NS + "noBreakHyphen":
                parts.append("-")
            walk(c)

    walk(p)
    return ["".join(parts)] + boxes


def _docx_table(tbl) -> list[str]:
    rows = []
    wrapped = [r for s in tbl.findall(W_NS + "sdt") for c in s.findall(W_NS + "sdtContent") for r in c.findall(W_NS + "tr")]
    for tr in tbl.findall(W_NS + "tr") + wrapped:
        cells = []
        for tc in tr.findall(W_NS + "tc"):
            pr = tc.find(W_NS + "tcPr")
            vm = pr.find(W_NS + "vMerge") if pr is not None else None
            if vm is not None and vm.get(W_NS + "val") in (None, "continue"):
                continue  # scalone w pionie: treść jest w komórce powyżej
            cells.append("\n".join(t for t in _docx_blocks(tc) if t.strip()).strip())
        if not any(cells):
            continue
        if len(cells) > 1 and re.fullmatch(r"\(?\d{1,3}[.)]?|[a-zA-Z][.)]", cells[0]):  # „1.” | pytanie → „1. pytanie”
            cells = [f"{cells[0]} {cells[1]}"] + cells[2:]
        rows.append(" | ".join(cells))
    return rows


def read_docx(path: Path) -> tuple[str, dict]:
    """Body in document order (tables where they stand, merged cells once, text boxes, content controls),
    plus headers, footers, footnotes and endnotes – the requester's address often sits in the letterhead."""
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            body_root = ET.fromstring(z.read("word/document.xml"))

            def part(pattern: str) -> list[str]:
                lines: list[str] = []
                for n in sorted(x for x in names if re.fullmatch(pattern, x)):
                    root = ET.fromstring(z.read(n))
                    items = root.findall(W_NS + "footnote") + root.findall(W_NS + "endnote") or [root]
                    for it in items:
                        lines += [t for t in _docx_blocks(it) if t.strip() and t not in lines]
                return lines

            headers, footers = part(r"word/header\d*\.xml"), part(r"word/footer\d*\.xml")
            notes = part(r"word/footnotes\.xml") + part(r"word/endnotes\.xml")
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
        raise IngestError(f"Nie da się otworzyć DOCX: {e}") from e
    body = body_root.find(W_NS + "body")
    lines = _docx_blocks(body if body is not None else body_root)
    text = "\n".join(headers + lines + notes + footers)
    return text, {"paragraphs": sum(1 for _ in body_root.iter(W_NS + "p")), "tables": sum(1 for _ in body_root.iter(W_NS + "tbl")),
                  "header_lines": len(headers), "footer_lines": len(footers), "note_lines": len(notes)}


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
    if meta.get("unread_pages"):
        nums = meta["unread_pages"]
        pages = (f"Strona {nums[0]} to skan bez warstwy tekstu i nie została odczytana" if len(nums) == 1 else
                 f"Strony {', '.join(map(str, nums))} to skany bez warstwy tekstu i nie zostały odczytane")
        miss = (f"{pages}: {meta.get('ocr_problem', '')} "
                "Uzupełnij ich treść ręcznie przed dalszą pracą.")
        warn = f"{miss} {warn}" if warn else miss
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
