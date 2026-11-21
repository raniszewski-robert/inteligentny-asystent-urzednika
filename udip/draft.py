"""Projekt odpowiedzi na wniosek UDIP z odpowiedzi wydziałów, wersje końcowe, eksport DOCX (CONTRACTS §2).

Dwa tryby:
- template (domyślny, offline, deterministyczny): pytania z wniosku + akapity z odpowiedzi wydziałów, podstawa prawna, pouczenia;
- llm: akapity „Ad n” redaguje udip.llm_tasks.drafting.paragraphs_llm (hook z T00, dostawca wg udip.llm); wynik przechodzi
  kontrolę liczb (każda liczba musi wystąpić w odpowiedzi wydziału) i schematu; gdy nie przejdzie albo LLM jest
  niedostępny → tryb template, a report["mode_used"] zostaje "template".

CLI: .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py
Zależności: python-docx (MIT). Reszta: biblioteka standardowa.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from .analyze import DEFAULT_DEPTS, load_departments, route, split_questions
from .anonymize import DATA, apply as anon_apply, detect, flatten, preview_html
from .deadlines import deadline_days, deadline_extended, shift_to_working_day
from .export import BLOCK
from .letters import LETTER_TYPES
from .textpl import tokens

TEMPLATES = LETTER_TYPES
# Liczby: daty, kwoty z separatorem tysięcy (spacja, kropka, twarda spacja) i części dziesiętne z przecinkiem.
NUM = re.compile(r"\d{1,2}\.\d{1,2}\.\d{4}|\d{1,3}(?:[ .\u00a0\u202f]\d{3})+(?:,\d+)?|\d+(?:,\d+)?(?:\.\d+)?")
NEXT_WORD = re.compile(r"\s*(?:zł\b|[a-ząćęłńóśźż]{2,})", re.I)


def pl_date(d: date) -> str:
    m = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]
    return f"{d.day} {m[d.month - 1]} {d.year} r."


INSTITUTION = re.compile(r"(?i)prezydent|urz[aą]d|bks\b|referat|kancelari|wydzia[lł]|biuro|^od:|^do:|^dw:|^temat:|^wys[lł]ano:|szanown|wniosek|powa[zż]aniem|rejestracj|sidas|^witam|^dzie[nń] dobry")


def applicant_block(req: str) -> list[str]:
    """Adresat pisma: linie nagłówka wniosku z danymi wnioskodawcy (do pierwszej pustej linii), bez nazw urzędu
    i nagłówków e-maila. Gdy nic nie zostaje → znacznik do uzupełnienia."""
    lines = [l.strip() for l in req.splitlines()[:15]]
    out = []
    for l in lines:
        if not l:
            if out:
                break
            continue
        if re.match(r"^(Bydgoszcz|[A-ZŁŚŻ][a-ząęłńóśźż]+),?\s*(dnia\s*)?\d", l) or INSTITUTION.search(l):
            if out:
                break
            continue
        if len(l) > 60:  # to już treść, nie nagłówek
            break
        out.append(l)
    return out[:5] or ["[adresat – uzupełnij z rejestru]"]


def answer_body(ans: str) -> str:
    """Wycina z pisma wydziału samą treść merytoryczną (bez nagłówka, „w miejscu”, „Sprawę prowadzi”)."""
    m = re.search(r"(?is)(uprzejmie informuj[eę][:.]?|informuj[eę], [żz]e)\s*(.+)", ans)
    body = m.group(2) if m else ans
    body = re.split(r"(?im)^\s*(Sprawę prowadzi|Sporządził|Z poważaniem|Do wiadomości)", body)[0]
    return re.sub(r"^[,\s]*(że|iż)\s+", "", body.strip())


ABBR = re.compile(r"(?:\b(?:r|ul|nr|tj|np|ok|tys|mln|art|ust|pkt|poz|al|os|pl|św|ks|dr|inż|mgr)\.)$", re.I)


def _sentences(body: str) -> list[str]:
    """Zdania bez cięcia po skrótach („2025 r. 839 psom”, „ul. Jezuicka”)."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ])", re.sub(r"\s+", " ", body))
    out: list[str] = []
    for x in parts:
        if out and ABBR.search(out[-1]):
            out[-1] += " " + x
        else:
            out.append(x)
    return [x.strip()[0].upper() + x.strip()[1:] for x in out if x.strip()]


