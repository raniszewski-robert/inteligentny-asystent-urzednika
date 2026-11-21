---
name: udip-projekty-odpowiedzi
description: Składa projekt pisma BKS UMB z odpowiedzi wydziałów („Ad 1…Ad N”) i z 7 typów pism (5 odtworzonych z próbek BKS – udostępnienie, odesłanie art. 4 ust. 3, brak danych, kwerenda, doprecyzowanie – oraz BIP i informacja przetworzona). Sprawdza liczby względem odpowiedzi wydziałów, zgłasza luki i niepewne przypisania, ostrzega o terminach, zaznacza dane do anonimizacji i daje DOCX/TXT do wysyłki i zanonimizowany. Użyj, gdy zespół mówi „wygeneruj odpowiedź”, „projekt pisma”, „złóż odpowiedź z wydziałów”, „kwerenda”, „doprecyzowanie” albo „podłącz Bielika”.
---

# udip-projekty-odpowiedzi

Wymaganie 7 (projekt pisma po wgraniu odpowiedzi wydziałów) i test jury nr 2. Zależność: `python-docx` (MIT); LLM opcjonalny przez API zgodne z OpenAI (Ollama/llama.cpp/vLLM).

## API dla aplikacji (`scripts/draft.py`)

```python
from draft import make_draft, finalize, write_docx
res = make_draft(request_text, [("WGK.txt", txt1), ("SCHRONISKO.txt", txt2)], date(2026, 8, 14), "udostepnienie",
                 number="BKS.IV.1431.543.2026", today=date(2026, 8, 26))
res["text"], res["spans"], res["report"], res["html"]      # spany: status suggested/review, flaga addressee
out = finalize(res["text"], res["spans"], accept={"s1"}, reject={"s2"}, edited_text=tekst_po_poprawkach)
out["to_send"], out["anonymized"], out["warnings"]          # + write_docx(out["text"], out["body_spans"], path, final=True)
```
Po edycji tekstu przez urzędnika `finalize(edited_text=…)` wykrywa spany od nowa i przenosi decyzje po (typ, tekst), bo stare offsety nie pasowałyby do nowego tekstu.

`report`: `gaps` (pytania bez treści), `uncertain_assignment` (zdania o niepewnym przypisaniu i pytania wyglądające na właściwość innej komórki niż autor odpowiedzi), `number_check_template` / `number_check` (liczby spoza odpowiedzi albo przy innym słowie), `omitted_numbers_template` (liczby z odpowiedzi, których nie ma w piśmie), `warnings` (terminy art. 13 ust. 2), `internal_notes` (notatki dla urzędnika – **nigdy nie trafiają do pisma**).

## Typy pism (`udip/data/letter_types.json`)

| Typ | Kiedy | Źródło wzoru |
|---|---|---|
| `udostepnienie` | odpowiedź merytoryczna z części wydziałów | próbki 293.2025, 543.2026, 18.2026, 590.2026 |
| `odeslanie_art_4_ust_3` | UMB nie posiada informacji (`entity`, `entity_contact`) | próbki 15.2026, 17.2026 |
| `brak_danych` | „nie prowadzi statystyk” | próbka 16.2026 |
| `przedluzenie` | kwerenda (`extension_until`, domyślnie 2 miesiące) | próbka „Kwerenda 543” |
| `doprecyzowanie` | 7 dni na doprecyzowanie, nowy termin (domyślnie dziś + 30 dni, w granicy 2 miesięcy) | próbka 509.2026 |
| `odeslanie_bip` | informacja jest w BIP (`bip_url`) | przepis + Zarządzenie § 8 (brak próbki) |
| `przetworzona` | wezwanie do wykazania szczególnie istotnego interesu publicznego | przepis + Zarządzenie § 11 ust. 7 (brak próbki) |

Decyzji odmownej celowo nie ma: projekt decyzji przygotowuje wydział (§ 11 ust. 9), podpisuje Prezydent (§ 12).

## CLI

```bash
python3 scripts/draft.py --request wniosek.txt --answer WGK.txt --answer SCHRONISKO.txt \
  --number BKS.IV.1431.543.2026 --received 2026-08-14 --today 2026-08-26 --out-dir wynik/ [--mode llm]
python3 scripts/draft.py --finalize wynik/ --accept s1,s3 --reject s2 [--edited poprawiony.txt]
```

## Przykład wejście → wyjście

