# Asystent UDIP: opis techniczny

## Jak to działa

- **Terminy:** 14 dni z art. 13 UDIP, przesunięcie z soboty i święta (art. 57 § 4 KPA), przedłużenie do 2 miesięcy, termin bezpieczny (ostatni dzień roboczy przed 14. dniem), Wigilia jako dzień wolny. 18 testów brzegowych.
- **Wczytywanie:** PDF (pdfplumber, pypdf), DOCX, ODT, TXT. Skany czyta OCR Tesseract (polski). Aplikacja ocenia jakość odczytu i przy rękopisie ostrzega „wpisz ręcznie”.
- **Bezpieczeństwo pliku:** skaner przy wgraniu wykrywa ukryty tekst (biały, 1 pt), obrazy i podpisy oraz polecenia wstrzyknięte w treść („zignoruj poprzednie instrukcje”). Skaner tylko raportuje, tekst urzędnika zostaje bez zmian. Treść dla modelu jest oznaczona jako niezaufana, a każdą liczbę z odpowiedzi modelu sprawdza się z dokumentem źródłowym.
- **Podobne sprawy i wydziały:** wyszukiwanie BM25 po archiwum odpowiedzi (okno 365 dni, starsze oznaczone). Wydział dla każdego pytania wynika ze słów kluczowych 46 komórek UMB i jednostek miejskich, z wydziałów podobnych spraw i z poprawek urzędnika.
- **Przekazanie do wydziałów:** pakiet dla wydziału z pytaniami, terminem wewnętrznym i formularzem odpowiedzi (DOCX). Odpowiedź z formularza trafia do właściwego „Ad” bez zgadywania.
- **Projekt pisma:** 7 typów pism (5 odtworzonych z pism BKS, 2 z przepisów i Zarządzenia). Zdania odpowiedzi są przypisane do pytań; zdanie niepewne trafia na listę „bez przypisania”, a nie do losowego „Ad”. Każda liczba w projekcie musi wystąpić w odpowiedzi wydziału przy tym samym słowie. Każde zdanie ma źródło (plik, akapit, sposób przypisania).
- **Anonimizacja:** wzorce z sumami kontrolnymi (PESEL, NIP, REGON, IBAN, dowód osobisty, księga wieczysta). Słownik 3 807 imion i 12 596 nazwisk polskich, ukraińskich i rosyjskich z odmianą, także w zapisie paszportowym i polskim ([udip/data/names/README.md](../udip/data/names/README.md)). Kategorie z listy UMB (adres, data i miejsce urodzenia, podpis, telefon, e-mail, działki, kategorie szczególne, tajemnica przedsiębiorcy). Osoby pełniące funkcje publiczne, adresy urzędów i patroni ulic idą do decyzji urzędnika albo zostają jawne.
- **Eksport:** dwie wersje pisma: do wysyłki (adresat jawny) i zanonimizowana (archiwum, BIP). Aplikacja blokuje eksport, dopóki urzędnik nie zdecyduje o każdym fragmencie. Zaczernienie ma stałą długość, żeby nie zdradzało długości nazwiska. Metadane DOCX są czyszczone, a XML pliku jest sprawdzany na wycieki przed pobraniem. Stopka podaje kategorie danych i podstawę prawną. Przy zaczernianiu danych osób trzecich w udostępnianej informacji aplikacja ostrzega, że częściowa odmowa wymaga decyzji.
- **Pamięć instytucjonalna:** aplikacja zapamiętuje decyzje urzędnika („to nazwisko zawsze zaczerniaj”, „to jest nazwa ulicy”), poprawki wydziałów i przepisy dodane do archiwum. Panel w Archiwum pozwala to przejrzeć i wyczyścić.
- **Model językowy (lokalny Bielik w tle, razem z regułami):** streszczenie wniosku i uzasadnienie wydziału, redakcja akapitów „Ad”, dodatkowe fragmenty do anonimizacji. Wynik modelu przechodzi przez te same kontrole co reguły: liczby spoza odpowiedzi są odrzucane, a fragmenty od modelu zawsze idą „do decyzji”. Odpowiedzi trafiają do pamięci podręcznej. Strony nie czekają na model: pokazują wynik reguł od razu, a Bielik dopisuje swoje w tle (streszczenie, uzasadnienia wydziałów, akapity, dodatkowe fragmenty do anonimizacji). Gdy Bielik nie działa na komputerze, aplikacja zostaje przy regułach.
- **Tryb pokazowy Gemini (chmura):** `UDIP_PROVIDER=gemini` i `GEMINI_API_KEY` w `.env` kierują te same zadania do Google Gemini (punkt zgodny z API OpenAI), co daje odpowiedź w kilka sekund zamiast minut. Tylko na danych testowych; ekran podpisuje wyniki „Gemini (chmura Google, dane testowe)”. W urzędzie zostaje lokalny Bielik – dane wniosków nie opuszczają wtedy komputera.
- **Zapytaj archiwum (Archiwum):** pytanie urzędnika → najlepiej pasujące sprawy i przepisy (BM25) → odpowiedź Bielika tylko z tych fragmentów, z odwołaniami [S1], [S2]. Odpowiedź bez źródeł albo z liczbą spoza źródeł jest odrzucana; bez modelu urzędnik dostaje same fragmenty.

