# Polskie modele: PLLuM i Bielik

Fakty i źródła: `prep/_wspolne/research/03_llm_modele_i_api.md` (odczyt kart modeli 2026-11-17). Tu jest wersja robocza na hackathon.

## Który wybrać

| Potrzeba | Wybór | Licencja | Uwagi |
|---|---|---|---|
| Najlepsza jakość lokalnie, laptop z 16 GB RAM | PLLuM-12B-chat-2512 albo Bielik-11B-v3.x-Instruct w GGUF Q4 | apache-2.0 obie [✔] | Bielik: repozytorium bramkowane, trzeba zaakceptować warunki na koncie HF [✔]; starsze karty wspominają dodatkowe warunki użytkowania [~] |
| Słaby laptop (8 GB RAM) albo szybkie demo | PLLuM-4B-chat-2512 | apache-2.0 na karcie [✔]; model bazowy Gemma 3, sprawdź też jego warunki [?] | |
| Argument „model dla administracji" na pitchu | PLLuM | | Karta mówi o administracji publicznej i tematach prawnych [✔]; rozwijany przez HIVE AI [✔] |
| Partner przejmuje prawa do rozwiązania | warianty apache-2.0 | | Unikaj `-nc-` (tylko niekomercyjnie) [✔] i rozważ ostrożnie licencję Llama 3.1 (Llama-PLLuM 8B, 70B) [?] |

Bielik 11B v3.1 (10.11.2026) zapowiada lepsze wywoływanie narzędzi i odpowiedzi w ścisłym formacie [~]. Sprawdź kartę na Hugging Face przed pobraniem.

## Uruchomienie bez GPU [?]

Poniższe polecenia nie zostały uruchomione w sesji przygotowawczej (brak modelu i limit czasu). Sprawdź je na laptopie przed wyjazdem i zapisz wynik w `references/test-run.md` repozytorium rozwiązania.

**Ollama** (najprostsze; serwer na porcie 11434, endpoint zgodny z API czatu pod `/v1`):

```bash
ollama pull hf.co/<repozytorium-GGUF>:Q4_K_M      # nazwa repozytorium GGUF z karty modelu
ollama run hf.co/<repozytorium-GGUF>:Q4_K_M "Streść w jednym zdaniu: ..."
```

**llama.cpp** (`llama-server`, endpoint zgodny z API czatu, domyślnie port 8080):

```bash
llama-server -m model-Q4_K_M.gguf -c 8192 --port 8080
```

Potem w aplikacji:

```bash
LLM_PROVIDER=openai_compat LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=<nazwa modelu> python3 app.py
```

`llm_client.py` wysyła `response_format` z typem `json_schema`. Czy dany serwer i wersja go respektują, sprawdź sam [?]. Klient i tak waliduje wynik schematem i ponawia zapytanie, więc nieposłuszny serwer da błąd, a nie zły zapis w bazie. Pomaga też opisanie schematu w prompcie i `temperature: 0`.

## Oczekiwania wydajności [?]

| Model w Q4 | RAM (szacunek) | Tokeny/s na CPU laptopa (szacunek) |
|---|---|---|
| 4B | około 3 GB | kilkanaście |
| 11–12B | około 7–8 GB | kilka |

Przy kilku tokenach na sekundę odpowiedź na 300 tokenów trwa około minuty. Na demo: krótkie odpowiedzi w schemacie, cache, tryb `replay`. Zmierz na własnym sprzęcie: `llm_client.py stats` podaje medianę i p90 opóźnienia.

## Checklista przed wyjazdem

- [ ] Konto Hugging Face, warunki Bielika zaakceptowane.
- [ ] Plik GGUF wybranego modelu pobrany na laptop demo (nie na salę).
- [ ] Ollama albo llama.cpp zainstalowane, jedno zapytanie testowe przeszło.
- [ ] `llm_client.py ask "Cześć"` z `LLM_PROVIDER=openai_compat` zwraca odpowiedź; `stats` pokazuje opóźnienie.
