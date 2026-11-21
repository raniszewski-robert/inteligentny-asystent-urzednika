"""Ingest security (T26): what an uploaded file hides, and a prompt-injection pre-filter for text sent to a model.

scan(path) -> {"hidden_text": [...], "images": [...], "injection": [...], "notes": [...]}
    hidden_text  text a reader does not see: DOCX w:vanish, size < 3 pt, white or near-white colour, comments,
                 tracked deletions; PDF chars < 3 pt, near-white fill (>= 0.95), outside the page, annotation notes.
    images       pictures in the file (word/media/*, images on PDF pages): signatures, stamps, scans, logos.
    injection    lines that read like instructions to a model ("zignoruj poprzednie instrukcje", role tags ...).
    notes        facts worth a look that are not findings (electronic signature, macros, attachments, scripts).
sanitize_for_llm(text) -> (clean_text, quarantined)
    Each suspected instruction line is replaced by MARKER; the rest of the text is unchanged (identical when nothing
    is found, so cached model answers stay valid). Quarantined spans are logged to security_events.

The scanner only reports. The clerk decides what to do with the file; nothing is deleted from the request.
Dependencies: pdfplumber (MIT), pypdf (BSD-3), Pillow (MIT-CMU/HPND), standard library XML.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

MARKER = "[fragment pominięty: możliwa instrukcja dla systemu]"
MIN_PT = 3.0           # PDF: smaller glyphs are unreadable on screen and in print
MIN_HALF_POINTS = 6    # DOCX w:sz is in half-points: < 6 = below 3 pt
WHITE = 0.95           # colour channel share (0-1) from which text counts as white on a white page
LINE_MAX = 300         # longer "lines" (no line breaks) are cut to the sentence instead

# ------------------------------------------------------------------ prompt injection

_PL_IGNORE = r"(?:zignoruj(?:cie)?|ignoruj(?:cie)?|pomi[nń](?:cie)?|pomijaj|zapomnij|odrzu[cć]|nie\s+(?:bierz\s+pod\s+uwag[eę]|stosuj\s+si[eę]\s+do|wykonuj))"
_PL_PRIOR = r"(?:wszystkie\s+|wszelkie\s+|swoje\s+|twoje\s+)?(?:poprzedni\w*|wcze[sś]niejsz\w*|powy[zż]sz\w*|dotychczasow\w*|wcze[sś]niej\s+podan\w*|systemow\w*)"
_PL_RULES = r"(?:instrukcj\w*|polece[nń]\w*|zasad\w*|regu[lł]\w*|wytyczn\w*|ustawie[nń]\w*|ogranicze[nń]\w*)"
_AI = r"(?:model\w*(?:\s+j[eę]zykow\w*)?|asysten\w*|AI|SI|sztuczn\w+\s+inteligencj\w+|chat\s?GPT|GPT|Claude|Bielik\w*|LLM|bot\w*)"
_ROLE_TAGS = (r"system|assistant|asystent|user|human|developer|instructions?|instrukcj[ae]|prompt|untrusted\w*|wniosek|"
              r"dokument|pytanie|odpowiedz_wydzialu|context|im_start|im_end")

INJECTION_PATTERNS: list[tuple[str, str, re.Pattern]] = [(label, kind, re.compile(rx, re.I | re.M)) for label, kind, rx in [
    ("polecenie zignorowania instrukcji", "instruction", _PL_IGNORE + r"\s+" + _PL_PRIOR + r"\s+" + _PL_RULES),
    ("polecenie zignorowania instrukcji", "instruction", _PL_IGNORE + r"\s+(?:wszystkie\s+|wszelkie\s+)?" + _PL_RULES + r"\s+" + _PL_PRIOR),
    ("nowe instrukcje dla modelu", "instruction", r"\bnow[ea]\s+(?:instrukcj\w*|polecenie|polecenia|zasady)\s*(?::|dla\b)"),
    ("tekst skierowany do modelu", "instruction", r"\b(?:instrukcj\w*|polecen\w*|wiadomo[sś][cć]|uwaga)\s+dla\s+" + _AI + r"\b"),
    ("tekst skierowany do modelu", "instruction", r"(?:^|(?<=[.!?]\s))(?:drogi\s+|szanowny\s+)?" + _AI + r"\s*[,:]\s*(?:zignoruj|ignoruj|pomi[nń]|przypisz|oznacz|zaklasyfikuj|uznaj|odpowiedz|napisz|wy[sś]lij|ujawnij|nie\s)"),
    ("zmiana roli modelu", "instruction", r"\b(?:jeste[sś]\s+(?:teraz|odt[aą]d|od\s+teraz)|od\s+(?:teraz|tej\s+chwili)\s+(?:jeste[sś]|dzia[lł]asz|odpowiadasz|masz)|wciel\s+si[eę]\s+w|udawaj,?\s+[zż]e\s+jeste[sś])"),
    ("prośba o ujawnienie instrukcji", "instruction", r"\b(?:prompt\w*\s+systemow\w*|system(?:owy|owe)?\s+prompt\w*|polecenie\s+systemowe|ujawnij\s+(?:sw[oó]j|swoje|twoje|tw[oó]j)\s+(?:prompt|instrukcj\w*|polecen\w*))"),
    ("polecenie pominięcia anonimizacji", "instruction", r"\b(?:nie\s+(?:anonimizuj|zaczerniaj|ukrywaj\s+danych)|pomi[nń]\s+anonimizacj\w*|wy[lł][aą]cz\s+anonimizacj\w*)"),
    ("ignore previous instructions", "instruction", r"\b(?:ignore|disregard|forget|override|skip)\s+(?:all\s+|any\s+|the\s+|your\s+)*(?:previous|prior|above|earlier|preceding|system|original)\s+(?:instructions?|prompts?|messages?|rules|directions)"),
    ("system prompt", "instruction", r"\b(?:system\s+prompt|developer\s+mode|jailbreak|do\s+anything\s+now|you\s+are\s+now\s+(?:a|an|the|in)\b|new\s+instructions\s*:|act\s+as\s+(?:a|an)\s+(?:different|new|unrestricted))"),
    ("znacznik roli lub instrukcji", "spoofing", r"<\s*/?\s*(?:" + _ROLE_TAGS + r")(?=[\s>/|])[^<>\n]{0,80}>"),
    ("znacznik roli lub instrukcji", "spoofing", r"<\|\s*(?:im_start|im_end|system|assistant|user|endoftext)\s*\|>|\[/?INST\]|<<\s*/?SYS\s*>>"),
    ("znacznik roli lub instrukcji", "spoofing", r"^[ \t]*(?:#{1,6}[ \t]*)?(?:system|assistant|asystent|developer)[ \t]*:"),
]]

_INVISIBLE = re.compile("[​‌‍⁠﻿­‪-‮⁦-⁩]")


def _visible_map(text: str) -> tuple[str, list[int]]:
    """Text without zero-width and bidi control chars (an evasion trick), and each kept char's index in `text`."""
    keep = [i for i, ch in enumerate(text) if not _INVISIBLE.match(ch)]
    return "".join(text[i] for i in keep), keep


