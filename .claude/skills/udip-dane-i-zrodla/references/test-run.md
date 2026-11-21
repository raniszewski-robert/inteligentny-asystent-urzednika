# test-run: udip-dane-i-zrodla

Uruchomione 2026-11-21, Python 3.13.18, w katalogu głównym repozytorium (`bash scripts/smoke.sh` uruchamia skrót tych testów).

```
$ python3 .claude/skills/udip-dane-i-zrodla/scripts/ingest.py --selftest
OK  a_wniosek.docx: 117 znaków, meta={'paragraphs': 2, 'tables': 0, 'quality': 0.81, 'warning': None}
OK  a_odpowiedz.pdf: 138 znaków, meta={'pages': 1, 'ocr': False, 'quality': 0.86, 'warning': None}
OK  b.txt: 53 znaków, meta={'encoding': 'cp1250', 'quality': 0.78, 'warning': None}
Zaimportowano 2 spraw do /tmp/tmpv0at4pw0/arch.jsonl (błędów: 0)
OK  archiwum: 2 sprawy, para wniosek+odpowiedź połączona, data 2026-11-03
OK  skan.pdf przez OCR: 'Odpowiedź: wydatki na oświetlenie w 2025 r. wyniosły 1 234 567 zł.\nWyd'
OK  .doc → czytelny komunikat: Stary format .doc: zapisz jako .docx albo PDF (albo: soffice --headless --convert-to docx).
Wynik: OK
The following objects are still open and will now be closed: [<PdfDocument 0x7f010ee4e5d0 from '/tmp/tmpv0at4pw0/skan.pdf'>, <PdfDocument 0x7f010eece270 from '/tmp/tmpv0at4pw0/a_odpowiedz.pdf'>]
```

Próbki UMB (oryginały poza repozytorium, katalog ~/umb_raw):

```
$ for f in ~/umb_raw/txt/*.json; do python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(f\"{d['file'][:55]:<57} chars={d['chars']:>5} ocr={d.get('ocr')} quality={d['quality']} warning={bool(d['warning'])}\")" "$f"; done
Doprecyzowanie - BKS.IV.1431.509.2026.anonymised.pdf      chars= 2278 ocr=False quality=0.88 warning=False
Kwerenda - BKS.IV.1431.543.2026.anonymised.pdf            chars=  907 ocr=False quality=0.83 warning=False
Odpowiedź - BKS.IV.1431.15.2026.anonymised.pdf            chars= 1409 ocr=False quality=0.85 warning=False
Odpowiedź - BKS.IV.1431.16.2026.anonymised.pdf            chars=  766 ocr=False quality=0.89 warning=False
Odpowiedź - BKS.IV.1431.17.2026.anonymised.pdf            chars= 1294 ocr=False quality=0.81 warning=False
Odpowiedź - BKS.IV.1431.18.2026.anonymised.pdf            chars=  854 ocr=False quality=0.87 warning=False
Odpowiedź - BKS.IV.1431.293.2025.anonymised.pdf           chars= 2857 ocr=False quality=0.79 warning=False
Odpowiedź - BKS.IV.1431.307.2025.anonymised.pdf           chars=  732 ocr=False quality=0.81 warning=False
Odpowiedź - BKS.IV.1431.543.2026.anonymised.pdf           chars= 1712 ocr=False quality=0.86 warning=False
Odpowiedź - BKS.IV.1431.590.2026.anonymised.pdf           chars= 1318 ocr=False quality=0.84 warning=False
Wniosek - BKS.IV.1431.15.2026.docx                        chars=  383 ocr=None quality=0.84 warning=False
Wniosek - BKS.IV.1431.16.2026.pdf                         chars= 1203 ocr=True quality=0.36 warning=True
Wniosek - BKS.IV.1431.17.2026.docx                        chars= 2263 ocr=None quality=0.82 warning=False
Wniosek - BKS.IV.1431.18.2026.docx                        chars= 1381 ocr=None quality=0.9 warning=False
Wniosek - BKS.IV.1431.293.2025.docx                       chars= 1344 ocr=None quality=0.83 warning=False
Wniosek - BKS.IV.1431.307.2025.docx                       chars=  245 ocr=None quality=0.83 warning=False
Wniosek - BKS.IV.1431.509.2026.docx                       chars=  548 ocr=None quality=0.89 warning=False
Wniosek - BKS.IV.1431.543.2026.pdf                        chars= 1679 ocr=True quality=0.83 warning=False
Wniosek - BKS.IV.1431.590.2026.pdf                        chars=  715 ocr=False quality=0.78 warning=False
Wniosek - BKS.IV.1431.599.2026.docx                       chars=  327 ocr=None quality=0.8 warning=False
Zarządzenie Informacja Publiczna 535-2024(1).pdf          chars= 9580 ocr=False quality=0.87 warning=False
```

