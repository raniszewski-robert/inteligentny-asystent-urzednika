# PROGRESS: pamięć robocza pakietu

Prompt źródłowy: `hacknation-2026-solutions/setup`, `prompts/gotowe/inteligentny_asystent_urzednika.md` (commit `badfd67`), uruchomiony 21.11.2026 po publikacji pełnej treści. Na prośbę użytkownika pakiet ląduje w **osobnym repozytorium** (katalog główny = pakiet), a nie w `prep/inteligentny_asystent_urzednika/` repo setup.

## Status faz (21.11.2026)

| Faza | Status | Dowód |
|---|---|---|
| Pełna treść i regulamin (OCR skanów) | ✅ | `docs/zadanie/*_ocr.txt` |
| Research równoległy (3 subagenci: partner, prawo, technologia) | ✅ | `research/notatki/*` |
| Materiały UMB od użytkownika (folder mentorów) | ✅ wczytane, 21 dokumentów | `data-partner/umb/`, test-run `udip-dane-i-zrodla` |
| Skrypty rdzenia + testy | ✅ | `references/test-run.md` w 6 skillach |
| Research 01–07, zrodla.md, README | ✅ | pliki |
| Skille: 8 `udip-*` + 5 `hn-*` (kopia) | ✅ | `.claude/skills/` |
| Przegląd krytyczny świeżym subagentem | ✅ 21.11 ok. 14:00; poprawki w drugim commicie | sekcja „Przegląd” |

## Założenia za pola [UZUPEŁNIJ] promptu

- Zespół: **2 osoby, obie piszą kod** (za promptem wspólnym `00_wspolne.md`, nowszym od zadaniowego, który zakładał 4). Role w `research/07`: B (backend) i F (frontend + prezentacja).
- Stack: Python 3.11+ (rdzeń gotowy w Pythonie), FastAPI/Flask + HTML; Claude Code jako narzędzie pracy.
- Zasoby: brak GPU; LLM opcjonalny lokalnie (Ollama, Bielik-4.5B Q8_0 ~5 GB); API Claude dozwolone tylko na danych testowych (treść pkt 1), rdzeń bez API.
- Pitch: treść UMB podaje film ≤ 3 min i ≤ 10 slajdów; czas pitchu finałowego nieznany → 3–5 min (hn-pitch-final).

## Wskazówki autora promptu: przyjęte, odrzucone, skorygowane

| Wskazówka | Decyzja | Uzasadnienie |
|---|---|---|
| „Warianty pełnej treści” (triage, projekty, wyszukiwanie, anonimizacja) | skorygowana | Treść jest znana; 06 opisuje warianty **akcentu**, nie treści |
| Klasyfikacja trybu z oceną F1 | ograniczona do flag | Jury nie liczy metryki; tryb to flaga dla urzędnika |
| Skill „udip-kwalifikacja-i-terminy” | podzielony | Terminy → `udip-kalendarz-terminy` (kalendarz jest wymaganiem nr 3), kwalifikacja → `udip-archiwum-i-wydzialy` |
| Skill „udip-bezpieczenstwo-wejscia” | wchłonięty | Ochrona przed prompt injection w `draft.py` (znaczniki, JSON, kontrola liczb, brak narzędzi), test z atrapą LLM; osobny skill zbędny przy rdzeniu bez LLM |
| „Ścieżki Pamięci 2.0” – co się stało po 2025 | nieustalone | Brak źródeł (research/02) |
| EZD „np. EZD RP” | skorygowana | UMB używa SIDAS (próbka 543.2026) |
| Termin z art. 57 KPA jako pewnik | skorygowana | Orzecznictwo niejednolite → dwie daty (`due_safe`) |
| spaCy do NER | odrzucona | modele `pl_core_news_*` GPL-3.0 |

## Ważne ustalenia z danych UMB (zmieniły kod)

1. pypdf rozstrzela litery w pismach BKS → pdfplumber pierwszy.
2. Rękopis 16.2026: OCR bezużyteczny → miara jakości tekstu i ostrzeżenie (próg 0,5; rękopis 0,36, pisma 0,78–0,90).
3. Nagłówek przekazanego e-maila (543.2026) psuł podział pytań i adresata → podział na liście numerowanej w całym tekście, filtr nagłówków.
4. Adres i e-mail urzędu oraz patroni ulic („św. Maksymiliana Kolbego”) były fałszywymi alarmami → listy jawnych adresów/domen, reguła patronów.
5. Pismo do wysyłki ≠ wersja do archiwum → dwie wersje przy finalizacji.
6. Arkusz UMB ma 6 niespójności → import z raportem i tryb demo.

## Ograniczenia i to, czego nie sprawdzono

