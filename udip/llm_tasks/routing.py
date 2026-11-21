"""LLM routing justification (T13): the model picks units from the 46-unit list with a one-line reason.

`route_llm(question, deps)` returns [{department, reason}] best first (ids from departments.json, at most 3) or None.
udip.analyze adds the reasons to the rule scores; the clerk decides.
"""
from __future__ import annotations

import re

from .. import llm, security

COORDINATOR = {"BKS"}  # coordinates UDIP, never the unit that answers


def _catalogue(deps: list[dict]) -> str:
    lines = []
    for d in deps:
        if d.get("id") in COORDINATOR:
            continue
        kw = ", ".join((d.get("keywords") or [])[:5])
        scope = re.sub(r"\s+", " ", d.get("scope") or "")[:110]
        lines.append(f"{d['id']} | {d.get('name', '')} | {scope} | {kw}")
    return "\n".join(lines)


def _schema(ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {"departments": {"type": "array", "maxItems": 3, "items": {
            "type": "object",
            "properties": {"department": {"type": "string", "enum": ids}, "reason": {"type": "string", "maxLength": 200}},
            "required": ["department", "reason"], "additionalProperties": False}}},
        "required": ["departments"], "additionalProperties": False,
    }


SYSTEM = (
    "Jesteś asystentem pracownika Biura Komunikacji Społecznej Urzędu Miasta Bydgoszczy. Do każdego pytania z wniosku o "
    "informację publiczną wskazujesz komórki lub jednostki, które mają tę informację i przygotują odpowiedź. Wybierasz "
    "wyłącznie z katalogu (identyfikator | nazwa | zakres | słowa kluczowe). Najpierw najbardziej właściwa; najwyżej "
    "3, zwykle 1. Do każdej jedno zdanie uzasadnienia po polsku (do 20 słów), odwołujące się do zakresu komórki. Gdy "
    "pytanie dotyczy podmiotu spoza Urzędu (np. spółki miejskiej), wskaż tę jednostkę, jeśli jest w katalogu.\n\n"
    "Katalog komórek i jednostek:\n"
)


def route_llm(question: str, deps: list[dict], provider: str | None = None) -> list[dict] | None:
    """[{department, reason}] best first (department = id from departments.json), or None."""
    ids = [d["id"] for d in deps if d.get("id") and d["id"] not in COORDINATOR]
    if not question or not question.strip() or not ids:
        return None
    out = llm.complete_json("routing", SYSTEM + _catalogue(deps), "Pytanie z wniosku:\n" + llm.wrap("pytanie", security.sanitize_for_llm(question)[0], limit=4000),
                            _schema(ids), provider=provider, max_tokens=600)
    if not out:
        return None
    res, seen = [], set()
    for item in out["departments"]:
        dep = item["department"]
        if dep in seen or dep not in ids:
            continue
        seen.add(dep)
        res.append({"department": dep, "reason": re.sub(r"\s+", " ", item["reason"]).strip()})
    return res or None


def _batch_schema(ids: list[str], n: int) -> dict:
    return {
        "type": "object",
        "properties": {"items": {"type": "array", "minItems": 1, "maxItems": n, "items": {
            "type": "object",
            "properties": {
                "no": {"type": "integer", "minimum": 1, "maximum": n},
                "departments": {"type": "array", "maxItems": 3, "items": {
                    "type": "object",
                    "properties": {"department": {"type": "string", "enum": ids}, "reason": {"type": "string", "maxLength": 200}},
                    "required": ["department", "reason"], "additionalProperties": False}},
            },
            "required": ["no", "departments"], "additionalProperties": False}}},
        "required": ["items"], "additionalProperties": False,
    }


def route_batch_llm(questions: list[str], deps: list[dict], provider: str | None = None) -> dict[int, list[dict]] | None:
    """One-call routing for all questions of a request (avoids re-sending the 45-unit catalogue N times on local models).
    Returns {question_no (1-based): [{department, reason}]} or None."""
    ids = [d["id"] for d in deps if d.get("id") and d["id"] not in COORDINATOR]
    n = len(questions)
    if not n or not ids:
        return None
    user_parts = ["Pytania z wniosku (wskaż 1–3 komórki dla każdego numeru pytania):"]
    for i, q in enumerate(questions, 1):
        user_parts.append(llm.wrap("pytanie", security.sanitize_for_llm(q)[0], limit=2000, nr=i))
    out = llm.complete_json("routing_batch", SYSTEM + _catalogue(deps), "\n".join(user_parts),
                            _batch_schema(ids, n), provider=provider, max_tokens=min(3000, 350 * n))
    if not out:
        return None
    by_no: dict[int, list[dict]] = {}
    for entry in out["items"]:
        no = entry["no"]
        if not (1 <= no <= n) or no in by_no:
            continue
        res, seen = [], set()
        for item in entry["departments"]:
            dep = item["department"]
            if dep in seen or dep not in ids:
                continue
            seen.add(dep)
            res.append({"department": dep, "reason": re.sub(r"\s+", " ", item["reason"]).strip()})
        if res:
            by_no[no] = res
    return by_no or None
