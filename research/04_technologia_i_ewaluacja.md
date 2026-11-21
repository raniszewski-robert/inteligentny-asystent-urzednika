# 04. Technologia i ewaluacja: architektura pod 22 h, model lokalny, pomiar

Stan: 21.11.2026. Licencje i wersje: `notatki/technologia_szczegoly.md` (PyPI/HF, dostęp 21.11.2026).

## Architektura MVP (rekomendowana)

```
przeglądarka (urzędnik BKS)
   │  HTTP (localhost / intranet)
   ▼
aplikacja webowa (FastAPI albo Flask + HTML; jeden proces Python)
   ├─ ingest.py ........ PDF/DOCX/ODT/TXT → tekst, OCR Tesseract pol, ocena jakości (rękopis → „wpisz ręcznie”)
   ├─ analyze.py ....... pytania z wniosku, tryb (UDIP/petycja/ooś…), flagi (przetworzona, BIP, dane osobowe)
   ├─ search.py ........ BM25 po archiwum (bez zależności) → podobne sprawy z ostatniego roku
   ├─ route (analyze) .. słowa kluczowe 29 komórek UMB i 17 jednostek + głosy podobnych spraw → ścieżka per pytanie
   ├─ draft.py ......... pismo BKS z odpowiedzi wydziałów (szablony UMB; opcjonalnie LLM lokalny)
   ├─ anonymize.py ..... wzorce z sumami kontrolnymi + imiona + lista UMB → szary/czarny
   └─ register.py ...... kalendarz: terminy art. 13 UDIP + art. 57 KPA, statusy a–e, HTML/CSV/ICS
   ▼
pliki / SQLite (rejestr, archiwum JSONL)        [opcjonalnie] Ollama: Bielik (API zgodne z OpenAI)
```

Zasada: **wszystko działa bez modelu językowego** (reguły, BM25, szablony). LLM jest wzmacniaczem redakcji akapitów i nigdy nie jest jedyną drogą. Dzięki temu demo nie zależy od Wi-Fi ani GPU, a odpowiedź na pytanie jury „czy działa bez internetu” brzmi: tak, łącznie z modelem, jeśli jest lokalny.

Zależności rdzenia: Python 3.11+, `pdfplumber` (MIT), `pypdf` (BSD-3), `python-docx` (MIT), `pypdfium2` (Apache-2.0/BSD-3), `openpyxl` (MIT), Tesseract + `pol` (Apache-2.0). Bez PyMuPDF (AGPL), docxtpl (LGPL), modeli spaCy pl (GPL-3.0) [✔ `notatki/technologia_szczegoly.md` § 4–5].

## Alternatywy

| Wariant | Co zmienia | Koszt / opóźnienie | Kiedy |
|---|---|---|---|
| A. Reguły + BM25 + szablony (rdzeń) | — | 0 zł; < 0,5 s na sprawę (test akceptacyjny 0,4 s na 13 dokumentów); BM25 na 5000 sprawach: indeks 0,37 s, zapytanie 10 ms [✔ pomiar 21.11] | zawsze, plan bazowy |
| B. A + lokalny LLM do redakcji akapitów | `draft.py --mode llm`, `LLM_BASE_URL` | 0 zł; czas zależny od sprzętu, CPU: kilka tok/s [?] – zmierzyć | gdy laptop ma ≥16 GB RAM i model pobrany przed demo |
| C. A + embeddingi (hybryda z BM25) | `sdadas/mmlw-retrieval-e5-base/large` (Apache-2.0) przez sentence-transformers | +1–2 GB, sekundy na indeksowanie setek spraw [?] | gdy archiwum UMB > kilkuset spraw albo synonimy psują BM25 |
| D. A + NER dla imion/adresów | GLiNER `flowxai/cee-pii` (Apache-2.0; deklarowane F1 0,94 dla PL [?]) | +1,2 GB, CPU | gdy słownik imion nie wystarcza (nazwiska bez imion) |

## Model lokalny: co wskazać w prezentacji

