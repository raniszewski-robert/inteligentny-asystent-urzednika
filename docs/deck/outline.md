# Prezentacja: struktura 10 slajdów (szkic T21)

Plik `deck.pptx` powstaje w fazie D2 z tego szkicu (python-pptx). Fakty pochodzą z `research/`, `docs/zadanie/`, `README.md` i z kodu; źródło jest podane przy każdym slajdzie. Znaczniki do uzupełnienia w D2:

- `[[EVAL]]`: liczby z `docs/eval/RESULTS.md` (T15) i `docs/eval/bielik.md` (T16, albo „nie zmierzono”).
- `[[SCREEN:<trasa>]]`: zrzut ekranu tej trasy (CONTRACTS §5) w trybie demo, dane UMB, 1280×720.
- `[[TEAM]]`: imiona i role członków zespołu (uzupełnia zespół).

## Pokrycie wymagań (treść zadania, sekcja 4)

| Wymaganie | Slajd |
|---|---|
| 1. Nazwa projektu i zespół | 1 |
| 2. Problem: przyspieszenie pracy, ochrona danych, dlaczego to ważne | 2 |
| 3. Jak działa: wyszukiwanie archiwum, anonimizacja, kalendarz; technologia | 3, 4, 5, 7 |
| 4. Jak to działa w praktyce: wgranie PDF/Word, przetwarzanie, projekt odpowiedzi | 5, 6 (i film) |
| 5. Dla kogo: urzędnicy JST | 9 |
| 6. Przyszłość w UMB | 9 |
| 7. Narzędzia | 10 |
| 8. Offline, bez dużych modeli, konkretny model lokalny | 10 (i 3) |
| Regulamin § 4 ust. 1: rozwiązania zewnętrzne wskazane w prezentacji | 10 |

Kolejność slajdów 3–8 idzie za kryteriami: związek z wyzwaniem 30%, kompletność prototypu 30%, bezpieczeństwo i anonimizacja 20%, łatwość obsługi 20%.

---

## 1. Asystent UDIP

- Podtytuł: kalendarz wniosków o informację publiczną, projekty pism i anonimizacja dla Urzędu Miasta Bydgoszczy.
- Zespół: `[[TEAM]]`.
- HackNation 2026, wyzwanie „Inteligentny asystent urzędnika”.
- Obraz: `[[SCREEN:/kalendarz]]` w tle, przyciemniony.

Źródło: `docs/zadanie/pelna_tresc_zadania_ocr.txt`.

## 2. Problem: rejestr w Excelu i pisma składane ręcznie

- Kalendarium BKS to arkusz z formułą `=E11+14`: termin wypada w sobotę, jeden termin wpisany z rokiem 2025 przy wniosku z 2026, data wpływu późniejsza niż odpowiedź, przedłużenie wpisane tekstem w kolumnie dat. Import w aplikacji wskazuje 6 takich miejsc w 10 sprawach.
- Te same pytania wracają co rok: bezdomne zwierzęta (293.2025 i 543.2026), uczniowie i cudzoziemcy w szkołach (307.2025 i 599.2026).
- Wydziały odpowiadają częściami, a BKS skleja odpowiedź „Ad 1…Ad N” i sam pilnuje 14 dni.
- Odpowiedź zawiera dane osób: PESEL, adresy, podpisy. Lista UMB ma 28 kategorii do anonimizacji.
- Skala: 266 940 wniosków w 2025 r. w badanych urzędach w Polsce, średnio 112 na urząd (Watchdog Polska, 2026; źródło wtórne).

Obraz: fragment arkusza UMB z zaznaczonymi niespójnościami. Źródła: `research/01`, `data-partner/umb/niespojnosci_arkusza.md`.

## 3. Rozwiązanie: proces z Zarządzenia UMB w jednej aplikacji

- Schemat (7 kroków, jak w treści zadania): wgraj wniosek → podobne sprawy i wydziały → kalendarz → odpowiedzi wydziałów → projekt pisma „Ad 1…Ad N” → anonimizacja szary/czarny → DOCX/TXT do wysyłki i do archiwum.
- Status sprawy a–e zmienia się na każdym kroku: a) brak działań, b) zapytania wysłane do wydziałów, c) kwerenda + liczba dni, d) przygotowana odpowiedź, e) odpowiedź wysłana.
- Aplikacja niczego nie wysyła. Każde pismo jest projektem, decyzję podejmuje urzędnik.
- Technologia: jeden proces Python (FastAPI, Jinja2, htmx), baza SQLite, przeglądarka w intranecie. Wszystko działa bez modelu językowego: reguły, wyszukiwanie BM25, szablony pism BKS. Model językowy tylko redaguje akapity i podpowiada, nigdy nie jest jedyną drogą.

Obraz: schemat procesu z rolami (AIP w BKS, wydziały). Źródła: `research/04` (architektura), `docs/zadanie/` (uproszczona instrukcja, pkt 9 i 12).

## 4. Kalendarz wniosków

