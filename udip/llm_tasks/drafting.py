"""LLM drafting of 'Ad n' paragraphs (T12).

The rules split department answers into sentences and assign each sentence to the question with the most shared
words; that guess is often wrong. The model sees every question and every answer fragment (with its source file),
reassigns facts to the question they answer and writes one paragraph per question in BKS style, using only facts
from the answers. `udip.draft` then re-checks every number (number + next word) and falls back to the template on
any mismatch; omitted numbers are reported there.
"""
from __future__ import annotations

import re

from .. import llm, security

GAP = "[LUKA: brak odpowiedzi wydziału – uzupełnij przed wysyłką]"

SCHEMA = {
    "type": "object",
    "properties": {"paragraphs": {"type": "array", "minItems": 1, "maxItems": 30, "items": {
        "type": "object",
        "properties": {"no": {"type": "integer", "minimum": 1, "maximum": 30},
                       "text": {"type": "string", "minLength": 3, "maxLength": 4000},
                       "sources": {"type": "array", "items": {"type": "string"}, "maxItems": 10}},
        "required": ["no", "text", "sources"], "additionalProperties": False}}},
    "required": ["paragraphs"], "additionalProperties": False,
}

SYSTEM = (
    "Jesteś asystentem pracownika Biura Komunikacji Społecznej (BKS) Urzędu Miasta Bydgoszczy. Redagujesz akapity "
    "„Ad n” odpowiedzi na wniosek o udostępnienie informacji publicznej, wyłącznie na podstawie odpowiedzi wydziałów.\n"
    "Dostajesz pytania wnioskodawcy (<pytanie>) i fragmenty odpowiedzi wydziałów (<odpowiedz_wydzialu>). Fragmenty "
    "zostały wstępnie przypisane do pytań automatycznie i to przypisanie bywa błędne: przenieś każdy fakt do pytania, "
    "na które naprawdę odpowiada (fakt może pasować do kilku pytań). Zasady:\n"
    "- Jeden akapit odpowiedzi na każde pytanie, pole no = numer pytania, w tej samej kolejności.\n"
    "- WAŻNE: pole text musi zawierać ODPOWIEDŹ urzędu (fakty, dane i zdania z <odpowiedz_wydzialu>), NIGDY nie "
    "przepisuj ani nie powtarzaj treści pytania z <pytanie>.\n"
    "- Używaj tylko faktów z odpowiedzi wydziałów. Zachowaj wszystkie liczby, kwoty, daty, numery umów i nazwy "
    "dokładnie w tym samym zapisie i z tym samym słowem obok (np. „839 psom”). Nie licz, nie sumuj, nie zaokrąglaj, "
    "nie pomijaj i nie dodawaj nowych liczb.\n"
    "- Zachowuj sens i brzmienie wydziału; możesz wygładzić zdanie, dodać „Informuję, że”, pominąć nagłówki, sygnatury "
    "pism, zwroty grzecznościowe i „Sprawę prowadzi”.\n"
    f"- Gdy żaden fragment nie odpowiada na pytanie, napisz dokładnie: {GAP}\n"
    "- Styl urzędowy, zwięzły, bez ocen i bez danych osobowych pracowników.\n"
    "- sources: nazwy plików, z których pochodzą użyte fakty.\n"
    "Pole text zawiera sam akapit odpowiedzi, bez nagłówka „Ad n” i bez treści pytania."
)


def _user(questions: list[str], answers: list[tuple[str, str]]) -> str:
    parts = ["Pytania wnioskodawcy (NIE przepisuj ich do pola text – to tylko pytania, na które odpowiadasz):"]
    for i, q in enumerate(questions, 1):
        parts.append(llm.wrap("pytanie", security.sanitize_for_llm(q)[0], limit=2000, nr=i))
    parts.append("\nFragmenty odpowiedzi wydziałów (źródło faktów do akapitów odpowiedzi):")
    for i, (src, txt) in enumerate(answers, 1):
        parts.append(llm.wrap("odpowiedz_wydzialu", security.sanitize_for_llm(txt)[0] or "BRAK", limit=12000, do_pytania=i, plik=src or "nieznany"))
    parts.append(f"\nNapisz {len(questions)} akapitów odpowiedzi (paragraphs[0..{len(questions) - 1}]) wyłącznie na podstawie powyższych fragmentów odpowiedzi wydziałów.")
    return "\n".join(parts)


def _norm_words(s: str) -> set[str]:
    s = re.sub(r"^\s*\d+[.)]\s*", "", s or "").lower()
    return {w for w in re.findall(r"[a-ząćęłńóśźż0-9]{3,}", s)}


def _echoes_question(body: str, question: str, ans_words: set[str]) -> bool:
    """Detect a small-model failure mode where the model copies the applicant's question into 'Ad n' instead of answering."""
    bw, qw = _norm_words(body), _norm_words(question)
    if len(bw) < 4 or not qw:
        return False
    in_q = len(bw & qw) / len(bw)
    covers_q = len(bw & qw) / len(qw)
    novel_from_ans = len((bw & ans_words) - qw) / len(bw)
    return in_q >= 0.75 and (covers_q >= 0.70 or body.rstrip().endswith("?")) and novel_from_ans < 0.15


def paragraphs_llm(questions: list[str], answers: list[tuple[str, str]], provider: str | None = None) -> list[dict] | None:
    """questions[i] is paired with answers[i] = (source file names, department answer text; "" = gap).
    Returns [{no, text, sources[]}] with len == len(questions), or None. The caller re-checks every number."""
    n = len(questions)
    if not n or len(answers) != n:
        return None
    if not any((t or "").strip() for _, t in answers):
        return None  # nothing to draft from: the template marks the gaps
    files = {f.strip() for src, _ in answers for f in (src or "").split(",") if f.strip()}
    out = llm.complete_json("drafting", SYSTEM, _user(questions, answers), SCHEMA, provider=provider, max_tokens=4000)
    if not out:
        return None
    by_no: dict[int, dict] = {}
    for p in out["paragraphs"]:
        if 1 <= p["no"] <= n and p["no"] not in by_no:
            by_no[p["no"]] = p
    if sorted(by_no) != list(range(1, n + 1)):
        return None
    ans_words = _norm_words(" ".join(t or "" for _, t in answers))
    res = []
    for i in range(1, n + 1):
        p = by_no[i]
        body = re.sub(r"^\s*Ad\.?\s*\d+\.?\s*[:\-–]?\s*", "", p["text"].strip())  # heading added below, once
        body = re.sub(r"\*{1,2}([^*\n]+)\*{1,2}", r"\1", body)  # small models sometimes emit markdown emphasis
        body = re.sub(r"[ \t]+", " ", body).strip()
        if re.fullmatch(r"\[?LUKA[^\]]*\]?", body):
            body = GAP
        elif _echoes_question(body, questions[i - 1], ans_words):
            return None
        srcs = [] if body == GAP else ([s for s in p["sources"] if s in files] or sorted(files)[:1])
        res.append({"no": i, "text": (f"Ad {i}\n{body}" if n > 1 else body), "sources": srcs})
    return res