| Środowisko | Model | Licencja | Uruchomienie | Pewność |
|---|---|---|---|---|
| Serwer UMB z GPU 16–24 GB | **Bielik-11B-v3.1-Instruct** (premiera 10.11.2026 [~], 32K kontekstu) | Apache-2.0 | `ollama pull SpeakLeash/bielik-11b-v3.1-instruct:Q5_K_M` (7,9 GB) albo vLLM ≥ 0.24 | [✔] Ollama/HF, [~] data premiery |
| Zapas (sprawdzony dłużej) | Bielik-11B-v3.0-Instruct albo PLLuM-12B-instruct-2512 (Apache-2.0, baza Mistral-Nemo) | Apache-2.0 | GGUF / vLLM | [✔] |
| Laptop demo bez GPU | Bielik-4.5B-v3.0-Instruct Q8_0 (5,1 GB, kontekst 8K) | Apache-2.0 | `ollama pull SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0` | [✔] |
| Unikać | PLLuM-*-nc (tylko badania), Llama-PLLuM (licencja Llama), PLLuM-4B (baza Gemma: warunki Gemma ≠ Apache) | — | — | [✔] |

„Uczenie się na wgrywanych danych” (treść pkt 1) realizujemy dziś przez **archiwum**: wysłane pisma i importowany katalog dokumentów (`ingest.py --archive`) od razu zasilają wyszukiwanie podobnych spraw i trasowanie do wydziałów. Ustawy i zarządzenia: do zrobienia w sobotę jako osobny zbiór w tym samym BM25 (wyszukiwanie przepisu do cytatu); szablony pism są stałe (`letter_types.json`) i nie uczą się same. Dostrajanie modelu (LoRA) to etap wdrożenia, nie 22 h [?].

## Ryzyka techniczne i zamienniki

| Ryzyko | Objaw | Zamiennik |
|---|---|---|
| Rękopis / słaby skan | OCR zwraca śmieci (16.2026: jakość 0,36) | Ostrzeżenie + ręczne wpisanie; docelowo model obrazowy lokalny |
| PDF z rozstrzelonymi literami | „Komunik acji” (pypdf) | pdfplumber `x_tolerance=1.5` (wdrożone) |
| LLM wymyśla liczby | liczba w akapicie spoza odpowiedzi wydziału | `check_numbers` odrzuca wynik → szablon (test: halucynacja 999 999 zł odrzucona) |
| LLM niedostępny | timeout/Connection refused | automatyczny powrót do szablonu (test) |
| Prompt injection we wniosku | „zignoruj instrukcje…” | treść w znacznikach, schemat JSON, brak narzędzi, kontrola liczb, akceptacja człowieka |
| Archiwum UMB ma 10 spraw | słabe podobieństwa | archiwum syntetyczne jako uzupełnienie, wyraźnie oznaczone |

## Jak mierzymy jakość

| Moduł | Metryka | Dane | Wynik 21.11.2026 | Skrypt |
|---|---|---|---|---|
| Podobne sprawy | „bliźniak” w top 3 (ten sam temat w innym wniosku) | 10 spraw UMB, leave-one-out | **5/6** (pudło: 509↔590 to w rzeczywistości różne tematy: Astrum vs Astoria) | `evaluate_partner.py` |
| Wydział | prawdziwy wydział UMB w top 1 / top 3 | 9 spraw UMB z wydziałem | **6/9 / 8/9** | `evaluate_partner.py` |
| Podobne sprawy | hit@5 / MRR (ostatni rok) | 16 wniosków syntetycznych; 5000 spraw (skala) | 0,88 / 0,76; przy 5000 sprawach 0,75 / 0,70 | `evaluate.py` |
| Wydział | top-1 / top-3 per pytanie | 20 pytań syntetycznych | 0,90 / 1,00; zbiór odłożony (seed 7) 0,75 / 1,00 – strojone na seedzie 2026 | `evaluate.py` |
| Anonimizacja | P / R / F1 spanów, wycieki | 40 dok., 144 spany syntetyczne | 0,99 / 1,00 / 0,99; 0 wycieków (zbiór odłożony seed 7: to samo) | `evaluate.py` |
| Scenariusz jury | 6 kroków z sekcji 6 treści + kontrola halucynacji liczb | dane UMB, pełne archiwum, okno 365 dni | **11/11** | `acceptance.py` |
| Terminy | przypadki brzegowe (Wigilia, Wielkanoc, Boże Ciało, 2 miesiące od 31.12) | 18 przypadków | 18/18 | `deadlines.py --selftest` |

„Wystarczająco dobre do demo”: `acceptance.py` na zielono, zero wycieków, kalendarz z czterema kolorami, projekt pisma 543.2026 zgodny z faktami pisma BKS. Jury nie zapowiada metryki liczbowej; ocenia „czy odnajduje podobne sprawy”, „czy poprawnie układa pismo”, „czy skutecznie ukrywa”. Liczby powyżej są argumentem w pitchu, nie wymogiem.
