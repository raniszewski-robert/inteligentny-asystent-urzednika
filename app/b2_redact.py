"""Redaction helpers for the Anonimizacja screen (lane B2): marking, manual spans, safe exports.

Detection stays in `udip.anonymize.detect`; finalization and DOCX in `udip.draft.finalize` / `write_docx`.
This module only prepares the span list before those calls so that the exported files cannot leak:

- `flatten()` unions overlapping accepted spans and drops undecided/rejected spans that overlap them
  (detect() returns special-category sentence spans that contain name spans; without this the core
  apply()/write_docx() printed the sentence in clear, reported to lane A and fixed there in 1308f75);
- `propagate()` blacks out every other occurrence of an accepted text (same name in the signature);
- `leaks()` checks the produced text and DOCX before a file is sent to the browser (fail closed).
"""
from __future__ import annotations

import copy
import html
import os
import re
import tempfile
from dataclasses import asdict
from pathlib import Path

from markupsafe import Markup

from udip import config
from udip.anonymize import LABEL, apply as anon_apply, detect
from udip.draft import finalize, write_docx

UNDECIDED = ("suggested", "review")
STATUS_LABEL = {"suggested": "propozycja", "review": "do decyzji", "accepted": "zaczernione", "rejected": "jawne"}
MANUAL = "RECZNIE"
VERSIONS = {"do_wysylki": "Do wysyłki (adresat jawny)", "zanonimizowana": "Zanonimizowana (archiwum, BIP)"}


def type_label(t: str) -> str:
    if t == MANUAL:
        return "zaznaczone ręcznie"
    if t.startswith("SZCZEGOLNE_"):
        return "dane szczególne: " + t.split("_", 1)[1].lower().replace("_", " ")
    return LABEL.get(t, "[dane]").strip("[]")


def undecided(spans: list[dict]) -> list[dict]:
    return [s for s in spans if s["status"] in UNDECIDED]


# ---- span list operations ----------------------------------------------------------------------------------------

def flatten(spans: list[dict]) -> list[dict]:
    """Non-overlapping spans for export: accepted regions unioned; other spans kept only outside them."""
    acc = sorted((s for s in spans if s["status"] == "accepted"), key=lambda s: s["start"])
    merged: list[dict] = []
    for s in acc:
        if merged and s["start"] < merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], s["end"])
        else:
            merged.append(dict(s))
    rest: list[dict] = []
    for s in sorted((s for s in spans if s["status"] != "accepted"), key=lambda s: (s["start"], -(s["end"] - s["start"]))):
        if any(s["start"] < m["end"] and m["start"] < s["end"] for m in merged):
            continue
        if rest and s["start"] < rest[-1]["end"]:
            continue
        rest.append(dict(s))
    return sorted(merged + rest, key=lambda s: s["start"])


def _occurrences(text: str, phrase: str) -> list[tuple[int, int]]:
    rx = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.I)
    return [m.span() for m in rx.finditer(text)]


def _covered(a: int, b: int, spans: list[dict]) -> bool:
    return any(s["status"] == "accepted" and s["start"] <= a and b <= s["end"] for s in spans)


def propagate(text: str, spans: list[dict], protected: list[tuple[int, int]] = ()) -> list[dict]:
    """Copy of spans where every occurrence of an accepted text is accepted too (outside `protected` ranges)."""
    out = [dict(s) for s in spans]
    types = {text[s["start"]:s["end"]].strip(): s["type"] for s in out if s["status"] == "accepted"}
    phrases = sorted(types, key=len, reverse=True)
    n = 0
    for ph in phrases:
        if len(ph) < 3:
            continue
        for a, b in _occurrences(text, ph):
            if _covered(a, b, out) or any(a < pe and ps < b for ps, pe in protected):
                continue
            n += 1
            out.append({"start": a, "end": b, "text": text[a:b], "type": types[ph], "confidence": 1.0, "id": f"p{n}",
                        "reason": "ten sam tekst zaczerniony w innym miejscu", "status": "accepted"})
    for s in out:  # a span the clerk left open but whose text is blacked elsewhere: black it too
        if s["status"] != "accepted" and text[s["start"]:s["end"]].strip() in phrases and not any(
                s["start"] < pe and ps < s["end"] for ps, pe in protected):
            s["status"] = "accepted"
    return out


def manual_phrases(spans: list[dict]) -> list[str]:
    return sorted({s.get("phrase") or s["text"] for s in spans if s["type"] == MANUAL})


def add_manual(text: str, spans: list[dict], phrases: list[str]) -> list[dict]:
    """Accepted spans of type RECZNIE for every occurrence of each phrase (whole words, case-insensitive)."""
    prev = {(s["start"], s["end"]): s["status"] for s in spans if s["type"] == MANUAL}
    out = [s for s in spans if s["type"] != MANUAL]
    n = 0
    for ph in dict.fromkeys(p.strip() for p in phrases):
        if len(ph) < 2:
            continue
        for a, b in _occurrences(text, ph):
            if any(s["start"] == a and s["end"] == b and s["status"] == "accepted" for s in out):
                continue
            n += 1
            out.append({"start": a, "end": b, "text": text[a:b], "type": MANUAL, "confidence": 1.0, "id": f"m{n}",
                        "reason": "zaznaczone przez urzędnika", "status": prev.get((a, b), "accepted"), "phrase": ph,
                        "addressee": False})
    return sorted(out, key=lambda s: (s["start"], -(s["end"] - s["start"])))


def detect_spans(text: str, keep: list[str] | None = None) -> list[dict]:
    return [asdict(s) for s in detect(text, keep=keep or None)]


