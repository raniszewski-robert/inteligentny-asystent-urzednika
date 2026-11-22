"""Reading Word and PDF files: document order, merged cells, headers/footers, text boxes, mixed scanned PDFs."""
from __future__ import annotations

from pathlib import Path

import docx
import pytest
from docx.oxml import parse_xml
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from udip import ingest
from udip.ingest import IngestError, read_any

REPO = Path(__file__).resolve().parents[2]
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
V = 'xmlns:v="urn:schemas-microsoft-com:vml"'
MC = 'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'


def _font() -> Path:
    for p in sorted((REPO / "app" / "static" / "fonts").glob("*.ttf")) + [Path("/usr/share/fonts/truetype/lato/Lato-Regular.ttf"),
                                                                          Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                                                                          Path("C:/Windows/Fonts/arial.ttf")]:
        if p.is_file():
            return p
    pytest.skip("brak fontu TTF z polskimi znakami")


@pytest.fixture
def letter(tmp_path: Path) -> Path:
    d = docx.Document()
    d.sections[0].header.paragraphs[0].text = "Stowarzyszenie Przykładowe, ul. Długa 5, 85-001 Bydgoszcz"
    d.sections[0].footer.paragraphs[0].text = "Kontakt: jan.kowalski@example.com, tel. 600 100 200"
    d.add_paragraph("Wnoszę o udostępnienie informacji:")
    t = d.add_table(rows=4, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "1.", "Ile wyniosły wydatki na oświetlenie w 2025 r.?"
    t.cell(1, 0).text, t.cell(1, 1).text = "2.", "Kto był wykonawcą?"
    t.cell(2, 0).merge(t.cell(2, 1)).text = "Odpowiedź proszę przesłać e-mailem."
    t.cell(3, 0).merge(t.cell(3, 0))  # zwykła komórka
    t.cell(3, 1).text = "Uwagi końcowe"
    box = d.add_paragraph("Akapit z ramką.")
    box._p.append(parse_xml(f'<w:r {W} {V}><w:pict><v:shape><v:textbox><w:txbxContent>'
                            f'<w:p><w:r><w:t>Tekst w ramce: PESEL 44051401359</w:t></w:r></w:p>'
                            f'</w:txbxContent></v:textbox></v:shape></w:pict></w:r>'))
    alt = d.add_paragraph()
    alt._p.append(parse_xml(f'<w:r {W} {MC}><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><w:txbxContent>'
                            f'<w:p><w:r><w:t>Ramka nowego typu</w:t></w:r></w:p></w:txbxContent></w:drawing></mc:Choice>'
                            f'<mc:Fallback><w:pict><w:txbxContent><w:p><w:r><w:t>Ramka nowego typu</w:t></w:r></w:p>'
                            f'</w:txbxContent></w:pict></mc:Fallback></mc:AlternateContent></w:r>'))
    sdt = parse_xml(f'<w:sdt {W}><w:sdtContent><w:p><w:r><w:t>Pole formularza: Bydgoszcz</w:t></w:r></w:p></w:sdtContent></w:sdt>')
    d.element.body.insert(len(d.element.body) - 1, sdt)
    d.add_paragraph("Z poważaniem, Jan Kowalski")
    p = tmp_path / "wniosek.docx"
    d.save(p)
    return p


def test_docx_keeps_document_order_and_merged_cells_once(letter: Path):
    text = read_any(letter)["text"]
    order = ["Wnoszę o udostępnienie", "1. Ile wyniosły", "2. Kto był", "Odpowiedź proszę", "Uwagi końcowe",
             "Akapit z ramką", "Z poważaniem"]
    pos = [text.index(s) for s in order]
    assert pos == sorted(pos), text
    assert text.count("Odpowiedź proszę przesłać e-mailem.") == 1


def test_docx_reads_header_footer_text_boxes_and_form_fields(letter: Path):
    text = read_any(letter)["text"]
    assert text.startswith("Stowarzyszenie Przykładowe, ul. Długa 5")
    assert text.rstrip().endswith("tel. 600 100 200")
    assert "Tekst w ramce: PESEL 44051401359" in text
    assert text.count("Ramka nowego typu") == 1  # mc:Fallback nie dubluje treści
    assert "Pole formularza: Bydgoszcz" in text


def test_docx_vertical_merge_is_read_once(tmp_path: Path):
    d = docx.Document()
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).merge(t.cell(1, 0)).text = "Wydział Edukacji"
    t.cell(0, 1).text, t.cell(1, 1).text = "pytanie 1", "pytanie 2"
    p = tmp_path / "v.docx"
    d.save(p)
    assert read_any(p)["text"].count("Wydział Edukacji") == 1


