"""T01: udip/ is the one copy of the core; skill scripts are thin CLI wrappers over it."""
from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SK = ROOT / ".claude" / "skills"
UMB = ROOT / "data-partner" / "umb"

# wrapper → udip module it fronts
WRAPPERS = {
    "udip-kalendarz-terminy/scripts/deadlines.py": "udip.deadlines",
    "udip-kalendarz-terminy/scripts/register.py": "udip.register",
    "udip-kalendarz-terminy/scripts/import_xlsx.py": "udip.importer",
    "udip-dane-i-zrodla/scripts/ingest.py": "udip.ingest",
    "udip-archiwum-i-wydzialy/scripts/search.py": "udip.search",
    "udip-archiwum-i-wydzialy/scripts/analyze.py": "udip.analyze",
    "udip-anonimizacja/scripts/anonymize.py": "udip.anonymize",
    "udip-projekty-odpowiedzi/scripts/draft.py": "udip.draft",
}
CLI_FUNCS = {"main", "_selftest", "_load_keep"}


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=ROOT, timeout=120)


def test_bridge_removed_and_no_skill_dirs_on_path():
    import udip.analyze  # noqa: F401
    import udip.draft  # noqa: F401
    assert not (ROOT / "udip" / "_skills.py").exists()
    assert not [p for p in sys.path if ".claude" in p and "skills" in p]


@pytest.mark.parametrize("rel,mod", sorted(WRAPPERS.items()))
def test_wrapper_is_thin(rel, mod):
    """A wrapper defines only CLI functions and imports its logic from udip (no duplicated logic)."""
    tree = ast.parse((SK / rel).read_text(encoding="utf-8"))
    defs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    assert set(defs) <= CLI_FUNCS, f"{rel} defines {set(defs) - CLI_FUNCS}"
    froms = {n.module for n in tree.body if isinstance(n, ast.ImportFrom)}
    assert mod in froms


@pytest.mark.parametrize("rel,mod", sorted(WRAPPERS.items()))
def test_wrapper_import_gives_udip_objects(rel, mod):
    spec = importlib.util.spec_from_file_location("w_" + Path(rel).stem, SK / rel)
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    real = importlib.import_module(mod)
    public = [k for k, v in vars(real).items() if not k.startswith("_") and callable(v) and getattr(v, "__module__", "") == mod]
    assert public and all(getattr(w, k) is getattr(real, k) for k in public)


def test_data_lives_in_udip_data():
    from udip.analyze import DEFAULT_DEPTS, load_departments
    from udip.anonymize import DATA, FIRST_NAMES
    from udip.letters import LETTER_TYPES
    data = ROOT / "udip" / "data"
    assert DEFAULT_DEPTS == data / "departments.json" and DATA == data
    assert len(load_departments()) > 40 and len(FIRST_NAMES) > 100 and "udostepnienie" in LETTER_TYPES
    for skill in ("udip-archiwum-i-wydzialy", "udip-projekty-odpowiedzi"):
        assert not list((SK / skill).glob("data/*"))


def test_analyze_cli_rules_by_default():
    r = _run(str(SK / "udip-archiwum-i-wydzialy/scripts/analyze.py"), str(UMB / "przypadek_543/wniosek.txt"),
             "--archive", str(UMB / "archiwum_umb.jsonl"), "--today", "2026-11-22")
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert res["provider"] == "rules" and res["llm_used"] is False and len(res["questions"]) == 5


def test_draft_cli_llm_mode_goes_through_udip_llm(tmp_path):
    """--mode llm uses udip.llm; with provider rules it falls back to the template and says why."""
    r = _run(str(SK / "udip-projekty-odpowiedzi/scripts/draft.py"), "--request", str(UMB / "przypadek_543/wniosek.txt"),
             "--answer", str(UMB / "przypadek_543/SCHRONISKO.txt"), "--received", "2026-08-14", "--today", "2026-11-22",
             "--mode", "llm", "--out-dir", str(tmp_path))
    assert r.returncode == 0, r.stderr
    rep = json.loads(r.stdout)
    assert rep["mode_used"] == "template" and "provider rules" in rep["llm_error"]
    assert (tmp_path / "projekt.docx").exists()


def test_import_cli_matches_library(tmp_path):
    from udip.importer import convert, extension_to_days, fill_departments
    from udip.search import load_archive
    out = tmp_path / "rej.json"
    r = _run(str(SK / "udip-kalendarz-terminy/scripts/import_xlsx.py"), str(UMB / "kalendarium_umb.xlsx"), "--out", str(out),
             "--archive", str(UMB / "archiwum_umb.jsonl"))
    assert r.returncode == 0, r.stderr
    cli = json.loads(out.read_text(encoding="utf-8"))["requests"]
    recs, _ = convert(UMB / "kalendarium_umb.xlsx")
    lib = extension_to_days(fill_departments(recs, load_archive(UMB / "archiwum_umb.jsonl")))
    assert [(c["number"], c["departments"], c.get("extension_days")) for c in cli] == \
           [(x["number"], x["departments"], x.get("extension_days")) for x in lib]
    assert any(x["departments"] for x in lib) and all("extension_until" not in x for x in lib)


def test_draft_spans_stay_rules_only(monkeypatch):
    """make_draft proposes anonymization by rules only; model spans belong to the anonymization screen (detect)."""
    import udip.llm as L
    from udip.draft import make_draft
    from udip.llm_tasks import anonymization
    monkeypatch.setattr(L, "available", lambda: True)
    monkeypatch.setenv("UDIP_PROVIDER", "anthropic:sonnet")
    monkeypatch.setattr(anonymization, "spans_llm", lambda t: [{"start": 0, "end": 5, "type": "OSOBA"}])
    req = (UMB / "przypadek_543/wniosek.txt").read_text(encoding="utf-8")
    d = make_draft(req, [], date(2026, 8, 14), today=date(2026, 11, 22))
    assert not any(s["reason"].startswith("model:") for s in d["spans"])


def test_search_matched_terms_deterministic():
    code = ("from udip.search import Archive, load_archive; import json;"
            f"a = Archive(load_archive(r'{UMB / 'archiwum_umb.jsonl'}'));"
            "print(json.dumps(a.search('schronisko psy koty bezdomne zwierzęta opieka')))")
    outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT,
                           env={"PYTHONHASHSEED": s, "PATH": ""}).stdout for s in ("1", "2", "3")}
    assert len(outs) == 1 and outs != {""}
