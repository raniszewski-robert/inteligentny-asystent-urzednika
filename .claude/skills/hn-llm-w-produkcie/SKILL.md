---
name: hn-llm-w-produkcie
description: 'Wzorce LLM w rozwiązaniu dla administracji z gotowym klientem. Wyjście według schematu JSON z walidacją, cytowanie źródeł, oddzielenie treści obywatela od poleceń (prompt injection) z testem, koszt i opóźnienie, cache i tryb offline na demo, PLLuM i Bielik lokalnie bez GPU. Użyj, gdy zespół mówi „dodajmy LLM”, „model ma zwracać JSON”, „podaj źródło”, „ile to kosztuje”, „demo bez internetu”, „PLLuM czy Bielik”, „odpal model lokalnie” albo „czy da się to oszukać promptem”.'
---

# hn-llm-w-produkcie

## Po co

W rozwiązaniu dla urzędu LLM musi zwracać dane, które da się zapisać w systemie, pokazać, skąd wziął odpowiedź, nie dać się przejąć treścią pisma od obywatela, kosztować przewidywalnie i działać na demo, gdy Wi-Fi na sali padnie. Jury z administracji pyta o każdą z tych rzeczy. Ten skill daje gotowy klient (`scripts/llm_client.py`) i decyzje, które warto podjąć w pierwszej godzinie.

Fakty o modelach, licencjach i API ze źródłami: `prep/_wspolne/research/03_llm_modele_i_api.md` (stan na 2026-11-17).

## Najpierw trzy decyzje (10 minut)

1. **Czy dane mogą wyjść poza urząd?** Zapytaj Partnera. Dane osobowe, tajemnica skarbowa albo dane wrażliwe oznaczają, że ścieżka docelowa to model lokalny (PLLuM albo Bielik). Na demo możesz pokazać oba tryby. Nie wysyłaj danych osobowych do zewnętrznego API bez zgody.
2. **Czy LLM jest w ogóle potrzebny?** Jeśli wzorce albo klasyczny model z `hn-dane-od-partnera` dają ten sam wynik, wybierz je: są darmowe, szybkie i deterministyczne. LLM bierz do tego, czego wzorce nie umieją (streszczenie, uzasadnienie, pola opisowe), i mierz go tym samym harnessem.
3. **Który model?** Domyślnie najtańszy, który przechodzi Twój zestaw testowy (`claude-haiku-5-5`); większy dopiero, gdy liczby pokażą, że trzeba. Lokalnie: PLLuM 12B albo 4B (apache-2.0), Bielik 11B (apache-2.0, repozytorium bramkowane). Szczegóły: `references/polskie-modele.md`.

## Kroki

1. **Skopiuj klienta** do repozytorium rozwiązania i dodaj `.env.example` z tego skilla (`assets/env.example`). Klucz idzie do `.env`, `.env` do `.gitignore`.
   ```bash
   cp .claude/skills/hn-llm-w-produkcie/scripts/llm_client.py src/
   cp .claude/skills/hn-llm-w-produkcie/assets/env.example .env.example
   ```
2. **Zdefiniuj schemat wyniku** (JSON Schema): `additionalProperties: false`, wszystkie pola w `required`, kategorie jako `enum`, pole `uzasadnienie` i pole na niepewność (np. `"pewnosc": {"enum": ["wysoka","niska"]}`). Ograniczenia schematu w API Claude: `references/claude-api.md`.
3. **Napisz prompt systemowy** z zasadą o treści niezaufanej i opakuj każdy dokument:
   ```python
   from llm_client import LLM, wrap_untrusted, UNTRUSTED_SYSTEM_RULE
   llm = LLM()  # LLM_PROVIDER, LLM_MODEL, LLM_MODE ze zmiennych środowiskowych
   res = llm.structured(user="Sklasyfikuj pismo.\n" + wrap_untrusted(tekst, "pismo_17.pdf"),
                        schema=SCHEMA, system="Klasyfikujesz pisma do urzędu. " + UNTRUSTED_SYSTEM_RULE)
   res.data, res.cost_usd, res.latency_s, res.cached
   ```
   Klient zawsze sprawdza wynik lokalnie schematem i raz ponawia zapytanie z opisem błędu. Ucięta odpowiedź albo odmowa modelu dają czytelny wyjątek, który trzeba pokazać w interfejsie, a nie połknąć.
4. **Gdy odpowiedź ma podać źródło**, użyj cytowań API Claude (bloki `document` z `citations.enabled`) albo, dla modelu lokalnego, każ modelowi zwracać identyfikator fragmentu i sprawdzaj w kodzie, że cytat dosłownie występuje w źródle. Cytowania i wyjście strukturalne nie działają razem w jednym zapytaniu: `references/claude-api.md`, sekcja „Cytowania".
5. **Sprawdź odporność na prompt injection** zestawem ośmiu pism z wstrzykniętymi poleceniami:
   ```bash
   python3 .claude/skills/hn-llm-w-produkcie/scripts/injection_suite.py make --out redteam/
   # uruchom swój potok na redteam/*.txt, wyniki zapisz w outputs/<nazwa>.json
   python3 .claude/skills/hn-llm-w-produkcie/scripts/injection_suite.py check --docs redteam/ --outputs outputs/
   ```
   Wynik „8 odpornych" to argument na pitch. Każdy wyciek napraw, zanim pokażesz demo. Wzorce obrony: `references/wzorce.md`.