```
$ python3 .claude/skills/udip-dane-i-zrodla/scripts/ingest.py 'data-partner/umb/probki/Wniosek - BKS.IV.1431.590.2026.pdf' | head -12
WNIOSEK O UDOSTĘPNIENIE INFORMACJI PUBLICZNEJ
Na podstawie art. 2 ust. 1 i art. 10 ust. 1 ustawy z dnia 6 września 2001 r. o dostępie do informacji
publicznej
(Dz. U. z 2016 r. poz. 1764 ze zm.) proszę o udostępnienie informacji dotyczącej Państwa inwestycji
pn. „Budowa kompleksu Astoria ul. Królowej Jadwigi 23 w Bydgoszczy – „Rewitalizacja kompleksu
Astoria na cele sportowo - rekreacyjne wraz z budową 50 -metrowego basenu” w następującym
zakresie:
1. Proszę o informację czy Pan pełnił funkcję Kierownika robót
teletechnicznych/telekomunikacyjnych ze wskazaniem terminu pełnienia funkcji
rozumianego jako okres wpisu do dziennika budowy (w układzie „od dzień/miesiąc/rok do
dzień/miesiąc/rok”).
Budowlanka S.A.
```

```
$ cd data-partner/umb && python3 build_archive.py ~/umb_raw/txt kalendarium_umb.xlsx
BKS.IV.1431.293.2025 2025-06-12 udostepnienie ['WGK', 'SCHRONISKO'] Opieka i odławianie bezdomnych zwierzat.
BKS.IV.1431.307.2025 2025-06-25 udostepnienie ['WE'] Aktualne zestawienie liczby uczniów w szkołach pod
BKS.IV.1431.15.2026 2026-09-12 odeslanie_art_4_ust_3 ['ZEWN-WKZ'] Zapytanie o rzeźbę Ludmiły Stehnovej która została
BKS.IV.1431.16.2026 2026-01-09 brak_danych ['WSO'] Pytanie o liczbę punktów sprzedaży alkoholu powsta
BKS.IV.1431.17.2026 2026-01-14 odeslanie_art_4_ust_3 ['ZDMiKP'] Proszę o udostępnienie informacji publicznej dot.r
BKS.IV.1431.18.2026 2026-01-15 udostepnienie ['WGO'] Liczba mieszkańców wskazanych ulic według opłat za
BKS.IV.1431.509.2026 2026-08-05 doprecyzowanie ['WAB'] Dokumentacja dotycząca basenu Astorii: projekt zag
BKS.IV.1431.543.2026 2026-08-14 udostepnienie+kwerenda ['WGK', 'SCHRONISKO'] Opieka nad bezdomnymi zwierzętami i ich wyłapywani
BKS.IV.1431.590.2026 2026-09-07 udostepnienie ['WIM'] Kompleks Astoria.
BKS.IV.1431.599.2026 2026-09-08 udostepnienie ['WE'] Edytowalne zestawienie liczby uczniów oraz uczniów
```

