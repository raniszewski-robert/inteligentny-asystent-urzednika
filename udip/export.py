"""Irreversible export hardening (T27): fixed-length blocks, metadata scrub, XML leak audit, redaction footer.

- BLOCK replaces every accepted span in a final DOCX, so the length of a PESEL or a name does not leak.
- harden_docx() removes personal and tool metadata (core/app/custom properties), comments and tracked changes.
- audit_docx() unzips the file and searches every XML part for the redacted texts, case-, whitespace- and
  diacritic-insensitive; the result is shown to the clerk as a badge and stored with the draft.
- metryczka() writes the footer that states what was withheld and on which legal basis.
"""
from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from datetime import date

BLOCK = "██████"

_CORE_FIELDS = ("creator", "lastModifiedBy", "title", "subject", "keywords", "description", "category", "contentStatus",
                "identifier", "language", "version", "revision")
_APP_FIELDS = ("Application", "AppVersion", "Company", "Manager", "Template", "HyperlinkBase")
_DROP_PARTS = re.compile(r"^(docProps/custom\.xml|word/comments[A-Za-z]*\.xml|word/people\.xml|customXml/.*)$")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("ł", "l")
    return re.sub(r"\s+", "", s)


def _norm_words(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("ł", "l")
    return re.sub(r"\s+", " ", s).strip()


def _scrub_core(xml: str) -> str:
    for f in _CORE_FIELDS:
        xml = re.sub(rf"<(\w+:)?{f}(\s[^>]*)?>.*?</(\w+:)?{f}>", "", xml, flags=re.S)
        xml = re.sub(rf"<(\w+:)?{f}(\s[^>]*)?/>", "", xml)
    return xml


def _scrub_app(xml: str) -> str:
    for f in _APP_FIELDS:
        xml = re.sub(rf"<{f}>.*?</{f}>", "", xml, flags=re.S)
        xml = re.sub(rf"<{f}/>", "", xml)
    return xml


def _scrub_document(xml: str) -> str:
    """Accept tracked insertions (keep text), drop deletions, comment anchors and the rsid tracking attributes."""
    xml = re.sub(r"<w:del\b[^>]*>.*?</w:del>", "", xml, flags=re.S)
    xml = re.sub(r"<w:ins\b[^>]*>(.*?)</w:ins>", r"\1", xml, flags=re.S)
    xml = re.sub(r"<w:(commentRangeStart|commentRangeEnd)\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:r>\s*<w:rPr>\s*<w:rStyle w:val=\"CommentReference\"/>\s*</w:rPr>\s*<w:commentReference\b[^>]*/>\s*</w:r>", "", xml)
    xml = re.sub(r"<w:commentReference\b[^>]*/>", "", xml)
    xml = re.sub(r'\sw:rsid\w*="[^"]*"', "", xml)
    return xml


def harden_docx(docx_bytes: bytes) -> bytes:
    src = zipfile.ZipFile(io.BytesIO(docx_bytes))
    dropped = {n for n in src.namelist() if _DROP_PARTS.match(n)}
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            name = item.filename
            if name in dropped:
                continue
            data = src.read(name)
            if name.endswith((".xml", ".rels")):
                xml = data.decode("utf-8")
                if name == "docProps/core.xml":
                    xml = _scrub_core(xml)
                elif name == "docProps/app.xml":
                    xml = _scrub_app(xml)
                elif name.startswith("word/") and name.endswith(".xml"):
                    xml = _scrub_document(xml)
                if name.endswith(".rels") or name == "[Content_Types].xml":
                    for d in dropped:  # relationships / overrides pointing at removed parts
                        base = d.rsplit("/", 1)[-1]
                        xml = re.sub(rf'<Relationship\b[^>]*Target="[^"]*{re.escape(base)}"[^>]*/>', "", xml)
                        xml = re.sub(rf'<Override\b[^>]*PartName="/{re.escape(d)}"[^>]*/>', "", xml)
                data = xml.encode("utf-8")
            dst.writestr(item, data)
    return out.getvalue()


def audit_docx(docx_bytes: bytes, secrets: list[str]) -> dict:
    """Search every XML part (text and attributes) for each secret. ok=True means 0 hits."""
    wanted = []
    for s in dict.fromkeys(x.strip() for x in secrets):
        nc = _norm(s)
        if len(nc) < 3:
            continue
        nw = _norm_words(s)
        # Compact substring matching catches split digits / multi-word secrets; short single words (e.g. "Rak")
        # use word boundaries so ordinary Polish words ("brak", "listopada") do not block exports.
        use_compact = any(c.isdigit() for c in nc) or (len(nc) >= 6 and (" " in nw or "-" in nw or "@" in nw))
        rx = re.compile(r"(?<![a-z0-9])" + re.escape(nw) + r"(?![a-z0-9])")
        wanted.append((s, nc, rx, use_compact))
    hits, preview, parts = [], "", 0
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        for name in z.namelist():
            if not name.endswith((".xml", ".rels")):
                continue
            parts += 1
            raw = z.read(name).decode("utf-8", "replace")
            text = re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", raw))
            attrs = " ".join(re.findall(r'"([^"]*)"', raw))
            hay_words = (_norm_words(text), _norm_words(attrs))
            hay_compact = (_norm(text), _norm(attrs))
            for orig, nc, rx, use_compact in wanted:
                if any(rx.search(h) for h in hay_words) or (use_compact and any(nc in h for h in hay_compact)):
                    hits.append({"part": name, "secret": orig})
            if name == "word/document.xml":
                preview = re.sub(r"\s+", " ", re.sub(r"</w:p>", "\n", raw))
                preview = re.sub(r"<[^>]+>", "", preview)[:600]
    return {"ok": not hits, "hits": hits, "parts": parts, "xml_preview": preview}


# span type → (what the reader sees, legal ground)
_PRIV = "prywatność osoby fizycznej"
CATEGORY = {
    "OSOBA": ("imiona i nazwiska", _PRIV), "ADRES": ("adresy", _PRIV), "KOD_MIEJSC": ("adresy", _PRIV),
    "EMAIL": ("adresy e-mail", _PRIV), "TELEFON": ("numery telefonów", _PRIV), "PESEL": ("numery PESEL", _PRIV),
    "DOWOD": ("numery dowodów osobistych", _PRIV), "PASZPORT": ("numery paszportów", _PRIV),
    "URODZENIE": ("daty i miejsca urodzenia", _PRIV), "REJESTRACJA": ("numery rejestracyjne pojazdów", _PRIV),
    "KW": ("numery ksiąg wieczystych", _PRIV), "DZIALKA": ("numery działek", _PRIV),
    "IBAN": ("numery rachunków bankowych", "prywatność osoby fizycznej lub tajemnica przedsiębiorcy"),
    "NIP": ("numery NIP", "prywatność osoby fizycznej lub tajemnica przedsiębiorcy"),
    "REGON": ("numery REGON", "prywatność osoby fizycznej lub tajemnica przedsiębiorcy"),
    "TAJEMNICA": ("informacje stanowiące tajemnicę przedsiębiorcy", "tajemnica przedsiębiorcy"),
    "RECZNIE": ("fragmenty wskazane przez urzędnika", "prywatność osoby fizycznej lub tajemnica przedsiębiorcy"),
}


def metryczka(categories: list[str], initials: str, on: date) -> str:
    """Footer text for the redacted version. Empty when nothing was withheld."""
    seen: dict[str, str] = {}
    for c in categories:
        if c.startswith("SZCZEGOLNE"):
            seen.setdefault("informacje o zdrowiu, sytuacji rodzinnej lub innych sprawach osobistych", _PRIV)
        elif c in CATEGORY:
            label, ground = CATEGORY[c]
            seen.setdefault(label, ground)
        else:
            seen.setdefault("inne dane osobowe", _PRIV)
    if not seen:
        return ""
    ground = next((g for g in seen.values() if "tajemnica" in g), _PRIV)
    who = f" Anonimizację wykonał(a): {initials}." if initials else ""
    return (f"Wyłączenie jawności: w dokumencie zaczerniono {', '.join(seen)}. Podstawa: art. 5 ust. 2 ustawy z dnia "
            f"6 września 2001 r. o dostępie do informacji publicznej ({ground}).{who} "
            f"Data: {on.strftime('%d.%m.%Y')} r.")
