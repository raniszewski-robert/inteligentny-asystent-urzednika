# Zapis uruchomień testowych: hn-llm-w-produkcie

Data: 2026-11-17, Python 3.13.18, jsonschema 4.26.0, Linux. Polecenie: `python3 scripts/selftest.py`.

**Wynik: 18 PASS, 0 FAIL.**

`selftest.py` importuje `llm_client.py` (testy 1–14 i 18 przez CLI `ask`), uruchamia `injection_suite.py make` i `check` (testy 15–16) oraz `cost_estimate.py` (test 17).

Test uruchamia lokalną atrapę API (serwer HTTP z biblioteki standardowej) odpowiadającą na `/v1/messages` w kształcie API Claude i na `/v1/chat/completions` w kształcie API zgodnego z OpenAI. Klucz API w teście to napis `test-not-a-real-key`. **Prawdziwe API Claude ani lokalny model nie były wywołane** (brak klucza i modelu w sesji przygotowawczej); kształt zapytania jest zgodny z dokumentacją z 2026-11-17 (`references/claude-api.md`).

| Test | Wynik |
|---|---|
| Nagłówki `x-api-key` i `anthropic-version: 2023-06-01` | PASS |
| Zapytanie zawiera `output_config.format` z typem `json_schema` | PASS |
| Wynik sparsowany i zgodny ze schematem | PASS |
| Koszt z cennika (1000 tokenów wejścia, 200 wyjścia, Haiku: 0,0002 USD) | PASS |
| Drugie identyczne wywołanie z cache, bez zapytania do serwera | PASS |
| Tryb `replay` działa bez klucza API, z cache | PASS |
| Tryb `replay` bez wpisu w cache daje czytelny błąd | PASS |
| Brak klucza w trybie `live` daje czytelny błąd z nazwą zmiennej | PASS |
| Zły typ pola → ponowienie z opisem błędu → poprawny wynik (2 zapytania) | PASS |
| Bez ponowień zły wynik kończy się wyjątkiem z opisem błędu walidacji | PASS |
| Dostawca `openai_compat`: ścieżka `/v1/chat/completions` i `response_format` | PASS |
| Model lokalny: koszt 0 | PASS |
| `wrap_untrusted` neutralizuje próbę zamknięcia i otwarcia znacznika | PASS |
| `stats` liczy wywołania, koszt i opóźnienie z dziennika | PASS |
| `injection_suite`: atrapa „naiwnego modelu" → 8 wycieków, kod 1 | PASS |
| `injection_suite`: potok ze schematem → 0 wycieków, kod 0 | PASS |
| `cost_estimate`: tabela kosztów i czas | PASS |
| CLI `ask` w trybie `replay` bez cache → kod 1 i komunikat | PASS |

Wyjście `cost_estimate.py --docs 50000 --in-tokens 3000 --out-tokens 400 --cached-share 0.6 --latency 4 --parallel 8`:

```
model                  USD razem   PLN razem  PLN/dok.
claude-haiku-5-5           16.90       62.53    0.0013
claude-sonnet-5-5         338.00     1250.60    0.0250
claude-opus-5-5           676.00     2501.20    0.0500
claude-fable-5-2         1352.00     5002.40    0.1000
model lokalny               0.00        0.00    0.0000  (+ koszt serwera i utrzymania)
Czas: 4.0 s na dokument, 8 rownolegle -> 6.9 h dla calego zbioru.
```

Kwoty wynikają z cen w `DEFAULT_PRICES` i kursu 3,7 zł/USD; oba trzeba sprawdzić przed pitchem.

## Błędy znalezione i poprawione

W pierwszym przebiegu 2 testy nie przeszły z powodu błędów w samym teście: atrapa zapisywała nagłówki z oryginalną wielkością liter (urllib wysyła `X-api-key`), a oczekiwany komunikat błędu walidacji był zbyt wąski (jsonschema zgłasza najpierw brakujące pole). Klient działał poprawnie.

## Czego nie testowano

- Prawdziwego API Claude, cytowań i cache promptu po stronie API.
- Ollamy i llama.cpp oraz tego, czy respektują `response_format`.
- Wydajności modeli lokalnych na CPU.