# ------------------------------------------------------------------ przypisanie zdań do pytań („Ad N”)
#
# Tier 1 (pewność 1.0): oznaczenia w odpowiedzi wydziału ([Ad N], Ad N., Ad. N – udip.dispatch.parse_reply, w tym
#   wypełniony formularz z pakietu), plik wgrany dla jednego pytania albo decyzja urzędnika (assignments).
# Tier 2 (reguły): typ odpowiedzi (kwota → pytanie o koszt, liczba → „ile”, dokument z numerem → prośba o treść
#   dokumentu, wykonawca → „z kim / komu”) zawęża kandydatów; potem wspólne słownictwo ważone odwrotnie do liczby
#   pytań, w których słowo występuje. Zdanie trafia do pytania tylko z wyraźną przewagą (MARGIN); inaczej idzie do
#   report["unassigned"] z kandydatami – nigdy nie jest wstawiane po cichu.

MIN_SCORE = 0.3
MARGIN = 0.2

Q_TYPES = {  # pytanie → jakiego typu odpowiedzi oczekuje
    "document": re.compile(r"(?i)(udost[eę]pn|przes[lł]a|przekaza|kopi|skan|tre[sś])\w*\W+(?:\w+\W+){0,6}?"
                           r"(umow|umów|unow|decyzj|uchwa|zarz[aą]dze|porozumie|aneks|dokument|protok|faktur|regulamin)"),
    "amount": re.compile(r"(?i)(?<!na )koszt|kwot|wysoko[sś]|bud[zż]et|wydatk|warto[sś]|wynagrodze|dotacj|przych[oó]d|doch[oó]d|ile wyni|ile wyda"),
    "count": re.compile(r"(?i)\bil[eu]\b|\bliczb|\bilo[sś][cć]"),
    "actor": re.compile(r"(?i)\bz kim\b|\bkomu\b|\bkto\b|\bkt[óo]r\w* (podmiot|firm)|\bjaki\w* (podmiot|firm|wykonawc)|\bwykonawc"),
}
S_TYPES = {  # zdanie → jakie typy odpowiedzi niesie; kandydaci = pytania choć jednego z tych typów
    "document": re.compile(r"(?i)\b(umow|decyzj|uchwa[lł]|zarz[aą]dzeni|porozumieni|aneks)\w*\s+(nr\.?\s*\S*\d|\S*\d+/\S+)"),
    "amount": re.compile(r"(?i)\d(?:[\d .  ]*\d)?(?:,\d+)?\s*(?:tys\.\s*|mln\s*)?(?:zł|złotych|pln)\b"),
    "count": None,  # liczba przy rzeczowniku (nie kwota, nie rok, nie numer dokumentu) – _is_count
    "actor": re.compile(r"(?i)\b(sprawuj\w*|realizowa[lł][oaiy]?|realizowali|realizuj\w*|prowadz[iąa]\w*|wykonuj\w*|"
                        r"wykonywa[lł]\w*|[sś]wiadcz\w*|odpowiada za)\b"),
}
_NON_COUNT = {"zł", "tys", "mln", "pln", "zło"}


def _is_count(sent: str) -> bool:
    for m in NUM.finditer(sent):
        raw = m.group().strip()
        if len(re.sub(r"\D", "", raw)) < 2 or re.fullmatch(r"(19|20)\d\d", raw) or re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}", raw):
            continue
        nxt, prev = sent[m.end():m.end() + 1], sent[m.start() - 1:m.start()]
        if nxt == "/" or (nxt == "." and sent[m.end() + 1:m.end() + 2].isalnum()) or (prev and prev in "/.-"):
            continue  # 1/2022/SZ, WGK.1431 – numer, nie liczność
        w = NEXT_WORD.match(sent, m.end())
        if w and w.group().strip().lower()[:3] not in _NON_COUNT:
            return True
    return False


def sentence_types(sent: str, q_types: list[set[str]]) -> set[str]:
    """Typy odpowiedzi w zdaniu, dla których jest choć jedno pytanie tego typu („375 działek za 1 272 139 zł”: liczba i kwota)."""
    out = set()
    for t, rx in S_TYPES.items():
        hit = _is_count(sent) if rx is None else bool(rx.search(sent))
        if hit and any(t in qt for qt in q_types):
            out.add(t)
    return out


def _tok(s: str) -> set[str]:
    """Rdzenie słów; „ó” → „o”, bo lekki stemmer zostawia „umów” obok „umow(y)”."""
    return {t.replace("ó", "o") for t in tokens(s)}


