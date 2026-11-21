"""T15: eval pipeline end to end with the rules provider and the mock model (no key, no network)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("eval_llm", ROOT / "scripts" / "eval_llm.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


def test_ad_score():
    text = "Szanowni\nAd 1\nSchronisko nie zawierało umów.\nAd 2\n839 psom\n"
    assert E.ad_score(text, {1: ["nie zawierało umów|nie udzielał"], 2: ["839 psom", "560 kotom"]}, 2) == (2, 3)
    assert E.ad_score("cały tekst 12 sztuk", {1: ["12 sztuk"]}, 1) == (1, 1)


def test_rank_llm_routing():
    assert E.rank_llm_routing([[{"department": "WE"}, {"department": "WOA"}], [{"department": "WOA"}], None]) == ["WOA", "WE"]


def test_mock_eval_end_to_end(iso, tmp_path):
    out = tmp_path / "eval" / "results"
    orig = E.llm.complete_json
    assert E.main(["--mock", "--out", str(out), "--limit", "10"]) == 0
    assert E.llm.complete_json is orig  # the cost meter unwraps itself
    res = {p.stem: json.loads(p.read_text(encoding="utf-8"))["summary"] for p in out.glob("*.json")}
    assert set(res) == {"rules", "openai_compat_mock"}
    r, m = res["rules"], res["openai_compat_mock"]
    assert r["items_umb"] == 10 and r["questions_acc_umb"] >= 0.8 and r["pii_leaks"] == 0
    assert m["summary_filled_umb"] == 1.0 and m["pii_llm_auto_accepted"] == 0 and m["injection"]["canary_leaked"] is False
    assert m["case_543"]["mode"] == "llm" and m["spent_this_run_usd"] == 0
    md = (tmp_path / "eval" / "RESULTS.md").read_text(encoding="utf-8")
    assert "| Miara | Reguły | openai_compat:mock |" in md and (tmp_path / "eval" / "chart.png").stat().st_size > 10_000
