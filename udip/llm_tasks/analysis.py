"""LLM request analysis (T11): question split, mode, risk flags, a calendar summary and the applicant type.

`analyze_llm(text)` returns {questions, mode, flags, summary, applicant_type} or None. udip.analyze merges it with the
rules (rules keep the question split, scores and similar cases; the model fills the summary and adds flags).
"""
from __future__ import annotations

import re

from .. import llm, security

MODES = ["udip", "ponowne_wykorzystanie", "petycja", "skarga_wniosek_kpa", "akta_sprawy", "informacja_o_srodowisku",
         "radny", "inny"]
APPLICANTS = ["osoba_fizyczna", "organizacja_spoleczna", "media", "firma", "radny", "kancelaria_prawna", "inny", "nieznany"]
FLAGS = {
    "informacja_przetworzona?": "wymaga zestawień, analiz lub danych z wielu lat (art. 3 ust. 1 pkt 1 UDIP)",
    "bip": "informacja zwykle publikowana w BIP (art. 10 ust. 1 UDIP)",
    "dane_osobowe": "dotyczy wynagrodzeń, umów lub danych konkretnych osób (art. 5 ust. 2 UDIP)",
    "niejasny_zakres": "pytanie nieprecyzyjne – może wymagać wezwania do doprecyzowania",
    "inny_podmiot": "część pytań dotyczy podmiotu spoza Urzędu (spółka, inna instytucja) – rozważ przekazanie lub wskazanie",
    "tajemnica": "może dotyczyć tajemnicy przedsiębiorstwa lub innej tajemnicy ustawowo chronionej (art. 5 ust. 1–2 UDIP)",
    "forma_udostepnienia": "wnioskodawca wskazuje szczególną formę lub sposób udostępnienia",
    "wiele_komorek": "odpowiedź wymaga danych z kilku komórek lub jednostek",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {"type": "array", "items": {"type": "string", "minLength": 3, "maxLength": 1200}, "minItems": 1, "maxItems": 30},
        "mode": {"type": "string", "enum": MODES},
        "flags": {"type": "array", "maxItems": 8, "items": {
            "type": "object",
            "properties": {"type": {"type": "string", "enum": list(FLAGS)}, "message": {"type": "string", "maxLength": 300}},
            "required": ["type", "message"], "additionalProperties": False}},
        "summary": {"type": "string", "minLength": 3, "maxLength": 120},
        "applicant_type": {"type": "string", "enum": APPLICANTS},
    },
    "required": ["questions", "mode", "flags", "summary", "applicant_type"],
    "additionalProperties": False,
}

SYSTEM = (
    "Jesteś asystentem pracownika Biura Komunikacji Społecznej Urzędu Miasta Bydgoszczy, który rejestruje wnioski o "
    "udostępnienie informacji publicznej (UDIP). Analizujesz jeden wniosek.\n"
    "1. questions: wypisz osobno każde pytanie lub żądanie informacji, w kolejności z wniosku, wiernie (możesz pominąć "
    "zwroty grzecznościowe, nagłówki przekazanego e-maila i stopkę). Lista numerowana = jedno pytanie na punkt; podpunkty "
    "a), b) należą do swojego punktu. Prośba o kopię umowy lub dokumentu to osobne żądanie.\n"
    "2. mode: tryb sprawy – udip (zwykły wniosek o informację publiczną), ponowne_wykorzystanie, petycja, "
    "skarga_wniosek_kpa, akta_sprawy (art. 73 KPA), informacja_o_srodowisku, radny (art. 24 ustawy o samorządzie gminnym), "
    "inny.\n"
    "3. flags: tylko sygnały rzeczywiście widoczne we wniosku, z krótkim uzasadnieniem po polsku. Dostępne typy: "
    + "; ".join(f"{k} – {v}" for k, v in FLAGS.items()) + ". Brak sygnałów = pusta lista.\n"
    "4. summary: temat wniosku do kalendarza, najwyżej 12 słów, bez danych osobowych wnioskodawcy, np. "
    "„Opieka nad bezdomnymi zwierzętami w 2025 r. – umowy i koszty”.\n"
    "5. applicant_type: kto pisze (osoba_fizyczna, organizacja_spoleczna, media, firma, radny, kancelaria_prawna, inny, "
    "nieznany).\n"
    "Nie oceniaj, czy informację należy udostępnić – to decyzja urzędnika."
)


def _words(s: str, n: int) -> str:
    w = s.split()
    return " ".join(w[:n]).rstrip(" ,;:–-") + ("…" if len(w) > n else "")


def analyze_llm(text: str, provider: str | None = None) -> dict | None:
    """{questions: [str], mode, flags: [{type, message}], summary (≤ 12 words), applicant_type} or None."""
    if not text or not text.strip():
        return None
    out = llm.complete_json("analysis", SYSTEM, "Wniosek do analizy:\n" + llm.wrap("wniosek", security.sanitize_for_llm(text)[0]), SCHEMA,
                            provider=provider, max_tokens=3000)
    if not out:
        return None
    qs = [re.sub(r"\s+", " ", q).strip() for q in out["questions"]]
    qs = [q for q in qs if len(q) >= 3]
    summary = _words(re.sub(r"\s+", " ", out["summary"]).strip().strip("„”\"."), 12)
    if not qs or not summary:
        return None
    seen, flags = set(), []
    for f in out["flags"]:
        if f["type"] not in seen and f["message"].strip():
            seen.add(f["type"])
            flags.append({"type": f["type"], "message": f["message"].strip()})
    return {"questions": qs, "mode": out["mode"], "flags": flags, "summary": summary, "applicant_type": out["applicant_type"]}
