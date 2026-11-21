"""T14: generator pipeline with the mock model and the validator (no key, no network)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("gen_synthetic_umb", ROOT / "scripts" / "gen_synthetic_umb.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def test_mock_generation_is_valid(iso, tmp_path):
    out = tmp_path / "syn"
    assert G.main(["--mock", "--n", "5", "--out", str(out)]) == 0
    cases = [json.loads(l) for l in (out / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 5 and (out / "archiwum.jsonl").is_file() and (out / "README.md").is_file()
    meta = json.loads((out / "generation.json").read_text(encoding="utf-8"))
    assert meta["valid"] == 5 and meta["usd"] == 0
    c = cases[0]
    assert c["gold"]["pii"] and all(G.DEPS.get(d) for d in c["gold"]["departments"])
    assert "Ad 1" in c["letter_text"] or len(c["paragraphs"]) == 1


def test_validator_catches_errors(iso, tmp_path):
    out = tmp_path / "syn"
    G.main(["--mock", "--n", "2", "--out", str(out)])
    c = json.loads((out / "cases.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert G.validate_case(c) == []
    bad = json.loads(json.dumps(c))
    bad["gold"]["pii"][0]["start"] += 1
    bad["gold"]["departments"].append("NIEMA")
    bad["paragraphs"][0]["text"] += " Dodatkowo 777 777,77 zł."
    errs = " | ".join(G.validate_case(bad))
    assert "pii span" in errs and "unknown department" in errs and "777" in errs


def test_without_provider_nothing_is_written(iso, tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert G.main(["--n", "1", "--out", str(tmp_path / "x")]) == 2 and not (tmp_path / "x").exists()


def test_seeds_use_known_departments():
    assert len(G.SEEDS) >= 40
    assert all(d in G.DEPS for s in G.SEEDS for d in s[1])