def _score_sentence(sent: str, questions: list[str], qtok: list[set[str]], df: dict[str, int], qtypes: list[set[str]]) -> dict:
    n = len(questions)
    st = _tok(sent)
    lex = [sum(1.0 / df[t] for t in st & qt) for qt in qtok]
    typ = sentence_types(sent, qtypes)
    cand = [i for i in range(n) if typ & qtypes[i]] if typ else list(range(n))
    typ = "+".join(sorted(typ))
    if len(cand) == 1:
        return {"no": cand[0] + 1, "confidence": 0.85, "rule": f"typ:{typ}", "candidates": [cand[0] + 1], "scores": lex}
    ranked = sorted(cand, key=lambda i: (-lex[i], i))
    best, second = lex[ranked[0]], lex[ranked[1]]
    near = [i + 1 for i in ranked if best - lex[i] < MARGIN and lex[i] > 0] or [i + 1 for i in ranked]
    if best >= MIN_SCORE and best - second >= MARGIN:
        conf = round(0.5 + 0.35 * min(1.0, (best - second) / best), 2)
        return {"no": ranked[0] + 1, "confidence": conf, "rule": f"słownictwo{'+typ:' + typ if typ else ''}",
                "candidates": near, "scores": lex}
    why = "brak wspólnego słownictwa" if best < MIN_SCORE else "kilka pytań pasuje podobnie"
    return {"no": None, "confidence": 0.0, "rule": why, "candidates": sorted(near), "scores": lex}


def _split_source(name: str, raw: str) -> tuple[str, list[tuple[int | None, str]]]:
    """(tier, [(nr pytania z oznaczenia albo None, zdanie)]) dla jednego pliku odpowiedzi."""
    from .dispatch import parse_reply
    blocks = parse_reply(raw)
    if blocks is not None:
        return "marker", [(k, s) for k, txt in sorted(blocks.items()) for s in _sentences(txt)]
    return "rules", [(None, s) for s in _sentences(answer_body(raw))]


def assign(questions: list[str], answers: list[tuple[str, str]], assignments: dict | None = None) -> dict:
    """Każde zdanie odpowiedzi wydziału → pytanie albo „bez przypisania”, z pochodzeniem (plik, nr zdania).

    answers: [(plik, surowy tekst odpowiedzi)]. assignments (decyzje urzędnika, tier 1): {"plik#nr": n} przenosi
    zdanie do pytania n (0 = pomiń zdanie), {"plik": n} – cały plik dotyczy pytania n (odpowiedź na jedno pytanie).
    Zwraca {"sentences": [{source, index, sentence, no, tier, confidence, rule, candidates}], "matches": [...],
    "unassigned": [...], "provenance": [...]}.
    """
    assignments = {str(k): v for k, v in (assignments or {}).items()}
    n = len(questions)
    qtok = [_tok(q) for q in questions]
    df: dict[str, int] = {}
    for qt in qtok:
        for t in qt:
            df[t] = df.get(t, 0) + 1
    qtypes = [{t for t, rx in Q_TYPES.items() if rx.search(q)} for q in questions]
    out: list[dict] = []
    for name, raw in answers:
        tier, sents = _split_source(name, raw)
        whole = assignments.get(name)
        for idx, (marked, sent) in enumerate(sents):
            rec = {"source": name, "index": idx, "sentence": sent}
            key = f"{name}#{idx}"
            if key in assignments or whole is not None:
                v = assignments.get(key, whole)
                k = int(v) if str(v).strip().lstrip("-").isdigit() else 0
                rec.update(no=k if 1 <= k <= n else None, tier="clerk", confidence=1.0, rule="decyzja urzędnika",
                           candidates=[k] if 1 <= k <= n else [], skipped=k == 0)
            elif tier == "marker":
                ok = marked is not None and 1 <= marked <= n
                rec.update(no=marked if ok else None, tier="marker", confidence=1.0 if ok else 0.0,
                           rule=f"oznaczenie Ad {marked}" + ("" if ok else f" – wniosek ma {n} pytań"), candidates=[marked] if ok else [])
            elif n == 1:
                rec.update(no=1, tier="single", confidence=1.0, rule="jedno pytanie", candidates=[1])
            elif n == 0:
                rec.update(no=None, tier="rules", confidence=0.0, rule="brak pytań", candidates=[])
            else:
                sc = _score_sentence(sent, questions, qtok, df, qtypes)
                rec.update(no=sc["no"], tier="rules", confidence=sc["confidence"], rule=sc["rule"], candidates=sc["candidates"])
            out.append(rec)
    matches = []
    for i, q in enumerate(questions, 1):
        parts = [r for r in out if r["no"] == i]
        matches.append({"no": i, "question": q, "text": " ".join(r["sentence"] for r in parts) or None,
                        "source": sorted({r["source"] for r in parts}) or None})
    unassigned = [{"sentence": r["sentence"], "source": r["source"], "index": r["index"], "candidates": r["candidates"],
                   "reason": r["rule"]} for r in out if r["no"] is None and not r.get("skipped")]
    provenance = [{"para": r["no"], "sentence": r["sentence"], "source": r["source"], "index": r["index"],
                   "tier": r["tier"], "confidence": r["confidence"], "rule": r["rule"]} for r in out if r["no"] is not None]
    return {"sentences": out, "matches": matches, "unassigned": unassigned, "provenance": provenance}