def test_docx_header_data_reaches_anonymization(letter: Path):
    from udip.anonymize import detect
    found = " ".join(s.text for s in detect(read_any(letter)["text"]))
    assert "jan.kowalski@example.com" in found and "44051401359" in found


def test_broken_docx_gives_clear_error(tmp_path: Path):
    p = tmp_path / "zly.docx"
    p.write_bytes(b"to nie jest plik Word")
    with pytest.raises(IngestError, match="Nie da się otworzyć DOCX"):
        read_any(p)


def _mixed_pdf(tmp_path: Path, scanned_only: bool = False) -> Path:
    font = _font()
    pdfmetrics.registerFont(TTFont("TestFont", str(font)))
    img = Image.new("RGB", (1240, 1754), "white")
    dr = ImageDraw.Draw(img)
    f = ImageFont.truetype(str(font), 40)
    for i, line in enumerate(["2. Proszę o wykaz umów zawartych w 2025 r.", "3. Proszę o kopię protokołu odbioru."]):
        dr.text((120, 200 + i * 80), line, fill="black", font=f)
    png = tmp_path / "skan.png"
    img.save(png)
    p = tmp_path / "mieszany.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    if not scanned_only:
        c.setFont("TestFont", 12)
        for i, line in enumerate(["WNIOSEK O UDOSTĘPNIENIE INFORMACJI PUBLICZNEJ",
                                  "1. Proszę o informację o wydatkach na drogi w 2025 r."]):
            c.drawString(72, 780 - i * 20, line)
        c.showPage()
    c.drawImage(str(png), 0, 0, *A4)
    c.showPage()
    c.save()
    return p


def test_mixed_pdf_without_ocr_keeps_text_pages_and_names_the_scanned_one(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(ingest, "ocr_unavailable", lambda lang="pol": "Tesseract nie jest zainstalowany.")
    d = read_any(_mixed_pdf(tmp_path))
    assert "1. Proszę o informację o wydatkach" in d["text"]
    assert d["unread_pages"] == [2]
    assert "Strona 2 to skan" in d["warning"] and "Tesseract nie jest zainstalowany" in d["warning"]


def test_mixed_pdf_ocrs_only_the_scanned_page(tmp_path: Path, monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "ocr_unavailable", lambda lang="pol": None)
    monkeypatch.setattr(ingest, "ocr_pages", lambda path, pages, lang="pol": calls.append(pages) or {i: "2. Wykaz umów z OCR." for i in pages})
    d = read_any(_mixed_pdf(tmp_path))
    assert calls == [[1]]
    assert d["ocr"] is True and d["ocr_pages"] == [2] and d["warning"] is None
    assert d["text"].index("1. Proszę o informację") < d["text"].index("2. Wykaz umów z OCR.")


def test_fully_scanned_pdf_without_ocr_is_an_error(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(ingest, "ocr_unavailable", lambda lang="pol": "Tesseract nie jest zainstalowany.")
    with pytest.raises(IngestError, match="skan"):
        read_any(_mixed_pdf(tmp_path, scanned_only=True))


@pytest.mark.skipif(ingest.ocr_unavailable() is not None, reason="Tesseract z językiem pol niedostępny")
def test_mixed_pdf_real_ocr(tmp_path: Path):
    d = read_any(_mixed_pdf(tmp_path))
    assert d["ocr_pages"] == [2]
    assert "protokołu odbioru" in d["text"] and "wydatkach na drogi" in d["text"]


def test_tesseract_cmd_from_env_is_used(tmp_path: Path, monkeypatch):
    exe = tmp_path / "tesseract.exe"
    exe.write_text("")
    monkeypatch.setenv("TESSERACT_CMD", str(exe))
    assert ingest._tesseract() == str(exe)
