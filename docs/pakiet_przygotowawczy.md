# Pakiet przygotowawczy (stan 21.11.2026, 14:30, przed budową aplikacji)

Archiwalny README z początku hackathonu: karta zadania, decyzje, ograniczenia znane przed budową UI. Aktualny opis: [README](../README.md).


Stan: 21.11.2026, 14:30 (po przeglądzie krytycznym), po publikacji pełnej treści i otrzymaniu materiałów UMB. Oznaczenia: [✔] źródło pierwotne, [~] wtórne, [?] hipoteza. Smoke test: `bash scripts/smoke.sh` (wszystko zielone 21.11).

## Karta zadania

| Pole | Treść |
|---|---|
| Partner i nagroda | Urząd Miasta Bydgoszczy (BKS i Biuro Rady Miasta); 15 000 zł brutto, jedna nagroda; zwycięzca przenosi prawa autorskie na Miasto [✔ `docs/zadanie/`] |
| Najbardziej prawdopodobny akcent | Pełna treść znana: jury wgra PDF/Word, sprawdzi podobne sprawy, projekt pisma z odpowiedzi wydziału, anonimizację i kalendarz 10 wniosków; najważniejszy jest kalendarz i składanie pisma w stylu BKS (`research/06`, wariant A+B, 65% [?]) |
| Rekomendowana koncepcja | Jedna aplikacja offline przeprowadzająca AIP przez proces z Zarządzenia UMB: wgraj → podobne sprawy i wydziały → kalendarz → odpowiedzi wydziałów → pismo „Ad 1…Ad N” z szarą anonimizacją → akceptacja → DOCX do wysyłki i do archiwum; LLM (Bielik lokalnie) tylko opcjonalnie |
| Dane | **Mamy:** 10 prawdziwych spraw UMB (wnioski, pisma BKS, arkusz kalendarium, Zarządzenie 2024, lista danych do anonimizacji), 29 komórek UMB (19 wydziałów, 10 biur) i 17 jednostek miejskich z BIP, dane syntetyczne ze złotymi etykietami. **Brak:** plików odpowiedzi wydziałów (odtworzyliśmy jeden przypadek), statystyki UMB, zgody na publikację próbek |
| Pomiar liczbowy przez jury | **Nie** w treści (jury testuje ręcznie 6 kroków). Mamy własne liczby: na UMB bliźniak w top 3 5/6, wydział top-1 6/9, top-3 8/9; anonimizacja 0 wycieków na danych syntetycznych |
| Kompetencje | Python (backend gotowy, spinamy API); frontend (3 ekrany: Kalendarz, Sprawa, Anonimizacja); ktoś czytający UDIP/KPA przy pytaniach jury; ML niepotrzebne |
| Wykonalność w 22 h | **5**: wszystkie klocki działają i mają testy (`acceptance.py` 11/11 na prawdziwej ścieżce: pełne archiwum, okno 365 dni); zostaje UI i spięcie |
| Siła demo | **4**: na ich danych (ich arkusz z 6 błędami, ich sprawa 543), szary → czarny, wyłączenie Wi-Fi; mniej „efektu AI” niż czat |
| Dopasowanie do Partnera | **5**: odtwarza ich proces z Zarządzenia, ich formuły pism, ich znak BKS.IV.1431, import ich Excela |
| Ryzyko prawne i etyczne | **2**: dane osobowe obywateli; mitygacja: offline, nic nie wysyła, anonimizacja wg listy UMB z akceptacją, ostrzeżenie o decyzji przy zaczernieniu (`research/05`) |
| Sygnały „nie bierzemy” | Już po wyborze: treść pasuje do pakietu. Zmiana akcentu, gdy mentor chce czatu AI zamiast procesu (wariant D) albo integracji z SIDAS |
| Największa niepewność | Czy jury nagrodzi solidny proces offline, czy „efekt AI”; odpowiedź: pokazać lokalny Bielik z kontrolą halucynacji jako dodatek (`research/06`, kontrargument) |

## TL;DR

Rdzeń jest gotowy w `.claude/skills/udip-*`: terminy (art. 13 UDIP + art. 57 KPA, Wigilia, termin bezpieczny), kalendarz z importem Excela UMB, archiwum BM25 i podpowiedź wydziału, generator 7 typów pism (5 odtworzonych z próbek BKS, 2 z przepisów i Zarządzenia), anonimizacja wg listy UMB, ewaluacja i test scenariusza jury. W sobotę budujemy **UI i API** (`research/07`), LLM tylko jeśli zostanie czas.

## Pierwsza godzina (13:30–14:30)