- Ścieżka LLM sprawdzona tylko na atrapie serwera (`mock_llm.py`); prawdziwego Bielika w tej sesji nie uruchamiano (brak sieci do pobrania modelu z maszyny sesji).
- Teksty ustaw z ELI: maszyna sesji nie ma dostępu (proxy 403); fakty prawne z subagenta przez przeglądarkę.
- Wagi trasowania i 2 listy słów (WOS, WOA) strojone na danych syntetycznych; zbiór odłożony (seed 7) daje te same wyniki, ale to wciąż nasze szablony.
- Odpowiedzi wydziałów w `przypadek_543/` odtworzone przez nas z pisma BKS.
- Treści z sieci: nie napotkano instrukcji skierowanych do agenta (subagenci nie zgłosili).

## Definicja ukończenia (sprawdzenie 21.11.2026)

| Punkt | Wynik |
|---|---|
| README na 1 stronę z Kartą i planem pierwszej godziny | ✅ |
| 06: warianty, rdzeń, kontrargument z odpowiedzią | ✅ (warianty akcentu, bo treść znana) |
| Liczby/daty/kwoty/API ze źródłem; [?] w README „DO WERYFIKACJI” | ✅ (8 punktów) |
| Każdy skrypt uruchomiony, wynik w `references/test-run.md`; frontmatter `name` = folder | ✅ (sprawdzenie skryptem przed commitem) |
| Brak kluczy/tokenów/haseł | ✅ (grep przed commitem) |
| `data-samples/` z README, ≤ 20 MB | ✅ (< 1 MB; `data-partner/` < 1 MB) |
| Założenia [UZUPEŁNIJ] w PROGRESS | ✅ |

## Otwarte pytania

Lista dla mentorów: `research/03` (7 pytań). Lista DO WERYFIKACJI: README.

## Przegląd (świeży subagent, 21.11.2026 ok. 14:00) i co poprawiono

| Znalezisko | Status |
|---|---|
| Kontrola liczb dzieliła „3.143.761,14” na części: odrzucała poprawny zapis, przepuszczała „3.143 zł” i zamianę psy/koty | ✅ normalizacja liczb, kontrola „liczba + następne słowo”, raport pominiętych liczb; test 2b w `acceptance.py` |
| Wyszukiwanie zwracało samą sprawę; testy maskowały to wykluczeniem i oknem 0 dni | ✅ deduplikacja w `analyze()`, powrót do starszych spraw z oznaczeniem; testy na pełnym archiwum i oknie 365 dni |
| BKS proponowany jako wydział; WGK pomijany w sprawach o zwierzętach | ✅ BKS wyłączony z trasowania; słowa WGK uzupełnione na podstawie pism UMB 293/543; top-1 UMB 5/9 → 6/9 |
| Błędne przypisanie zdań do „Ad” ukrywało luki | ⚠️ częściowo: ważenie słów odwrotne do liczby pytań, kontrola właściwości (pytanie WZP, odpowiedź ZDMiKP → oznaczone); w 543 nadal 2 zdania w innym „Ad” niż u BKS i bez oznaczenia – opisane jako ograniczenie, UI ma pozwalać przenosić zdania |
| Przedłużenie po terminie bez ostrzeżenia; notatki robocze w „Podstawa prawna” | ✅ `report.warnings` (pismo po 14 dniach, termin w przeszłości, ponad 2 mies., brak powodu); `legal_basis` tylko przepisy, notatki w `internal_notes` |
| Formuła zakresu i zwrot w 16.2026, 15.2026, 307.2025 | ✅ filtr nagłówków (rękopis, pieczęć kancelarii), „w zakresie: …”, imiona WIELKIMI LITERAMI → „Szanowny Panie” |
| Brak API do UI (`build()` bez spanów), offsety po edycji | ✅ `make_draft()`, `finalize(edited_text=…)` z ponownym wykryciem |
| Dane syntetyczne: odpowiedź o innej ulicy niż pytanie | ✅ wspólny zestaw parametrów na sprawę; dane wygenerowane od nowa |
| Ogólniki i nieuzasadnione liczby w 06/07/README (prawdopodobieństwa, „milisekundy”, RAG, SQLite, „46 komórek”, „7 typów z próbek”, kierunek 293→543) | ✅ 06 przepisany na tabelę „test jury → wynik dziś”; pomiar BM25 na 5000 sprawach; poprawione liczby i kierunek demo (599 → 307) |
| Rozbieżności dat w danych UMB (543 ze znakiem 2025, 15.2026) | ✅ dopisane do `niespojnosci_arkusza.md` i pytań do mentora; „rozbieżności”, nie „błędy” |

Nie poprawiono: rejestr UMB ma same zamknięte sprawy (kolory tylko w trybie demo – zgodnie z danymi), brak warstwy aplikacji/SQLite (praca na sobotę), LLM niesprawdzony na prawdziwym modelu.
