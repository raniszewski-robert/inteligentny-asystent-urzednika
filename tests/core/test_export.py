"""T27: fixed-length blocks, scrubbed metadata, XML audit, footer only for categories actually redacted."""
from __future__ import annotations

import io
import zipfile
from datetime import date

import docx

from udip import export as ex
from udip.anonymize import detect
from udip.draft import write_docx

PII = ("Anna Nowak-Kowalska\nul. Słoneczna 7/12\n85-001 Bydgoszcz\nanna.nowak@example.com\n"
       "PESEL 44051401359, rachunek PL61 1090 1014 0000 0712 1981 2874\nZ poważaniem\nAnna Nowak-Kowalska\n")


def _final_docx(tmp_path, text, spans, footer=""):
    p = tmp_path / "x.docx"
    write_docx(text, spans, p, final=True, footer=footer)
    d = docx.Document(str(p))
    d.core_properties.author = "Jan Urzędnik"
    d.core_properties.title = "Anna Nowak-Kowalska – odpowiedź"
    d.core_properties.comments = "PESEL 44051401359"
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_export_has_no_leak_and_no_metadata(tmp_path):
    spans = [dict(s.__dict__, status="accepted") for s in detect(PII)]
    secrets = [PII[s["start"]:s["end"]] for s in spans]
    assert any("44051401359" in x for x in secrets) and any("Nowak" in x for x in secrets)
    raw = _final_docx(tmp_path, PII, spans)
    assert not ex.audit_docx(raw, secrets)["ok"]  # unhardened: the author/title/comments still carry personal data
    hard = ex.harden_docx(raw)
    a = ex.audit_docx(hard, secrets + ["Jan Urzędnik"])
    assert a["ok"], a["hits"]
    core = zipfile.ZipFile(io.BytesIO(hard)).read("docProps/core.xml").decode()
    for tag in ("creator", "lastModifiedBy", "title", "subject", "keywords", "description"):
        assert f"{tag}>" not in core or f"<dc:{tag}></dc:{tag}>" in core
    assert docx.Document(io.BytesIO(hard)).paragraphs  # still a valid DOCX


def test_blocks_have_fixed_length(tmp_path):
    text = "PESEL 44051401359 i Jan."
    spans = [{"start": 6, "end": 17, "status": "accepted", "type": "PESEL", "id": "s1"}]
    body = "\n".join(p.text for p in docx.Document(io.BytesIO(_final_docx(tmp_path, text, spans))).paragraphs)
    assert ex.BLOCK in body and "█" * 11 not in body and "44051401359" not in body


def test_audit_is_case_whitespace_and_diacritic_insensitive(tmp_path):
    raw = _final_docx(tmp_path, "Pani ANNA  NOWAK-KÓWALSKA mieszka tu.", [])
    assert not ex.audit_docx(raw, ["anna nowak-kowalska"])["ok"]


def test_metryczka_lists_only_redacted_categories():
    m = ex.metryczka(["PESEL", "OSOBA"], "PK", date(2026, 11, 22))
    assert "numery PESEL" in m and "imiona i nazwiska" in m and "art. 5 ust. 2" in m and "PK" in m and "22.11.2026" in m
    assert "adresy" not in m and "NIP" not in m
    assert "tajemnica przedsiębiorcy" in ex.metryczka(["NIP"], "", date(2026, 11, 22))
    assert ex.metryczka([], "PK", date(2026, 11, 22)) == ""


def test_footer_lands_in_docx(tmp_path):
    raw = _final_docx(tmp_path, "Tekst.", [], footer=ex.metryczka(["OSOBA"], "PK", date(2026, 11, 22)))
    d = docx.Document(io.BytesIO(raw))
    assert "Wyłączenie jawności" in d.sections[0].footer.paragraphs[0].text
