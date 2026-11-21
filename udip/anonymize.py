"""Anonimizacja odpowiedzi UDIP: propozycja (szary) → akceptacja urzędnika → redakcja (czarny).

Wykrywa (tylko biblioteka standardowa, licencja kodu: MIT jak reszta pakietu):
- PESEL (z sumą kontrolną i poprawną datą), NIP, REGON (9/14), IBAN PL (mod 97), nr dowodu osobistego (suma kontrolna), paszport;
- e-mail, telefon, kod pocztowy z miejscowością, adres (ul./al./os./pl. + numer), numer księgi wieczystej, nr rejestracyjny pojazdu;
- imię i nazwisko: słownik polskich imion z odmianą + wielka litera; „Pan/Pani X”; podpis po „Z poważaniem”.
Funkcjonariusze publiczni z listy `--keep` (art. 5 ust. 2 UDIP: jawne dane związane z pełnieniem funkcji)
dostają status „review”, a nie „suggested”: urzędnik decyduje.

Wyjście: lista spanów {id,start,end,text,type,confidence,reason,status}. Statusy: suggested (szary),
review (do decyzji), accepted (czarny), rejected (jawne).

Gdy provider != "rules", detect() dokłada spany z llm_tasks.anonymization.spans_llm (hook z T00) ze statusem
„review” – nigdy nie są przyjmowane automatycznie; spany nachodzące na wynik reguł są pomijane.

CLI i selftest: .claude/skills/udip-anonimizacja/scripts/anonymize.py
"""
from __future__ import annotations

import html as htmlmod
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------- walidatory


def pesel_ok(s: str) -> bool:
    if not re.fullmatch(r"\d{11}", s):
        return False
    w = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    if (10 - sum(int(s[i]) * w[i] for i in range(10)) % 10) % 10 != int(s[10]):
        return False
    yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
    century = {0: 1900, 20: 2000, 40: 2100, 60: 2200, 80: 1800}
    base = (mm // 20) * 20
    if base not in century:
        return False
    try:
        date(century[base] + yy, mm - base, dd)
    except ValueError:
        return False
    return True


def nip_ok(s: str) -> bool:
    d = re.sub(r"\D", "", s)
    if len(d) != 10:
        return False
    w = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    c = sum(int(d[i]) * w[i] for i in range(9)) % 11
    return c != 10 and c == int(d[9])


def regon_ok(s: str) -> bool:
    d = re.sub(r"\D", "", s)
    if len(d) == 9:
        w = [8, 9, 2, 3, 4, 5, 6, 7]
    elif len(d) == 14:
        w = [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8]
    else:
        return False
    c = sum(int(d[i]) * w[i] for i in range(len(w))) % 11 % 10
    return c == int(d[-1])


def iban_ok(s: str) -> bool:
    d = re.sub(r"\s", "", s).upper()
    if d.isdigit() and len(d) == 26:
        d = "PL" + d
    if not re.fullmatch(r"PL\d{26}", d):
        return False
    r = d[4:] + d[:4]
    num = "".join(str(int(ch, 36)) for ch in r)
    return int(num) % 97 == 1


def idcard_ok(s: str) -> bool:
    s = s.replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{3}\d{6}", s):
        return False
    vals = [ord(c) - 55 for c in s[:3]] + [int(c) for c in s[3:]]
    w = [7, 3, 1, 0, 7, 3, 1, 7, 3]
    return sum(v * x for v, x in zip(vals, w)) % 10 == vals[3]


# ---------------------------------------------------------------- słowniki


def _load_lines(name: str) -> list[str]:
    p = DATA / name
    if not p.exists():
        return []
    return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]


