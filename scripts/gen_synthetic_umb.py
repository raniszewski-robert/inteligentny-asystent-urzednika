#!/usr/bin/env python3
"""T14: synthetic UDIP cases modelled on the 10 UMB cases (data-partner/umb/), with gold for the eval.

Each case = request (forwarded e-mail, multi-question form, short e-mail, handwritten note, company letter), department
answers (some with 'Ad N', some prose), the final BKS letter and gold: questions, departments, 'Ad' placement (facts per
paragraph), PII spans with offsets. Claude writes the texts (one call per case, through udip.llm: cache + budget); the
gold offsets and the letter frame are computed here; the validator drops anything inconsistent.

  python scripts/gen_synthetic_umb.py --n 44                      # Sonnet 5.5, writes data-samples/syntetyczne_umb/
  python scripts/gen_synthetic_umb.py --mock --n 6 --out /tmp/syn  # no key, no network: pipeline check
  python scripts/gen_synthetic_umb.py --validate data-samples/syntetyczne_umb
Exit code: 0 = every written case valid.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from udip import llm  # noqa: E402
from udip.analyze import load_departments  # noqa: E402
from udip.draft import check_numbers  # noqa: E402

OUT = ROOT / "data-samples" / "syntetyczne_umb"
DEPS = {d["id"]: d for d in load_departments()}
PII_TYPES = ["OSOBA", "ADRES", "KOD_MIEJSC", "EMAIL", "TELEFON", "PESEL", "IBAN", "DOWOD", "REJESTRACJA", "DZIALKA", "URODZENIE"]

# (topic, departments, request style, answer style, applicant) – topics and styles follow the UMB sample
SEEDS = [
    ("opieka nad bezdomnymi zwierzętami: umowy, liczba zwierząt, koszty", ["SCHRONISKO", "WGK"], "email_przekazany", "proza", "organizacja"),
    ("liczba uczniów i uczniów cudzoziemców w szkołach podstawowych", ["WE"], "krotki_email", "proza", "osoba"),
    ("stan i miejsce przechowywania usuniętej rzeźby z ronda", ["BKZ"], "krotki_email", "proza", "osoba"),
    ("liczba punktów sprzedaży alkoholu i wydanych zezwoleń", ["WSO"], "pismo_odreczne", "proza", "osoba"),
    ("dokumentacja realizacji umowy na system informatyczny: aneksy, faktury, protokoły", ["ZDMiKP"], "formularz_wielopunktowy", "ad", "osoba"),
    ("liczba mieszkańców ulic według deklaracji opłat za odpady", ["WGO"], "pismo_parafii", "proza", "organizacja"),
    ("dokumentacja budowy apartamentowca nad rzeką i przebudowy bulwarów", ["WAB", "WIM"], "krotki_email", "ad", "osoba"),
    ("kierownik robót na budowie kompleksu basenowego", ["WIM"], "pismo_firmy", "proza", "firma"),
    ("wycinka drzew przy ulicy i nasadzenia zastępcze", ["WGK"], "formularz_wielopunktowy", "ad", "osoba"),
    ("remont ulicy: koszt, wykonawca, termin zakończenia", ["ZDMiKP"], "formularz_wielopunktowy", "ad", "osoba"),
    ("interwencje straży miejskiej wobec źle zaparkowanych pojazdów", ["SM"], "formularz_wielopunktowy", "proza", "media"),
    ("dodatki mieszkaniowe i energetyczne: liczba i kwoty", ["WSR"], "formularz_wielopunktowy", "ad", "osoba"),
    ("wydatki na promocję miasta i sponsoring klubów sportowych", ["BP", "WE"], "formularz_wielopunktowy", "ad", "media"),
    ("przetarg na odbiór odpadów: oferty, cena, umowa", ["WGO", "WZP"], "formularz_wielopunktowy", "ad", "firma"),
    ("zaległości podatkowe i umorzenia podatku od nieruchomości", ["WPL", "WW"], "formularz_wielopunktowy", "proza", "media"),
    ("sprzedaż miejskich działek i lokali w 2025 r.", ["WMG"], "formularz_wielopunktowy", "ad", "osoba"),
    ("liczba kursów i punktualność autobusów linii nocnych", ["ZDMiKP", "MZK"], "email_przekazany", "proza", "osoba"),
    ("ceny ciepła i inwestycje w sieć ciepłowniczą", ["KPEC"], "formularz_wielopunktowy", "proza", "organizacja"),
    ("awarie wodociągowe i jakość wody w dzielnicy", ["MWIK"], "krotki_email", "proza", "osoba"),
    ("liczba mieszkań komunalnych i oczekujących na przydział", ["ADM", "WMG"], "formularz_wielopunktowy", "ad", "organizacja"),
    ("dotacje dla organizacji pozarządowych na zadania senioralne", ["BAS"], "formularz_wielopunktowy", "ad", "organizacja"),
    ("program in vitro i programy zdrowotne finansowane przez miasto", ["BZS"], "krotki_email", "proza", "osoba"),
    ("liczba osób korzystających z pomocy społecznej i wydatki MOPS", ["MOPS"], "formularz_wielopunktowy", "ad", "media"),
    ("koszty utrzymania hali sportowej i liczba imprez", ["BCS", "BOS"], "formularz_wielopunktowy", "proza", "osoba"),
    ("plan miejscowy dla osiedla: etap prac i uwagi mieszkańców", ["MPU"], "email_przekazany", "proza", "organizacja"),
    ("projekty unijne miasta: wartość dofinansowania i stan rozliczeń", ["WF", "BZIT"], "formularz_wielopunktowy", "ad", "firma"),
    ("wydatki na oprogramowanie i licencje Urzędu", ["WI"], "formularz_wielopunktowy", "ad", "firma"),
    ("zatrudnienie i liczba etatów w Urzędzie, nabory", ["WOA"], "formularz_wielopunktowy", "proza", "media"),
    ("wykonanie budżetu miasta i zadłużenie", ["WZB"], "formularz_wielopunktowy", "ad", "osoba"),
    ("ochrona przeciwpowodziowa i schrony dla ludności", ["WZK"], "krotki_email", "proza", "osoba"),
    ("smog, pomiary powietrza i dotacje do wymiany pieców", ["WOS"], "formularz_wielopunktowy", "ad", "organizacja"),
    ("rejestracja pojazdów i liczba wydanych praw jazdy", ["WUK"], "krotki_email", "proza", "media"),
    ("wydarzenia kulturalne finansowane przez miasto w 2025 r.", ["BKB"], "formularz_wielopunktowy", "ad", "osoba"),
    ("liczba zgłoszeń w systemie „Dbamy o Bydgoszcz” i czas reakcji", ["BCB"], "email_przekazany", "proza", "osoba"),
    ("uchwały rady miasta o nazwach ulic i honorowe obywatelstwo", ["BRM"], "krotki_email", "proza", "osoba"),
    ("koszty utrzymania zoo i parku w Myślęcinku", ["MYSLECINEK"], "formularz_wielopunktowy", "ad", "organizacja"),
    ("ilość odpadów przetworzonych w spalarni i opłaty", ["PRONATURA", "WGO"], "formularz_wielopunktowy", "proza", "media"),
    ("czynsze i liczba mieszkań w budownictwie społecznym", ["BTBS"], "pismo_odreczne", "proza", "osoba"),
    ("cmentarze komunalne: opłaty i wolne miejsca", ["WGK"], "pismo_odreczne", "proza", "osoba"),
    ("budowa przedszkola: koszt, wykonawca, opóźnienia", ["WIM", "WE"], "formularz_wielopunktowy", "ad", "osoba"),
    ("finansowanie szkół niepublicznych i dotacje oświatowe", ["BBFO", "WE"], "formularz_wielopunktowy", "ad", "firma"),
    ("punkty informacji turystycznej i liczba odwiedzających", ["BCI"], "krotki_email", "proza", "osoba"),
    ("wynagrodzenia prezydenta i zastępców oraz nagrody", ["WOA"], "krotki_email", "ad", "media"),
    ("zabytkowe kamienice: ewidencja i dotacje na remonty", ["BKZ", "WMG"], "formularz_wielopunktowy", "ad", "organizacja"),
]

STYLE = {
    "email_przekazany": "e-mail przekazany do BKS przez kancelarię: puste nagłówki Od:/Wysłano:/Do:/Temat:, „Prośba o rejestrację w "
                        "SIDAS.”, stopka referatu, a dopiero niżej właściwy wniosek z numerowanymi pytaniami (2–5)",
    "formularz_wielopunktowy": "formalny wniosek z podstawą prawną (art. 2 ust. 1 UDIP) i numerowaną listą 3–7 punktów, prośba o formę "
                               "elektroniczną",
    "krotki_email": "krótki e-mail („Witam”, „W trybie dostępu do informacji publicznej proszę o…”), 1–2 pytania, podpis "
                    "„Pozdrawiam | imię nazwisko”",
    "pismo_odreczne": "przepisany rękopis: imię WIELKIMI LITERAMI, data, pieczęć kancelarii (data wpływu, nr wpływu), jedno pytanie, "
                      "nieporadny styl",
    "pismo_firmy": "pismo spółki z o.o. lub S.A. z numerowanymi pytaniami (1–3) i nazwą firmy na końcu",
    "pismo_parafii": "pismo instytucji (parafii, stowarzyszenia) z jednym żądaniem i listą ulic lub obiektów",
}
APPLICANT = {"osoba": "osoba fizyczna (fikcyjne imię, nazwisko, adres w Bydgoszczy, e-mail @example.com, czasem telefon)",
             "organizacja": "stowarzyszenie lub fundacja (fikcyjna nazwa, prezes z imienia i nazwiska)",
             "media": "redakcja lokalnego portalu (dziennikarz z imienia i nazwiska, e-mail redakcji @example.com)",
             "firma": "spółka (fikcyjna nazwa, pełnomocnik z imienia i nazwiska, telefon)"}


def _schema() -> dict:
    ids = sorted(DEPS)
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 160},
            "request_text": {"type": "string", "minLength": 80},
            "questions": {"type": "array", "minItems": 1, "maxItems": 9, "items": {"type": "string"}},
            "answers": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
                "type": "object", "properties": {"department": {"type": "string", "enum": ids}, "text": {"type": "string", "minLength": 40}},
                "required": ["department", "text"], "additionalProperties": False}},
            "paragraphs": {"type": "array", "minItems": 1, "maxItems": 9, "items": {
                "type": "object", "properties": {"no": {"type": "integer"}, "text": {"type": "string"},
                                                 "facts": {"type": "array", "items": {"type": "string"}, "maxItems": 6}},
                "required": ["no", "text", "facts"], "additionalProperties": False}},
            "pii": {"type": "array", "maxItems": 30, "items": {
                "type": "object", "properties": {"text": {"type": "string"}, "type": {"type": "string", "enum": PII_TYPES},
                                                 "role": {"type": "string", "enum": ["wnioskodawca", "pracownik", "osoba_trzecia"]}},
                "required": ["text", "type", "role"], "additionalProperties": False}},
        },
        "required": ["title", "request_text", "questions", "answers", "paragraphs", "pii"],
        "additionalProperties": False,
    }


def _example() -> str:
    d = ROOT / "data-partner" / "umb" / "przypadek_543"
    if not d.is_dir():
        return ""
    rec = next((json.loads(l) for l in (ROOT / "data-partner/umb/archiwum_umb.jsonl").open(encoding="utf-8")
                if "543.2026" in l), None)
    letter = rec["response_text"].split("[Odpowiedź]")[-1][:1800] if rec else ""
    return ("Przykład prawdziwej sprawy UMB (styl, nie treść do kopiowania):\n"
            + llm.wrap("wniosek", (d / "wniosek.txt").read_text(encoding="utf-8")[:2500])
            + "\n" + llm.wrap("odpowiedz_wydzialu", (d / "SCHRONISKO.txt").read_text(encoding="utf-8"), plik="SCHRONISKO.txt")
            + "\n" + llm.wrap("pismo_bks", letter))


SYSTEM = (
    "Tworzysz fikcyjne, realistyczne sprawy z dostępu do informacji publicznej w Urzędzie Miasta Bydgoszczy, na wzór "
    "prawdziwych spraw Biura Komunikacji Społecznej (BKS). Wszystkie osoby, adresy, telefony i e-maile są zmyślone "
    "(e-maile w domenie example.com, telefony 5xx xxx xxx). Każda sprawa ma:\n"
    "- request_text: wniosek w podanym stylu, po polsku, z danymi wnioskodawcy;\n"
    "- questions: pytania/żądania z wniosku, osobno, w kolejności (tyle, ile odrębnych pytań);\n"
    "- answers: odpowiedzi wskazanych komórek do BKS (sygnatura np. „WGK.1431.77.2026”, „Biuro Komunikacji Społecznej w "
    "miejscu”, treść z konkretnymi liczbami, kwotami w zapisie 1.234.567,89 zł lub 1 234 567,89 zł, datami, numerami umów, "
    "na końcu „Sprawę prowadzi: imię nazwisko, tel.”); w stylu „ad” odpowiedź ma akapity „Ad 1”, „Ad 2”…, w stylu „proza” "
    "jest ciągłym tekstem w innej kolejności niż pytania;\n"
    "- paragraphs: akapity pisma BKS, po jednym na pytanie (no = numer pytania), oparte WYŁĄCZNIE na odpowiedziach komórek: "
    "każda liczba w akapicie musi wystąpić w odpowiedzi komórki z tym samym słowem obok; gdy komórka czegoś nie ma, akapit "
    "to informacja, że komórka nie dysponuje danymi;\n"
    "- facts: dla każdego akapitu 1–3 krótkie fragmenty (liczba z następnym słowem, numer umowy, nazwa), przepisane "
    "dosłownie, które występują i w akapicie, i w odpowiedzi komórki;\n"
    "- pii: wszystkie dane osobowe dosłownie tak, jak występują w request_text lub answers (imiona i nazwiska także w "
    "odmianie, adres ulicy z numerem jako ADRES, kod z miejscowością jako KOD_MIEJSC, e-mail, telefon), z rolą.\n"
    "Nie używaj prawdziwych nazwisk urzędników. Teksty mają wyglądać jak skany po OCR: zwykły tekst, bez Markdown."
)


def _user(i: int, seed: tuple, attempt: int) -> str:
    topic, deps, style, ans_style, applicant = seed
    rnd = random.Random(i)
    day = date(2025, 1, 2) + timedelta(days=rnd.randrange(0, 640))
    return (f"Sprawa nr {i} (wariant {attempt}). Temat: {topic}.\n"
            "Komórki odpowiadające: " + ", ".join(f"{d} ({DEPS[d]['name']})" for d in deps) + ".\n"
            f"Styl wniosku: {STYLE[style]}.\nStyl odpowiedzi komórek: {ans_style}.\nWnioskodawca: {APPLICANT[applicant]}.\n"
            f"Data wpływu: {day.isoformat()}.\n\n" + _example())


# ------------------------------------------------------------------ assembling and validation


def _offsets(text: str, frag: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(re.escape(frag), text)] if frag and len(frag) >= 2 else []


def letter_text(case: dict) -> str:
    deps = [DEPS[a["department"]]["name"] for a in case["answers"]]
    n = len(case["paragraphs"])
    body = []
    for p in sorted(case["paragraphs"], key=lambda p: p["no"]):
        body += ([f"Ad {p['no']}"] if n > 1 else []) + [p["text"].strip()]
    return "\n".join(["URZĄD MIASTA BYDGOSZCZY", "Biuro Komunikacji Społecznej", f"Bydgoszcz, dnia {case['date']}", case["number"], "",
                      "w odpowiedzi na wniosek o udostępnienie informacji publicznej, na podstawie informacji przekazanych przez "
                      + " oraz ".join(deps) + ", przekazuję poniższe wyjaśnienia.", *body, "", "Łączę wyrazy szacunku,",
                      "Biuro Komunikacji Społecznej", "Urząd Miasta Bydgoszczy", "e-mail: bip@um.bydgoszcz.pl"])


def build_case(i: int, seed: tuple, out: dict) -> dict:
    day = date(2025, 1, 2) + timedelta(days=random.Random(i).randrange(0, 640))
    case = {"id": f"SYN-UMB-{i:03d}", "date": day.isoformat(), "number": f"BKS.IV.1431.{700 + i}.{day.year}",
            "title": out["title"].strip(), "topic": seed[0], "style": seed[2], "answer_style": seed[3], "applicant": seed[4],
            "request_text": out["request_text"].strip(),
            "answers": [{"file": f"{a['department']}.txt", "department": a["department"], "text": a["text"].strip()} for a in out["answers"]],
            "paragraphs": sorted(out["paragraphs"], key=lambda p: p["no"])}
    case["letter_text"] = letter_text(case)
    docs = {"request_text": case["request_text"], **{a["file"]: a["text"] for a in case["answers"]}}
    spans = []
    for p in out["pii"]:
        for doc, txt in docs.items():
            for s, e in _offsets(txt, p["text"].strip()):
                spans.append({"doc": doc, "start": s, "end": e, "type": p["type"], "text": txt[s:e], "role": p["role"]})
    uniq = {(s["doc"], s["start"], s["end"]): s for s in spans}
    case["gold"] = {"questions": [q.strip() for q in out["questions"]], "departments": [a["department"] for a in out["answers"]],
                    "ad": [{"no": p["no"], "facts": [f.strip() for f in p["facts"] if f.strip()]} for p in case["paragraphs"]],
                    "pii": sorted(uniq.values(), key=lambda s: (s["doc"], s["start"]))}
    return case


def validate_case(c: dict) -> list[str]:
    errs = []
    g = c["gold"]
    docs = {"request_text": c["request_text"], **{a["file"]: a["text"] for a in c["answers"]}}
    for s in g["pii"]:
        if docs.get(s["doc"], "")[s["start"]:s["end"]] != s["text"]:
            errs.append(f"pii span {s['text']!r} does not match {s['doc']}")
    if not any(s["doc"] == "request_text" for s in g["pii"]):
        errs.append("no PII in the request")
    for d in g["departments"]:
        if d not in DEPS:
            errs.append(f"unknown department {d}")
    nos = [p["no"] for p in c["paragraphs"]]
    if nos != list(range(1, len(g["questions"]) + 1)):
        errs.append(f"paragraphs {nos} vs {len(g['questions'])} questions")
    answers = [a["text"] for a in c["answers"]]
    bad = check_numbers([p["text"] for p in c["paragraphs"]], answers)
    if bad:
        errs.append(f"letter numbers not in answers: {bad[:4]}")
    all_ans = "\n".join(answers)
    by_no = {p["no"]: p["text"] for p in c["paragraphs"]}
    for a in g["ad"]:
        for f in a["facts"]:
            if f not in by_no.get(a["no"], ""):
                errs.append(f"fact {f!r} not in Ad {a['no']}")
            elif f not in all_ans and not (re.search(r"\d", f) and not check_numbers([f], answers)):
                errs.append(f"fact {f!r} not in answers")
    if not any(a["facts"] for a in g["ad"]):
        errs.append("no Ad facts")
    for p in c["paragraphs"]:
        if re.search(r"(?i)\b[\w.]+@(?!example\.com|um\.bydgoszcz\.pl)[\w.-]+\.\w+", p["text"]):
            errs.append("non-example e-mail in letter")
    return errs


def validate_dir(d: Path) -> tuple[int, int]:
    f = d / "cases.jsonl"
    if not f.is_file():
        print(f"brak {f}")
        return 0, 1
    n = bad = 0
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        n += 1
        e = validate_case(c)
        if e:
            bad += 1
            print(c["id"], "; ".join(e))
    print(f"Walidacja {f}: {n} spraw, błędnych {bad}")
    return n, bad


# ------------------------------------------------------------------ mock model (no key, no network)


def mock_transport(provider, model, system, user, schema, max_tokens, timeout) -> dict:
    m = re.search(r"Sprawa nr (\d+)", user)
    i = int(m.group(1)) if m else 1
    seed = SEEDS[(i - 1) % len(SEEDS)]
    rnd = random.Random(i)
    name = rnd.choice(["Anna Testowa", "Piotr Próbny", "Ewa Przykładowa", "Marek Fikcyjny"])
    n = 1 if seed[2] in ("krotki_email", "pismo_odreczne", "pismo_parafii") else 3
    qs = [f"Ile wyniosły w 2025 r. wydatki na zadanie {k} ({seed[0]})?" for k in range(1, n + 1)]
    nums = [f"{rnd.randrange(100, 999)}.{rnd.randrange(100, 999)},{rnd.randrange(10, 99)} zł" for _ in qs]
    dep = seed[1][0]
    ans = f"{dep}.1431.{i}.2026\nBiuro Komunikacji Społecznej\nw miejscu\n" + "\n".join(
        (f"Ad {k}\n" if seed[3] == "ad" else "") + f"Wydatki na zadanie {k} wyniosły {v}." for k, v in enumerate(nums, 1)) \
        + "\nSprawę prowadzi: Jan Urzędniczy, tel. 52 58 00 000"
    req = (f"Bydgoszcz, 2.03.2026\n{name}\nul. Testowa {i}/2\n85-0{i:02d} Bydgoszcz\ne-mail: test{i}@example.com\n\n"
           "Wniosek o udostępnienie informacji publicznej\n" + "\n".join(f"{k}. {q}" for k, q in enumerate(qs, 1)) + f"\n\n{name}")
    out = {"title": seed[0][:80], "request_text": req, "questions": qs, "answers": [{"department": dep, "text": ans}],
           "paragraphs": [{"no": k, "text": f"Informuję, że wydatki na zadanie {k} wyniosły {v}.", "facts": [v]} for k, v in enumerate(nums, 1)],
           "pii": [{"text": name, "type": "OSOBA", "role": "wnioskodawca"}, {"text": f"ul. Testowa {i}/2", "type": "ADRES", "role": "wnioskodawca"},
                   {"text": f"test{i}@example.com", "type": "EMAIL", "role": "wnioskodawca"},
                   {"text": "Jan Urzędniczy", "type": "OSOBA", "role": "pracownik"}]}
    return {"text": json.dumps(out, ensure_ascii=False), "input_tokens": 0, "output_tokens": 0}


# ------------------------------------------------------------------ main


def to_archive(c: dict) -> dict:
    return {"id": c["id"], "date": c["date"], "title": c["title"], "request_text": c["request_text"],
            "response_text": "[Odpowiedź]\n" + c["letter_text"], "departments": c["gold"]["departments"],
            "outcome": "udostepnienie", "source": "syntetyczne_umb"}


README = """# data-samples/syntetyczne_umb – sprawy syntetyczne na wzór spraw UMB