def _unit(text: str, s: int, e: int) -> tuple[int, int]:
    """The line around [s, e); the sentence when the line is very long."""
    ls = text.rfind("\n", 0, s) + 1
    le = text.find("\n", e)
    le = len(text) if le < 0 else le
    if le - ls > LINE_MAX:
        cut = [m.end() for m in re.finditer(r"[.!?…](?:\s+)", text[ls:s])]
        ls = ls + cut[-1] if cut else ls
        m = re.search(r"[.!?…](?=\s|$)", text[e:le])
        le = e + m.end() if m else le
    while ls < le and text[ls] in " \t":
        ls += 1
    while le > ls and text[le - 1] in " \t\r":
        le -= 1
    return ls, le


def find_injection(text: str) -> list[dict]:
    """Suspected instructions to a model: [{start, end, text, label, kind}] sorted, merged per line (offsets in `text`)."""
    if not text:
        return []
    vis, idx = _visible_map(text)
    hits: list[tuple[int, int, str, str]] = []
    for label, kind, rx in INJECTION_PATTERNS:
        for m in rx.finditer(vis):
            if m.end() <= m.start():
                continue
            s, e = idx[m.start()], idx[m.end() - 1] + 1
            us, ue = _unit(text, s, e)
            hits.append((us, max(ue, e), label, kind))
    hits.sort()
    out: list[dict] = []
    for s, e, label, kind in hits:
        if out and s < out[-1]["end"]:
            last = out[-1]
            last["end"] = max(last["end"], e)
            if label not in last["labels"]:
                last["labels"].append(label)
            continue
        out.append({"start": s, "end": e, "labels": [label], "kind": kind})
    for o in out:
        o["text"] = text[o["start"]:o["end"]]
        o["label"] = "; ".join(o.pop("labels"))
    return out