def name_forms(base: str) -> set[str]:
    """Proste formy przypadków dla polskich imion (mianownik → dop., cel., bier., narz., miejsc.)."""
    f = {base}
    if base.endswith("a"):  # żeńskie i nieliczne męskie (Kuba, Barnaba)
        st = base[:-1]
        f |= {st + "y", st + "ę", st + "ą", st + "o"}
        if st.endswith(("i", "j")):
            f |= {st + "i"}
        if st.endswith("k"):
            f |= {st[:-1] + "ce", st + "i"}
        elif st.endswith("g"):
            f |= {st[:-1] + "dze", st + "i"}
        elif st.endswith("r"):
            f |= {st[:-1] + "rze"}
        elif st.endswith("t"):
            f |= {st[:-1] + "cie"}
        elif st.endswith("d"):
            f |= {st[:-1] + "dzie"}
        elif st.endswith("ł"):
            f |= {st[:-1] + "le"}
        else:
            f |= {st + "ie", st + "i"}
    else:
        st = base
        if base.endswith("ek"):
            st = base[:-2] + "k"   # Marek → Marka
        elif base.endswith("eł"):
            st = base[:-2] + "ł"   # Paweł → Pawła
        elif base.endswith("ń"):
            st = base[:-1] + "ni"
        f |= {st + "a", st + "owi", st + "em", st + "ie", st + "u"}
        if base.endswith("y") or base.endswith("i"):  # Antoni, Jerzy
            f |= {base + "ego", base + "emu", base + "m"}
        if base.endswith("r"):
            f |= {base[:-1] + "rze"}
        if base.endswith("ł"):
            f |= {st[:-1] + "le" if st.endswith("ł") else base[:-1] + "le"}
        if base.endswith("t"):
            f |= {base[:-1] + "cie"}
        if base.endswith("d"):
            f |= {base[:-1] + "dzie"}
    return f


FIRST_NAMES = _load_lines("imiona.txt")
NAME_FORMS: dict[str, str] = {}
for _n in FIRST_NAMES:
    for _f in name_forms(_n):
        NAME_FORMS.setdefault(_f, _n)
STOP_CAPS = set(_load_lines("nie_nazwiska.txt"))


def _load_tsv(name: str) -> tuple[dict[str, str], set[str]]:
    """T28 lexicon (udip/data/names/*.tsv, built by scripts/build_names.py): form → base form, plus the forms that
    are also ordinary words („Mieszka”, „Zając”); those count only next to another name part."""
    out: dict[str, str] = {}
    amb: set[str] = set()
    p = DATA / "names" / name
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "\t" in line:
                form, base, *flag = line.split("\t")
                if form not in STOP_CAPS:
                    out[form] = base
                    if flag:
                        amb.add(form)
    return out, amb


_first, _first_amb = _load_tsv("imiona.tsv")
for _f, _b in _first.items():
    if _f not in _first_amb:
        NAME_FORMS.setdefault(_f, _b)
AMBIG_FIRST = {f: b for f, b in _first.items() if f in _first_amb and f not in NAME_FORMS}
SURNAME_FORMS, SURNAME_AMB = _load_tsv("nazwiska.tsv")
UPPER_NAMES = {f.upper(): b for f, b in NAME_FORMS.items()}
OFFICIALS = _load_lines("funkcjonariusze.txt")
SPECIAL = [(l.split("\t")[0], re.compile(l.split("\t")[1], re.I)) for l in _load_lines("kategorie_szczegolne.txt") if "\t" in l]
PATRON = re.compile(r"(?:\bśw\.|\bim\.|\bul\.|\bal\.|\bpl\.|\bos\.|\bulic\w*|\balei|\baleja|\bplac\w*|\bosiedl\w*|\bparafi\w*|\bkości\w*|\brond\w*|\bmost\w*|\bszkoł\w*|\bpark\w*)\s*$", re.I)
PUBLIC_ADDR = [a.casefold() for a in _load_lines("jawne_adresy.txt")]
PUBLIC_EMAIL_DOMAINS = tuple(d.casefold() for d in _load_lines("jawne_domeny.txt"))

UP = "A-ZĄĆĘŁŃÓŚŹŻ"
LOW = "a-ząćęłńóśźż"
SURNAME = rf"[{UP}][{LOW}]+(?:-[{UP}][{LOW}]+)?"
WORD_CAP = re.compile(rf"\b[{UP}][{LOW}]+\b")

# ---------------------------------------------------------------- wykrywanie


@dataclass
class Span:
    start: int
    end: int
    text: str
    type: str
    confidence: float
    reason: str
    status: str = "suggested"
    id: str = ""


