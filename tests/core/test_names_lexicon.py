"""T28: name lexicon (udip/data/names) – the torture document from the external review, offline, rules only."""
from __future__ import annotations

import docx
import pytest

from udip import anonymize as N
from udip.anonymize import apply, detect
from udip.ingest import read_any

TORTURE = [
    "Wnioskodawca Bogumił Krawczyk (PESEL 44051401359) wraz z sąsiadką Bożeną Zając wnosi o udostępnienie informacji.",
    "W sprawie pomagała mi Olena Shevchenko, a tłumaczyła Ołena Szewczenko.",
    "Nieruchomość ma księgę wieczystą BY1B/00012345/6, działka nr 123/4 obręb Fordon, której właścicielem jest wnioskodawca.",
    "Zwrot opłaty proszę przelać na rachunek PL61 1090 1014 0000 0712 1981 2874.",
    "Spółka zastrzega, że załączony kosztorys stanowi tajemnicę przedsiębiorstwa.",
    "Pismo kieruję do Prezydenta Miasta Bydgoszczy Rafała Bruskiego, Urząd Miasta Bydgoszczy, ul. Jezuicka 1, 85-102 Bydgoszcz.",
    "Szkoła mieści się przy ul. św. Maksymiliana Kolbego 5. Mieszka przy niej woźny.",
]
PRIVATE = ["Bogumił Krawczyk", "44051401359", "Bożeną Zając", "Olena Shevchenko", "Ołena Szewczenko", "BY1B/00012345/6",
           "PL61 1090 1014 0000 0712 1981 2874"]
DECIDE = ["123/4", "tajemnicę przedsiębiorstwa", "Rafała Bruskiego"]  # clerk decides (plot owner, business secret, official)
PUBLIC = ["Jezuicka", "Kolbego", "Maksymiliana", "Mieszka"]


@pytest.fixture()
def torture_docx(tmp_path, monkeypatch):
    monkeypatch.setenv("UDIP_OFFLINE", "1")
    d = docx.Document()
    for p in TORTURE:
        d.add_paragraph(p)
    path = tmp_path / "pii_torture_test.docx"
    d.save(str(path))
    return path


def test_lexicon_loaded():
    assert {"Olena", "Bożena", "Bożeną", "Ołena"} <= set(N.NAME_FORMS)
    assert {"Shevchenko", "Szewczenko", "Krawczyk", "Krawczykowi"} <= set(N.SURNAME_FORMS)
    assert "Mieszka" in N.AMBIG_FIRST and "Mieszka" not in N.NAME_FORMS  # „mieszka” = lives


def test_torture_document_offline(torture_docx):
    text = read_any(torture_docx)["text"]
    spans = detect(text, provider="rules")
    by_text = lambda frag: [s for s in spans if frag in s.text or s.text in frag and len(s.text) > 3]
    for frag in PRIVATE:
        hits = by_text(frag)
        assert hits and any(s.status == "suggested" for s in hits), f"private data not proposed: {frag}"
    for frag in DECIDE:
        hits = by_text(frag)
        assert hits and all(s.status == "review" for s in hits), f"should be the clerk's decision: {frag} {hits}"
    for frag in PUBLIC:
        assert not any(frag in s.text for s in spans if s.type in ("OSOBA", "ADRES")), f"false positive on {frag}"
    # accept every proposal → no private data left in the anonymized text
    out = apply(text, [dict(s.__dict__, status="accepted" if s.status == "suggested" else "rejected") for s in spans])
    assert not any(frag in out for frag in PRIVATE)
    assert "Jezuicka 1" in out and "Kolbego" in out and "Mieszka przy niej" in out


def test_ambiguous_first_name_needs_a_pair():
    assert not [s for s in N.detect_rules("Mieszka przy ul. Długiej.") if s.type == "OSOBA"]
    assert [s.text for s in N.detect_rules("Pismo podpisała Róża Wrona.") if s.type == "OSOBA"] == ["Róża Wrona"]


def test_known_surname_with_unknown_first_name():
    hits = [s for s in N.detect_rules("Odpowiedź otrzymała Zlatka Kowalska.") if s.type == "OSOBA"]
    assert [s.text for s in hits] == ["Zlatka Kowalska"] and "ze słownika" in hits[0].reason


def test_business_secret_sentence_is_review():
    sp = [s for s in N.detect_rules("Oferta zawiera tajemnicę handlową wykonawcy. Cena wynosi 10 zł.") if s.type == "TAJEMNICA"]
    assert len(sp) == 1 and sp[0].status == "review" and "Cena" not in sp[0].text


def test_demo_asset_ukrainian_name_detected():
    from pathlib import Path
    text = read_any(Path(__file__).resolve().parents[2] / "demo_assets" / "02_wniosek_atak_bezpieczenstwa.docx")["text"]
    assert any(s.text == "Olena Shevchenko" and s.status == "suggested" for s in detect(text, provider="rules"))