def sanitize_for_llm(text: str, *, case_id: int | None = None, log: bool = True) -> tuple[str, list[dict]]:
    """(clean text, quarantined spans). Each suspected instruction line becomes MARKER; offsets refer to `text`.
    Text with no finding comes back unchanged. Findings are logged to security_events (a logging error is ignored)."""
    text = text or ""
    spans = find_injection(text)
    if not spans:
        return text, []
    parts, pos = [], 0
    for sp in spans:
        parts.append(text[pos:sp["start"]])
        parts.append(MARKER)
        pos = sp["end"]
    parts.append(text[pos:])
    if log:
        for sp in spans:
            _log(case_id, "prompt_injection", sp["label"], sp["text"])
    return "".join(parts), spans


def _log(case_id, kind: str, detail: str, raw: str) -> None:
    try:
        from . import db
        db.log_security_event(case_id, kind, detail, (raw or "")[:1000])
    except Exception:  # logging must never stop the analysis
        pass


def log_scan(result: dict, case_id: int | None) -> int:
    """Write one security_events row per finding of a scan() result (e.g. once the case exists). Returns the count."""
    n = 0
    for h in result.get("hidden_text", []):
        _log(case_id, "hidden_text", h.get("reason", ""), h.get("text", "")); n += 1
    for im in result.get("images", []):
        _log(case_id, "image", im.get("label", ""), im.get("name", "")); n += 1
    for inj in result.get("injection", []):
        _log(case_id, "prompt_injection", inj.get("label", ""), inj.get("text", "")); n += 1
    return n


# ------------------------------------------------------------------ file scanner

def empty() -> dict:
    return {"hidden_text": [], "images": [], "injection": [], "notes": []}


def count(result: dict | None) -> int:
    """Number of findings (hidden text + images + suspected instructions); notes are not findings."""
    if not result:
        return 0
    return sum(len(result.get(k) or []) for k in ("hidden_text", "images", "injection"))


def scan(path: Path, text: str | None = None) -> dict:
    """Findings for one file. `text` = the text ingest extracted (else it is read here, without OCR).
    Never raises: a part that cannot be checked becomes a note."""
    path = Path(path)
    res = empty()
    ext = path.suffix.lower()
    try:
        if ext == ".docx":
            _scan_docx(path, res)
        elif ext == ".pdf":
            _scan_pdf(path, res)
    except Exception as e:
        res["notes"].append(f"Nie udało się w pełni sprawdzić pliku ({type(e).__name__}).")
    if text is None:
        try:
            text = _read_text(path)
        except Exception:
            text = ""
    res["injection"] = [{k: v for k, v in sp.items()} for sp in find_injection(text)]
    if _INVISIBLE.search(text or ""):
        res["notes"].append("Tekst zawiera niewidoczne znaki sterujące (np. spacje o zerowej szerokości).")
    return res


def _read_text(path: Path) -> str:
    from . import ingest
    ext = path.suffix.lower()
    if ext == ".pdf":
        return ingest.read_pdf(path, ocr="never")[0]
    if ext == ".docx":
        return ingest.read_docx(path)[0]
    if ext == ".odt":
        return ingest.read_odt(path)[0]
    return path.read_bytes().decode("utf-8", errors="replace")


