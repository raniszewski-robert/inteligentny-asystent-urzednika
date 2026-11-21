# 07. Plan do niedzieli 11:00 i demo

Założenie zespołu: 2 osoby, obie piszą kod (kontekst pakietu wspólnego `hn-*`; PROGRESS.md). Osoba **F** (frontend + prezentacja), osoba **B** (backend + dane + testy). Przy 3–4 osobach: wydzielić „prezentacja i wideo” oraz „LLM lokalny”.

## Wymagania formalne z treści zadania (sekcja 4)

- Film **maks. 3 minuty** (treść zadania); HackNation zaleca do 2 minut → celujemy w 2:00–2:30.
- Prezentacja **maks. 10 slajdów**: nazwa i zespół; problem (czas urzędnika, ochrona danych); pomysł (wyszukiwanie archiwum, anonimizacja, kalendarz) i technologia; jak działa (wgranie PDF/Word → projekt pisma); dla kogo (urzędnicy JST); przyszłość w UMB; narzędzia; **czy działa offline i jaki model lokalny**.
- Regulamin: rozwiązanie zewnętrzne wskazać w prezentacji (§ 4 ust. 1); zwycięzca przenosi prawa (§ 4) → slajd „Licencje”.

## Harmonogram

| Kiedy | B (backend) | F (frontend, prezentacja) | Punkt kontrolny |
|---|---|---|---|
| sob. 14:30–15:00 | `bash scripts/smoke.sh` (wszystkie selftesty i akceptacja na zielono); decyzja: FastAPI | Szkic 3 ekranów: Kalendarz, Sprawa, Anonimizacja (wg arkusza UMB) | wszystko zielone na laptopie demo |
| 15:00–17:00 | API: `POST /wnioski` (ingest+analyze), `GET /kalendarz`, `POST /sprawy/{id}/odpowiedzi`, `POST /sprawy/{id}/projekt`, `POST /sprawy/{id}/finalizuj`; pliki JSON (jak `register.py`) albo SQLite – decyzja o 14:30; funkcje do wywołania: `analyze()`, `rows()`, `make_draft()`, `finalize()` | Ekran Kalendarz (tabela, kolory, filtr roku, statusy) z `register.rows()` | 17:00: kalendarz z 10 sprawami UMB w przeglądarce |
| 17:00–20:00 | Ekran Sprawa: podobne sprawy, ścieżka wydziałów, lista pytań; wgrywanie odpowiedzi | Ekran Anonimizacja: tekst z `<mark>` szary/ramka/czarny, klik = akceptuj/odrzuć | **19:30 kontrola HackTribe (`hn-zgloszenie`); 20:00 wybór zadania zamknięty** |
| 20:00–24:00 | Eksport DOCX/TXT (dwie wersje), archiwizacja po „e) wysłana”; import XLSX z UI | Widok „Baza wiedzy”: wgraj ustawę/zarządzenie/archiwum; licznik spraw | 24:00: pełna ścieżka 1–5 klikalna |
| nd. 00:00–04:00 | (opcja) Ollama + Bielik 4.5B: `--mode llm` za przełącznikiem; pomiar czasu 5 akapitów vs `LLM_TIMEOUT` | Przenoszenie zdań między „Ad” (lista `uncertain_assignment`); edycja tekstu → `finalize(edited_text)`; slajdy 1–10 | 04:00: feature freeze dla opcji |
| 04:00–07:00 | `acceptance.py` w CI/README, instalacja jedną komendą, `.env.example` | Nagranie wideo (scenariusz niżej) | 07:00: koniec funkcji |
| 07:00–09:30 | Próba generalna na `acceptance.py` (11/11) i ręcznie wg „definicji done”; README dla jury | Montaż, napisy | **09:30 zamrożenie kodu** |
| 09:30–10:30 | `hn-zgloszenie`: preflight, licencje, sekrety, linki | Zgłoszenie w HackTribe | **10:30 zgłoszenie gotowe; 11:00 termin** |

## Definicja „done” dla MVP

1. Wgranie `Wniosek - BKS.IV.1431.599.2026.docx` pokazuje 2 pytania, sprawę 307.2025 i wydział WE w < 3 s; wgranie 293.2025 – WGK i Schronisko.
2. Kalendarz pokazuje 10 spraw UMB od najstarszej, z czterema poziomami pilności i statusami a–e; filtr roku działa.
3. Dla sprawy 543.2026 wgranie dwóch odpowiedzi wydziałów daje pismo „Ad 1…Ad 5” z 839 psami, 560 kotami i 3.143.761,14 zł; UI pozwala przenieść dowolne zdanie między „Ad” (2 zdania są u nas gdzie indziej niż w piśmie BKS, a raport ich nie oznacza).
4. Plik z danymi osobowymi: wszystkie dane z listy UMB na szaro, po akceptacji na czarno, 0 wycieków w DOCX.
5. `acceptance.py` = 11/11; aplikacja startuje jedną komendą bez internetu.

## Scenariusz wideo (2:00–2:30)