def match_answers(questions: list[str], answers: list[tuple[str, str]], assignments: dict | None = None) -> list[dict]:
    """Zgodność wstecz: same dopasowania pytań (zob. assign()). answers: [(plik, surowy tekst)]."""
    res = assign(questions, answers, assignments)
    match_answers.unassigned = res["unassigned"]  # type: ignore[attr-defined]
    return res["matches"]


def _norm_num(n: str) -> str:
    if re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}", n):
        return n  # data
    return re.sub(r"[ .\u00a0\u202f](?=\d{3}\b)", "", n)  # 3.143.761,14 == 3 143 761,14 → 3143761,14


def number_facts(s: str) -> list[tuple[str, str]]:
    """(liczba znormalizowana, pierwsze 3 litery następnego słowa) – „839 psom” → ('839', 'pso')."""
    out = []
    for m in NUM.finditer(s):
        raw = m.group().strip()
        if len(re.sub(r"\D", "", raw)) < 2 or re.fullmatch(r"(19|20)\d\d", raw):
            continue  # pojedyncze cyfry i same lata pomijamy (numeracja, „w 2025 r.”)
        w = NEXT_WORD.match(s, m.end())
        out.append((_norm_num(raw), w.group().strip().lower()[:3] if w else ""))
    return out


def numbers(s: str) -> set[str]:
    return {n for n, _ in number_facts(s)}


AD_HEAD = re.compile(r"^\s*Ad\s+\d{1,3}\s*[.:)]?\s*", re.I)


def _strip_ad(paras: list[str]) -> list[str]:
    """Nagłówki „Ad 10” to numeracja pytań, nie fakty – nie sprawdzamy ich jako liczb."""
    return [AD_HEAD.sub("", p_, count=1) for p_ in paras]


def check_numbers(draft_paras: list[str], sources: list[str]) -> list[str]:
    """Liczby w projekcie, których nie ma w źródłach, albo stoją przy innym słowie („839 kotów” zamiast „839 psom”)."""
    draft_paras = _strip_ad(draft_paras)
    src: dict[str, set[str]] = {}
    for s_ in sources:
        for n, w in number_facts(s_):
            src.setdefault(n, set()).add(w)
    bad = []
    for p_ in draft_paras:
        for n, w in number_facts(p_):
            if n not in src:
                bad.append(n)
            elif w and w not in ("zł",) and src[n] - {""} and w not in src[n]:
                bad.append(f"{n} ({w}… zamiast {'/'.join(sorted(src[n] - {''}))}…)")
    return bad


def omitted_numbers(draft_paras: list[str], sources: list[str]) -> list[str]:
    """Liczby z odpowiedzi wydziałów, których nie ma w projekcie (fakty pominięte)."""
    draft_paras = _strip_ad(draft_paras)
    have = set().union(*(numbers(p_) for p_ in draft_paras)) if draft_paras else set()
    return sorted({n for s_ in sources for n in numbers(s_)} - have)


# ------------------------------------------------------------------ LLM (opcjonalnie)

def llm_paragraphs(matches: list[dict], timeout: int = 60, provider: str | None = None) -> list[str]:
    """Akapity „Ad n” z udip.llm_tasks.drafting (hook z T00). ValueError = zostań przy szablonie (build() zapisuje llm_error)."""
    from . import llm
    from .llm_tasks import drafting
    p = llm.provider_for(provider)
    if p == "rules":
        raise ValueError("LLM niedostępny (provider rules) – akapity z szablonu")
    qs = [m["question"] for m in matches]
    ans = [(", ".join(m.get("source") or []), m.get("text") or "") for m in matches]
    out = drafting.paragraphs_llm(qs, ans, provider=p)
    if not out or len(out) != len(matches) or not all(isinstance(p, dict) and isinstance(p.get("text"), str) for p in out):
        raise ValueError("Model nie zwrócił akapitów – akapity z szablonu")
    return [p["text"].strip() for p in sorted(out, key=lambda p: p.get("no", 0))]