# ---- DOCX

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_OFF = {"0", "false", "off"}


def _on(el) -> bool:
    return el is not None and el.get(W + "val", "true").lower() not in _OFF


def _rpr_props(rpr) -> dict:
    """Relevant run properties set in one w:rPr (only the keys present)."""
    p: dict = {}
    if rpr is None:
        return p
    for tag in ("vanish", "specVanish", "webHidden"):
        el = rpr.find(W + tag)
        if el is not None:
            p["vanish"] = _on(el)
    sz = rpr.find(W + "sz")
    if sz is not None and (sz.get(W + "val") or "").isdigit():
        p["sz"] = int(sz.get(W + "val"))
    col = rpr.find(W + "color")
    if col is not None:
        p["color"] = (col.get(W + "val") or "").lower()
        p["theme"] = (col.get(W + "themeColor") or "").lower()
    shd = rpr.find(W + "shd")
    if shd is not None:
        p["fill"] = (shd.get(W + "fill") or "").lower()
    hl = rpr.find(W + "highlight")
    if hl is not None:
        p["highlight"] = (hl.get(W + "val") or "").lower()
    return p


class _Styles:
    def __init__(self, xml: bytes | None):
        self.rpr: dict[str, dict] = {}
        self.based: dict[str, str] = {}
        self.defaults: dict = {}
        self.default_para = ""
        if not xml:
            return
        root = ET.fromstring(xml)
        dd = root.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")
        self.defaults = _rpr_props(dd)
        for st in root.findall(W + "style"):
            sid = st.get(W + "styleId") or ""
            self.rpr[sid] = _rpr_props(st.find(W + "rPr"))
            b = st.find(W + "basedOn")
            if b is not None:
                self.based[sid] = b.get(W + "val") or ""
            if st.get(W + "type") == "paragraph" and st.get(W + "default") in ("1", "true"):
                self.default_para = sid

    def chain(self, sid: str) -> dict:
        out: dict = {}
        seen = set()
        stack = []
        while sid and sid not in seen:
            seen.add(sid)
            stack.append(self.rpr.get(sid, {}))
            sid = self.based.get(sid, "")
        for d in reversed(stack):
            out.update(d)
        return out


def _hex_white(v: str) -> bool:
    if not re.fullmatch(r"[0-9a-f]{6}", v or ""):
        return False
    return min(int(v[i:i + 2], 16) for i in (0, 2, 4)) / 255 >= WHITE


def _dark_background(p: dict, para_fill: str) -> bool:
    fill = p.get("fill") or para_fill
    if fill and fill != "auto" and not _hex_white(fill):
        return True
    return bool(p.get("highlight") and p["highlight"] not in ("none", "white"))


def _run_reasons(p: dict, para_fill: str) -> list[str]:
    r = []
    if p.get("vanish"):
        r.append("tekst ukryty (atrybut „ukryty”)")
    if "sz" in p and p["sz"] < MIN_HALF_POINTS:
        r.append(f"czcionka {p['sz'] / 2:g} pt")
    if (_hex_white(p.get("color", "")) or p.get("theme") in ("background1", "light1")) and not _dark_background(p, para_fill):
        r.append("biały tekst")
    return r


def _runs(el):
    """w:r elements of one paragraph (through hyperlinks, insertions, content controls), not deletions or nested paragraphs."""
    for ch in el:
        if ch.tag == W + "r":
            yield ch
        elif ch.tag in (W + "p", W + "del", W + "moveFrom", W + "pPr"):
            continue
        else:
            yield from _runs(ch)