PATTERNS: list[tuple[str, re.Pattern, float, str, object]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), 0.99, "adres e-mail", None),
    ("IBAN", re.compile(r"\b(?:PL ?)?\d{2}(?: ?\d{4}){6}\b"), 0.97, "numer rachunku (IBAN, suma mod 97)", iban_ok),
    ("PESEL", re.compile(r"(?<!\d)\d{11}(?!\d)"), 0.99, "PESEL (suma kontrolna i data)", pesel_ok),
    ("NIP", re.compile(r"(?<!\d)(?:\d{3}-\d{3}-\d{2}-\d{2}|\d{3}-\d{2}-\d{2}-\d{3}|\d{10})(?!\d)"), 0.9, "NIP (suma kontrolna)", nip_ok),
    ("REGON", re.compile(r"(?<!\d)(?:\d{14}|\d{9})(?!\d)"), 0.85, "REGON (suma kontrolna)", regon_ok),
    ("DOWOD", re.compile(r"\b[A-Z]{3} ?\d{6}\b"), 0.95, "seria i nr dowodu osobistego (suma kontrolna)", idcard_ok),
    ("PASZPORT", re.compile(r"(?i:paszport\w*)[^\n]{0,20}?\b([A-Z]{2}\d{7})\b"), 0.9, "numer paszportu", None),
    ("KW", re.compile(r"\b[A-Z]{2}\d[A-Z]/\d{8}/\d\b"), 0.95, "numer księgi wieczystej", None),
    ("TELEFON", re.compile(r"(?<![\w/])(?:\+48[ -]?)?(?:\d{3}[ -]\d{3}[ -]\d{3}|\d{2}[ -]\d{3}[ -]\d{2}[ -]\d{2}|(?<=tel\. )\d{9}|(?<=tel\.: )\d{9}|(?<=telefon: )\d{9})(?![\w/])"), 0.9, "numer telefonu", None),
    ("KOD_MIEJSC", re.compile(rf"\b\d{{2}}-\d{{3}} [{UP}][{LOW}]+(?:[ -][{UP}][{LOW}]+)?"), 0.8, "kod pocztowy z miejscowością (część adresu)", None),
    ("ADRES", re.compile(rf"\b(?:ul\.|ulica|al\.|aleja|os\.|osiedle|pl\.|plac)\s+(?:[{UP}0-9][\w.ąćęłńóśźżĄĆĘŁŃÓŚŹŻ-]*\s+){{0,3}}\d+[A-Za-z]?(?:\s*/\s*\d+[A-Za-z]?|\s+m\.\s*\d+|\s+lok\.\s*\d+)?"), 0.85, "adres zamieszkania", None),
    ("REJESTRACJA", re.compile(r"\b(?:nr rej\.|numer rejestracyjny|tablic\w* rejestracyjn\w*)\s*:?\s*([A-Z]{2,3} ?[0-9A-Z]{4,5})\b"), 0.9, "numer rejestracyjny pojazdu", None),
]


def detect_patterns(text: str) -> list[Span]:
    out: list[Span] = []
    for typ, rx, conf, reason, validator in PATTERNS:
        for m in rx.finditer(text):
            g = 1 if m.groups() else 0
            s, e = m.span(g)
            val = m.group(g)
            if validator and not validator(val):
                continue
            out.append(Span(s, e, val, typ, conf, reason))
    return out