**Pochodzenie:** wygenerowane skryptem `scripts/gen_synthetic_umb.py` (tor C, T14) przez model {model} na podstawie
stylu 10 spraw z `data-partner/umb/` (jako wzorzec w prompcie: wniosek 543.2026, odpowiedź Schroniska, pismo BKS).
Wszystkie osoby, adresy, telefony i e-maile są fikcyjne. Licencja jak repozytorium (MIT).

| Plik | Zawartość |
|---|---|
| `cases.jsonl` | {n} spraw: `request_text`, `answers[{{file, department, text}}]`, `paragraphs` i `letter_text` (pismo BKS), `gold` = `questions`, `departments`, `ad[{{no, facts}}]` (fakty, które muszą trafić do akapitu „Ad n”), `pii[{{doc, start, end, type, text, role}}]` |
| `archiwum.jsonl` | te same sprawy w formacie archiwum (`id, date, title, request_text, response_text, departments, outcome, source`) |
| `generation.json` | model, data, koszt, liczba wywołań, odrzucone sprawy |

Walidacja: `python scripts/gen_synthetic_umb.py --validate data-samples/syntetyczne_umb` (spany PII zgodne z tekstem,
wydziały istnieją w `departments.json`, każda liczba z pisma jest w odpowiedzi wydziału z tym samym słowem obok,
fakty „Ad n” są w akapicie n i w odpowiedziach).
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=44)
    ap.add_argument("--provider", default="anthropic:sonnet")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--mock", action="store_true", help="fake model, isolated cache and usage (no key, no network)")
    ap.add_argument("--validate", type=Path, metavar="DIR")
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--max-usd", type=float, default=3.0, help="stop once this run has spent more than this")
    a = ap.parse_args(argv)
    if a.validate:
        n, bad = validate_dir(a.validate)
        return 0 if n and not bad else 1
    os.environ.setdefault("UDIP_LLM_TAG", "T14")
    if a.mock:
        tmp = Path(tempfile.mkdtemp(prefix="udip_mock_"))
        os.environ["UDIP_DATA_DIR"] = str(tmp)
        os.environ["UDIP_LLM_CACHE_DIR"] = str(tmp / "llm_cache")
        llm.set_transport(mock_transport)
        a.provider = "openai_compat:mock"
        a.out = a.out or tmp / "syntetyczne_umb"
    out_dir = a.out or OUT
    if llm.provider_for(a.provider) == "rules":
        print(f"Provider {a.provider} niedostępny (brak ANTHROPIC_API_KEY albo budżetu). Nic nie wygenerowano.", file=sys.stderr)
        return 2
    before = llm.usage()
    cases, rejected = [], []
    for i in range(1, a.n + 1):
        if llm.usage()["usd"] - before["usd"] > a.max_usd:
            print(f"Przerwano przed sprawą {i}: wydano ponad ${a.max_usd}", file=sys.stderr)
            break
        seed = SEEDS[(i - 1) % len(SEEDS)]
        case, errs = None, ["no answer"]
        for attempt in range(a.retries + 1):
            out = llm.complete_json("gen_synthetic_umb", SYSTEM, _user(i, seed, attempt), _schema(), provider=a.provider, max_tokens=6000)
            if not out:
                errs = [llm.LAST.get("error", "no answer")]
                if llm.LAST.get("error") == "budget":
                    break
                continue
            case = build_case(i, seed, out)
            errs = validate_case(case)
            if not errs:
                break
        if case and not errs:
            cases.append(case)
        else:
            rejected.append({"i": i, "topic": seed[0], "errors": errs[:5]})
        print(f"{i:3d}/{a.n} {'OK ' if case and not errs else 'ODRZ'} {seed[0][:60]}  "
              f"${llm.usage()['usd'] - before['usd']:.3f}", file=sys.stderr)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cases.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
    (out_dir / "archiwum.jsonl").write_text("".join(json.dumps(to_archive(c), ensure_ascii=False) + "\n" for c in cases),
                                            encoding="utf-8")
    after = llm.usage()
    model = llm.model_for(a.provider)
    meta = {"model": model, "provider": a.provider, "generated": date.today().isoformat(), "requested": a.n, "valid": len(cases),
            "rejected": rejected, "usd": round(after["usd"] - before["usd"], 4), "calls": after["calls"] - before["calls"],
            "cached": after["cached"] - before["cached"]}
    (out_dir / "generation.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "README.md").write_text(README.format(model=model, n=len(cases)), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("valid", "usd", "calls", "cached")}, ensure_ascii=False))
    print(f"Zapisano {out_dir}")
    n, bad = validate_dir(out_dir)
    return 0 if n and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