# ------------------------------------------------------------------ składanie pisma


DEPTS = {d["id"]: d for d in (lambda x: x["departments"] if isinstance(x, dict) else x)(
    json.loads(DEFAULT_DEPTS.read_text(encoding="utf-8")))}
_NAMES = (DATA / "imiona.txt").read_text(encoding="utf-8").split()
FEMALE = {n for n in _NAMES if n.endswith("a") and n not in ("Kuba",)}
MALE = {n for n in _NAMES if n[0].isupper() and n not in FEMALE}
ORG = re.compile(r"(?i)stowarzyszen|fundacj|sp\. z o\.o|s\.a\.|spółk|redakcj|parafi|związ|klub|towarzystw|komitet")


def address_form(request: str, applicant: list[str]) -> tuple[str, str]:
    """(zwrot grzecznościowy, forma „przez Pana/Panią/Państwa”). Organizacja albo brak danych → Państwo."""
    head = " ".join(applicant) + " " + request[-300:]
    if ORG.search(" ".join(applicant)) or ORG.search(request[:400]):
        return "Szanowni Państwo,", "Państwa"
    head += " " + " ".join(w.capitalize() for w in re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ]{3,}\b", request[:300] + request[-200:]))
    for w in re.findall(r"[A-ZŁŚŻ][a-ząęłńóśźż]+", head):
        if w in FEMALE:
            return "Szanowna Pani,", "Panią"
        if w in MALE:
            return "Szanowny Panie,", "Pana"
    if re.search(r"(?m)^\s*ks\.", request):
        return "Szanowny Panie,", "Pana"
    return "Szanowni Państwo,", "Państwa"


def detect_depts(answers: list[tuple[str, str]]) -> list[str]:
    ids = []
    for name, txt in answers:
        m = re.search(r"(?m)^\s*([A-Z][A-Za-z]{1,9})[.\-]\d{3,4}[.\d]*", txt) or re.match(r"([A-Za-z]+)", name)
        if m and m.group(1) in DEPTS and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def komorki_nom(ids: list[str]) -> str:
    if not ids:
        return "komórka merytoryczna, tj. [nazwa wydziału] Urzędu Miasta Bydgoszczy"
    names = [DEPTS[i]["name"] + ("" if DEPTS[i]["type"] == "jednostka" else " Urzędu Miasta Bydgoszczy") for i in ids]
    return ("komórka merytoryczna, tj. " if len(ids) == 1 else "komórki merytoryczne, tj. ") + " oraz ".join(names)


def komorki_phrase(ids: list[str]) -> str:
    if not ids:
        return "komórkę merytoryczną, tj. [nazwa wydziału] Urzędu Miasta Bydgoszczy"
    names = [DEPTS[i]["name"] + ("" if DEPTS[i]["type"] == "jednostka" else " Urzędu Miasta Bydgoszczy") for i in ids]
    if len(ids) == 1:
        lead = "jednostkę, tj. " if DEPTS[ids[0]]["type"] == "jednostka" else "komórkę merytoryczną, tj. "
        return lead + names[0]
    return "jednostki merytoryczne, tj. " + ", ".join(names[:-1]) + " oraz " + names[-1]


def summarize_scope(request: str, qs: list[str], limit: int = 220) -> str:
    flat = re.sub(r"\s+", " ", request)
    m = re.search(r"(?i)(?:na temat|w zakresie|dotycząc\w*|w sprawie)\s+(.{15,240}?)(?:[.:;]\s|$)", flat)
    from_question = not m
    if m:
        s = m.group(1)
    else:
        s = re.sub(r"^\s*\d+[.)]\s*", "", qs[0]) if qs else flat[:limit]
        s = re.sub(r"(?i)^(w trybie dostępu do informacji publicznej )?(proszę o|wnoszę o|wnioskuję o)\s*(informację,?\s*)?", "", s).strip()
    s = re.sub(r"(?i)^(dzień dobry\.?\s*)?(w trybie dostępu do informacji publicznej\s*)?(chc[eę]|pragn[eę])\s+(Państwa\s+)?zapyta[ćc]\s+(o to,?\s*)?", "", s).strip()
    if re.match(r"(?i)(ile|ilu|jak[iaie]?|czy|kto|kiedy|gdzie|w jakim|w jakiej|z kim|komu|dlaczego)\b", s):
        q = s.rstrip(" .,")
        q = q if q.endswith("?") else q + "?"
        q = (q[:limit] + "…") if len(q) > limit else q
        return f": {q[0].upper() + q[1:]}"  # jak BKS w 16.2026: „w zakresie: Ile punktów…?”
    s = (s[0].lower() + s[1:]) if s and not s[:2].isupper() else s
    s = s.rstrip(" .?,")
    s = (s[:limit] + "…") if len(s) > limit else s
    return (": " + s) if from_question else s  # „w zakresie: aktualne zestawienie…” – bez psucia przypadku