Technologia: Python 3.11+, FastAPI, Jinja2, htmx (bez CDN), SQLite; jeden proces, przeglądarka w intranecie. Kod: `udip/` (rdzeń), `app/` (ekrany), `scripts/` (seed, ewaluacja, słownik imion), `tests/`.

## Praca lokalna, bez chmury

- Bez internetu działa całość: kalendarz, wyszukiwanie, wydziały, pisma, anonimizacja (reguły i BM25). `UDIP_OFFLINE=1` blokuje każde połączenie poza komputer urzędu.
- Rozwiązanie korzysta tylko z modeli uruchomionych lokalnie; dane wniosków nie opuszczają urzędu. Klient zewnętrznego API jest w kodzie wyłączoną opcją i nie był używany w pomiarach.
- Model lokalny w urzędzie: **Bielik-11B-v3.1-Instruct** (Apache-2.0) przez Ollama albo vLLM na serwerze z GPU 16–24 GB. Na laptopie bez GPU: Bielik-4.5B-v3.0-Instruct (Q8_0). Podłączenie: `UDIP_PROVIDER=openai_compat:<model>` i `LLM_BASE_URL` w `.env`.

## Wyniki

Ewaluacja na danych UMB (reguły oraz lokalny Bielik 4.5B przez Ollama, offline, $0): [eval/RESULTS.md](eval/RESULTS.md), [eval/bielik.md](eval/bielik.md).

| Miara | Reguły | Bielik 4.5B (`Q8_0`, offline) |
|---|---:|---:|
| Liczba pytań zgodna z ręczną (10 spraw UMB) | 90% | 60% |
| Podsumowanie do kalendarza wypełnione (UMB) | nie dotyczy | 100% |
| Wydział UMB: top-1 / top-3 | 67% / 89% (6/9, 8/9) | 56% / 56% |
| Fakty we właściwym „Ad” (sprawa 543) | 100% (6/6; zdania niejednoznaczne trafiają do listy „bez przypisania”) | 83% (5/6, 0 błędnych liczb) |
| Anonimizacja: czułość / precyzja / wycieki | 100% / 99% / 0 | 100% / 67% / 0 |
| Wstrzyknięcie poleceń (`injection_pl.txt`) | nie dotyczy | schemat zachowany, brak wycieku |
| Czas na wniosek (laptop bez GPU) | poniżej 0,02 s | 165,6 s |
| Koszt całej ewaluacji | $0.00 | $0.00 |

Reguły są szybsze i dokładniejsze; Bielik dodaje streszczenia do kalendarza i redakcję akapitów. Na serwerze z GPU czas Bielika spada do kilku sekund.

## Ograniczenia

- Odpowiedzi wydziałów w przykładowej sprawie 543.2026 są odtworzone z pisma BKS (oryginalne pliki wydziałów nie są dołączone).
- Przypisanie zdań odpowiedzi do pytań jest leksykalne; niepewne przypisania są na liście, a urzędnik przenosi zdanie jednym wyborem.
- Arkusz UMB ma same zamknięte sprawy; kolory pilności pokazuje tryb demo z przesuniętymi datami.
- Słownik nazwisk nie jest pełny: rzadkie nazwisko z rzadkim imieniem bez „Pan/Pani” może zostać pominięte. Listę imion z rejestru PESEL (dane.gov.pl) można dodać jako kolejne źródło słownika.
- Brak logowania i ról (lista urzędników w nagłówku); brak integracji z SIDAS (zgodnie z pkt 11 treści zadania).
