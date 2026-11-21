# 06. Warianty i rekomendacja

Stan: 21.11.2026, 14:30 (po przeglądzie krytycznym). Pełna treść jest opublikowana (`docs/zadanie/`), więc nie zgadujemy już, czego zażąda Partner. Ten plik odpowiada na dwa pytania: co jury sprawdzi i co dziś pokażemy, oraz na co położyć akcent przy kryteriach 30/20/20/30.

## Test jury (sekcja 6 treści) → co pokazujemy → wynik dziś

| Krok jury | Co pokazujemy | Wynik 21.11 (`acceptance.py`, `evaluate_partner.py`) | Co jeszcze nie działa |
|---|---|---|---|
| 1. Wgranie wniosku PDF/Word → podobne sprawy | Wgranie `Wniosek - BKS.IV.1431.599.2026.docx` → sprawa 307.2025 (ten sam temat rok wcześniej), wydział WE | ✅ na 3 plikach UMB; bliźniak w top 3: 5/6 spraw UMB | 590.2026 (Astoria) nie ma podobnej sprawy w archiwum 10 spraw – to poprawne, ale słabo wygląda; dołożyć archiwum syntetyczne oznaczone jako przykładowe |
| 2. Odpowiedź wydziału → projekt pisma | Przypadek 543.2026: dwie odpowiedzi (Schronisko, WGK) → pismo „Ad 1…Ad 5” | ✅ liczby zgodne z pismem BKS, „839 psom” w Ad 3; 2 zdania w innym „Ad” niż u BKS i raport ich **nie** oznacza (`uncertain_assignment` zgłasza 2 inne miejsca) | UI do przenoszenia zdań między „Ad” (albo LLM) |
| 3. Plik z danymi osobowymi → ukrycie | Dokument z PESEL, dowodem, IBAN, adresem, „ur. … w Toruniu”, podpisem → szary → czarny | ✅ 0 wycieków; „J. Nowak” do decyzji | Brak redakcji w PDF-obrazie (tylko DOCX/TXT) |
| 4. Łatwość, stabilność, realność | Jedna komenda, offline, 0,4 s na 13 dokumentów | ✅ 0 błędów na wszystkich próbkach UMB | Brak UI – do zbudowania w sobotę |
| 5. Kalendarz: kolejność, pilne, etapy | 10 spraw UMB: od najstarszej, kolory, statusy a–e, kwerenda; filtr roku | ✅ (kolory w trybie demo z przesuniętymi datami; arkusz UMB ma same zamknięte sprawy) | Zmiana statusu z UI, historia |
| 6. Wgrywanie danych, ustaw, archiwum | Import arkusza XLSX UMB z raportem rozbieżności; import katalogu pism do archiwum | ✅ 10 spraw, 6 rozbieżności (część zależy od interpretacji art. 57 KPA) | Ustawy jako osobny zbiór wyszukiwania |

## Akcenty (z czego składa się rekomendacja)

| Akcent | Moduły | Kryterium, któremu służy | Wykonalność 22 h | Siła demo |
|---|---|---|---|---|
| A. Kalendarz i proces BKS | `register.py`, `import_xlsx.py`, `deadlines.py` | zgodność 30%, łatwość 20% | 5 (gotowe) | 4 |
| B. Pismo z odpowiedzi wydziałów | `draft.py`, `letter_types.json` | kompletność 30% | 4 (gotowe; LLM opcjonalnie) | 5 |
| C. Anonimizacja wg listy UMB | `anonymize.py` | bezpieczeństwo 20% | 5 (gotowe) | 4 |
| D. Czat AI o wniosku | brak w pakiecie | żadne wprost | 2 | 3 |

## Rekomendacja: wspólny rdzeń A + B + C, D pomijamy

Jedna aplikacja webowa prowadzi AIP przez ścieżkę z „uproszczonej instrukcji” Partnera:

1. Wgraj wniosek (PDF/DOCX). Aplikacja pokazuje pytania, tryb, flagi, podobne sprawy (ostatni rok, a gdy brak – starsze z oznaczeniem) i wydział per pytanie (bez BKS, bo to koordynator). Funkcja: `analyze()`.
2. Zatwierdź dane w kalendarzu: numer BKS.IV.1431, data wpływu, inicjały. Termin wylicza się sam (ustawowy i bezpieczny), status „b”. Funkcja: `rows()`.
3. Wgraj odpowiedzi wydziałów. Powstaje projekt pisma z szarymi propozycjami, luki, niepewne przypisania i ostrzeżenia terminowe. Funkcja: `make_draft()`.
4. Popraw tekst, zaakceptuj lub odrzuć propozycje. Powstają wersja do wysyłki i wersja zanonimizowana, z ostrzeżeniem o decyzji. Funkcja: `finalize(edited_text=…)` wykrywa spany od nowa po edycji.
5. Wyślij poza narzędziem, oznacz „e”. Pismo trafia do archiwum, które zasila następne wyszukiwania.

LLM (Bielik lokalnie) to tylko przełącznik w kroku 3, z kontrolą liczb i powrotem do szablonu. RAG po archiwum dla LLM nie jest zrobiony: tryb `llm` dostaje tylko pytania i odpowiedzi wydziałów.

## Najmocniejszy kontrargument i odpowiedź

**Kontrargument:** „To nie jest »inteligentny asystent«, tylko reguły i szablony. Inne zespoły pokażą LLM, który pisze całe pismo, i jury nagrodzi efekt AI.”

**Odpowiedź:**
1. Treść stawia na „prosty i bezpieczny” program, docelowo „bez dostępu do Internetu” (pkt 1) i sprawdzany pod kątem halucynacji (pkt 7). Bezpieczeństwo ma 20%.
2. Kontrola liczb działa na każdym tekście, także z LLM: odrzuca zmyśloną kwotę („3.143 zł”) i zamienione fakty („560 psów” zamiast „560 kotom”) – test 2b. Na prawdziwym Bieliku jeszcze tego nie sprawdziliśmy (atrapa serwera).
3. Wskazujemy konkretny model lokalny (Bielik-11B-v3.1, Apache-2.0) i pokazujemy, że całość działa także bez niego.
4. Pracujemy na danych UMB: ich 10 spraw, ich arkusz, ich formuły pism, ich Zarządzenie.

## Pytania do mentorów, które mogą zmienić akcent

- Czy BKS chce przenosić zdania między „Ad” ręcznie, czy wolą, żeby wydziały odsyłały odpowiedzi już ponumerowane „Ad N”? (Wtedy `draft.py` bierze je bez zgadywania.)
- Sprawa 15.2026: data wpływu 12.09 czy 12.01? Pisma 543: rok 2025 czy 2026 w znaku? (Rozbieżności w danych, które pokażemy.)
- Czy art. 57 § 4 KPA (sobota → poniedziałek) BKS stosuje? Od tego zależy, ile z 6 rozbieżności arkusza to faktyczne błędy.