def detect_names(text: str) -> list[Span]:
    out: list[Span] = []
    tokens = list(WORD_CAP.finditer(text))
    i = 0
    while i < len(tokens):
        t = tokens[i]
        w = t.group()
        if w in NAME_FORMS and w not in STOP_CAPS and PATRON.search(text[max(0, t.start() - 15):t.start()]):
            i += 1  # „św. Maksymiliana Kolbego”, „ul. Jana Pawła II” – patron/nazwa ulicy, nie osoba
            while i < len(tokens) and text[tokens[i - 1].end():tokens[i].start()] == " ":
                i += 1
            continue
        if w in NAME_FORMS and w not in STOP_CAPS:
            j, end = i, t.end()
            # kolejne imię lub nazwisko bezpośrednio po spacji
            while j + 1 < len(tokens) and text[tokens[j].end():tokens[j + 1].start()] in (" ", "-") and tokens[j + 1].group() not in STOP_CAPS and j - i < 2:
                j += 1
                end = tokens[j].end()
            if j > i:  # imię + nazwisko
                out.append(Span(t.start(), end, text[t.start():end], "OSOBA", 0.9, f"imię „{NAME_FORMS[w]}” + nazwisko"))
            else:
                out.append(Span(t.start(), end, w, "OSOBA", 0.6, f"samo imię „{NAME_FORMS[w]}”"))
            i = j + 1
            continue
        i += 1
    # T28: nieznane imię + nazwisko ze słownika („Ołena Szewczenko”, „Bogumił Krawczyk” gdy imię spoza listy)
    taken = [(x.start, x.end) for x in out]
    for k in range(1, len(tokens)):
        a, b = tokens[k - 1], tokens[k]
        w1, w2 = a.group(), b.group()
        if text[a.end():b.start()] != " " or w1 in STOP_CAPS or w2 in STOP_CAPS:
            continue
        if w1 in AMBIG_FIRST and (w2 in SURNAME_FORMS or w2 in NAME_FORMS or w2 not in AMBIG_FIRST):
            why = f"imię „{AMBIG_FIRST[w1]}” + nazwisko"  # „Róża Wrona”, „Lew Tołstoj”: ambiguous first name, only in a pair
        elif w2 in SURNAME_FORMS and w2 not in SURNAME_AMB:
            why = f"nazwisko „{SURNAME_FORMS[w2]}” ze słownika"
        else:
            continue
        if any(s <= a.start() < e or s < b.end() <= e for s, e in taken):
            continue
        if PATRON.search(text[max(0, a.start() - 15):a.start()]) or not re.fullmatch(rf"[{UP}][{LOW}]+", w1):
            continue
        out.append(Span(a.start(), b.end(), text[a.start():b.end()], "OSOBA", 0.8, why))
    # imię WIELKIMI LITERAMI (rękopisy, nagłówki e-maili): „JERZY”, „ANNA KOWALSKA”
    for m in re.finditer(rf"\b([{UP}]{{3,}})(?:\s+([{UP}]{{3,}}(?:-[{UP}]{{3,}})?))?\b", text):
        if m.group(1) in UPPER_NAMES and (m.group(2) or len(m.group(1)) >= 4):  # „ELI”, „ADA” alone are acronyms
            out.append(Span(m.start(), m.end(), m.group(0), "OSOBA", 0.85 if m.group(2) else 0.7, "imię (wielkie litery)" + (" + nazwisko" if m.group(2) else "")))
    # inicjał + nazwisko: „E. Góra”, „J. Nowak”
    for m in re.finditer(rf"(?<![\w.])([{UP}])\.\s?({SURNAME})\b", text):
        if m.group(2) not in STOP_CAPS and not PATRON.search(text[max(0, m.start() - 12):m.start()]):
            sig = re.search(r"(?i)(pozdrawiam|poważaniem|szacunku|\|)\s*$", text[max(0, m.start() - 30):m.start()])
            out.append(Span(m.start(), m.end(), m.group(0), "OSOBA", 0.85 if sig else 0.65, "inicjał + nazwisko" + (" w podpisie" if sig else "")))
    # „Pan/Pani/Państwo X” bez imienia ze słownika
    for m in re.finditer(rf"\b(?:Pan|Pani|Pana|Panu|Panią|Panem|p\.)\s+({SURNAME}(?:\s+{SURNAME})?)", text):
        s, e = m.span(1)
        if m.group(1).split()[0] not in STOP_CAPS:
            out.append(Span(s, e, m.group(1), "OSOBA", 0.85, "zwrot grzecznościowy + nazwisko"))
    # samo nazwisko o typowej końcówce (-ski, -cka, -wicz…), bez imienia: niska pewność → status review
    sx = re.compile(rf"(?<![.!?]\s)(?<!^)\b([{UP}][{LOW}]+(?:sk|ck|dzk)(?:i|a|iego|iemu|im|iej|ą)|[{UP}][{LOW}]+wicz(?:a|owi|em|u)?)\b", re.M)
    for m in sx.finditer(text):
        w = m.group(1)
        before = text[max(0, m.start(1) - 40):m.start(1)]
        after = text[m.end(1):m.end(1) + 40]
        in_name = (re.search(rf"[{UP}][{LOW}]+[ -]$", before) or re.match(rf"[ -][{UP}]", after) or before.endswith("-")
                   or PATRON.search(before))  # „ulicy Fordońska”, „ul. Kujawska”
        if w not in STOP_CAPS and not in_name:  # pomija nazwy instytucji: „Urząd Miejski”, „Bydgoski Park”
            out.append(Span(m.start(1), m.end(1), w, "OSOBA", 0.6, "wyraz o końcówce typowej dla nazwiska"))
    # podpis po „Z poważaniem”
    for m in re.finditer(rf"(?:Z poważaniem|Z wyrazami szacunku|Pozdrawiam)[,.]?\s*\n\s*({SURNAME}\s+{SURNAME})", text):
        s, e = m.span(1)
        a, b = m.group(1).split()[:2]
        if a in STOP_CAPS or b in STOP_CAPS:
            continue  # „Kierownik Referatu”, „Dyrektor Wydziału”
        out.append(Span(s, e, m.group(1), "OSOBA", 0.9 if a in NAME_FORMS else 0.6, "podpis pod pismem"))
    return out


