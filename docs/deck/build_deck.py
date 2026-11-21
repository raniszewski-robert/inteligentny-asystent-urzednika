"""Builds docs/deck/deck.pptx (T21 final) from docs/deck/outline.md content, docs/screens/ and docs/eval/RESULTS.md.

    python docs/deck/build_deck.py            # then: soffice --headless --convert-to pdf docs/deck/deck.pptx

python-pptx (MIT). Numbers below come from docs/eval/RESULTS.md and scripts/smoke.sh output; update EVAL when T15
gets model columns and rebuild. [[TEAM]] is left for the team to fill in.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
SCREENS = ROOT / "docs" / "screens"
IMG = ROOT / "docs" / "deck" / "img"
OUT = ROOT / "docs" / "deck" / "deck.pptx"

DARK = RGBColor(0x0F, 0x3B, 0x57)      # river blue band (app header, grainwave)
ACCENT = RGBColor(0x0F, 0x3B, 0x57)    # the app's primary button colour
WARM = RGBColor(0xB4, 0x3C, 0x0C)      # key numbers
TEXT = RGBColor(0x1F, 0x24, 0x2B)
MUTED = RGBColor(0x5B, 0x64, 0x70)
TINT = RGBColor(0xEE, 0xF2, 0xF7)      # card background
LINE = RGBColor(0xC9, 0xD1, 0xDB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEAD, BODY = "Lato", "Lato"  # team choice; PDF embeds it, the .pptx needs Lato installed (else PowerPoint substitutes)

# Evaluation (docs/eval/RESULTS.md, docs/eval/bielik.md, 21.11.2026): Reguły vs Bielik 4.5B (Q8_0, offline Ollama).
EVAL = [
    ("Liczba pytań zgodna z ręczną (10 spraw UMB)", 90, 60),
    ("Wydział: top-1 (sprawy UMB)", 67, 56),
    ("Wydział: top-3 (sprawy UMB)", 89, 56),
    ("Fakty we właściwym „Ad” (sprawy UMB)", 100, 83),
    ("Anonimizacja: czułość (recall)", 100, 100),
    ("Anonimizacja: precyzja", 99, 67),
]
BIELIK_BAR = RGBColor(0xD9, 0x8A, 0x00)


def crop(src: str, box: tuple[int, int, int, int], name: str) -> Path:
    IMG.mkdir(parents=True, exist_ok=True)
    out = IMG / name
    Image.open(SCREENS / src).convert("RGB").crop(box).save(out, optimize=True)
    return out


def text(slide, x, y, w, h, runs, size=16, color=TEXT, font=BODY, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None):
    """runs: str or list of paragraphs; a paragraph is str or list of (text, {bold, color, size}) pieces."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        pieces = para if isinstance(para, list) else [(para, {})]
        for t, o in pieces:
            r = p.add_run()
            r.text = t
            r.font.name = o.get("font", font)
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.color.rgb = o.get("color", color)
    return tb


def bullets(slide, x, y, w, h, items, size=15, color=TEXT, gap=8):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        pieces = item if isinstance(item, list) else [(item, {})]
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(Inches(0.22)))
        pPr.set("indent", str(-Inches(0.22)))
        bu = pPr.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar", {"char": "•"})
        pPr.append(bu)
        for t, o in pieces:
            r = p.add_run()
            r.text = t
            r.font.name = BODY
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", False)
            r.font.color.rgb = o.get("color", color)
    return tb