def _scan_docx(path: Path, res: dict) -> None:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        styles = _Styles(z.read("word/styles.xml") if "word/styles.xml" in names else None)
        parts = ["word/document.xml"] + sorted(n for n in names if re.fullmatch(r"word/(header|footer)\d*\.xml|word/(footnotes|endnotes)\.xml", n))
        for part in parts:
            if part not in names:
                continue
            root = ET.fromstring(z.read(part))
            where_base = "treść" if part == "word/document.xml" else {"header": "nagłówek", "footer": "stopka", "footnotes": "przypisy",
                                                                      "endnotes": "przypisy końcowe"}[re.sub(r"word/|\d*\.xml", "", part)]
            for no, p in enumerate(root.iter(W + "p"), 1):
                ppr = p.find(W + "pPr")
                pstyle = ppr.find(W + "pStyle").get(W + "val") if ppr is not None and ppr.find(W + "pStyle") is not None else styles.default_para
                pshd = ppr.find(W + "shd") if ppr is not None else None
                para_fill = (pshd.get(W + "fill") or "").lower() if pshd is not None else ""
                base = {**styles.defaults, **styles.chain(pstyle)}
                hidden_txt, reasons = [], []
                for r in _runs(p):
                    txt = "".join(t.text or "" for t in r.findall(W + "t"))
                    if not txt.strip():
                        continue
                    rpr = r.find(W + "rPr")
                    rs = rpr.find(W + "rStyle") if rpr is not None else None
                    props = {**base, **(styles.chain(rs.get(W + "val")) if rs is not None else {}), **_rpr_props(rpr)}
                    why = _run_reasons(props, para_fill)
                    if why:
                        hidden_txt.append(txt)
                        reasons += [w for w in why if w not in reasons]
                if hidden_txt:
                    res["hidden_text"].append({"kind": "hidden", "where": f"{where_base}, akapit {no}", "reason": ", ".join(reasons),
                                               "text": _short(" ".join(hidden_txt))})
                deleted = [t.text or "" for d in p.iter(W + "del") for t in d.iter(W + "delText")]
                if "".join(deleted).strip():
                    res["hidden_text"].append({"kind": "deleted", "where": f"{where_base}, akapit {no}",
                                               "reason": "usunięty tekst w śledzeniu zmian", "text": _short("".join(deleted))})
        if "word/comments.xml" in names:
            root = ET.fromstring(z.read("word/comments.xml"))
            for i, c in enumerate(root.iter(W + "comment"), 1):
                txt = " ".join("".join(t.text or "" for t in p.iter(W + "t")) for p in c.iter(W + "p")).strip()
                if txt:
                    res["hidden_text"].append({"kind": "comment", "where": f"komentarz {i}", "reason": "komentarz w dokumencie",
                                               "text": _short(txt)})
        for n in sorted(names):
            if n.startswith("word/media/") and not n.endswith("/"):
                res["images"].append(_image_info(n.rsplit("/", 1)[1], z.read(n), page=None))
            elif n.startswith("word/embeddings/") and not n.endswith("/"):
                res["notes"].append(f"Osadzony obiekt: {n.rsplit('/', 1)[1]}.")
        if any(n.lower().endswith("vbaproject.bin") for n in names):
            res["notes"].append("Plik zawiera makra (vbaProject.bin).")
        if any(n.startswith("_xmlsignatures/") for n in names):
            res["notes"].append("Plik ma podpis cyfrowy (sprawdź go w programie do podpisu).")


def _image_info(name: str, data: bytes | None, page: int | None, width=None, height=None, full_page=False) -> dict:
    w, h = width, height
    if data and (w is None or h is None):
        try:
            from PIL import Image
            with Image.open(io.BytesIO(data)) as im:
                w, h = im.size
        except Exception:
            pass
    hint = ""
    if full_page:
        hint = "skan strony"
    elif w and h and w / max(h, 1) >= 2.2 and h <= 300:
        hint = "możliwy podpis lub parafa"
    label = "obraz" + (f" ({hint})" if hint else "")
    return {"page": page, "kind": "image", "name": name, "width": int(w) if w else None, "height": int(h) if h else None,
            "hint": hint, "label": label}


def _short(s: str, n: int = 300) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# ---- PDF

