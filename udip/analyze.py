"""Analiza wniosku: pytania, tryb, sygnały ryzyka, podobne sprawy i ścieżka do wydziałów (CONTRACTS §2).

Reguły są jawne i testowalne i dają wynik zawsze, także offline. Gdy provider != "rules", analyze() dokłada wynik
llm_tasks.analysis/routing (hook z T00): LLM uzupełnia streszczenie, flagi i uzasadnienia, reguły zostawiają
podobne sprawy, podział na pytania i punktację.

CLI: .claude/skills/udip-archiwum-i-wydzialy/scripts/analyze.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from .search import Archive
from .textpl import norm, stem, tokens

DEFAULT_DEPTS = Path(__file__).resolve().parent / "data" / "departments.json"
# Słowa z nazw komórek, które nic nie mówią o temacie („Miejski”, „Bydgoskie”, „Sp. z o.o.”).
GENERIC = set(tokens("miejski miejskie miejska miejskich miasta miasto bydgoszcz bydgoskie bydgoski bydgoska bydgoskiej wydział biuro zarząd "
                     "urząd spółka sp. z o.o. ośrodek centrum zakład zakłady sprawy spraw ds. gospodarki gospodarka i oraz "
                     "międzygminny przedsiębiorstwo komunalne komunalny administracja"))

# Tryby łatwe do pomylenia z UDIP (research/05, sekcja „Inne tryby”). Kolejność = priorytet.
MODES = [
    ("ponowne_wykorzystanie", r"ponowne(go)? wykorzystani|w celu ponownego wykorzystania|otwartych danych", "Wniosek o ponowne wykorzystanie (ustawa o otwartych danych) – inny tryb i terminy."),
    ("petycja", r"\bpetycj", "Petycja (ustawa o petycjach) – inny tryb; przekaż do Biura Rady Miasta lub właściwej komórki."),
    ("skarga_wniosek_kpa", r"\bskarg[aię]\b|skarżę|na podstawie art\.? 2(2[1-9]|4[1-7])", "Skarga/wniosek z działu VIII KPA – inny tryb (termin 1 miesiąc)."),
    ("akta_sprawy", r"wgląd do akt|dostęp do akt|art\.? 73 k\.?p\.?a|akt(a|ach) (mojej )?sprawy", "Dostęp do akt sprawy (art. 73 KPA) – tylko dla strony postępowania, nie UDIP."),
    ("informacja_o_srodowisku", r"informacj\w* o środowisku|ustaw\w* o udostępnianiu informacji o środowisku|oddziaływani\w* na środowisko", "Informacja o środowisku – odrębna ustawa (termin do 1 miesiąca); sprawdź."),
    ("radny", r"\bradn[ya] |jako radn|interpelacj|zapytanie radnego", "Wniosek radnego (art. 24 ustawy o samorządzie gminnym) – inny tryb, Biuro Rady Miasta."),
]
PROCESSED = r"zestawieni|analiz|za lata|w latach \d{4}|od \d{4} (r\.? )?do \d{4}|wszystkich (umów|decyzji|faktur|spraw)|każde(go|j) z|statystyk|w podziale na|porówna|zbiorcz"
REUSE_PUBLISHED = r"\bBIP\b|Biuletyn|opublikowan|uchwał\w* (nr|budżetow)"
PERSONAL = r"wynagrodze|pensj|premi|nagr[oó]d\w* (dla|prezydenta|dyrektor)|umow\w* o prac|oświadczen\w* majątkow"


ITEM = re.compile(r"(?m)^\s*(?:\d{1,2}[.)]|[a-z][)]|[-•*])\s+(.+(?:\n(?!\s*(?:\d{1,2}[.)]|[a-z][)]|[-•*])\s)(?!\s*\n).+)*)")


def split_questions(text: str) -> list[str]:
    """Pytania z wniosku: najpierw lista numerowana w całym tekście (odporne na nagłówki przekazanych e-maili),
    potem zdania z „?” lub „proszę/wnoszę”, na końcu cały tekst."""
    items = [re.sub(r"\s+", " ", i).strip() for i in ITEM.findall(text)]
    items = [i for i in items if len(i) > 15 and not re.match(r"(?i)(od|do|dw|temat|wysłano):", i)]
    if len(items) >= 2 or (items and len(items[0]) > 40):
        return items[:30]
    # nagłówek: daty, pieczęcie kancelarii, adresat, linie WIELKIMI LITERAMI (rękopisy), zwroty grzecznościowe
    header = re.compile(r"(?i)^(\S+,?\s*(dnia\s*)?\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]\d{4}|.*(kancelaria|nr wpływu|data wpływu|urząd miasta|prezydent|szanown|dzień dobry|witam)\b.*)$")
    lines = [l for l in text.splitlines() if l.strip() and not header.match(l.strip())
             and not (len(l.split()) <= 4 and (lambda x: sum(c.isupper() for c in x) > 0.6 * max(1, sum(c.isalpha() for c in x)))(re.sub(r"\[.*?\]", "", l)))]
    text = "\n".join(lines) or text
    body = text
    m = re.search(r"(?i)(wnosz[eę]|zwraca(m|my)? si[eę]|prosz[eę]|wnioskuj[eę]|chc[eę] .{0,20}zapyta)", text)
    if m:
        body = text[m.start():]
    stop = re.search(r"\n\s*(Z powa[zż]aniem|Pozdrawiam|Z wyrazami szacunku|--)", body, re.I)
    if stop:
        body = body[:stop.start()]
    sents = re.split(r"(?<=[.?!])\s+", re.sub(r"\s+", " ", body))
    items = [s.strip() for s in sents if len(s.strip()) > 15 and ("?" in s or re.search(r"(?i)prosz[eę]|wnosz[eę]|wnioskuj|udost[eę]pni|zapyta", s))]
    return items[:30] or [re.sub(r"\s+", " ", text).strip()[:500]]


def requested_form(text: str) -> str:
    t = norm(text)
    if re.search(r"e-?mail|elektroniczn|skrzynk", t):
        return "elektronicznie (e-mail)"
    if "epuap" in t:
        return "ePUAP"
    if re.search(r"poczt|listown|na adres", t):
        return "pocztą tradycyjną"
    return "nie wskazano (art. 14 UDIP: forma zgodna z wnioskiem, gdy możliwa)"


def load_departments(path: Path | None = None) -> list[dict]:
    d = json.loads(Path(path or DEFAULT_DEPTS).read_text(encoding="utf-8"))
    deps = d["departments"] if isinstance(d, dict) else d
    for x in deps:
        x["_stems"] = ({stem(norm(k)) for kw in x.get("keywords", []) for k in kw.split() if len(k) > 2}
                       | set(tokens(x.get("name", "")))) - GENERIC
    return deps


COORDINATOR = {"BKS"}  # Biuro Komunikacji Społecznej koordynuje UDIP (AIP), nie jest komórką merytoryczną


def route(question: str, deps: list[dict], similar: list[dict], k: int = 3) -> list[dict]:
    q = set(tokens(question))
    score: dict[str, float] = defaultdict(float)
    why: dict[str, list[str]] = defaultdict(list)
    for d in deps:
        hit = q & d["_stems"]
        if hit:
            score[d["id"]] += 1.5 * len(hit)
            why[d["id"]].append("słowa: " + ", ".join(sorted(hit)[:5]))
    if similar:
        top = similar[0]["score"] or 1
        for s in similar:
            for dep in s.get("departments", []):
                score[dep] += 1.0 * s["score"] / top
                why[dep].append(f"podobna sprawa {s['id']}")
    try:  # T25: departments the clerk chose instead of the proposal for similar questions
        from . import learning
        for dep, (extra, reason) in learning.boost(question, dict(score)).items():
            score[dep] += extra
            why[dep].insert(0, reason)
    except Exception:
        pass
    names = {d["id"]: d["name"] for d in deps}
    ranked = sorted(((d_, v) for d_, v in score.items() if d_ not in COORDINATOR and not d_.startswith("ZEWN")), key=lambda x: -x[1])[:k]
    total = sum(v for _, v in ranked) or 1
    return [{"department": dep, "name": names.get(dep, dep), "score": round(v, 2), "share": round(v / total, 2),
             "reasons": list(dict.fromkeys(why[dep]))[:4]} for dep, v in ranked]


def _similar(archive: Archive | None, text: str, k: int, since: date | None, exclude_id: str | None,
             also_exclude: set | frozenset = frozenset()) -> list[dict]:
    """Podobne sprawy bez samej siebie (ten sam numer albo identyczny tekst wniosku). Gdy w oknie czasowym pusto –
    szuka w całym archiwum i oznacza wyniki „older_than_window”."""
    if not archive:
        return []
    same = {r.get("id") for r in archive.records if exclude_id and r.get("id") == exclude_id}
    norm_q = re.sub(r"\s+", " ", text).strip()
    same |= {r.get("id") for r in archive.records if re.sub(r"\s+", " ", r.get("request_text", "")).strip() == norm_q}
    same |= set(also_exclude)  # per-question search: the whole request's own archive record
    res = [x for x in archive.search(text, k=k + len(same), since=since) if x["id"] not in same][:k]
    if not res and since:
        res = [dict(x, older_than_window=True) for x in archive.search(text, k=k + len(same)) if x["id"] not in same][:k]
    return res


def analyze_rules(text: str, archive: Archive | None, deps: list[dict], today: date, since_days: int = 365,
                  exclude_id: str | None = None) -> dict:
    """Analiza samymi regułami (bez pól llm_used/provider)."""
    flags = []
    mode = "udip"
    for m, rx, msg in MODES:
        if re.search(rx, text, re.I):
            mode = m
            flags.append({"type": "tryb", "message": msg})
            break
    if re.search(PROCESSED, text, re.I):
        flags.append({"type": "informacja_przetworzona?", "message": "Możliwa informacja przetworzona (art. 3 ust. 1 pkt 1 UDIP): przy dużym nakładzie pracy rozważ wezwanie do wykazania szczególnego interesu publicznego. Decyduje urzędnik/radca prawny."})
    if re.search(REUSE_PUBLISHED, text, re.I):
        flags.append({"type": "bip", "message": "Wniosek może dotyczyć informacji opublikowanej w BIP: art. 10 ust. 1 UDIP – informacja udostępniona w BIP nie podlega udostępnieniu na wniosek, ale wtedy wskaż dokładny adres (dobra praktyka)."})
    if re.search(PERSONAL, text, re.I):
        flags.append({"type": "dane_osobowe", "message": "Pytanie o wynagrodzenia/umowy osób: sprawdź art. 5 ust. 2 UDIP (prywatność vs osoby pełniące funkcje publiczne)."})
    since = today - timedelta(days=since_days) if since_days else None
    similar = _similar(archive, text, 5, since, exclude_id)
    norm_t = re.sub(r"\s+", " ", text).strip()
    self_ids = {r.get("id") for r in (archive.records if archive else [])
                if r.get("id") == exclude_id or re.sub(r"\s+", " ", r.get("request_text", "")).strip() == norm_t}
    questions = split_questions(text)
    per_q = []
    for i, q in enumerate(questions, 1):
        sim_q = _similar(archive, q, 3, since, exclude_id, self_ids) if len(questions) > 1 else similar[:3]
        per_q.append({"no": i, "text": q, "routing": route(q, deps, sim_q)})
    overall = route(text, deps, similar, k=5)
    plan = defaultdict(list)
    for q in per_q:
        if q["routing"]:
            plan[q["routing"][0]["department"]].append(q["no"])
    return {
        "mode": mode, "flags": flags, "requested_form": requested_form(text),
        "questions": per_q, "similar_cases": similar, "departments_overall": overall,
        "routing_plan": [{"department": d, "name": next((x["name"] for x in deps if x["id"] == d), d), "questions": qs} for d, qs in plan.items()],
        "disclaimer": "Propozycja narzędzia. Kwalifikację trybu i wybór wydziału zatwierdza urzędnik.",
    }


def _merge_llm(res: dict, text: str, deps: list[dict], provider: str) -> dict:
    """LLM fills summary, extra flags and routing reasons; rules keep similar_cases, question split and scores."""
    from . import llm
    from .llm_tasks import analysis as la, routing as lr

    used = False
    a = la.analyze_llm(text, provider=provider)
    if a:
        used = True
        res["summary"] = a.get("summary", "")
        res["applicant_type"] = a.get("applicant_type", "")
        have = {f["type"] for f in res["flags"]}
        for f in a.get("flags") or []:
            if f.get("type") not in have:
                res["flags"].append({"type": f.get("type", "llm"), "message": f.get("message", ""), "source": "llm"})
        if a.get("mode") and a["mode"] != res["mode"]:
            res["flags"].append({"type": "tryb_llm", "source": "llm",
                                 "message": f"Model wskazuje tryb „{a['mode']}”, reguły: „{res['mode']}”. Rozstrzyga urzędnik."})
        n_llm = len(a.get("questions") or [])
        if n_llm and n_llm != len(res["questions"]):
            res["llm_questions"] = a["questions"]
            res["flags"].append({"type": "liczba_pytan", "source": "llm",
                                 "message": f"Model widzi {n_llm} pytań, reguły {len(res['questions'])}. Sprawdź podział wniosku."})
    batched = None
    if provider.startswith("openai_compat:") and len(res["questions"]) > 1:
        batched = lr.route_batch_llm([q["text"] for q in res["questions"]], deps, provider=provider)
    for q in res["questions"]:
        r = batched.get(q["no"]) if batched is not None else lr.route_llm(q["text"], deps, provider=provider)
        if not r:
            continue
        used = True
        q["llm_routing"] = r
        by_id = {x["department"]: x for x in q["routing"]}
        for item in r:
            hit = by_id.get(item.get("department"))
            if hit is not None:
                hit.setdefault("reasons", []).append("Model: " + item.get("reason", ""))
    res["llm_used"] = used
    res["provider"] = provider if used else "rules"
    if used:
        res["llm_usage"] = llm.usage()
    return res


def analyze(text: str, archive: Archive | None, deps: list[dict], today: date, since_days: int = 365,
            exclude_id: str | None = None, provider: str | None = None) -> dict:
    res = analyze_rules(text, archive, deps, today, since_days=since_days, exclude_id=exclude_id)
    res["llm_used"] = False
    res["provider"] = "rules"
    if provider != "rules":
        from . import llm
        p = llm.provider_for(provider)
        if p != "rules":
            res = _merge_llm(res, text, deps, p)
    return res