def build(request: str, answers: list[tuple[str, str]], number: str, received: date, ltype: str, mode: str,
          sign: str, today: date, extension_until: date | None = None, reason: str = "", dept_ids: list[str] | None = None,
          scope: str = "", entity: str = "", entity_contact: str = "", bip_url: str = "", provider: str | None = None,
          assignments: dict | None = None) -> tuple[str, dict]:
    """Składa tekst pisma. Zwraca (tekst, raport). Dla UI wygodniej: make_draft()."""
    t = TEMPLATES[ltype]
    qs = split_questions(request)
    asg = assign(qs, answers, assignments) if answers else {"matches": [], "unassigned": [], "provenance": [], "sentences": []}
    matches = asg["matches"]
    report = {"type": ltype, "mode_requested": mode, "mode_used": "template", "questions": len(qs), "gaps": [],
              "uncertain_assignment": [], "number_check": [], "warnings": [],
              "unassigned": asg["unassigned"],      # zdania bez pewnego pytania: urzędnik wybiera „Ad” (nie ma ich w piśmie)
              "provenance": asg["provenance"],      # każde zdanie w akapicie „Ad”: plik, nr zdania, tier, pewność
              "assignment_tiers": {k: sum(1 for s in asg["sentences"] if s["tier"] == k and s["no"])
                                   for k in ("marker", "clerk", "single", "rules")}}
    sources = [m["text"] or "" for m in matches]
    # Kontrola właściwości: pytanie wyglądające na sprawę innego wydziału niż autor przypisanej odpowiedzi → do sprawdzenia
    if answers and len(qs) > 1:
        deps = load_departments()
        by_file = {n: (detect_depts([(n, a)]) or ["?"])[0] for n, a in answers}
        for m in matches:
            r = [x["department"] for x in route(m["question"], deps, [], k=2) if x["score"] >= 1.5]
            got = {by_file.get(f, "?") for f in (m["source"] or [])}
            if r and m["text"] and not (got & set(r)) and "?" not in got:
                report["uncertain_assignment"].append({"question": m["no"], "expected_department": r,
                    "answer_from": sorted(got), "note": "pytanie wygląda na właściwość innej komórki – czy brakuje jej odpowiedzi?"})
    paras: list[str] = []
    if ltype == "udostepnienie":
        report["gaps"] = [m["no"] for m in matches if not m["text"]]
        if mode == "llm":
            try:
                paras = llm_paragraphs(matches, provider=provider)
                bad = check_numbers(paras, sources)
                if bad:
                    report["number_check"] = bad
                    report["llm_rejected"] = f"liczby spoza odpowiedzi wydziałów albo przy innym słowie: {bad}"
                    paras = []
                else:
                    report["mode_used"] = "llm"
                    report["omitted_numbers"] = omitted_numbers(paras, sources)
            except (TimeoutError, ValueError, KeyError, AttributeError, json.JSONDecodeError, OSError) as e:
                report["llm_error"] = f"{type(e).__name__}: {e}"[:300]
                paras = []
        if not paras:
            if not matches:
                paras = ["[LUKA: brak wgranych odpowiedzi wydziałów]"]
            pending = {c for u in report["unassigned"] for c in u["candidates"]}
            for m in matches:
                txt = m["text"] or ("[LUKA: odpowiedź czeka na przypisanie – wybierz zdanie z listy „Zdania bez przypisania”]"
                                    if m["no"] in pending else "[LUKA: brak odpowiedzi wydziału – uzupełnij przed wysyłką]")
                paras += [f"Ad {m['no']}", txt] if len(matches) > 1 else [txt]
    # terminy pism proceduralnych (art. 13 ust. 2 UDIP)
    due14 = deadline_days(received)
    if ltype in ("przedluzenie", "doprecyzowanie", "przetworzona") and today > due14:
        report["warnings"].append(f"Pismo datowane {today} po upływie 14 dni ({due14}): powiadomienie z art. 13 ust. 2 powinno wyjść przed upływem terminu.")
    if extension_until and extension_until <= today:
        report["warnings"].append(f"Wskazany nowy termin {extension_until} już minął lub jest dziś – popraw --until.")
    if extension_until and extension_until > deadline_extended(received, months=2)[0]:
        report["warnings"].append(f"Nowy termin {extension_until} przekracza 2 miesiące od wpływu (art. 13 ust. 2 UDIP).")
    if ltype in ("przedluzenie", "doprecyzowanie") and not reason:
        report["warnings"].append("Brak konkretnego powodu – lakoniczne uzasadnienie przedłużenia sądy uznają za bezczynność (II SAB/Ol 107/23).")
    applicant = applicant_block(request)
    salutation, pan_gen = address_form(request, applicant)
    ids = dept_ids or detect_depts(answers)
    ctx = {"number": number, "today": pl_date(today), "received": pl_date(received), "sign": sign,
           "deadline": pl_date(due14), "extension_until": pl_date(extension_until) if extension_until else "[data]",
           "reason": reason or t.get("default_reason", ""), "bip_url": bip_url or "[uzupełnij adres strony BIP]",
           "salutation": salutation, "pan_gen": pan_gen, "zakres": scope or summarize_scope(request, qs),
           "zakres_sep": (lambda z: z if z.startswith(":") else " " + z)(scope or summarize_scope(request, qs)),
           "komorki": komorki_phrase(ids), "komorki_nom": komorki_nom(ids), "podmiot": entity or "[nazwa właściwego podmiotu]",
           "podmiot_kontakt": entity_contact or "[adres i e-mail właściwego podmiotu]"}
    lines = [f"Bydgoszcz, dnia {ctx['today']}", number, ""] + applicant + [""]
    if t["subject"]:
        lines += [t["subject"], ""]
    lines += [x.format(**ctx) for x in t["intro"]]
    lines += paras
    lines += [x.format(**ctx) for x in t.get("closing", [])]
    lines += ["", "Łączę wyrazy szacunku,", "", sign, "Biuro Komunikacji Społecznej", "Urząd Miasta Bydgoszczy", "e-mail: bip@um.bydgoszcz.pl"]
    if t.get("legal_basis"):
        lines += ["", "Podstawa prawna: " + t["legal_basis"]]
    text = "\n".join(lines)
    notes = [t[k] for k in ("internal_note", "notice") if t.get(k)]
    report.update({"sources": [n for n, _ in answers], "departments": ids, "salutation": salutation,
                   "internal_notes": notes,  # notatki dla urzędnika: w raporcie/UI, nigdy w piśmie
                   "number_check_template": check_numbers(paras, sources) if paras and matches else [],
                   # liczby ze zdań bez przypisania też są „pominięte”, dopóki urzędnik nie wybierze im „Ad”
                   "omitted_numbers_template": omitted_numbers(paras, sources + [u["sentence"] for u in report["unassigned"]])
                   if paras and matches and ltype == "udostepnienie" else []})
    return text, report