| Czas | Obraz | Lektor |
|---|---|---|
| 0:00–0:15 | Excel UMB z zaznaczonymi rozbieżnościami | „Tak dziś wygląda rejestr wniosków. Import pokazuje 6 miejsc do sprawdzenia, np. termin wpisany z rokiem 2025 przy wniosku z 2026.” |
| 0:15–0:40 | Kalendarz: 10 spraw, kolory | „Od najstarszej. Czerwone po terminie, pomarańczowe na jutro. Termin liczony z Wigilią, Wielkanocą i sobotami.” |
| 0:40–1:05 | Wgranie wniosku 599.2026 (DOCX) | „Narzędzie wyciąga 2 pytania, znajduje zeszłoroczną sprawę 307 o tym samym i proponuje Wydział Edukacji i Sportu.” |
| 1:05–1:35 | Sprawa 543: wgranie odpowiedzi Schroniska i WGK → pismo | „Pismo w stylu BKS, Ad 1 do Ad 5. Każda liczba jest sprawdzana z odpowiedzią wydziału.” |
| 1:35–2:05 | Anonimizacja: szary → czarny, DOCX | „Szare to propozycja według listy UMB. Urzędnik akceptuje, eksport w dwóch wersjach: do wysyłki i do archiwum.” |
| 2:05–2:25 | Wyłączenie Wi-Fi, dalej działa; slajd Bielik | „Działa bez internetu. Docelowo lokalny Bielik 11B, licencja Apache 2.0.” |

## Demo na żywo (finał): realne / zmockowane / awaryjne

| Element | Stan | Plan awaryjny |
|---|---|---|
| Kalendarz, import XLSX, terminy | realne | zrzut HTML z `register.py --html` |
| Analiza i podobne sprawy | realne (BM25, offline) | wynik JSON z `acceptance.py` |
| Pismo z odpowiedzi wydziałów | realne (szablon); odpowiedzi wydziałów 543 odtworzone z pisma BKS (mówimy to); 2 zdania do przeniesienia ręcznie (pokazać jako „urzędnik poprawia”) | gotowe `projekt.docx` |
| LLM | opcjonalne, lokalne | wyłączyć: tryb szablonu jest domyślny |
| Rękopis 16.2026 | realny komunikat „wpisz ręcznie” | — |

## 10 najtrudniejszych pytań jury

| Pytanie | Odpowiedź |
|---|---|
| Czy to działa bez internetu? | Tak. Rdzeń (reguły, BM25, szablony, anonimizacja) nie używa sieci. LLM opcjonalny: Bielik lokalnie przez Ollama. Pokażemy po wyłączeniu Wi-Fi. |
| Jaki model w urzędzie? | Bielik-11B-v3.1-Instruct (Apache-2.0, 32K) na serwerze z GPU 16–24 GB; na laptopie Bielik-4.5B. Zapas: PLLuM-12B-instruct-2512 (Apache-2.0). |
| Co z halucynacjami? | Każda liczba w projekcie musi wystąpić w odpowiedzi wydziału i przy tym samym słowie („839 psom”), inaczej akapit jest odrzucany; raport pokazuje też liczby pominięte. Na prawdziwym Bieliku jeszcze nie sprawdzone. Pismo ma status projektu. |
| Jak anonimizujecie i czy to skuteczne? | Wzorce z sumami kontrolnymi (PESEL, NIP, REGON, IBAN, dowód), słownik imion z odmianą, lista UMB. Na 148 spanach 0 wycieków; to dane syntetyczne, więc jury powinno sprawdzić własnym plikiem. |
| Czy zaczernienie nie jest odmową? | Jest częściową odmową wymagającą decyzji (WSA Opole I SAB/Op 11/26), dlatego narzędzie to sygnalizuje i niczego nie zaczernia bez akceptacji. |
| 14 dni a soboty i święta? | Liczymy wg art. 57 § 4 KPA, ale sądy nie przesądziły tego dla UDIP, więc pokazujemy też termin bezpieczny. |
| „Uczenie się”? | Każde wysłane pismo i importowany katalog dokumentów trafiają do archiwum, z którego od razu korzysta wyszukiwanie i trasowanie do wydziałów. Ustawy: osobny zbiór wyszukiwania (w budowie). Dostrajanie modelu to etap wdrożenia. |
| Jak wdrożyć w UMB? | Jeden proces Python na serwerze w intranecie, dane w plikach lub SQLite; bez integracji z SIDAS (zgodnie z pkt 11). Import obecnego arkusza XLSX. |
| Skala? | Zmierzone: 5000 spraw – indeks 0,37 s, zapytanie 10 ms (BM25, CPU). Przy 5000 sprawach trafność spada (hit@5 0,75), więc docelowo hybryda z embeddingami (04, wariant C). |
| Licencje przy przeniesieniu praw? | Tylko MIT/BSD/Apache; bez PyMuPDF (AGPL), docxtpl (LGPL), modeli spaCy pl (GPL). Lista w README. |