def merge(spans: list[Span]) -> list[Span]:
    spans.sort(key=lambda x: (x.start, -(x.end - x.start), -x.confidence))
    res: list[Span] = []
    for s in spans:
        if res and s.start < res[-1].end:
            last = res[-1]
            if s.end > last.end:
                last.end = s.end
                last.text = None  # uzupełnione niżej
            if s.confidence > last.confidence:
                last.type, last.confidence, last.reason = s.type, s.confidence, s.reason
            continue
        res.append(s)
    return res


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).casefold()


BIRTH = re.compile(r"\b(?:ur\.|urodzon\w*)\s+(?:dnia\s+)?(?:\d{1,2}[.\-/ ]\s?(?:\d{1,2}|[a-ząćęłńóśźż]+)[.\-/ ]\s?\d{4}|\d{4})(?:\s?r\.)?(?:\s+w\s+[A-ZŁŚŻ][\wąćęłńóśźż-]+)?")
PLOT = re.compile(r"\b(?:działk\w*|dz\.)\s*(?:ewid\w*\.?\s*)?(?:nr\s*)?(\d+(?:/\d+)?)")


def detect_special(text: str) -> list[Span]:
    """Dane z listy UMB „Dane podlegające anonimizacji”, których nie łapią wzorce identyfikatorów."""
    out = [Span(m.start(), m.end(), m.group(), "URODZENIE", 0.9, "data i miejsce urodzenia") for m in BIRTH.finditer(text)]
    out += [Span(m.start(1), m.end(1), m.group(1), "DZIALKA", 0.6, "nr działki – anonimizuj, jeśli identyfikuje prywatnego właściciela") for m in PLOT.finditer(text)]
    pos = 0
    for sent in re.split(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ])|\n\s*\n|\n(?=\s*\d+[.)]\s)", text):
        st = text.find(sent, pos)
        pos = st + len(sent)
        for cat, rx in SPECIAL:
            if cat in ("URODZENIE", "DZIALKA"):
                continue
            if rx.search(sent):
                out.append(Span(st, st + len(sent.rstrip()), sent.strip(), "SZCZEGOLNE_" + cat, 0.55, f"możliwe dane szczególne ({cat.lower()}) – lista UMB"))
                break
        if SECRET.search(sent):
            out.append(Span(st, st + len(sent.rstrip()), sent.strip(), "TAJEMNICA", 0.6,
                            "zastrzeżona tajemnica przedsiębiorcy (art. 5 ust. 1 u.d.i.p.) – zdecyduj, czego dotyczy"))
    return out


SECRET = re.compile(r"(?i)\btajemnic\w*\s+(przedsiębiorstw\w*|przedsiębiorc\w*|handlow\w*)|\bknow-how\b")


def _sentence_span(s: Span) -> bool:
    return s.type.startswith("SZCZEGOLNE") or s.type == "TAJEMNICA"


def _official(span_text: str, keep: list[str]) -> bool:
    toks = [t for t in re.findall(r"\w+", norm(span_text)) if len(t) >= 4]
    for k in keep:
        for kt in re.findall(r"\w+", norm(k)):
            if len(kt) >= 5 and any(t[:5] == kt[:5] and abs(len(t) - len(kt)) <= 4 for t in toks):
                if len(re.findall(r"\w+", norm(k))) == 1 or kt == re.findall(r"\w+", norm(k))[-1]:
                    return True  # zgodność nazwiska (z odmianą: Bruski/Bruskiego)
    return False