- 10 spraw z arkusza UMB, od najstarszej do najnowszej; filtr roku.
- Kolory pilności: po terminie, termin dziś, termin jutro (następny dzień roboczy), do 3 dni roboczych, w terminie, zakończony. Liczniki „po terminie / dziś / jutro” nad tabelą.
- Dwie daty: termin ustawowy (art. 13 UDIP, przesunięcie z soboty i święta według art. 57 § 4 KPA) i termin bezpieczny (ostatni dzień roboczy przed 14. dniem), bo sądy nie przesądziły stosowania KPA do UDIP. Kalendarz zna Wigilię jako dzień wolny od 2025 r.
- Kolumny arkusza BKS: lp., nr wniosku, data wpływu, skrócony opis, inicjały, status, kwerenda, termin, data odpowiedzi.
- Import obecnego arkusza XLSX z raportem niespójności; tryb demo przesuwa daty na dziś i jest oznaczony.
- Testy terminów: 18 przypadków brzegowych (Wigilia, Wielkanoc, Boże Ciało, 2 miesiące od 31.12).

Obraz: `[[SCREEN:/kalendarz]]`. Źródła: `research/05` (reguły terminów), `research/04` (testy).

## 5. Jak to działa (1/2): wniosek z pliku, podobne sprawy, wydziały

- Urzędnik wgrywa PDF, Word (DOCX, ODT) albo TXT. Skany czyta OCR (Tesseract, język polski); rękopis dostaje ostrzeżenie „wpisz ręcznie” (wniosek 16.2026).
- Narzędzie wyciąga pytania i flagi (np. informacja przetworzona, inny tryb niż UDIP).
- Podobne sprawy: wyszukiwanie BM25 po archiwum odpowiedzi. Wniosek 599.2026 (uczniowie i cudzoziemcy) znajduje sprawę 307.2025 o tym samym temacie; sprawa starsza niż rok jest tak oznaczona.
- Wydziały: słowa kluczowe 46 komórek (19 wydziałów, 10 biur UMB, 17 jednostek miejskich z BIP) i wydziały z podobnych spraw dają propozycję dla każdego pytania. Dla 599.2026: Wydział Edukacji i Sportu.
- Baza wiedzy rośnie z pracą: wysłane pisma, importowany katalog spraw oraz ustawy i zarządzenia od razu trafiają do wyszukiwania.

Obraz: `[[SCREEN:/wniosek/nowy]]` (wynik analizy 599.2026), mały `[[SCREEN:/archiwum]]`. Źródła: `research/04`, `tests/fixtures/analysis_599.json`, `.claude/skills/udip-archiwum-i-wydzialy/data/departments.json`.

## 6. Jak to działa (2/2): odpowiedzi wydziałów → projekt pisma

- Urzędnik wgrywa odpowiedzi wydziałów w sprawie; narzędzie rozpoznaje wydział i przypisuje zdania do pytań.
- Sprawa 543.2026 (bezdomne zwierzęta): odpowiedzi Schroniska i WGK dają pismo „Ad 1…Ad 5” w stylu BKS, z liczbami 839 psów, 560 kotów i kwotą 3.143.761,14 zł z odpowiedzi wydziałów.
- 7 typów pism: 5 odtworzonych z pism BKS (udostępnienie, odesłanie art. 4 ust. 3, brak danych, przedłużenie, doprecyzowanie), 2 z przepisów i Zarządzenia (odesłanie do BIP, informacja przetworzona).
- Kontrola halucynacji: każda liczba w projekcie musi wystąpić w odpowiedzi wydziału przy tym samym słowie. Zmyślona kwota i zamienione psy z kotami są odrzucane.
- Raport obok pisma: luki, niepewne przypisania, liczby pominięte. Urzędnik przenosi zdanie między „Ad” i zapisuje nową wersję.
- Uczciwie: odpowiedzi wydziałów w sprawie 543 odtworzyliśmy z pisma BKS, bo UMB nie przekazał plików wydziałów.

Obraz: `[[SCREEN:/sprawy/{id}/projekt]]` dla 543.2026 (pismo i raport obok siebie). Źródła: `research/07` (definicja done), `.claude/skills/udip-projekty-odpowiedzi/data/letter_types.json`, `udip-ewaluacja/scripts/acceptance.py` (test 2b).

## 7. Anonimizacja i bezpieczeństwo

