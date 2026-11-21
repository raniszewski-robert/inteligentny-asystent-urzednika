# API Claude: wyjście strukturalne, cytowania, cache promptu

Stan dokumentacji: odczyt 2026-11-17. Skilla „claude-api" nie było w sesji, więc przykłady są przepisane z dokumentacji (źródła Z23–Z25 w `prep/_wspolne/research/zrodla.md`). **Przykłady SDK nie zostały uruchomione** (brak klucza w sesji przygotowawczej). Ten sam kształt zapytania HTTP wysyła `scripts/llm_client.py`, sprawdzony na atrapie API (`references/test-run.md`). Przed użyciem sprawdź stronę dokumentacji, bo API się zmienia.

- Wyjście strukturalne: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Cytowania: https://platform.claude.com/docs/en/build-with-claude/citations
- Cache promptu: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Cennik: https://platform.claude.com/docs/en/about-claude/pricing

## Wyjście strukturalne

Parametr `output_config.format` z typem `json_schema`. Odpowiedź to poprawny JSON w pierwszym bloku tekstowym.

```python
import json, anthropic

client = anthropic.Anthropic()  # klucz z ANTHROPIC_API_KEY
schema = {
    "type": "object",
    "additionalProperties": False,
    "required": ["kategoria", "uzasadnienie"],
    "properties": {
        "kategoria": {"type": "string", "enum": ["wniosek", "skarga", "zapytanie", "inne"]},
        "uzasadnienie": {"type": "string"},
    },
}
resp = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Sklasyfikuj pismo: ..."}],
    output_config={"format": {"type": "json_schema", "schema": schema}},
)
data = json.loads(resp.content[0].text)
```

Z Pydantic: `client.messages.parse(..., output_format=Model)`, wynik w `resp.parsed_output`.

Ograniczenia schematu według dokumentacji: `additionalProperties` musi być `false`; nie są obsługiwane `minimum`/`maximum`, `minLength`/`maxLength` ani schematy rekurencyjne; `minItems` tylko 0 albo 1; nieobsługiwana cecha daje błąd 400. Zakresy liczb i długości sprawdzaj więc we własnym kodzie (`llm_client.validate` używa pełnego jsonschema lokalnie, ale schemat wysyłany do API musi mieścić się w ograniczeniach).

Sprawdzaj `stop_reason`: `max_tokens` oznacza uciętą odpowiedź (zwiększ `max_tokens`), `refusal` odmowę modelu.

## Cytowania

Dokument przekazujesz jako blok `document` z włączonymi cytowaniami. Odpowiedź składa się z bloków tekstu, z których część ma listę `citations` z polami `cited_text`, `document_index`, `start_char_index`, `end_char_index` (dla zwykłego tekstu).

```python
resp = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "document",
             "source": {"type": "text", "media_type": "text/plain", "data": tekst_uchwaly},
             "title": "Uchwała nr XII/45/2026",
             "citations": {"enabled": True}},
            {"type": "text", "text": "Jakie są warunki przyznania dotacji? Odpowiedz krótko."},
        ],
    }],
)
for block in resp.content:
    if block.type == "text":
        print(block.text, [c.cited_text for c in (block.citations or [])])
```

**Cytowania i wyjście strukturalne naraz zwracają błąd 400.** Dokumentacja zaleca wtedy prosić o jedną linię na pole (`kategoria: ...`), parsować ją we własnym kodzie i sprawdzać, że każde pole ma wartość i cytat. Alternatywa: dwa zapytania (najpierw cytowania, potem strukturyzacja wyniku) albo pole `cytat` w schemacie z kontrolą dosłownego wystąpienia w źródle.

## Cache promptu

Stały prefiks (instrukcje, przykłady, długi dokument referencyjny) można cache'ować. Najprościej jednym polem na najwyższym poziomie zapytania:

```python
resp = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=1024,
    cache_control={"type": "ephemeral"},
    system=DLUGIE_INSTRUKCJE_I_PRZYKLADY,
    messages=[{"role": "user", "content": wrap_untrusted(pismo)}],
)
```

Można też stawiać `cache_control` na konkretnych blokach; czas życia domyślnie 5 minut, opcjonalnie godzina. Zmienna część (pismo) idzie zawsze na koniec, po stałym prefiksie. Odczyt z cache jest tańszy od zwykłego wejścia; aktualny mnożnik sprawdź w cenniku (`cost_estimate.py` przyjmuje 10% [?]).

To jest cache po stronie API, oszczędza koszt i czas. `llm_client.py` ma osobny cache po stronie aplikacji (całe odpowiedzi na dysku), który daje tryb offline na demo.

## Identyfikatory modeli i ceny

Wyjście strukturalne i cytowania obsługują m.in. `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-fable-5-2` [✔ Z23, Z24]. Ceny w `llm_client.DEFAULT_PRICES` pochodzą z fragmentów cennika i serwisów wtórnych [~ Z26]; przed pitchem sprawdź je na stronie cennika.