1. `bash scripts/smoke.sh` na laptopie demo; `apt install tesseract-ocr tesseract-ocr-pol`, `pip install -r requirements.txt` (licencje: `LICENSES-THIRD-PARTY.md`).
2. Mentorzy UMB: 7 pytań z `research/03` (publikacja próbek, art. 57 KPA, decyzja przy anonimizacji, lista funkcjonariuszy).
3. Decyzja frameworku (FastAPI + HTML) i podział ról B/F wg `research/07`.
4. 19:30 kontrola HackTribe (`hn-zgloszenie`); 20:00 zamknięcie wyboru.

## 5 decyzji dla zespołu

1. Akcent: proces A+B+C, LLM jako dodatek. **Rekomendacja: tak.**
2. Przechowywanie: pliki JSON czy SQLite. **SQLite** (jeden plik, łatwe wdrożenie).
3. Termin w UI: pokazujemy dwie daty (ustawowa, bezpieczna)? **Tak**, kolor wg ustawowej, plan wg bezpiecznej.
4. Archiwum w demo: UMB (10) + syntetyczne (90), wyraźnie oddzielone? **Tak.**
5. LLM w demo: Bielik-4.5B lokalnie czy wcale. **Tylko jeśli** do 04:00 działa na laptopie demo, a 5 akapitów mieści się w `LLM_TIMEOUT` (domyślnie 60 s; Bielik-4.5B na CPU: szybkość niezmierzona).

## Checklista (sobota)

- [ ] Python 3.11+, Tesseract z `pol`, paczki jak wyżej (licencje: MIT/BSD/Apache).
- [ ] (opcja) `ollama pull SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0` przez normalną sieć przed nocą (5,1 GB).
- [ ] Zgoda mentora na `data-partner/` w publicznym repozytorium zgłoszenia.
- [ ] Repozytorium zgłoszenia publiczne przed 11:00 w niedzielę; `.env` poza repo.

## DO WERYFIKACJI

1. Daty w próbkach UMB: znak 543.2025 przy wniosku z 2026, wpływ 15.2026 (12.09?) – `data-partner/umb/niespojnosci_arkusza.md`. 1a. Numer Zarządzenia UMB 2024 (plik „535-2024”, OCR „Nr 536”). 2. Zakres zmiany UDIP z Dz.U. 2025 poz. 1844 (BKS cytuje ją w piśmie 509.2026, więc szablony też). 3. Stosowanie art. 57 § 4 KPA do art. 13 UDIP w praktyce BKS. 4. JRWA 1431. 5. Organ odwoławczy (SKO) dla decyzji UMB. 6. Data premiery Bielik-11B-v3.1 (10.11.2026, źródło wtórne). 7. Szybkość Bielika na CPU laptopa demo. 8. Sygnatury z iszd.pl (lista w `research/notatki/prawo_szczegoly.md` § 6).

## Materiały przygotowane przed wydarzeniem i w jego trakcie (do ujawnienia)

Pakiet powstał 21.11.2026 w Claude Code: research, skrypty `udip-*`, dane syntetyczne, archiwum UMB. Skille `hn-*` pochodzą z pakietu wspólnego (repo `hacknation-2026-solutions/setup`, `prep/_wspolne`, commit `badfd67`). Regulamin zadania § 4 ust. 1: rozwiązania zewnętrzne wskazać w prezentacji (biblioteki: pdfplumber, pypdf, python-docx, pypdfium2, openpyxl, Tesseract; opcjonalnie Ollama i Bielik).

## Znane ograniczenia (stan po przeglądzie 21.11)

- Przypisanie zdań odpowiedzi do pytań jest leksykalne: w 543.2026 dwa zdania trafiają nie do tego „Ad”, co w piśmie BKS, i raport `uncertain_assignment` ich nie oznacza; UI musi pozwalać przenieść każde zdanie (albo LLM, albo wydziały odsyłają „Ad N”).
- Kalendarz z prawdziwego arkusza UMB ma same zamknięte sprawy; kolory pokazuje tryb demo (przesunięte daty, oznaczone `[DEMO]`).
- Brak warstwy aplikacji: API i SQLite trzeba zbudować w sobotę (`research/07`); funkcje `make_draft()`, `finalize()`, `analyze()`, `rows()` są gotowe do wywołania.
- Ścieżka LLM przetestowana tylko na atrapie serwera.

## Mapa plików

`docs/zadanie/` pełna treść i regulamin (PDF + OCR) · `research/01–07, zrodla.md, notatki/` · `.claude/skills/udip-*` (8 skilli zadania) i `hn-*` (5 wspólnych) · `data-partner/umb/` próbki UMB · `data-samples/syntetyczne/` · `scripts/smoke.sh` · `PROGRESS.md` · `.env.example`.