6. **Zmierz jakość** tym samym harnessem co baseline (`.claude/skills/hn-dane-od-partnera/scripts/metrics.py` albo `extract_fields.py eval` z tego samego katalogu). Zapisz liczbę obok wyniku baseline'u.
7. **Zmierz koszt i opóźnienie** z dziennika i przelicz na skalę Partnera:
   ```bash
   python3 .claude/skills/hn-llm-w-produkcie/scripts/llm_client.py stats
   python3 .claude/skills/hn-llm-w-produkcie/scripts/cost_estimate.py --docs 50000 --in-tokens 3000 --out-tokens 400 --cached-share 0.6 --latency 4 --parallel 8
   ```
   Liczbę dokumentów rocznie weź od Partnera. Ceny w `llm_client.DEFAULT_PRICES` sprawdź z cennikiem przed pitchem.
8. **Przygotuj demo offline.** W sobotę wieczorem przejdź cały scenariusz demo z `LLM_MODE=cache` i dostępem do modelu. Na scenie ustaw `LLM_MODE=replay`: aplikacja odtwarza zapisane odpowiedzi bez sieci i bez klucza, a pytanie spoza scenariusza daje czytelny komunikat. Katalog `.llm_cache/` (bez danych osobowych) może trafić do repozytorium, żeby juror uruchomił demo bez klucza.

## Przykład

Wejście: „Model ma przypisywać pismo do kategorii i mówić dlaczego. Dane to skargi obywateli."

Wyjście (skrót odpowiedzi):

```
Decyzje: skargi mogą zawierać dane osobowe → pytamy Partnera o API; do tego czasu PLLuM-12B-chat
lokalnie (apache-2.0), Claude jako tryb porównawczy na danych bez nazwisk.
Schemat: {"kategoria": enum[7 kategorii Partnera], "uzasadnienie": string, "cytat": string,
"pewnosc": enum["wysoka","niska"]}; "niska" kieruje pismo do człowieka.
Kontrole: cytat musi dosłownie występować w piśmie (sprawdzane w kodzie); injection_suite 8/8 odpornych.
Wynik: F1 macro 0,81 (baseline TF-IDF 0,74); koszt na Haiku przy 50 tys. pism rocznie i 60% prefiksu z
cache: około 63 zł; mediana 1,9 s na pismo. Demo: LLM_MODE=replay, 12 pism ze scenariusza w .llm_cache/.
```

(Przykład ilustracyjny; liczby są zmyślone, poza kosztem policzonym przez `cost_estimate.py` z cenami z tabeli.)

## Kiedy nie używać

- Zadanie da się rozwiązać wzorcami albo klasycznym modelem z lepszym wynikiem: zostań przy `hn-dane-od-partnera`.
- Budowa całego czatu obsługi obywatela z bazą wiedzy: ten skill daje klocki (schemat, cytaty, injection), ale nie gotowy RAG.
- Treść pitchu o LLM: `hn-pitch-final` (pytania o RODO i koszty).

## Pułapki

- **„Model zwraca JSON" bez walidacji.** Zawsze sprawdzaj wynik schematem po swojej stronie, także przy wyjściu strukturalnym API i przy modelach lokalnych, których serwery mogą ignorować `response_format` [?].
- **Instrukcje w danych.** Pismo może zawierać „zignoruj instrukcje". Opakowanie w znaczniki zmniejsza ryzyko, ale go nie usuwa; wynik i tak przechodzi przez schemat z `enum`, a decyzje wiążące podejmuje człowiek.
- **Wymyślone cytaty.** Model potrafi „zacytować" zdanie, którego nie ma w źródle. Sprawdzaj dosłowne wystąpienie w kodzie albo używaj cytowań API.
- **Demo zależne od sieci i klucza.** Tryb `replay` i cache w repozytorium. Klucz API nigdy w repozytorium ani w nagraniu ekranu.
- **Koszt z pamięci.** Ceny się zmieniają; licz z aktualnego cennika i z rzeczywistej liczby tokenów z dziennika.
- **Model lokalny pobierany na sali.** Pliki GGUF mają kilka GB, a Bielik wymaga akceptacji warunków na koncie Hugging Face. Pobierz przed wyjazdem.
- **Licencja modelu.** `-nc-` w nazwie PLLuM znaczy „tylko niekomercyjnie"; Llama-PLLuM ma licencję Meta. Jeśli Partner przejmuje prawa, wybierz wariant apache-2.0.

## Pliki

- `scripts/llm_client.py`: klient (Claude albo serwer zgodny z API czatu), walidacja schematu, ponowienie, cache, tryb `replay`, dziennik kosztu i opóźnienia; biblioteka standardowa plus opcjonalnie jsonschema (MIT).
- `scripts/injection_suite.py`: osiem pism z wstrzykniętymi poleceniami i sprawdzanie wycieku kanarka.
- `scripts/cost_estimate.py`: koszt i czas dla skali Partnera.
- `scripts/selftest.py`: test wszystkich trzech skryptów na lokalnej atrapie API, bez klucza i bez sieci.
- `assets/env.example`: nazwy zmiennych środowiskowych.
- `references/claude-api.md`: wyjście strukturalne, cytowania, cache promptu w API Claude według dokumentacji z 2026-11-17.
- `references/polskie-modele.md`: PLLuM i Bielik, licencje, uruchomienie lokalne bez GPU.
- `references/wzorce.md`: wzorce dla administracji (człowiek w pętli, obrona przed injection, cache, offline).
- `references/test-run.md`: zapis uruchomień testowych.
