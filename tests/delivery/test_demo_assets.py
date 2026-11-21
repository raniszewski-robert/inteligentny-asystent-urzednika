"""T29: demo files exist, open, and trigger the behaviour demo_assets/README.md promises."""
from datetime import date
from pathlib import Path

from udip.anonymize import detect
from udip.draft import check_numbers
from udip.ingest import read_any

D = Path(__file__).resolve().parents[2] / "demo_assets"


def test_files_open():
    for f in ("01_rejestr_umb.xlsx", "02_wniosek_atak_bezpieczenstwa.docx", "03_odpowiedz_wydzialu.docx",
              "03b_odpowiedz_wydzialu_zamienione_liczby.docx", "04_nowelizacja_udip_2026_demo.pdf"):
        assert (D / f).stat().st_size > 0
    assert "NIE JEST AKTEM PRAWNYM" in read_any(D / "04_nowelizacja_udip_2026_demo.pdf")["text"]


def test_attack_request_spans():
    t = read_any(D / "02_wniosek_atak_bezpieczenstwa.docx")["text"]
    sp = {s.text: (s.type, s.status) for s in detect(t, provider="rules")}
    for secret in ("44051401359", "PL61 1090 1014 0000 0712 1981 2874", "b.krawczyk@example.com", "601 234 567", "ul. Fordońska 112/7"):
        assert sp.get(secret, ("", ""))[1] == "suggested", secret
    assert sp.get("Rafał Bruski") == ("OSOBA", "review")  # public official: clerk decides
    assert not any("Jezuicka" in k for k in sp)  # city hall address stays public


def test_swapped_numbers_are_flagged():
    good = read_any(D / "03_odpowiedz_wydzialu.docx")["text"]
    bad = read_any(D / "03b_odpowiedz_wydzialu_zamienione_liczby.docx")["text"]
    assert check_numbers(["Schronisko zapewniło opiekę w 2025 r. 839 psom oraz 560 kotom."], [good]) == []
    swapped = next(l for l in bad.splitlines() if "839" in l)
    assert check_numbers([swapped], [good])