def detect_rules(text: str, keep: list[str] | None = None, min_conf: float = 0.5) -> list[Span]:
    """Wykrywanie samymi regułami."""
    names = detect_names(text)
    special = detect_special(text)
    spans = merge(detect_patterns(text) + names + [s for s in special if not _sentence_span(s)])
    spans += [s for s in special if _sentence_span(s)]  # zdania nie scalają się z danymi w nich
    spans.sort(key=lambda x: x.start)
    keep = list(keep or []) + OFFICIALS
    keep_n = [norm(k) for k in keep]
    out = []
    for n, s in enumerate(spans, 1):
        s.text = text[s.start:s.end]
        s.id = f"s{n}"
        if s.confidence < min_conf:
            continue
        if s.type in ("ADRES", "KOD_MIEJSC") and any(a in norm(s.text) or norm(s.text) in a for a in PUBLIC_ADDR):
            continue  # adres urzędu / jednostki: jawny
        if s.type == "EMAIL" and norm(s.text).split("@")[-1].endswith(PUBLIC_EMAIL_DOMAINS):
            continue  # służbowa skrzynka instytucji (bip@um.bydgoszcz.pl)
        if s.type == "ADRES" and re.search(r"(?i)(inwestycj|kompleks|budow\w|obiekt|szkoł|budynek|basen|siedzib)\w*[^.]{0,80}$", text[max(0, s.start - 90):s.start]):
            s.status = "review"
            s.reason += "; prawdopodobnie adres obiektu/inwestycji (jawny) – zdecyduj"
        elif s.type == "OSOBA" and (any(k and (k in norm(s.text) or norm(s.text) in k) for k in keep_n) or _official(s.text, keep)):
            s.status = "review"
            s.reason += "; na liście osób pełniących funkcje publiczne (art. 5 ust. 2 UDIP) – zdecyduj"
        elif s.confidence < 0.75 or _sentence_span(s):
            s.status = "review"
        out.append(s)
    return _learned(text, out)


def _learned(text: str, spans: list[Span]) -> list[Span]:
    """T25: the clerk's remembered decisions come first. "allow" drops rule spans on that phrase (any person span
    touching it, other spans lying inside it); "redact" adds a suggested span, replacing rule spans inside it."""
    try:
        from . import learning
        found = learning.apply_rules(text)
    except Exception:
        return spans
    if not found:
        return spans
    allow = [r for r in found if r["action"] == "allow"]
    hit = lambda s, r: s.start < r["end"] and r["start"] < s.end  # noqa: E731
    spans = [s for s in spans if not any(hit(s, a) and (s.type == "OSOBA" or (s.start >= a["start"] and s.end <= a["end"]))
                                         for a in allow)]
    n = 0
    for r in (x for x in found if x["action"] == "redact"):
        if any(s.start <= r["start"] and r["end"] <= s.end for s in spans):
            continue  # already covered by a rule span or an earlier learned span
        spans = [s for s in spans if not (r["start"] <= s.start and s.end <= r["end"])]
        n += 1
        spans.append(Span(r["start"], r["end"], text[r["start"]:r["end"]], r["category"] or "RECZNIE", 0.9, learning.REASON_PII,
                          "suggested", f"w{n}"))
    spans.sort(key=lambda x: x.start)
    return spans


