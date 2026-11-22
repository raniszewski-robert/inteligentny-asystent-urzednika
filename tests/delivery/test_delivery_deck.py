"""T21 draft: deck outline fits 10 slides and covers task section 4; video script fits 2:45 and uses only
contract routes; the demo file for the anonymization scene still gives what the script promises."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTLINE = REPO / "docs/deck/outline.md"
SCRIPT = REPO / "docs/video_script.md"
CONTRACTS = (REPO / "docs/plan/CONTRACTS.md").read_text(encoding="utf-8")


def _slides() -> list[int]:
    return [int(m) for m in re.findall(r"^## (\d+)\. ", OUTLINE.read_text(encoding="utf-8"), re.M)]


def test_outline_has_at_most_ten_slides_in_order():
    s = _slides()
    assert s == list(range(1, len(s) + 1)) and 1 <= len(s) <= 10


def test_outline_covers_every_item_of_task_section_4():
    text = OUTLINE.read_text(encoding="utf-8")
    table = text.split("## Pokrycie wymagań", 1)[1].split("\n---\n", 1)[0]
    rows = [r for r in table.splitlines() if r.startswith("| ") and not r.startswith("| Wymaganie")]
    items = {int(m.group(1)) for r in rows if (m := re.match(r"\| (\d)\. ", r))}
    assert items == set(range(1, 9)), "task section 4 lists 8 required items"
    n = len(_slides())
    for r in rows:
        cited = [int(x) for x in re.findall(r"\b(\d+)\b", r.split("|")[2])]
        assert cited and all(1 <= x <= n for x in cited), r


def _spoken_seconds(script_text: str, wpm: float = 130.0) -> float:
    words = 0
    for line in script_text.splitlines():
        if line.startswith(("#", ">")) or not line.strip():
            continue
        spoken = re.sub(r"\[[^\]]*\]", " ", line)
        words += len(re.findall(r"\w+", spoken))
    return words / wpm * 60.0


def test_video_script_fits_limit():
    text = SCRIPT.read_text(encoding="utf-8")
    limit = 165.0  # 2:45
    assert _spoken_seconds(text) <= limit * 0.9, "spoken text should leave at least 10% margin at 130 wpm"
    planned = sum(int(m) * 60 + int(s) for m, s in
                  re.findall(r"^## \d+\..*\((\d+):(\d\d)\)\s*$", text, re.M))
    assert 0 < planned <= 165, f"scene plan {planned}s exceeds 2:45"


def test_video_script_uses_contract_routes_only():
    paths = set(re.findall(r"`(?:GET/POST |GET |POST )?(/[a-z][^`\s]*)`", SCRIPT.read_text(encoding="utf-8")))
    assert paths
    for p in paths:
        base = re.sub(r"\.(docx|txt)$", "", p)
        assert p in CONTRACTS or base in CONTRACTS, f"{p} is not a route in CONTRACTS §5"


def test_demo_personal_data_file_redacts_fully():
    import udip.anonymize as A
    from udip.ingest import read_any
    text = read_any(REPO / "docs/deck/demo_dane_osobowe.docx")["text"]
    spans = [s.__dict__ for s in A.detect(text, provider="rules")]
    out = A.apply(text, spans, accept_all=True)
    for secret in ["Nowak-Kowalska", "Słoneczna 7/12", "601 234 567", "anna.nowak@", "44051401359", "ABA300000",
                   "1090 1014", "12.03.1980"]:
        assert secret not in out
    assert any(s["text"] == "J. Nowak" and s["status"] == "review" for s in spans), "scene 6 shows J. Nowak for review"
