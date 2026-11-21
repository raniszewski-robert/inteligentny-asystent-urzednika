#!/usr/bin/env python3
"""T15: rules vs Sonnet 5.5 vs Haiku 5.5 (vs Bielik) on the 10 UMB cases + the synthetic UMB-style cases.

Measures per provider: question extraction (count vs manual gold), calendar summary filled, routing top-1/top-3,
'Ad' placement (gold facts in the right paragraph), numbers the model invented or swapped (caught by the number check),
numbers omitted, anonymization precision/recall/leaks, a prompt-injection probe, latency and cost per request.
Every LLM call goes through udip.llm (shared cache + budget): a repeated run costs $0 and reuses the recorded cost.

  python scripts/eval_llm.py --provider rules
  python scripts/eval_llm.py --provider anthropic:haiku
  python scripts/eval_llm.py --provider anthropic:sonnet
  python scripts/eval_llm.py --provider openai_compat:bielik --limit 20
  python scripts/eval_llm.py --report            # docs/eval/RESULTS.md + docs/eval/chart.png from docs/eval/results/*.json
  python scripts/eval_llm.py --mock              # fake model, isolated cache: pipeline check without key or network
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from udip import anonymize as N, draft as D, llm  # noqa: E402
from udip.analyze import analyze_rules, load_departments, route, split_questions  # noqa: E402
from udip.llm_tasks import analysis, anonymization, routing  # noqa: E402
from udip.search import Archive, load_archive  # noqa: E402

EVAL = ROOT / "docs" / "eval"
UMB = ROOT / "data-partner" / "umb"
SYN = ROOT / "data-samples" / "syntetyczne_umb" / "cases.jsonl"
PII = ROOT / "data-samples" / "syntetyczne"
INJ = ROOT / "tests" / "llm" / "fixtures" / "injection_pl.txt"
CANARY = "KANAREK-7Q"
TODAY = date(2026, 11, 22)
LABELS = {"rules": "Reguły", "anthropic:sonnet": "Sonnet 5.5", "anthropic:haiku": "Haiku 5.5", "openai_compat:bielik": "Bielik 4.5B"}


# ------------------------------------------------------------------ data


def load_items(limit: int | None = None) -> list[dict]:
    gold = json.loads((EVAL / "umb_gold.json").read_text(encoding="utf-8"))["cases"]
    items = []
    for r in load_archive(UMB / "archiwum_umb.jsonl"):
        g = gold.get(r["id"])
        if not g:
            continue
        it = {"id": r["id"], "source": "umb", "text": r["request_text"], "q_ok": g["questions_ok"], "q": g["questions"],
              "deps": [d for d in g["departments"] if not d.startswith("ZEWN")], "received": date.fromisoformat(r["date"])}
        if "ad_anchors" in g:
            d = UMB / "przypadek_543"
            it["text"] = (d / "wniosek.txt").read_text(encoding="utf-8")
            it["answers"] = [(f, (d / f).read_text(encoding="utf-8")) for f in ("SCHRONISKO.txt", "WGK.txt")]
            it["ad"] = {int(k): v for k, v in g["ad_anchors"].items()}
        items.append(it)
    if SYN.is_file():
        for line in SYN.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            c = json.loads(line)
            n = len(c["gold"]["questions"])
            items.append({"id": c["id"], "source": "syn", "text": c["request_text"], "q_ok": [n], "q": n,
                          "deps": c["gold"]["departments"], "received": date.fromisoformat(c["date"]),
                          "answers": [(a["file"], a["text"]) for a in c["answers"]],
                          "ad": {a["no"]: a["facts"] for a in c["gold"]["ad"] if a["facts"]}})
    if limit:  # keep all UMB items and a spread of synthetic ones
        umb = [i for i in items if i["source"] == "umb"]
        syn = [i for i in items if i["source"] == "syn"]
        k = max(0, limit - len(umb))
        items = umb[:limit] + (syn[:: max(1, len(syn) // k)][:k] if k and syn else [])
    return items


def load_pii_docs(limit: int | None = None) -> list[dict]:
    docs = []
    for g in json.loads((PII / "pii" / "gold.json").read_text(encoding="utf-8")):
        p = next((x for x in (PII / g["file"], PII / "pii" / g["file"]) if x.is_file()), None)
        if p:
            docs.append({"id": g["file"], "text": p.read_text(encoding="utf-8"), "spans": g["spans"]})
    if SYN.is_file():
        for line in SYN.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            c = json.loads(line)
            texts = {"request_text": c["request_text"], **{a["file"]: a["text"] for a in c["answers"]}}
            for doc, text in texts.items():
                docs.append({"id": f"{c['id']}/{doc}", "text": text, "spans": [s for s in c["gold"]["pii"] if s["doc"] == doc]})
    return docs[:limit] if limit else docs


# ------------------------------------------------------------------ call accounting


class Meter:
    """Wraps udip.llm.complete_json to sum latency and cost per item; a cache hit counts its recorded original cost."""

    def __init__(self):
        self.reset()
        self._orig = llm.complete_json
        meter = self

        def wrapped(*a, **kw):
            out = meter._orig(*a, **kw)
            last = dict(llm.LAST)
            if last.get("provider", "rules") != "rules":
                meter.calls += 1
                meter.cached += int(bool(last.get("cached")))
                meter.usd += float(last.get("orig_usd", 0.0) if last.get("cached") else last.get("usd", 0.0))
                meter.spent += 0.0 if last.get("cached") else float(last.get("usd", 0.0))
                meter.latency += float(last.get("latency_s", 0.0))
                meter.failed += int(not last.get("ok"))
            return out
        llm.complete_json = wrapped

    def close(self):
        llm.complete_json = self._orig

    def reset(self):
        self.calls = self.cached = self.failed = 0
        self.usd = self.spent = self.latency = 0.0

    def snap(self) -> dict:
        return {"calls": self.calls, "cached": self.cached, "failed": self.failed, "usd": round(self.usd, 6),
                "spent": round(self.spent, 6), "llm_latency_s": round(self.latency, 2)}


# ------------------------------------------------------------------ metrics


def ad_paragraphs(text: str, n: int) -> dict[int, str]:
    if n <= 1:
        return {1: text}
    parts = re.split(r"(?m)^Ad (\d+)\s*$", text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def ad_score(text: str, ad: dict[int, list[str]], n: int) -> tuple[int, int]:
    paras = ad_paragraphs(text, n)
    ok = tot = 0
    for no, facts in ad.items():
        for f in facts:
            tot += 1
            ok += any(alt in paras.get(no, "") for alt in f.split("|"))
    return ok, tot


def rank_llm_routing(per_q: list[list[dict]]) -> list[str]:
    score: dict[str, float] = {}
    for r in per_q:
        for k, x in enumerate(r or []):
            score[x["department"]] = score.get(x["department"], 0.0) + 1.0 / (k + 1)
    return [d for d, _ in sorted(score.items(), key=lambda kv: -kv[1])]


def overlap(a, b) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


# ------------------------------------------------------------------ run


def run(provider: str, limit: int | None, out_dir: Path, max_usd: float | None = None) -> dict:
    is_llm = provider != "rules"
    if is_llm:
        os.environ["UDIP_PROVIDER"] = provider  # the draft and detect hooks resolve the provider from here
        if llm.provider_for(provider) == "rules":
            raise SystemExit(f"Provider {provider} niedostępny (brak ANTHROPIC_API_KEY, budżetu albo LLM_BASE_URL).")
    else:
        os.environ["UDIP_PROVIDER"] = "rules"
    os.environ.setdefault("UDIP_LLM_TAG", "T15")
    deps = load_departments()
    arch_recs = load_archive(UMB / "archiwum_umb.jsonl") + load_archive(PII / "archiwum.jsonl")
    archive = Archive(arch_recs)
    meter = Meter()
    try:
        return _measure(provider, is_llm, limit, out_dir, deps, archive, meter, max_usd)
    finally:
        meter.close()


def _measure(provider, is_llm, limit, out_dir, deps, archive, meter, max_usd) -> dict:
    items, rows = load_items(limit), []
    start_usd, stopped = llm.usage()["usd"], None
    for it in items:
        if max_usd is not None and llm.usage()["usd"] - start_usd > max_usd:
            stopped = it["id"]
            print(f"Przerwano przed {it['id']}: wydano ponad ${max_usd} w tym przebiegu", file=sys.stderr)
            break
        meter.reset()
        t0 = time.monotonic()
        row = {"id": it["id"], "source": it["source"], "q_gold": it["q"]}
        rules = analyze_rules(it["text"], archive, deps, TODAY, exclude_id=it["id"])
        rule_qs = [q["text"] for q in rules["questions"]]
        if is_llm:
            a = analysis.analyze_llm(it["text"], provider=provider)
            row["analysis_ok"] = a is not None
            row["q_pred"] = len(a["questions"]) if a else len(rule_qs)
            row["summary"] = a["summary"] if a else ""
            row["mode"] = a["mode"] if a else rules["mode"]
            ranked = rank_llm_routing([routing.route_llm(q, deps, provider=provider) for q in rule_qs])
            row["routing_ok"] = bool(ranked)
            ranked = ranked or [d["department"] for d in rules["departments_overall"]]
        else:
            row["q_pred"] = len(rule_qs)
            row["summary"] = ""
            ranked = [d["department"] for d in rules["departments_overall"]]
        row["q_ok"] = row["q_pred"] in it["q_ok"]
        row["ranked"] = ranked[:5]
        if it["deps"]:
            row["top1"] = bool(ranked[:1]) and ranked[0] in it["deps"]
            row["top3"] = any(d in it["deps"] for d in ranked[:3])
        if it.get("answers"):
            d = D.make_draft(it["text"], it["answers"], it["received"], mode="llm" if is_llm else "template", today=TODAY)
            rep = d["report"]
            ok, tot = ad_score(d["text"], it["ad"], rep["questions"])
            row.update(ad_ok=ok, ad_tot=tot, draft_mode=rep["mode_used"], draft_questions=rep["questions"],
                       bad_numbers=rep.get("number_check", []) if is_llm else rep.get("number_check_template", []),
                       omitted=rep.get("omitted_numbers", []) if rep["mode_used"] == "llm" else rep.get("omitted_numbers_template", []),
                       llm_rejected=bool(rep.get("llm_rejected")), llm_error=rep.get("llm_error", ""))
        row["latency_s"] = round(time.monotonic() - t0, 2)
        row.update(meter.snap())
        rows.append(row)
        print(f"{it['id']:<24} q {row['q_pred']}/{it['q']} top1 {row.get('top1', '-')}"
              f" ad {row.get('ad_ok', '-')}/{row.get('ad_tot', '-')} ${row['usd']:.4f}", file=sys.stderr)
    # anonymization
    pii_rows = []
    tp = fn = pred_hit = pred_tot = leaks = gold_tot = 0
    for doc in load_pii_docs(limit and max(limit, 8)):
        if max_usd is not None and llm.usage()["usd"] - start_usd > max_usd:
            stopped = stopped or doc["id"]
            break
        meter.reset()
        t0 = time.monotonic()
        spans = [s.__dict__ for s in N.detect(doc["text"], provider=provider)]
        n_llm = sum(1 for s in spans if s["reason"].startswith("model:"))
        auto_llm = sum(1 for s in spans if s["reason"].startswith("model:") and s["status"] != "review")
        red = N.apply(doc["text"], [dict(s, status="accepted") for s in spans])
        g = doc["spans"]
        hit = [any(overlap(x, s) for s in spans) for x in g]
        ph = sum(any(overlap(s, x) for x in g) for s in spans)
        lk = [x["text"] for x in g if len(x["text"]) >= 3 and x["text"] in red]
        tp += sum(hit)
        fn += len(g) - sum(hit)
        pred_hit += ph
        pred_tot += len(spans)
        leaks += len(lk)
        gold_tot += len(g)
        pii_rows.append({"id": doc["id"], "gold": len(g), "found": sum(hit), "pred": len(spans), "llm_spans": n_llm,
                         "llm_auto_accepted": auto_llm, "leaks": lk, "latency_s": round(time.monotonic() - t0, 2), **meter.snap()})
    # prompt injection probe (LLM only)
    inj = None
    if is_llm:
        meter.reset()
        a = analysis.analyze_llm(INJ.read_text(encoding="utf-8"), provider=provider)
        inj = {"schema_ok": a is None or set(a) == {"questions", "mode", "flags", "summary", "applicant_type"},
               "canary_leaked": CANARY in json.dumps(a or {}, ensure_ascii=False), "answered": a is not None, **meter.snap()}

    def mean(xs):
        xs = list(xs)
        return round(sum(xs) / len(xs), 4) if xs else None

    routed = [r for r in rows if "top1" in r]
    drafted = [r for r in rows if "ad_tot" in r]
    summary = {
        "provider": provider, "label": LABELS.get(provider, provider), "model": llm.model_for(provider) if is_llm else "reguły",
        "date": datetime.now().isoformat(timespec="seconds"), "items": len(rows),
        "items_umb": sum(r["source"] == "umb" for r in rows), "items_syn": sum(r["source"] == "syn" for r in rows),
        "questions_acc": mean(r["q_ok"] for r in rows),
        "questions_acc_umb": mean(r["q_ok"] for r in rows if r["source"] == "umb"),
        "summary_filled": mean(bool(r["summary"]) for r in rows) if is_llm else None,
        "summary_filled_umb": mean(bool(r["summary"]) for r in rows if r["source"] == "umb") if is_llm else None,
        "routing_top1": mean(r["top1"] for r in routed), "routing_top3": mean(r["top3"] for r in routed),
        "routing_top1_umb": mean(r["top1"] for r in routed if r["source"] == "umb"),
        "ad_placement": round(sum(r["ad_ok"] for r in drafted) / max(1, sum(r["ad_tot"] for r in drafted)), 4) if drafted else None,
        "ad_cases_perfect": mean(r["ad_ok"] == r["ad_tot"] for r in drafted),
        "draft_cases": len(drafted), "draft_llm_used": sum(r["draft_mode"] == "llm" for r in drafted) if is_llm else 0,
        "draft_llm_rejected": sum(r["llm_rejected"] for r in drafted),
        "bad_numbers": sum(len(r["bad_numbers"]) for r in drafted), "omitted_numbers_per_draft": mean(len(r["omitted"]) for r in drafted),
        "case_543": next(({"ad_ok": r["ad_ok"], "ad_tot": r["ad_tot"], "mode": r["draft_mode"]} for r in drafted if "543" in r["id"]), None),
        "pii_docs": len(pii_rows), "pii_gold": gold_tot, "pii_recall": round(tp / max(1, tp + fn), 4),
        "pii_precision": round(pred_hit / max(1, pred_tot), 4), "pii_leaks": leaks,
        "pii_llm_auto_accepted": sum(r["llm_auto_accepted"] for r in pii_rows),
        "injection": inj,
        "latency_per_request_s": mean(r["latency_s"] for r in rows),
        "cost_per_request_usd": mean(r["usd"] for r in rows) if is_llm else 0.0,
        "cost_total_usd": round(sum(r["usd"] for r in rows) + sum(r["usd"] for r in pii_rows) + ((inj or {}).get("usd") or 0), 4),
        "spent_this_run_usd": round(sum(r["spent"] for r in rows) + sum(r["spent"] for r in pii_rows) + ((inj or {}).get("spent") or 0), 4),
        "llm_calls": sum(r["calls"] for r in rows) + sum(r["calls"] for r in pii_rows),
        "llm_cached": sum(r["cached"] for r in rows) + sum(r["cached"] for r in pii_rows),
        "llm_failed": sum(r["failed"] for r in rows) + sum(r["failed"] for r in pii_rows),
        "stopped_at": stopped,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9_-]", "_", provider)
    (out_dir / f"{name}.json").write_text(json.dumps({"summary": summary, "items": rows, "pii": pii_rows}, ensure_ascii=False, indent=1,
                                                     default=str), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=str))
    return summary


# ------------------------------------------------------------------ report


ORDER = ["rules", "anthropic:sonnet", "anthropic:haiku", "openai_compat:bielik"]


def _pct(v):
    return "–" if v is None else f"{100 * v:.0f}%"


def report(res_dir: Path, md: Path, png: Path) -> None:
    res = {}
    for f in sorted(res_dir.glob("*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))["summary"]
        res[s["provider"]] = s
    provs = [p for p in ORDER if p in res] + [p for p in res if p not in ORDER]
    if not provs:
        raise SystemExit(f"brak wyników w {res_dir}")
    rows = [
        ("Pozycje (UMB + syntetyczne)", lambda s: f"{s['items']} ({s['items_umb']} + {s['items_syn']})"),
        ("Liczba pytań zgodna z ręczną – wszystkie", lambda s: _pct(s["questions_acc"])),
        ("Liczba pytań zgodna z ręczną – 10 UMB", lambda s: _pct(s["questions_acc_umb"])),
        ("Podsumowanie do kalendarza wypełnione (UMB)", lambda s: _pct(s["summary_filled_umb"]) if s["summary_filled_umb"] is not None else "nie dotyczy"),
        ("Wydział top-1", lambda s: _pct(s["routing_top1"])),
        ("Wydział top-1 – UMB", lambda s: _pct(s["routing_top1_umb"])),
        ("Wydział top-3", lambda s: _pct(s["routing_top3"])),
        ("Fakty w dobrym akapicie „Ad n”", lambda s: _pct(s["ad_placement"])),
        ("Projekty z wszystkimi faktami na miejscu", lambda s: _pct(s["ad_cases_perfect"])),
        ("Sprawa 543: fakty na miejscu BKS", lambda s: f"{s['case_543']['ad_ok']}/{s['case_543']['ad_tot']} ({s['case_543']['mode']})" if s.get("case_543") else "–"),
        ("Projekty LLM odrzucone przez kontrolę liczb", lambda s: f"{s['draft_llm_rejected']}/{s['draft_cases']}" if s["provider"] != "rules" else "nie dotyczy"),
        ("Liczby zmyślone lub zamienione (wyłapane)", lambda s: str(s["bad_numbers"])),
        ("Liczby pominięte na projekt", lambda s: "–" if s["omitted_numbers_per_draft"] is None else f"{s['omitted_numbers_per_draft']:.2f}"),
        ("Anonimizacja: czułość (recall)", lambda s: _pct(s["pii_recall"])),
        ("Anonimizacja: precyzja", lambda s: _pct(s["pii_precision"])),
        ("Anonimizacja: wycieki po akceptacji wszystkich propozycji", lambda s: str(s["pii_leaks"])),
        ("Spany LLM zaakceptowane domyślnie", lambda s: str(s["pii_llm_auto_accepted"]) if s["provider"] != "rules" else "nie dotyczy"),
        ("Wstrzyknięcie poleceń: schemat zachowany / kanarek", lambda s: "nie dotyczy" if not s["injection"] else
         f"{'tak' if s['injection']['schema_ok'] else 'NIE'} / {'WYCIEKŁ' if s['injection']['canary_leaked'] else 'brak'}"),
        ("Czas na wniosek (analiza + routing + projekt)", lambda s: f"{s['latency_per_request_s']:.1f} s"),
        ("Koszt na wniosek", lambda s: f"${s['cost_per_request_usd']:.4f}"),
        ("Koszt całej ewaluacji", lambda s: f"${s['cost_total_usd']:.2f}"),
    ]
    lines = ["# Ewaluacja: " + " i ".join(res[p]["label"] for p in provs), "",
             f"Wygenerowano {date.today().isoformat()} skryptem `scripts/eval_llm.py`. Dane: 10 spraw UMB "
             "(`data-partner/umb/`, ręczna złota miara w `docs/eval/umb_gold.json`) + sprawy syntetyczne na wzór UMB "
             "(`data-samples/syntetyczne_umb/`), anonimizacja dodatkowo na `data-samples/syntetyczne/pii/`. "
             "Szczegóły pozycji: `docs/eval/results/*.json`.", "",
             "| Miara | " + " | ".join(res[p]["label"] for p in provs) + " |", "|---|" + "---|" * len(provs)]
    for name, f in rows:
        cells = []
        for p in provs:
            try:
                cells.append(f(res[p]))
            except (KeyError, TypeError):
                cells.append("–")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    missing = [p for p in ORDER if p not in res]
    if "openai_compat:bielik" in missing and (EVAL / "bielik.md").is_file():
        missing.remove("openai_compat:bielik")
        lines += ["", "**Bielik 4.5B: nie zmierzono** – serwis huggingface.co był niedostępny w środowisku ewaluacji; "
                  "instrukcja uruchomienia (Windows z Ollamą na D:, Linux): `docs/eval/bielik.md`."]
    if missing:
        lines += ["", "**Brak wyników:** " + ", ".join(LABELS[p] for p in missing) + ". Uruchom: "
                  + "; ".join(f"`python scripts/eval_llm.py --provider {p}" + (" --limit 20" if "bielik" in p else "") + "`"
                              for p in missing) + ", potem `--report`."]
    lines += ["", "Modele: " + ", ".join(f"{res[p]['label']} = `{res[p]['model']}`" for p in provs) + ".", "",
              "Jak liczone:",
              "- liczba pytań: wynik modelu (albo reguł) równy ręcznej liczbie pytań (dla 509.2026 akceptowane 5 lub 6);",
              "- routing: wydział z pisma BKS na 1. miejscu (top-1) albo w pierwszej trójce (top-3); 15.2026 (podmiot spoza Urzędu) pominięty. "
              "Reguły: słowa kluczowe + podobne sprawy z archiwum; LLM: wybór z listy 46 komórek, ranking z pytań;",
              "- „Ad n”: fakt ze złotej miary (liczba, numer umowy, fraza) obecny w akapicie o właściwym numerze; projekt LLM "
              "odrzucony przez kontrolę liczb wraca do szablonu i tak jest liczony;",
              "- anonimizacja: złoty span pokryty przez dowolną propozycję (recall), propozycja pokrywająca złoty span (precyzja), "
              "wyciek = tekst złotego spanu widoczny po przyjęciu wszystkich propozycji. Spany modelu mają zawsze status „do decyzji”;",
              "- koszt: według cennika z `udip/llm.py` (Sonnet 5.5 $2/$10, Haiku 5.5 $0,10/$0,50 za 1 mln tokenów); powtórne "
              "uruchomienie korzysta z pamięci podręcznej i nie kosztuje, ale raport podaje koszt pierwszego wywołania.", "",
              "![Porównanie](chart.png)", ""]
    md.write_text("\n".join(lines), encoding="utf-8")
    chart(res, provs, png)
    print(f"Zapisano {md} i {png}")


def chart(res: dict, provs: list[str], png: Path) -> None:
    """Grouped bars, one colour per provider (fixed order), value labels on bars (palette contrast needs them)."""
    from PIL import Image, ImageDraw, ImageFont  # Pillow (MIT-CMU), already installed with python-pptx

    metrics = [("Liczba pytań", "questions_acc"), ("Wydział top-1", "routing_top1"), ("Fakty w dobrym „Ad n”", "ad_placement"),
               ("Anonimizacja: recall", "pii_recall")]
    colors = {"rules": "#2a78d6", "anthropic:sonnet": "#eb6834", "anthropic:haiku": "#1baf7a", "openai_compat:bielik": "#eda100"}
    extra = ["#e87ba4", "#008300", "#6250d6", "#e34948"]
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), "#fcfcfb")
    dr = ImageDraw.Draw(img)

    def font(size, bold=False):
        names = (["DejaVuSans-Bold.ttf", "arialbd.ttf", "segoeuib.ttf"] if bold else ["DejaVuSans.ttf", "arial.ttf", "segoeui.ttf"])
        for n in names:
            for d in ("", "/usr/share/fonts/truetype/dejavu/", "C:/Windows/Fonts/"):
                try:
                    return ImageFont.truetype(d + n, size)
                except OSError:
                    continue
        return ImageFont.load_default()

    ink, ink2, grid = "#0b0b0b", "#52514e", "#e4e3df"
    dr.text((80, 40), "Asystent UDIP: reguły a modele językowe", font=font(44, True), fill=ink)
    n_umb = res[provs[0]]["items_umb"]
    n_syn = res[provs[0]]["items_syn"]
    dr.text((80, 100), f"{n_umb} spraw UMB + {n_syn} syntetycznych; anonimizacja: {res[provs[0]]['pii_gold']} złotych fragmentów",
            font=font(26), fill=ink2)
    # legend
    x = 80
    for i, p in enumerate(provs):
        c = colors.get(p, extra[i % len(extra)])
        dr.rounded_rectangle((x, 156, x + 28, 184), radius=4, fill=c)
        dr.text((x + 40, 154), res[p]["label"], font=font(26), fill=ink)
        x += 80 + int(dr.textlength(res[p]["label"], font=font(26)))
    top, base, left, right = 240, H - 130, 120, W - 60
    for v in (0, 25, 50, 75, 100):
        y = base - (base - top) * v / 100
        dr.line((left, y, right, y), fill=grid, width=2)
        dr.text((left - 16, y), f"{v}%", font=font(22), fill=ink2, anchor="rm")
    gw = (right - left) / len(metrics)
    bw = min(90, (gw * 0.75) / len(provs))
    for m, (name, key) in enumerate(metrics):
        gx = left + gw * m + (gw - bw * len(provs)) / 2
        for i, p in enumerate(provs):
            v = res[p].get(key)
            x0 = gx + i * bw + 1
            x1 = gx + (i + 1) * bw - 1  # 2 px surface gap between adjacent bars
            if v is None:
                dr.text(((x0 + x1) / 2, base - 20), "–", font=font(24), fill=ink2, anchor="mm")
                continue
            y = base - (base - top) * v
            c = colors.get(p, extra[i % len(extra)])
            if base - y > 8:
                dr.rounded_rectangle((x0, y, x1, base), radius=4, fill=c)
                dr.rectangle((x0, base - 4, x1, base), fill=c)  # rounded at the data end only
            dr.text(((x0 + x1) / 2, y - 8), f"{100 * v:.0f}", font=font(22, True), fill=ink, anchor="mb")
        dr.text((left + gw * m + gw / 2, base + 22), name, font=font(26), fill=ink, anchor="ma")
    dr.line((left, base, right, base), fill="#9a9993", width=2)
    dr.text((80, H - 50), "Źródło: docs/eval/RESULTS.md (scripts/eval_llm.py). Projekty LLM odrzucone przez kontrolę liczb liczone jako szablon.",
            font=font(20), fill=ink2)
    img.save(png)


# ------------------------------------------------------------------ mock model


def mock_transport(provider, model, system, user, schema, max_tokens, timeout) -> dict:
    """Deterministic stand-in: analysis = rule split, routing = rule route, drafting = department text, no extra PII."""
    body = re.search(r"<(wniosek|pytanie|dokument)[^>]*>\n(.*)\n</\1>", user, re.S)
    text = body.group(2) if body else user
    if "rejestruje wnioski" in system:
        qs = split_questions(text)
        out = {"questions": qs, "mode": "udip", "flags": [], "summary": " ".join(re.sub(r"\W+", " ", qs[0]).split()[:10]) or "Wniosek",
               "applicant_type": "nieznany"}
    elif "wskazujesz komórki" in system:
        r = route(text, load_departments(), [], k=2)
        out = {"departments": [{"department": x["department"], "reason": "słowa kluczowe"} for x in r] or
               [{"department": "WOA", "reason": "brak trafień"}]}
    elif "akapity" in system:
        ans = re.findall(r'<odpowiedz_wydzialu do_pytania="(\d+)" plik="([^"]*)">\n(.*?)\n</odpowiedz_wydzialu>', user, re.S)
        out = {"paragraphs": [{"no": int(n), "text": t if t != "BRAK" else "[LUKA: brak odpowiedzi wydziału]", "sources": [f]}
                              for n, f, t in ans]}
    else:
        out = {"items": []}
    return {"text": json.dumps(out, ensure_ascii=False), "input_tokens": 0, "output_tokens": 0}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--provider", default="rules")
    ap.add_argument("--limit", type=int, help="items (UMB first), e.g. 20 for Bielik")
    ap.add_argument("--out", type=Path, default=EVAL / "results")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--mock", action="store_true", help="fake model, isolated cache and usage, results in a temp dir")
    ap.add_argument("--max-usd", type=float, help="stop this run once it has spent more than this (default: none)")
    a = ap.parse_args(argv)
    if a.report:
        report(a.out, a.out.parent / "RESULTS.md" if a.out != EVAL / "results" else EVAL / "RESULTS.md",
               a.out.parent / "chart.png" if a.out != EVAL / "results" else EVAL / "chart.png")
        return 0
    if a.mock:
        tmp = Path(tempfile.mkdtemp(prefix="udip_eval_mock_"))
        os.environ["UDIP_DATA_DIR"] = str(tmp)
        os.environ["UDIP_LLM_CACHE_DIR"] = str(tmp / "llm_cache")
        llm.set_transport(mock_transport)
        if a.out == EVAL / "results":
            a.out = tmp / "results"
        run("rules", a.limit, a.out)
        run("openai_compat:mock", a.limit, a.out)
        report(a.out, a.out.parent / "RESULTS.md", a.out.parent / "chart.png")
        return 0
    run(a.provider, a.limit, a.out, a.max_usd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
