"""LLM anonymization pass (T13): personal data the dictionaries and regexes miss.

`spans_llm(text)` returns [{start, end, text, type, confidence, reason}] or None. The model returns only the exact
fragments; offsets are computed here (every occurrence), so a wrong offset from the model can never mark the wrong text.
udip.anonymize gives these spans status "review" (never auto-accepted) and drops those overlapping rule spans.
"""
from __future__ import annotations

import re

from .. import llm, security

TYPES = {
    "OSOBA": "imię i nazwisko osoby fizycznej (także w odmianie, inicjał + nazwisko, sam podpis)",
    "ADRES": "adres zamieszkania lub korespondencyjny osoby fizycznej",
    "TELEFON": "prywatny numer telefonu",
    "EMAIL": "prywatny adres e-mail",
    "URODZENIE": "data lub miejsce urodzenia",
    "REJESTRACJA": "numer rejestracyjny prywatnego pojazdu",
    "DZIALKA": "numer działki lub księgi wieczystej pozwalający ustalić właściciela",
    "DOKUMENT": "numer dowodu, paszportu, PESEL, NIP osoby fizycznej, numer rachunku",
    "DANE_WRAZLIWE": "zdrowie, niepełnosprawność, nałogi, pomoc społeczna, karalność, poglądy, wyznanie, sytuacja rodzinna "
                     "lub majątkowa konkretnej osoby",
}
CHUNK = 12_000

SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "maxItems": 60, "items": {
        "type": "object",
        "properties": {"text": {"type": "string", "minLength": 2, "maxLength": 300},
                       "type": {"type": "string", "enum": list(TYPES)},
                       "reason": {"type": "string", "maxLength": 200},
                       "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
        "required": ["text", "type", "reason", "confidence"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False,
}

SYSTEM = (
    "Jesteś asystentem anonimizacji pism Urzędu Miasta Bydgoszczy przed publikacją w BIP. W dokumencie wskaż fragmenty, "
    "które identyfikują osobę fizyczną lub ujawniają jej dane chronione. Kategorie: "
    + "; ".join(f"{k} – {v}" for k, v in TYPES.items()) + ".\n"
    "Zasady: przepisz każdy fragment dokładnie tak, jak stoi w dokumencie (te same litery, odmiana i odstępy), bez "
    "dopisków. Nie wskazuj: nazw urzędów, wydziałów, spółek, fundacji i stowarzyszeń; ulic jako miejsc inwestycji; "
    "służbowych danych Urzędu (bip@, bks@, centrala); kwot i dat niezwiązanych z osobą. Osoby pełniące funkcje publiczne "
    "(prezydent, radni, dyrektorzy) wskaż z uzasadnieniem „funkcja publiczna – decyzja urzędnika” i pewnością 0.3. "
    "Pewność 0–1. Nic nie znaleziono = pusta lista. Decyzję o zaczernieniu podejmuje urzędnik."
)


def _locate(text: str, frag: str) -> list[tuple[int, int]]:
    frag = frag.strip()
    if len(frag) < 2:
        return []
    out = [(m.start(), m.end()) for m in re.finditer(re.escape(frag), text)]
    if not out:  # model normalised whitespace: match with flexible spaces
        rx = r"\s+".join(re.escape(p) for p in frag.split())
        out = [(m.start(), m.end()) for m in re.finditer(rx, text)]
    return out


def spans_llm(text: str, provider: str | None = None) -> list[dict] | None:
    """Extra spans the rules missed: [{start, end, text, type, confidence, reason}], or None.
    The caller sets status "review" (never auto-accepted) and drops spans overlapping rule spans."""
    if not text or not text.strip():
        return None
    found: dict[tuple[int, int], dict] = {}
    ok = False
    for base in range(0, len(text), CHUNK):
        part = text[base: base + CHUNK + 200]  # small overlap so a name on the boundary is seen whole
        out = llm.complete_json("anonymization", SYSTEM, "Dokument:\n" + llm.wrap("dokument", security.sanitize_for_llm(part)[0], limit=CHUNK + 200), SCHEMA,
                                provider=provider, max_tokens=2500)
        if out is None:
            continue
        ok = True
        for it in out["items"]:
            for s, e in _locate(part, it["text"]):
                key = (base + s, base + e)
                if key not in found:
                    found[key] = {"start": key[0], "end": key[1], "text": text[key[0]:key[1]], "type": it["type"],
                                  "confidence": round(float(it["confidence"]), 2), "reason": it["reason"].strip()}
    if not ok:
        return None
    # nested duplicates (e.g. "Kowalska" inside "Anna Kowalska"): keep the longer span
    spans = sorted(found.values(), key=lambda x: (x["start"], -(x["end"] - x["start"])))
    res: list[dict] = []
    for sp in spans:
        if res and sp["start"] < res[-1]["end"]:
            continue
        res.append(sp)
    return res