- Szary = propozycja, ramka = do decyzji urzędnika, czarny = zaakceptowane. Nic nie znika bez kliknięcia.
- Wykrywanie: wzorce z sumami kontrolnymi (PESEL, NIP, REGON, IBAN, dowód osobisty), słownik imion z odmianą, kategorie z listy UMB (adres, data i miejsce urodzenia, podpis, telefon, e-mail).
- Eksport w dwóch wersjach: do wysyłki (z adresatem) i zanonimizowana (archiwum, BIP).
- Ostrzeżenie prawne: zaczernienie danych osób trzecich w udostępnianej informacji to częściowa odmowa i wymaga decyzji (WSA w Opolu, I SAB/Op 11/26). Funkcjonariusze publiczni (np. Prezydent) nie są anonimizowani automatycznie (art. 5 ust. 2 UDIP).
- Model językowy może dodać propozycję, ale zawsze jako „do decyzji”.
- Wynik: `[[EVAL]]` (precyzja, czułość, wycieki). Dziś: 0 wycieków na 144 spanach w 40 dokumentach syntetycznych; plik testowy jury z PESEL, dowodem, rachunkiem, adresem i datą urodzenia: 0 wycieków po akceptacji.

Obraz: `[[SCREEN:/anonimizacja]]` przed i po akceptacji. Źródła: `research/05` (czerwone linie), `udip-ewaluacja` (evaluate.py, acceptance.py test 3).

## 8. Wyniki na danych UMB

- Tabela `[[EVAL]]` z T15: reguły, Claude Sonnet, Claude Haiku, Bielik (albo „nie zmierzono”): pytania z wniosku, wydział top-1/top-3, przypisanie do „Ad”, liczby zmyślone/zamienione/pominięte, anonimizacja P/R/wycieki, czas i koszt na wniosek.
- Wykres `[[EVAL]]` (jeden, z `docs/eval/`).
- Liczby z 21.11, które już mamy (reguły, bez modelu): bliźniacza sprawa w top 3 w 5 z 6 przypadków UMB; wydział UMB top-1 6/9, top-3 8/9; scenariusz jury (`acceptance.py`) 11/11.
- Skala: 5000 spraw w archiwum, indeks 0,37 s, zapytanie 10 ms na CPU; trafność spada do hit@5 0,75, dlatego docelowo wyszukiwanie hybrydowe (slajd 9).

Źródła: `research/04` (tabela pomiarów), `docs/eval/RESULTS.md` (D2).

## 9. Dla kogo i jak dalej w Urzędzie Miasta Bydgoszczy

- Użytkownicy: AIP w Biurze Komunikacji Społecznej (rejestr, rozsyłanie, składanie pisma, terminy); wydziały merytoryczne (jasny zakres pytań, mniej pracy z anonimizacją); kierownik BKS (zaległości na jednym ekranie). Ten sam proces mają inne JST: zmienia się lista komórek i szablony pism.
- Wdrożenie bez migracji: import obecnego arkusza XLSX, bez integracji z SIDAS (pkt 11 zadania), jeden proces Python na serwerze w intranecie, instalacja jednym poleceniem.
- Etapy: rejestr i terminy → archiwum i wyszukiwanie → generator pism → model lokalny.
- Dalszy rozwój: wyszukiwanie hybrydowe (BM25 + embeddingi mmlw, Apache-2.0) dla tysięcy spraw; zbiór ustaw i zarządzeń do cytowania przepisów; dostrajanie modelu na pismach BKS jako osobny etap.
- Decyzja o wdrożeniu: Biuro Cyfryzacji i Bezpieczeństwa Informacji z IOD, Wydział Informatyki.

Źródła: `research/01` (użytkownicy, decydenci), `research/04` (alternatywy C), `.claude/skills/udip-demo-i-pitch/SKILL.md` (argumenty o wdrożeniu).

## 10. Offline, model lokalny, narzędzia

- Bez internetu i bez dużego modelu: tak. Kalendarz, wyszukiwanie, wydziały, pisma i anonimizacja działają na regułach i BM25. W filmie pokazujemy pracę po wyłączeniu Wi-Fi.
- Model lokalny w urzędzie: **Bielik-11B-v3.1-Instruct** (Apache-2.0, kontekst 32K) przez Ollama albo vLLM na serwerze z GPU 16–24 GB. Laptop bez GPU: Bielik-4.5B-v3.0-Instruct (Q8_0, 5,1 GB). Zapas: PLLuM-12B-instruct-2512 (Apache-2.0). Pomiar Bielika: `[[EVAL]]` albo „nie zmierzono”.
- Podczas hackathonu model zewnętrzny (Claude) działał tylko na danych testowych, zgodnie z pkt 1 zadania; adres modelu zmienia się jednym ustawieniem (`LLM_BASE_URL`).
- Narzędzia i licencje: Python 3.11+, FastAPI (MIT), Uvicorn (BSD), Jinja2 (BSD), htmx (0BSD), SQLite, pdfplumber (MIT), pypdf (BSD), pypdfium2 (Apache-2.0/BSD), python-docx (MIT), openpyxl (MIT), Tesseract OCR (Apache-2.0); opcjonalnie Ollama i Bielik. Tylko licencje MIT, BSD, Apache, bo Miasto przejmuje prawa (Regulamin § 4); bez PyMuPDF (AGPL), docxtpl (LGPL), modeli spaCy pl (GPL).

Źródła: `research/04` (model lokalny), `LICENSES-THIRD-PARTY.md`, `requirements.txt`, `README.md`.
