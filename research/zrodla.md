# Źródła

Data dostępu: 21.11.2026, jeśli nie podano inaczej. Pełne listy z sygnaturami i adresami: `notatki/prawo_szczegoly.md` (sekcja „Źródła”), `notatki/technologia_szczegoly.md`, `notatki/partner_szczegoly.md`.

## Partner i zadanie

| Źródło | Co wzięto |
|---|---|
| `docs/zadanie/UMB_pelna_tresc_zadania.pdf` (UMB, opublikowane 21.11.2026 11:00; OCR w `pelna_tresc_zadania_ocr.txt`) | wymagania 1–12, instrukcja, kryteria 30/20/20/30, test jury, forma zgłoszenia |
| `docs/zadanie/UMB_regulamin_zadania.pdf` | nagroda 15 000 zł, przeniesienie praw, jury, max 3 zespoły w prezentacji |
| Materiały UMB od mentorów (folder „Hacknation 2026 - UMB”; w repo: `data-partner/umb/`) | 10 wniosków i pism BKS, arkusz kalendarium, Zarządzenie 2024, lista danych do anonimizacji |
| https://bip.um.bydgoszcz.pl/artykuly/198/wydzialy, https://bip.um.bydgoszcz.pl/artykuly/1158/biura | 19 wydziałów, 10 biur → `departments.json` |
| https://bip.um.bydgoszcz.pl/artykuly/853/biuro-komunikacji-spolecznej-bks | BKS prowadzi centralną ewidencję wniosków |
| https://bip.um.bydgoszcz.pl/contents/content/7/2 | kanały składania wniosków, odwołanie do SKO |
| https://bip.um.bydgoszcz.pl/artykul/1052/2/udostepnianie-informacji-publicznej | instrukcja UMB (link z materiałów UMB) |
| https://madkom.pl/wp-content/uploads/2024/05/KATALOG_PRODUKTU_SIDAS_CU.pdf | SIDAS to produkt MADKOM |
| https://www.gov.pl/web/cyfryzacja/tysiace-pomyslow-24-godziny-i-jeden-cel--usprawnic-panstwo-w-bydgoszczy-zakonczyl-sie-hacknation-2025 | HackNation 2025: Ścieżki Pamięci 2.0 |
| https://www.bydgoszcz.pl/aktualnosci/tresc/atos-smart-city-2026-eksperci-o-cyfrowej-przys/ | wypowiedź wiceprezydenta o AI w urzędach |

## Prawo

| Źródło | Co wzięto |
|---|---|
| https://api.sejm.gov.pl/eli/acts/DU/2022/902 | UDIP tj., art. 1–21 |
| https://api.sejm.gov.pl/eli/acts/DU/2025/1844 | nowelizacja UDIP od 1.01.2026 (zakres DO WERYFIKACJI) |
| https://api.sejm.gov.pl/eli/acts/DU/2025/1691 | KPA tj., art. 57, 107, 129 |
| https://eli.gov.pl/api/acts/DU/2024/1965/text.html | Wigilia jako dzień wolny (lit. ka) |
| https://api.sejm.gov.pl/eli/acts/DU/2025/296/text.pdf | tekst jednolity ustawy o dniach wolnych |
| https://orzeczenia.nsa.gov.pl (13 sygnatur, lista w `notatki/prawo_szczegoly.md` § 6) | III OSK 754/25 (termin, e-mail), I SAB/Op 11/26 (anonimizacja = decyzja), III OSK 2073/22 (przetworzona), II SAB/Ol 107/23 (przedłużenie) i in. |
| https://api.sejm.gov.pl/eli/acts/DU/2026/1003 | ustawa o systemach AI |
| https://genai.owasp.org/llm-top-10/ | OWASP Top 10 for LLM 2025 |
| https://siecobywatelska.pl/wp-content/uploads/2026/07/Naduzywanie-prawa-do-informacji.pdf | 266 940 wniosków w 2025 r. [~] |

## Technologia

| Źródło | Co wzięto |
|---|---|
| https://ollama.com/SpeakLeash/bielik-11b-v3.1-instruct | tagi Q4_K_M 6,7 GB … Q8_0 12 GB, kontekst 32K |
| https://huggingface.co/speakleash/Bielik-11B-v3.1-Instruct, https://www.gradually.ai/en/ai-models/bielik-11b-v3.1-instruct/ | Apache-2.0, 56 języków |
| https://pasqualepillitteri.it/en/news/32601/bielik-11b-v31-polish-llm-56-languages | data premiery 10.11.2026 [~] |
| https://ollama.com/SpeakLeash/bielik-4.5b-v3.0-instruct | model na laptop, 5,1 GB, 8K |
| https://huggingface.co/CYFRAGOVPL/PLLuM-12B-instruct-2512 | PLLuM 12B Apache-2.0, baza Mistral-Nemo |
| https://raw.githubusercontent.com/explosion/spacy-models/master/meta/pl_core_news_md-3.8.0.json | modele spaCy pl: GPL-3.0 (unikać) |
| https://pypi.org/project/pdfplumber/, /pypdf/, /python-docx/, /openpyxl/, /pypdfium2/, /PyMuPDF/, /docxtpl/ | licencje bibliotek |
| https://huggingface.co/sdadas/mmlw-retrieval-e5-large | embedder PL, Apache-2.0, PIRB 58,30 |
| https://huggingface.co/flowxai/cee-pii | GLiNER PII, Apache-2.0 (wynik PL deklarowany) |
| https://github.com/tesseract-ocr/tessdata_fast | model OCR pol, Apache-2.0 |
