"""Redaction with nested spans: a SZCZEGOLNE_* sentence span contains OSOBA/ADRES spans (report from lane B2)."""
from __future__ import annotations

import docx

from udip.anonymize import apply, detect, flatten
from udip.draft import finalize, write_docx

T = "Wnioskodawca Jan Kowalski choruje na cukrzycę i leczy się w poradni. Mieszka przy ul. Długa 15/4."
SECRET = ["Kowalski", "cukrzyc", "poradni", "Długa 15/4"]


def _spans(status="accepted"):
    sp = [dict(s.__dict__, status=status) for s in detect(T, provider="rules")]
    assert any(a["start"] < b["start"] < a["end"] for a in sp for b in sp), "fixture must contain nested spans"
    return sp


def test_apply_nested_accepted_no_corruption():
    out = apply(T, _spans())
    assert not any(x in out for x in SECRET)
    assert out.endswith("Mieszka przy [adres].") and out.count("[") == 2


def test_apply_block_mode_keeps_length():
    out = apply(T, _spans(), mode="block")
    assert len(out) == len(T) and not any(x in out for x in SECRET)


def test_flatten_accepted_wins_and_no_overlap():
    sp = _spans("suggested")
    sp[1]["status"] = "accepted"  # inner OSOBA accepted, outer sentence only suggested
    flat = flatten(sp)
    assert all(a["end"] <= b["start"] for a, b in zip(flat, flat[1:]))
    assert [s["status"] for s in flat if s["start"] <= sp[1]["start"] < s["end"]] == ["accepted"]


def _docx_text(path):
    return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)


def test_write_docx_final_hides_nested(tmp_path):
    p = tmp_path / "x.docx"
    write_docx(T, _spans(), p, final=True)
    txt = _docx_text(p)
    assert not any(x in txt for x in SECRET)
    assert "██████" in txt and "███████" not in txt  # T27: fixed-length blocks, lengths do not leak


def test_finalize_versions_hide_nested():
    r = finalize(T, _spans("suggested"), accept_all_suggested=True)
    for v in (r["anonymized"], r["to_send"]):
        assert not any(x in v for x in SECRET)