def redetect(old_text: str, spans: list[dict], new_text: str, *, letter: bool, keep: list[str] | None = None) -> list[dict]:
    """Spans for edited text. Letters: udip.draft.finalize (sets the addressee flag). Other documents: detect with
    the keep list. Decisions carry over by (type, text); manual phrases are re-applied."""
    phrases = manual_phrases(spans)
    base = [s for s in spans if s["type"] != MANUAL]
    if letter:
        new = finalize(old_text, copy.deepcopy(base), edited_text=new_text)["spans"]
    else:
        decided = {(s["type"], s["text"]): s["status"] for s in base if s["status"] in ("accepted", "rejected")}
        new = detect_spans(new_text, keep)
        for s in new:
            s["status"] = decided.get((s["type"], s["text"]), s["status"])
    return add_manual(new_text, new, phrases)


def legal_warnings(text: str, spans: list[dict]) -> list[str]:
    """The partial-refusal warning only: undecided fragments block the export on this screen instead."""
    w = finalize(text, copy.deepcopy([s for s in spans if s["type"] != MANUAL]))["warnings"]
    return [x for x in w if x.startswith("UWAGA PRAWNA")]


# ---- exports -----------------------------------------------------------------------------------------------------

def export_spans(text: str, spans: list[dict], version: str) -> list[dict]:
    if version == "do_wysylki":
        body = [dict(s, status="rejected") if s.get("addressee") else dict(s) for s in spans]
        protected = [(s["start"], s["end"]) for s in spans if s.get("addressee")]
        return flatten(propagate(text, body, protected))
    if version == "zanonimizowana":
        return flatten(propagate(text, spans))
    raise ValueError(version)


def export_text(text: str, spans: list[dict], version: str) -> str:
    return anon_apply(text, export_spans(text, spans, version), "label")


def redacted_categories(text: str, spans: list[dict], version: str) -> list[str]:
    return sorted({s["type"] for s in export_spans(text, spans, version) if s["status"] == "accepted"})


def export_docx(text: str, spans: list[dict], version: str, initials: str = "") -> bytes:
    """Final DOCX: fixed-length blocks, footer with the legal ground, metadata scrubbed (udip.export, T27)."""
    from udip import export as ex
    flat = export_spans(text, spans, version)
    footer = ex.metryczka(redacted_categories(text, spans, version), initials, config.today())
    tmp = config.data_dir() / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=".docx", dir=tmp)
    os.close(fd)
    try:
        write_docx(text, flat, Path(name), final=True, footer=footer)
        return ex.harden_docx(Path(name).read_bytes())
    finally:
        Path(name).unlink(missing_ok=True)


def audit(text: str, spans: list[dict], version: str) -> dict:
    """XML-level leak audit of the final DOCX (every part, normalised): {ok, hits, parts, xml_preview}."""
    from udip import export as ex
    secrets = [text[s["start"]:s["end"]] for s in export_spans(text, spans, version) if s["status"] == "accepted"]
    return ex.audit_docx(export_docx(text, spans, version), secrets)


def docx_text(data: bytes) -> str:
    """All text of a DOCX: paragraphs, tables, headers and footers (for the leak check)."""
    import io

    import docx
    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        parts += [c.text for row in t.rows for c in row.cells]
    for sec in d.sections:
        parts += [p.text for p in sec.header.paragraphs] + [p.text for p in sec.footer.paragraphs]
    cp = d.core_properties
    parts += [cp.author or "", cp.title or "", cp.subject or "", cp.comments or "", cp.keywords or ""]
    return "\n".join(parts)


def leaks(output: str, text: str, spans: list[dict], version: str) -> list[str]:
    """Accepted texts still readable in an export. For 'do wysyłki' the addressee's own data may stay."""
    out = output
    if version == "do_wysylki":
        for s in spans:
            if s.get("addressee"):
                out = out.replace(text[s["start"]:s["end"]], "")
    found = []
    for s in spans:
        if s["status"] != "accepted" or (version == "do_wysylki" and s.get("addressee")):
            continue
        t = text[s["start"]:s["end"]].strip()
        if t and re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", out, re.I):
            found.append(t)
    return found


# ---- display -----------------------------------------------------------------------------------------------------

def marked_html(text: str, spans: list[dict]) -> Markup:
    """Text with <mark> per span, nested where spans nest. A span that crosses the end of an enclosing span is
    drawn in two pieces with the same data-id (display only; exports use flatten())."""
    import heapq
    esc = html.escape
    heap = [(s["start"], -(s["end"] - s["start"]), i, s["start"], s["end"]) for i, s in enumerate(spans)]
    heapq.heapify(heap)
    out: list[str] = []
    stack: list[int] = []
    pos = 0
    while heap:
        _, _, i, st, en = heapq.heappop(heap)
        s = spans[i]
        while stack and stack[-1] <= st:
            e = stack.pop()
            out.append(esc(text[pos:e]) + "</mark>")
            pos = e
        st = max(st, pos)
        if stack and en > stack[-1]:
            heapq.heappush(heap, (stack[-1], -(en - stack[-1]), i, stack[-1], en))  # the rest after the outer mark
            en = stack[-1]
        if en <= st:
            continue
        out.append(esc(text[pos:st]))
        pos = st
        tip = f"{type_label(s['type'])}: {s.get('reason', '')} ({STATUS_LABEL.get(s['status'], s['status'])})"
        llm = " sp-llm" if s.get("source") == "llm" else ""
        out.append(f'<mark class="sp sp-{esc(s["status"])}{llm}" data-id="{esc(s["id"])}" title="{esc(tip)}" tabindex="0" '
                   f'role="button" aria-pressed="{"true" if s["status"] == "accepted" else "false"}">')
        stack.append(en)
    while stack:
        e = stack.pop()
        out.append(esc(text[pos:e]) + "</mark>")
        pos = e
    out.append(esc(text[pos:]))
    return Markup("".join(out))