Wejście: wniosek UMB 543.2026 (5 pytań) + `WGK.txt`, `SCHRONISKO.txt` z `data-partner/umb/przypadek_543/` (kolejność plików jak wyżej).
Wyjście (fragment): „…na podstawie materiału przygotowanego przez jednostki merytoryczne, tj. Wydział Zieleni i Gospodarki Komunalnej Urzędu Miasta Bydgoszczy oraz Schronisko dla Zwierząt w Bydgoszczy informuję, co następuje. Ad 1 Wyłapywanie bezdomnych zwierząt w 2025 r. realizowało Schronisko… Ad 3 Schronisko zapewniło opiekę w 2025 r. 839 psom oraz 560 kotom.” Raport: `gaps: []`, `number_check_template: []`, `omitted_numbers_template: []`, 2 wpisy w `uncertain_assignment`.

Wniosek 16.2026 (rękopis przepisany ręcznie, `--type brak_danych --dept WSO`) daje pismo prawie identyczne z pismem BKS: „Szanowny Panie, w związku z wystosowanym przez Pana zapytaniem w zakresie: Ile punktów sprzedaży alkoholu… informuję, że Urząd Miasta Bydgoszczy nie prowadzi statystyk…”.

## Jak składa treść (i gdzie się myli)

Odpowiedź wydziału z „Ad N” jest brana akapitami. W przeciwnym razie zdania (bez cięcia po „r.”, „ul.”) trafiają do pytania o największym wspólnym słownictwie, ważonym odwrotnie do liczby pytań zawierających słowo (+ premia dla liczb przy „ile/koszt”). **To heurystyka z progiem (T24).** Zdanie, które pasuje do dwóch „Ad” podobnie, nie jest wstawiane po cichu: trafia do `report["unassigned"]` (źródło i numer zdania), a urzędnik wybiera „Ad” w panelu raportu. W 543.2026 „Miasto nie zawierało umów…” trafia do listy bez przypisania, a „Umowa 1/2022/SZ” do Ad 5 jak w piśmie BKS. Najpewniejsza droga: formularz odpowiedzi „Pytanie / Odpowiedź wydziału” z paczki przekazania (`udip.dispatch`), mapowany w 100% po znacznikach.

## Kontrola liczb (odpowiedź na „halucynacje”)

Liczby są normalizowane (3.143.761,14 = 3 143 761,14; daty osobno; same lata pomijane). Każda liczba w piśmie musi wystąpić w odpowiedziach wydziałów **przy tym samym słowie** („839 psom”, nie „839 kotów”). Test: zmyślone „3.143 zł” i zamienione psy/koty są odrzucane (`acceptance.py`, test 2b). W trybie LLM odrzucenie oznacza powrót do szablonu (`raport.llm_rejected`). Kontrola nie wyłapie zmyślonego faktu bez liczby – dlatego pismo jest projektem.

## Tryb LLM (opcjonalny)

Od T01 tryb `--mode llm` idzie przez `udip.llm` (dostawca z `UDIP_PROVIDER`: `anthropic:sonnet`, `anthropic:haiku` albo `openai_compat:<model>`); zmienne poniżej dotyczą tylko dostawcy `openai_compat`. `LLM_BASE_URL` (domyślnie `http://localhost:11434/v1`), `LLM_MODEL` (domyślnie `SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0`), `LLM_API_KEY` (pusty dla Ollama), `LLM_TIMEOUT` (domyślnie 60 s). Treści w znacznikach `<pytanie>`, `<odpowiedz_wydzialu>`; wynik JSON z akapitem na każde pytanie. Brak serwera albo timeout → `raport.llm_error` i szablon. Sprawdzone tylko na atrapie `scripts/mock_llm.py` (tryby `good`/`bad`); na prawdziwym Bieliku nie testowane. LLM nie dostaje archiwum (to nie jest RAG).

## Kiedy nie używać

- Do decyzji administracyjnych (odmowa, umorzenie): tylko wydział i radca prawny.
- Gdy wydziały odpowiedziały załącznikiem (tabela, skany umów): pismo przewodnie `udostepnienie` z listą „Załączniki:” dopisaną ręcznie (wzór 307.2025).

## Pułapki

- Adresat nieznany (wniosek przekazany e-mailem, jak 543.2026) → `[adresat – uzupełnij z rejestru]`.
- Zakres („w zakresie …”) pochodzi z frazy wniosku („na temat”, „w zakresie”, „dotyczące”) albo z 1. pytania po dwukropku. Sprawdź gramatykę.
- Pismo przedłużenia z datą po 14. dniu albo z nowym terminem w przeszłości dostaje ostrzeżenie w `report.warnings` – nie wysyłaj go bez zmiany.
- Przy finalizacji z zaczernieniem danych osób trzecich narzędzie ostrzega o decyzji (art. 16 UDIP); elementy bez decyzji zostają jawne i są wymienione w ostrzeżeniu.

Wyniki uruchomień: `references/test-run.md`.