def _color_white(c) -> bool:
    if c is None or isinstance(c, str):
        return False
    try:
        vals = [float(x) for x in (c if isinstance(c, (list, tuple)) else [c])]
    except (TypeError, ValueError):
        return False
    if len(vals) in (1, 3):
        return min(vals) >= WHITE
    if len(vals) == 4:  # CMYK: white = no ink
        return max(vals) <= 1 - WHITE
    return False


def _inside(ch: dict, boxes: list[tuple]) -> bool:
    cx, cy = (ch["x0"] + ch["x1"]) / 2, (ch["top"] + ch["bottom"]) / 2
    return any(x0 <= cx <= x1 and t <= cy <= b for x0, t, x1, b in boxes)


def _scan_pdf(path: Path, res: dict) -> None:
    import pdfplumber
    with pdfplumber.open(str(path)) as pdf:
        for pno, pg in enumerate(pdf.pages, 1):
            W_, H_ = float(pg.width), float(pg.height)
            imgs = list(pg.images)
            under = [(im["x0"], im["top"], im["x1"], im["bottom"]) for im in imgs]
            under += [(r["x0"], r["top"], r["x1"], r["bottom"]) for r in pg.rects
                      if r.get("fill") and not _color_white(r.get("non_stroking_color"))]
            lines: dict[int, dict] = {}
            for ch in pg.chars:
                if not (ch.get("text") or "").strip():
                    continue
                why = []
                if ch["x1"] < 0 or ch["x0"] > W_ or ch["bottom"] < 0 or ch["top"] > H_:
                    why.append("tekst poza obszarem strony")
                if float(ch.get("size") or 0) < MIN_PT:
                    why.append(f"czcionka {float(ch.get('size') or 0):.1f} pt".replace(".", ","))
                if _color_white(ch.get("non_stroking_color")) and not _inside(ch, under):
                    why.append("biały tekst")
                if not why:
                    continue
                key = round(ch["top"] / 3)
                ln = lines.setdefault(key, {"chars": [], "why": []})
                ln["chars"].append(ch)
                ln["why"] += [w for w in why if w not in ln["why"]]
            for ln in lines.values():
                txt = "".join(c["text"] for c in sorted(ln["chars"], key=lambda c: c["x0"]))
                res["hidden_text"].append({"kind": "hidden", "where": f"strona {pno}", "reason": ", ".join(_dedupe_sizes(ln["why"])),
                                           "text": _short(txt)})
            for i, im in enumerate(imgs, 1):
                full = (im["x1"] - im["x0"]) * (im["bottom"] - im["top"]) >= 0.6 * W_ * H_
                sw, sh = (im.get("srcsize") or (None, None))[:2]
                res["images"].append(_image_info(f"strona {pno}, obraz {i}", None, page=pno, width=sw, height=sh, full_page=full))
            for a in pg.annots or []:
                txt = (a.get("contents") or "").strip()
                if txt:
                    res["hidden_text"].append({"kind": "comment", "where": f"strona {pno}", "reason": "notatka (adnotacja) w PDF",
                                               "text": _short(txt)})
    _pdf_notes(path, res)


def _dedupe_sizes(why: list[str]) -> list[str]:
    out, size = [], False
    for w in why:
        if w.startswith("czcionka"):
            if size:
                continue
            size = True
        out.append(w)
    return out


def _pdf_notes(path: Path, res: dict) -> None:
    from pypdf import PdfReader
    r = PdfReader(str(path))
    root = r.trailer["/Root"]
    names = root.get("/Names") or {}
    names = names.get_object() if hasattr(names, "get_object") else names
    if "/JavaScript" in names or "/JS" in str(root.get("/OpenAction", "")):
        res["notes"].append("PDF zawiera skrypt (JavaScript).")
    if "/EmbeddedFiles" in names:
        res["notes"].append("PDF ma załączone pliki.")
    form = root.get("/AcroForm")
    if form is not None:
        fields = form.get_object().get("/Fields") or []
        if any(f.get_object().get("/FT") == "/Sig" for f in fields):
            res["notes"].append("PDF ma pole podpisu elektronicznego (sprawdź podpis w programie do PDF).")