def box(slide, x, y, w, h, fill=TINT, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    return s


def picture(slide, path: Path, x, y, w=None, h=None):
    im = Image.open(path)
    ratio = im.height / im.width
    if w is not None and h is not None:  # fit inside the box
        if w * ratio > h:
            w = h / ratio
        else:
            h = w * ratio
    elif w is not None:
        h = w * ratio
    else:
        w = h / ratio
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    pic.line.color.rgb = LINE
    pic.line.width = Pt(0.75)
    return pic, w, h


def title(slide, t, sub=None):
    text(slide, 0.6, 0.45, 12.1, 0.8, t, size=34, font=HEAD, bold=True, color=TEXT, name="Title")
    if sub:
        text(slide, 0.6, 1.2, 12.1, 0.45, sub, size=16, color=MUTED, name="Subtitle")


def stat(slide, x, y, w, number, label, h=1.25, fill=TINT, num_color=WARM, label_color=TEXT):
    box(slide, x, y, w, h, fill=fill)
    text(slide, x + 0.25, y + 0.12, w - 0.5, 0.6, number, size=34, font=HEAD, bold=True, color=num_color)
    text(slide, x + 0.25, y + 0.72, w - 0.5, h - 0.8, label, size=13, color=label_color)


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


def footer(slide, n):
    text(slide, 12.2, 7.0, 0.6, 0.3, str(n), size=10, color=MUTED, align=PP_ALIGN.RIGHT)


def build() -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    prs.core_properties.title = "Asystent UDIP – Urząd Miasta Bydgoszczy"
    prs.core_properties.subject = "HackNation 2026, Inteligentny asystent urzędnika"

    cal = crop("kalendarz.png", (24, 156, 1342, 900), "kalendarz.png")
    wn = crop("wniosek_nowy_599.png", (47, 206, 1319, 1226), "wniosek_599.png")
    pj = crop("projekt_543.png", (47, 211, 1319, 1136), "projekt_543.png")
    an = crop("anonimizacja_dane_osobowe.png", (47, 156, 1319, 996), "anonimizacja.png")

    # 1. Title
    s = prs.slides.add_slide(blank)
    s.shapes.add_picture(str(ROOT / "docs/deck/img/bg_title.jpg"), 0, 0, prs.slide_width, prs.slide_height)
    text(s, 0.9, 0.9, 11.0, 0.5, "HackNation 2026, wyzwanie „Inteligentny asystent urzędnika”", size=16, color=RGBColor(0xCF, 0xE3, 0xEA))
    text(s, 0.9, 1.45, 11.0, 1.2, "Asystent UDIP", size=60, font=HEAD, bold=True, color=WHITE)
    text(s, 0.9, 2.75, 9.5, 1.0, "Kalendarz wniosków, projekty pism i anonimizacja dla Urzędu Miasta Bydgoszczy",
         size=22, color=RGBColor(0xE6, 0xF0, 0xF4))
    text(s, 0.9, 6.55, 8.0, 0.5, "Zespół: [[TEAM]]", size=16, bold=True, color=RGBColor(0x0D, 0x22, 0x30))
    notes(s, "Asystent UDIP: jedna aplikacja dla Biura Komunikacji Społecznej UMB. Źródło: treść zadania (docs/zadanie/).")

    # 2. Problem
    s = prs.slides.add_slide(blank)
    title(s, "Rejestr w Excelu, pisma składane ręcznie")
    bullets(s, 0.6, 1.6, 7.4, 5.0, [
        "Kalendarium BKS liczy termin formułą =E11+14: termin wypada w sobotę, przy wniosku z 2026 r. wpisano rok 2025, data wpływu bywa późniejsza niż odpowiedź.",
        "Te same pytania wracają co rok: bezdomne zwierzęta (293.2025 i 543.2026), uczniowie i cudzoziemcy w szkołach (307.2025 i 599.2026).",
        "Wydziały odpowiadają częściami; BKS skleja odpowiedź „Ad 1…Ad N” i sam pilnuje 14 dni.",
        "Odpowiedź zawiera dane osób: PESEL, adresy, podpisy. Lista UMB ma 28 kategorii do anonimizacji.",
    ], size=16, gap=12)
    stat(s, 8.6, 1.6, 4.1, "6 miejsc", "z niespójnościami w 10 sprawach arkusza UMB (raport importu)")
    stat(s, 8.6, 3.05, 4.1, "14 dni", "na odpowiedź (art. 13 UDIP), 2 miesiące po przedłużeniu")
    stat(s, 8.6, 4.5, 4.1, "112", "wniosków rocznie na urząd, średnio (Watchdog Polska, 2026; źródło wtórne)")
    notes(s, "Źródła: research/01, data-partner/umb/niespojnosci_arkusza.md, raport importu w aplikacji (6 niespójności).")
    footer(s, 2)

    # 3. Solution: process
    s = prs.slides.add_slide(blank)
    title(s, "Proces z Zarządzenia UMB w jednej aplikacji", "Status sprawy a–e zmienia się na każdym kroku; każde pismo jest projektem, decyzję podejmuje urzędnik")
    steps = [("Wniosek", "PDF, Word, skan (OCR)"), ("Archiwum", "podobne sprawy i wydziały"), ("Kalendarz", "terminy, status a–e"),
             ("Odpowiedzi", "wydziałów do sprawy"), ("Projekt pisma", "„Ad 1…Ad N” w stylu BKS"), ("Anonimizacja", "szary, ramka, czarny"),
             ("Eksport", "DOCX do wysyłki i do archiwum")]
    w, gap, x0, y0 = 1.62, 0.13, 0.6, 2.2
    for i, (h1, h2) in enumerate(steps):
        x = x0 + i * (w + gap)
        box(s, x, y0, w, 1.55, fill=ACCENT if i in (1, 4, 5) else TINT)
        dark = i in (1, 4, 5)
        text(s, x + 0.15, y0 + 0.15, w - 0.3, 0.35, str(i + 1), size=13, bold=True, color=WHITE if dark else MUTED)
        text(s, x + 0.15, y0 + 0.5, w - 0.3, 0.4, h1, size=15, bold=True, color=WHITE if dark else TEXT)
        text(s, x + 0.15, y0 + 0.88, w - 0.3, 0.6, h2, size=12, color=WHITE if dark else MUTED)
    text(s, 0.6, 4.2, 5.9, 0.4, "Zasady", size=20, font=HEAD, bold=True)
    bullets(s, 0.6, 4.75, 5.9, 2.2, ["Aplikacja niczego nie wysyła sama.", "Każdy krok działa bez modelu językowego: reguły, wyszukiwanie BM25, szablony pism BKS.",
                                     "Model językowy tylko proponuje; reguły sprawdzają jego wynik."], size=15)
    text(s, 6.9, 4.2, 5.8, 0.4, "Technologia", size=20, font=HEAD, bold=True)
    bullets(s, 6.9, 4.75, 5.8, 2.2, ["Jeden proces Python: FastAPI, Jinja2, htmx; baza SQLite; przeglądarka w intranecie.",
                                     "Instalacja jednym poleceniem na Windows (setup.ps1, run.ps1) i Linux (run.sh).",
                                     "Wyróżnione kroki (2, 5, 6) zastępują dziś ręczną pracę BKS."], size=15)
    notes(s, "Źródła: research/04 (architektura), uproszczona instrukcja z treści zadania (pkt 9 i 12).")
    footer(s, 3)

    # 4. Calendar
    s = prs.slides.add_slide(blank)
    title(s, "Kalendarz: od najstarszego wniosku, pilne na kolorowo")
    picture(s, cal, 0.6, 1.5, w=7.6)
    bullets(s, 8.6, 1.5, 4.2, 5.5, [
        "Kolory: po terminie, dziś, jutro, do 3 dni roboczych, w terminie, zakończony; liczniki nad tabelą.",
        "Termin ustawowy (art. 13 UDIP, przesunięcie z soboty i święta) i termin bezpieczny: ostatni dzień roboczy przed 14. dniem.",
        "Kolumny arkusza BKS i statusy a–e z historią zmian; eksport CSV i ICS.",
        "Import obecnego arkusza XLSX z raportem niespójności, bez migracji.",
        "18 testów brzegowych terminów (Wigilia, Wielkanoc, Boże Ciało, 2 miesiące od 31.12).",
    ], size=15, gap=10)
    notes(s, "Ekran /kalendarz, dane UMB w trybie demo (daty przesunięte, oznaczone). Źródła: research/05, research/04.")
    footer(s, 4)

    # 5. Request → similar cases, departments
    s = prs.slides.add_slide(blank)
    title(s, "Wniosek z pliku: pytania, podobne sprawy, wydział")
    picture(s, wn, 0.6, 1.5, w=6.5, h=5.5)
    bullets(s, 7.4, 1.5, 5.4, 4.0, [
        "PDF, DOCX, ODT, TXT; skany przez OCR (Tesseract, polski); rękopis dostaje ostrzeżenie „wpisz ręcznie”.",
        "Pytania i flagi: informacja przetworzona, inny tryb niż UDIP, dane osobowe.",
        "Wniosek 599.2026 znajduje sprawę 307.2025 o tym samym temacie (BM25 po archiwum odpowiedzi).",
        "Wydział dla każdego pytania: słowa kluczowe 46 komórek UMB i jednostek oraz wydziały z podobnych spraw. Tu: Wydział Edukacji i Sportu.",
    ], size=15, gap=10)
    stat(s, 7.4, 5.6, 2.55, "5 z 6", "bliźniaczych spraw UMB w top 3", h=1.3)
    stat(s, 10.15, 5.6, 2.65, "8 z 9", "wydziałów UMB w top 3", h=1.3)
    notes(s, "Ekran /wniosek/nowy po wgraniu Wniosek - BKS.IV.1431.599.2026.docx. Źródła: scripts/smoke.sh (Ewaluacja UMB), research/04.")
    footer(s, 5)

    # 6. Draft
    s = prs.slides.add_slide(blank)
    title(s, "Odpowiedzi wydziałów → projekt pisma „Ad 1…Ad 5”")
    picture(s, pj, 0.6, 1.5, w=6.8, h=5.5)
    bullets(s, 7.7, 1.5, 5.1, 5.5, [
        "Sprawa 543.2026: odpowiedzi Schroniska i WGK dają pismo w stylu BKS z liczbami 839 psów, 560 kotów i kwotą 3.143.761,14 zł.",
        "Każda liczba w projekcie musi wystąpić w odpowiedzi wydziału przy tym samym słowie; zmyślona kwota i zamienione psy z kotami są odrzucane.",
        "Raport obok pisma: luki, niepewne przypisania, liczby pominięte. Zdanie przenosi się między „Ad” jednym wyborem.",
        "7 typów pism: 5 odtworzonych z pism BKS, 2 z przepisów i Zarządzenia.",
        [("Uczciwie: ", {"bold": True}), ("odpowiedzi wydziałów w sprawie 543 odtworzyliśmy z pisma BKS, bo UMB nie przekazał plików wydziałów.", {})],
    ], size=15, gap=10)
    notes(s, "Ekran /sprawy/{id}/projekt dla 543.2026. Źródła: acceptance.py test 2 i 2b, udip/data/letter_types.json.")
    footer(s, 6)

    # 7. Anonymization
    s = prs.slides.add_slide(blank)
    title(s, "Anonimizacja: nic nie znika bez decyzji urzędnika")
    picture(s, an, 0.6, 1.5, w=7.0, h=5.5)
    bullets(s, 7.9, 1.5, 4.9, 3.9, [
        "Szary: propozycja. Ramka: do decyzji. Czarny: zaczernione.",
        "Wzorce z sumami kontrolnymi (PESEL, NIP, REGON, IBAN, dowód), imiona z odmianą, kategorie z listy UMB.",
        "Dwie wersje: do wysyłki (z adresatem) i zanonimizowana (archiwum, BIP).",
        "Eksport blokowany, dopóki choć jeden fragment nie ma decyzji; każdy plik sprawdzany na wycieki przed pobraniem.",
        "Funkcjonariusze publiczni do decyzji, nie automatycznie (art. 5 ust. 2 UDIP).",
    ], size=14, gap=8)
    stat(s, 7.9, 5.6, 2.35, "0", "wycieków w DOCX i TXT (testy, plik jury)", h=1.3)
    stat(s, 10.45, 5.6, 2.35, "11", "danych wykrytych w pliku testowym", h=1.3)
    notes(s, "Ekran /anonimizacja z docs/deck/demo_dane_osobowe.docx (syntetyczny). Ostrzeżenie prawne: WSA Opole I SAB/Op 11/26. "
             "Źródła: acceptance.py test 3, tests/e2e/test_jury_path.py, tests/app/test_b2_anonimizacja.py.")
    footer(s, 7)

    # 8. Results
    s = prs.slides.add_slide(blank)
    title(s, "Wyniki na danych UMB: reguły vs Bielik 4.5B (offline)", "Ewaluacja 21.11.2026; skrypt scripts/eval_llm.py, szczegóły w docs/eval/RESULTS.md i docs/eval/bielik.md")
    cd = CategoryChartData()
    cd.categories = [c for c, _, _ in EVAL]
    cd.add_series("Reguły", [r / 100 for _, r, _ in EVAL])
    cd.add_series("Bielik 4.5B (Q8_0, offline)", [b / 100 for _, _, b in EVAL])
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.8), Inches(7.6), Inches(5.0), cd)
    ch = gf.chart
    ch.has_legend = True
    ch.legend.include_in_layout = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.font.size = Pt(12)
    ch.legend.font.name = BODY
    ch.has_title = False
    plot = ch.plots[0]
    plot.gap_width = 70
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = "0%"
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(11)
    dl.font.name = BODY
    dl.font.color.rgb = TEXT
    plot.series[0].format.fill.solid()
    plot.series[0].format.fill.fore_color.rgb = ACCENT
    plot.series[1].format.fill.solid()
    plot.series[1].format.fill.fore_color.rgb = BIELIK_BAR
    ca, va = ch.category_axis, ch.value_axis
    ca.reverse_order = True
    ca.tick_labels.font.size = Pt(12)
    ca.tick_labels.font.name = BODY
    ca.tick_labels.font.color.rgb = TEXT
    ca.format.line.color.rgb = LINE
    va.maximum_scale, va.minimum_scale = 1.0, 0.0
    va.visible = False
    va.has_major_gridlines = False
    stat(s, 8.6, 1.8, 4.1, "11/11", "testów scenariusza jury (acceptance.py) i ścieżka jury end-to-end w aplikacji")
    stat(s, 8.6, 3.25, 4.1, "0", "wycieków i 0 błędnych liczb: reguły i Bielik 4.5B (5/6 Ad n w 543, 100% streszczeń)")
    box(s, 8.6, 4.7, 4.1, 2.1, fill=WHITE, line=LINE)
    text(s, 8.85, 4.85, 3.6, 1.9, [
        [("Bielik 4.5B offline ($0)", {"bold": True})],
        "7,3 tok/s (Ollama, num_ctx=8192); 0 wycieków PII, odporny na prompt injection (kanarek: brak).",
        "Modeli chmurowych świadomie nie używamy: dane wniosków nie opuszczają urzędu.",
    ], size=13)
    notes(s, "Liczby z docs/eval/RESULTS.md (Reguły + Bielik 4.5B Q8_0) i docs/eval/bielik.md. Pytania: 10 spraw UMB; wydział: 9 spraw UMB; anonimizacja: 20 dok. (64 spany) dla Bielika, 40 dok. (144 spany) dla reguł.")
    footer(s, 8)

    # 9. Users and next steps
    s = prs.slides.add_slide(blank)
    title(s, "Dla kogo i jak dalej w Urzędzie Miasta Bydgoszczy")
    cols = [("AIP w BKS", "Rejestr, rozsyłanie pytań, składanie pisma, terminy w jednym miejscu."),
            ("Wydziały merytoryczne", "Jasny zakres pytań, mniej pracy z anonimizacją odpowiedzi."),
            ("Kierownik BKS", "Zaległości i terminy na jednym ekranie, historia statusów.")]
    for i, (h1, b) in enumerate(cols):
        x = 0.6 + i * 4.1
        box(s, x, 1.6, 3.9, 1.9)
        text(s, x + 0.3, 1.8, 3.3, 0.45, h1, size=18, font=HEAD, bold=True)
        text(s, x + 0.3, 2.35, 3.3, 1.1, b, size=15)
    text(s, 0.6, 3.85, 12, 0.4, "Wdrożenie etapami, bez migracji i bez integracji z SIDAS", size=20, font=HEAD, bold=True)
    stages = ["Rejestr i terminy (import arkusza XLSX)", "Archiwum i wyszukiwanie", "Generator pism", "Model lokalny na serwerze Miasta"]
    for i, st in enumerate(stages):
        x = 0.6 + i * 3.1
        circ = box(s, x, 4.55, 0.55, 0.55, fill=ACCENT, shape=MSO_SHAPE.OVAL)
        tf = circ.text_frame
        tf.text = str(i + 1)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        r = tf.paragraphs[0].runs[0]
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(16), True, WHITE, BODY
        text(s, x + 0.7, 4.6, 2.25, 0.9, st, size=15)
    bullets(s, 0.6, 5.75, 12.1, 1.3, [
        "Ten sam proces mają inne JST: zmienia się lista komórek i szablony pism. Dalej: wyszukiwanie hybrydowe (BM25 + embeddingi), zbiór ustaw do cytowania przepisów.",
        "Decyzja o wdrożeniu: Biuro Cyfryzacji i Bezpieczeństwa Informacji z IOD, Wydział Informatyki.",
    ], size=14, gap=6)
    notes(s, "Źródła: research/01 (użytkownicy, decydenci), research/04 (warianty), treść zadania pkt 11 (bez integracji z SIDAS).")
    footer(s, 9)

    # 10. Offline, local model, tools
    s = prs.slides.add_slide(blank)
    s.shapes.add_picture(str(ROOT / "docs/deck/img/bg_end.jpg"), 0, 0, prs.slide_width, prs.slide_height)
    text(s, 0.6, 0.45, 12.1, 0.8, "Offline, model lokalny, narzędzia", size=34, font=HEAD, bold=True, color=WHITE)
    light = RGBColor(0xDB, 0xE4, 0xEE)
    cards = [
        ("Bez internetu i bez dużego modelu: tak", ["Kalendarz, wyszukiwanie, wydziały, pisma i anonimizacja działają na regułach i BM25.",
                                                   "Tylko lokalnie: reguły albo Bielik na komputerze urzędu, bez chmury."]),
        ("Model lokalny w urzędzie", ["Serwer Miasta (GPU 16–24 GB): Bielik-11B-v3.1-Instruct (Apache-2.0) przez Ollama lub vLLM.",
                                      "Zmierzono na laptopie: Bielik-4.5B-v3.0-Instruct Q8_0 (7,3 tok/s, $0, offline; Q4_K_M szybszy)."]),
        ("Narzędzia i licencje", ["Python, FastAPI, Uvicorn, Jinja2, htmx, SQLite, pdfplumber, pypdf, python-docx, openpyxl, Tesseract OCR.",
                                  "Tylko MIT, BSD, Apache: Miasto przejmuje prawa (Regulamin § 4)."]),
    ]
    for i, (h1, items) in enumerate(cards):
        x = 0.6 + i * 4.1
        box(s, x, 1.6, 3.9, 3.6, fill=RGBColor(0x26, 0x38, 0x4C))
        text(s, x + 0.3, 1.8, 3.3, 0.8, h1, size=18, font=HEAD, bold=True, color=WHITE)
        bullets(s, x + 0.3, 2.7, 3.3, 3.2, items, size=14, color=light, gap=10)
    notes(s, "Źródła: research/04 (model lokalny), LICENSES-THIRD-PARTY.md, requirements.txt, docs/eval/bielik.md, README.md.")

    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