def detect(text: str, keep: list[str] | None = None, min_conf: float = 0.5, provider: str | None = None) -> list:
    spans = detect_rules(text, keep=keep, min_conf=min_conf)
    if provider == "rules":
        return spans
    from . import llm
    p = llm.provider_for(provider)
    if p == "rules":
        return spans
    from .llm_tasks import anonymization as la
    extra = la.spans_llm(text, provider=p) or []
    n = len(spans)
    for e in extra:
        try:
            s, t = int(e["start"]), int(e["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= s < t <= len(text)) or any(s < x.end and x.start < t for x in spans):
            continue
        n += 1
        spans.append(Span(start=s, end=t, text=text[s:t], type=str(e.get("type", "OSOBA")), confidence=float(e.get("confidence", 0.6)),
                          reason="model: " + str(e.get("reason", "")), status="review", id=f"s{n}"))
    spans.sort(key=lambda x: x.start)
    return spans


# ---------------------------------------------------------------- zastosowanie i podgląd

LABEL = {"OSOBA": "[imię i nazwisko]", "ADRES": "[adres]", "KOD_MIEJSC": "[adres]", "EMAIL": "[e-mail]", "TELEFON": "[telefon]",
         "PESEL": "[PESEL]", "NIP": "[NIP]", "REGON": "[REGON]", "IBAN": "[nr rachunku]", "DOWOD": "[nr dowodu]",
         "PASZPORT": "[nr paszportu]", "KW": "[nr księgi wieczystej]", "REJESTRACJA": "[nr rejestracyjny]",
         "URODZENIE": "[data i miejsce urodzenia]", "DZIALKA": "[nr działki]", "TAJEMNICA": "[tajemnica przedsiębiorcy]"}


def _union(spans: list[dict]) -> list[dict]:
    """Nachodzące na siebie spany → jeden span od najwcześniejszego początku do najpóźniejszego końca.
    Typ, id i status bierze z najdłuższego członka grupy (zdanie SZCZEGOLNE_* połyka OSOBA w środku)."""
    out: list[tuple[dict, dict]] = []  # (span wynikowy, najdłuższy członek)
    for s in sorted(spans, key=lambda x: (x["start"], -x["end"])):
        if out and s["start"] < out[-1][0]["end"]:
            cur, best = out[-1]
            if s["end"] - s["start"] > best["end"] - best["start"]:
                best = s
            cur = dict(best, start=cur["start"], end=max(cur["end"], s["end"]))
            out[-1] = (cur, best)
        else:
            out.append((dict(s), s))
    return [c for c, _ in out]


def flatten(spans: list[dict]) -> list[dict]:
    """Spany bez nakładania się, do redakcji i eksportu: zaakceptowane scalone (wygrywają), propozycje/do decyzji
    scalone między sobą i pominięte tam, gdzie nachodzą na zaakceptowane; odrzucone pominięte (zostają jawne)."""
    acc = _union([s for s in spans if s["status"] == "accepted"])
    rest = [s for s in spans if s["status"] in ("suggested", "review")
            and not any(s["start"] < a["end"] and a["start"] < s["end"] for a in acc)]
    return sorted(acc + _union(rest), key=lambda x: x["start"])


def apply(text: str, spans: list[dict], mode: str = "label", accept_all: bool = False) -> str:
    """mode: 'label' → [PESEL]; 'block' → █████ tej samej długości. Nachodzące spany redaguje jako jeden fragment."""
    chosen = [s for s in spans if s["status"] == "accepted" or (accept_all and s["status"] in ("suggested", "accepted"))]
    chosen = _union(chosen)
    chosen.sort(key=lambda s: s["start"], reverse=True)
    for s in chosen:
        rep = LABEL.get(s["type"], "[dane zanonimizowane]") if mode == "label" else "█" * (s["end"] - s["start"])
        text = text[:s["start"]] + rep + text[s["end"]:]
    return text


def preview_html(text: str, spans: list[dict], title: str = "Podgląd anonimizacji") -> str:
    """Szary = propozycja, pomarańczowa ramka = do decyzji, czarny = zaakceptowane (jak w treści zadania)."""
    style = {"suggested": "background:#adb5bd;color:#000", "review": "background:#fff;outline:2px dashed #e8590c",
             "accepted": "background:#000;color:#000", "rejected": "text-decoration:underline dotted"}
    parts, pos = [], 0
    for s in sorted(spans, key=lambda x: x["start"]):
        parts.append(htmlmod.escape(text[pos:s["start"]]))
        parts.append(f'<mark data-id="{s["id"]}" title="{htmlmod.escape(s["type"] + ": " + s["reason"])}" style="{style[s["status"]]}">{htmlmod.escape(text[s["start"]:s["end"]])}</mark>')
        pos = s["end"]
    parts.append(htmlmod.escape(text[pos:]))
    return f"""<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:Georgia,serif;max-width:820px;margin:24px auto;line-height:1.5}}pre{{white-space:pre-wrap;font-family:inherit}}mark{{padding:0 2px}}</style></head>
<body><h1>{title}</h1><p><mark style="{style['suggested']}">szary</mark> propozycja ·
<mark style="{style['review']}">ramka</mark> do decyzji urzędnika · <mark style="{style['accepted']}">czarny</mark> zaakceptowane</p>
<pre>{''.join(parts)}</pre></body></html>"""