def _spans_for(text: str, salutation: str | None, keep: list[str] | None = None) -> list[dict]:
    spans = [s.__dict__ for s in detect(text, keep=keep, provider="rules")]  # LLM-owe spany: tylko w ekranie anonimizacji
    head_end = text.find(salutation) if salutation and salutation in text else -1
    for s_ in spans:  # dane adresata w nagłówku: zostają w piśmie do wysyłki, znikają w wersji do archiwum/BIP
        s_["addressee"] = 0 <= s_["start"] < head_end
    return spans


def make_draft(request: str, answers: list[tuple[str, str]], received: date, ltype: str = "udostepnienie", *,
               number: str = "BKS.IV.1431.___.2026", today: date | None = None, mode: str = "template", sign: str = "[podpis AIP]",
               extension_until: date | None = None, reason: str = "", dept_ids: list[str] | None = None, scope: str = "",
               entity: str = "", entity_contact: str = "", bip_url: str = "", keep: list[str] | None = None,
               provider: str | None = None, assignments: dict | None = None) -> dict:
    """API dla aplikacji: {'text', 'spans', 'report', 'html'}. Spany mają status suggested/review i flagę addressee.
    assignments: decyzje urzędnika o przypisaniu zdań („plik#nr” → nr pytania, 0 = pomiń; „plik” → cały plik), zob. assign()."""
    today = today or date.today()
    if ltype in ("przedluzenie", "doprecyzowanie") and extension_until is None:
        # domyślnie: przedłużenie = maks. 2 miesiące; doprecyzowanie = 30 dni od dziś (praktyka 509.2026: ok. 5 tygodni), w granicy 2 miesięcy
        cap = deadline_extended(received, months=2)[0]
        extension_until = cap if ltype == "przedluzenie" else min(cap, shift_to_working_day(today + timedelta(days=30)))
    text, report = build(request, answers, number, received, ltype, mode, sign, today, extension_until, reason,
                         dept_ids, scope, entity, entity_contact, bip_url, provider=provider, assignments=assignments)
    spans = _spans_for(text, report.get("salutation"), keep)
    report["anonymization_suggestions"] = len(spans)
    return {"text": text, "spans": spans, "report": report, "html": preview_html(text, spans, f"Projekt odpowiedzi {number}")}


