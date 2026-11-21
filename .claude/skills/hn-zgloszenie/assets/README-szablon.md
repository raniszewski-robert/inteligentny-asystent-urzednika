<!-- Szablon z hn-zgloszenie. Wypełnij każde pole {{...}} albo usuń zdanie, które nie pasuje (np. LLM_MODE, gdy projekt nie używa LLM; Python, gdy to inny stack). Usuń też ten komentarz. -->
# {{NAZWA_PROJEKTU}}: {{JEDNO_ZDANIE_CO_ROBI}}

{{NAZWA_PROJEKTU}} pozwala {{KTO}} {{ZROBIC_CO}} w {{ILE_CZASU}} zamiast {{JAK_DZIS}}. Rozwiązanie zadania {{NAZWA_ZADANIA}} ({{PARTNER}}) na HackNation 2026.

**Demo (2 min):** {{DEMO_URL}} · **Prezentacja:** {{PREZENTACJA_URL_ALBO_docs/prezentacja.pdf}} · **Działająca wersja:** {{APP_URL_ALBO_USUN}} · **Repozytorium:** {{REPO_URL}}

![Zrzut ekranu najważniejszego widoku](docs/screenshot.png)

## Dla kogo i jaki problem rozwiązuje

- **Użytkownik:** {{np. urzędnik wydziału X, który dziennie obsługuje N spraw}}.
- **Problem dziś:** {{jedno zdanie z liczbą od Partnera albo z treści zadania}}.
- **Co zmienia nasze rozwiązanie:** {{jedno zdanie z liczbą z naszej ewaluacji}}.

## Jak spełniamy kryteria

Kryteria i wagi z treści zadania. Kolumna „Gdzie to zobaczyć" prowadzi do dowodu.

| Kryterium | Waga | Co zrobiliśmy | Gdzie to zobaczyć |
|---|---|---|---|
| {{Kryterium 1}} | {{40%}} | {{funkcja}} | wideo 0:20–0:50, sekcja „Wyniki" |
| {{Kryterium 2}} | {{30%}} | {{funkcja}} | `src/...`, sekcja „Architektura" |

## Wyniki

| Metryka | Nasze rozwiązanie | Punkt odniesienia | Zbiór |
|---|---|---|---|
| {{F1 macro}} | {{0,81}} | {{0,74 (TF-IDF + regresja logistyczna)}} | {{walidacja, 2 400 pism, podział czasowy}} |

Jak powstały liczby: `python scripts/evaluate.py` (opis podziału i metryki w `docs/ewaluacja.md`).

## Uruchomienie

Wymagania: Python 3.11+ (albo Docker). Klucz API nie jest potrzebny: domyślnie aplikacja odtwarza zapisane odpowiedzi modelu (`LLM_MODE=replay`).

```bash
git clone {{REPO_URL}} && cd {{KATALOG}}
cp .env.example .env
pip install -r requirements.txt && python app.py      # albo: docker compose up
```

Potem otwórz aplikację w przeglądarce ({{adres lokalny, np. port 8000}}) i kliknij „Przykład 1". Przykładowe dane bez danych osobowych są w `examples/`. Tryb z prawdziwym modelem: ustaw `ANTHROPIC_API_KEY` i `LLM_MODE=cache` w `.env`.

## Architektura

{{3–5 zdań albo diagram: wejście → przetwarzanie → wyjście; gdzie jest model, gdzie dane, co zostaje w urzędzie}}.

## Dane

{{Skąd dane, licencja albo zgoda Partnera, czy są dane osobowe i jak je chronimy. Danych Partnera nie ma w repozytorium.}}

## Ograniczenia

{{2–4 punkty: czego prototyp nie robi, na czym nie był testowany, co wymaga decyzji Partnera. Juror ceni szczerość bardziej niż niedopowiedzenia.}}

## Wdrożenie i koszty

{{Gdzie to działa (chmura rządowa, serwer w urzędzie, model lokalny), koszt na dokument, integracja z systemami Partnera, następny krok.}}

## Ujawnienie

- **Co powstało podczas hackathonu:** {{np. cała aplikacja, model, ewaluacja na danych Partnera, interfejs}}.
- **Materiały przygotowane przed wydarzeniem:** {{lista, np. skrypty profilowania danych i klient LLM z pakietu przygotowawczego zespołu, notatki o modelach; albo „brak"}}. Oznaczone w kodzie komentarzem `# przygotowane przed HackNation`.
- **Narzędzia AI użyte przy tworzeniu:** {{np. Claude Code do pisania części kodu i dokumentacji; model {{nazwa}} w działaniu aplikacji}}.
- **Kod i zasoby stron trzecich:** zależności z licencjami w `LICENSES-THIRD-PARTY.md`; {{inne: zbiory danych, ikony, szablony}}.

## Zespół

{{Imię Nazwisko: rola}} · {{...}}

## Licencja

{{MIT / Apache-2.0 / zgodnie z regulaminem zadania}}. Zależności: `LICENSES-THIRD-PARTY.md`.