def finalize(text: str, spans: list[dict], accept: set[str] | None = None, reject: set[str] | None = None,
             accept_all_suggested: bool = False, edited_text: str | None = None, salutation: str | None = None) -> dict:
    """Akceptacja anonimizacji → dwie wersje pisma. Gdy urzędnik edytował tekst (edited_text), spany wykrywa się od nowa
    na nowym tekście, a decyzje przenosi po (typ, tekst) – stare offsety nie pasowałyby do nowego tekstu."""
    accept, reject = accept or set(), reject or set()
    for s_ in spans:
        if s_["id"] in accept or (accept_all_suggested and s_["status"] == "suggested" and s_["id"] not in reject):
            s_["status"] = "accepted"
        elif s_["id"] in reject:
            s_["status"] = "rejected"
    if edited_text is not None and edited_text != text:
        decided = {(s_["type"], s_["text"]): s_["status"] for s_ in spans if s_["status"] in ("accepted", "rejected")}
        sal = salutation or next((x for x in ("Szanowni Państwo,", "Szanowna Pani,", "Szanowny Panie,") if x in edited_text), None)
        spans = _spans_for(edited_text, sal)
        for s_ in spans:
            s_["status"] = decided.get((s_["type"], s_["text"]), s_["status"])
        text = edited_text
    warnings = []
    third = [s_["text"] for s_ in spans if s_["status"] == "accepted" and not s_.get("addressee")]
    if third:
        warnings.append("UWAGA PRAWNA: zaczernienie danych w treści udostępnianej informacji to częściowa odmowa – rozważ decyzję "
                        "(art. 16 UDIP; WSA Opole I SAB/Op 11/26). Zaczernione w treści: " + "; ".join(third[:5]))
    undecided = [s_["id"] for s_ in spans if s_["status"] in ("review", "suggested")]
    if undecided:
        warnings.append(f"Bez decyzji urzędnika: {', '.join(undecided)} – w wersjach końcowych pozostają jawne.")
    body_spans = [dict(s_, status="rejected") if s_.get("addressee") else s_ for s_ in spans]
    return {"text": text, "spans": spans, "warnings": warnings,
            "anonymized": anon_apply(text, spans, "label"),      # archiwum, BIP, załączniki
            "to_send": anon_apply(text, body_spans, "label"),    # do wnioskodawcy: adresat jawny
            "body_spans": body_spans}


def write_docx(text: str, spans: list[dict], path: Path, final: bool = False, footer: str = "") -> None:
    """DOCX: szare tło = propozycja/do decyzji, czarne = zaakceptowane (final=True: zaczernione █)."""
    import docx
    from docx.enum.text import WD_COLOR_INDEX
    from docx.shared import Pt
    d = docx.Document()
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    offs = 0
    sp = flatten(spans)  # bez nakładania: zagnieżdżony span nie może cofnąć kursora i odsłonić tekstu
    for line in text.split("\n"):
        p = d.add_paragraph()
        a, b = offs, offs + len(line)
        cur = a
        for s in sp:
            if s["end"] <= a or s["start"] >= b:
                continue
            ss, se = max(s["start"], a), min(s["end"], b)
            if ss > cur:
                p.add_run(text[cur:ss])
            r = p.add_run(text[ss:se] if not (final and s["status"] == "accepted") else BLOCK)  # stała długość (T27)
            if s["status"] == "accepted":
                r.font.highlight_color = WD_COLOR_INDEX.BLACK
            elif s["status"] in ("suggested", "review") and not final:
                r.font.highlight_color = WD_COLOR_INDEX.GRAY_25
            cur = se
        if cur < b:
            p.add_run(text[cur:b])
        offs = b + 1
    if footer:
        fp = d.sections[0].footer.paragraphs[0]
        fp.text = footer
        for r in fp.runs:
            r.font.size = Pt(9)
    d.save(str(path))
