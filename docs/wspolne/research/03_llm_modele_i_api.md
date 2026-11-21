# Modele i API dla rozwiązań z LLM: stan na 2026-11-17

Pytanie: **z czego zespół może legalnie i szybko zbudować funkcję LLM, także bez internetu i bez GPU?** Oznaczenia: [✔] karta modelu lub dokumentacja odczytana 2026-11-17, [~] źródło wtórne, [?] hipoteza do sprawdzenia na własnym laptopie. Źródła: `zrodla.md`.

## 1. PLLuM (CYFRAGOVPL na Hugging Face)

Rodzinę rozwijało konsorcjum PLLuM (2024), a od 2025 r. HIVE AI. Karta podaje, że modele sprawdzają się szczególnie w tematach administracji publicznej, prawnych i urzędowych z wyszukiwaniem dokumentów. [✔ Z17]

Generacja 2512 (grudzień 2025) [✔ Z17]:

| Model | Rozmiar | Model bazowy | Licencja na karcie |
|---|---|---|---|
| PLLuM-4B-base / instruct / chat-2512 | 4B | gemma-3-4b-pt | apache-2.0 |
| Llama-PLLuM-8B-base / instruct / chat-2512 | 8B | Llama-3.1-8B | llama3.1 |
| PLLuM-12B-base / instruct / chat-2512 | 12B | Mistral-Nemo-Base-2407 | apache-2.0 |
| Llama-PLLuM-70B-instruct / chat-2512 | 70B | Llama-3.1-70B | llama3.1 |

- Wariant `-chat` jest dostrojony do preferencji ludzi i bezpieczniejszy w dialogu; `-instruct` do poleceń. [✔ Z17]
- Modele z `-nc-` w nazwie (starsze generacje) są tylko do użytku niekomercyjnego (CC BY-NC 4.0). Nie używać w rozwiązaniu, do którego Partner może nabyć prawa. [✔ Z18]
- Karta PLLuM-4B-chat-2512 pokazuje 3 skwantyzowane wersje dla llama.cpp, LM Studio i podobnych. Wymagań sprzętowych do inferencji nie podaje. [✔ Z17]
- Model 4B bazuje na Gemmie. Karta podaje apache-2.0, ale przed użyciem w rozwiązaniu sprawdź też warunki modelu bazowego. [?]
- Licencja llama3.1 (8B, 70B) to licencja społecznościowa Meta z własnymi warunkami. Jeśli Partner przejmuje prawa, prościej wybrać wariant apache-2.0 (4B albo 12B). [?]

## 2. Bielik (SpeakLeash i ACK Cyfronet AGH)

| Fakt | Pewność | Źródło |
|---|---|---|
| Bielik-11B-v3.0-Instruct: 11B parametrów, licencja apache-2.0, format czatu ChatML | [✔] | Z19 |
| Repozytorium jest bramkowane: trzeba się zalogować na Hugging Face i zaakceptować warunki, zanim pobierze się pliki | [✔] | Z19 |
| Karta wskazuje 22 skwantyzowane warianty (llama.cpp, Ollama, LM Studio) | [✔] | Z19 |
| Bielik 11B v3.1 wyszedł 10.11.2026 (56 języków, lepsze wywoływanie narzędzi i odpowiedzi w ścisłym formacie), z wersjami GGUF i FP8 | [~] | Z20 |
| Starsze karty Bielika wspominają o dodatkowych Warunkach Użytkowania (bielik.ai/terms) obok Apache 2.0 | [~] | Z21 |
| Istnieją mniejsze modele serii v3 (Bielik v3 Small, Minitron 7B v3) | [~] | Z22 |

## 3. Uruchomienie lokalne bez GPU

- Droga: plik GGUF plus llama.cpp, Ollama albo LM Studio. Wszystkie udostępniają lokalny endpoint zgodny z API czatu, więc kod aplikacji różni się tylko adresem i nazwą modelu. [?] Sprawdź na własnym sprzęcie.
- Szacunek pamięci: model 11–12B w kwantyzacji Q4 potrzebuje około 7–8 GB RAM, a 4B około 3 GB. Szybkość na CPU laptopa to pojedyncze do kilkunastu tokenów na sekundę. [?] Zmierz przed wyjazdem na laptopie, który pojedzie do Bydgoszczy.
- **Pobierz modele przed 21.11.** Pliki mają kilka GB, Bielik wymaga akceptacji warunków na koncie Hugging Face, a Wi-Fi na sali z 1500 osobami może nie wystarczyć. [?]

## 4. Kiedy polski model lokalny, a kiedy API

| Sytuacja | Wybór |
|---|---|
| Partner mówi, że dane nie mogą wyjść poza urząd (dane osobowe, tajemnica skarbowa, dane wrażliwe) | Model lokalny jako ścieżka docelowa. W demo można pokazać oba tryby |
| Jury pyta o suwerenność i koszty utrzymania | Argument: PLLuM powstał dla administracji i jest rozwijany przez HIVE AI, wagi są otwarte |
| Trzeba najwyższej jakości rozumowania, długiego kontekstu albo wyjścia ściśle według schematu | API Claude |
| Demo ma działać bez internetu | Model lokalny albo tryb odtwarzania z cache (`hn-llm-w-produkcie`, `scripts/llm_client.py`, `LLM_MODE=replay`) |

## 5. API Claude: co sprawdzono w dokumentacji 2026-11-17

| Funkcja | Jak | Pewność | Źródło |
|---|---|---|---|
| Wyjście strukturalne (dostępne ogólnie) | Parametr `output_config={"format": {"type": "json_schema", "schema": {...}}}` w `client.messages.create`. Odpowiedź to poprawny JSON w bloku tekstowym. Stary parametr `output_format` z nagłówkiem beta działa przejściowo | [✔] | Z23 |
| Pomocnik Pydantic | `client.messages.parse(..., output_format=Model)`, wynik w `response.parsed_output` | [✔] | Z23 |
| Ograniczenia schematu | `additionalProperties` musi być `false`; brak `minimum`/`maximum`, `minLength`/`maxLength`, schematów rekurencyjnych; `minItems` tylko 0 lub 1; nieobsługiwana cecha zwraca błąd 400 | [✔] | Z23 |
| Cytowania | Blok `document` z `"citations": {"enabled": True}`. Odpowiedź to bloki tekstu z listą `citations` (`cited_text`, `document_index`, `start_char_index`, `end_char_index`) | [✔] | Z24 |
| Cytowania i wyjście strukturalne naraz | Nie da się: API zwraca błąd 400. Dokumentacja zaleca prośbę o jedną linię na pole (`pole: wartość`) i parsowanie we własnym kodzie, z kontrolą, czy każde pole ma wartość i cytat | [✔] | Z24 |
| Cache promptu | Najprościej jedno pole `cache_control={"type": "ephemeral"}` na najwyższym poziomie żądania (automatyczne). Można też stawiać punkty na blokach; czas życia `5m` (domyślnie) albo `1h` | [✔] / [~] | Z25 |
| Identyfikatory modeli | `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-fable-5-2` (lista modeli obsługujących wyjście strukturalne i cytowania) | [✔] | Z23, Z24 |
| Ceny za milion tokenów (wejście / wyjście) | Haiku 5.5: 0,10 / 0,50 USD dla promptów do 100 tys. tokenów, powyżej 0,50 / 2,50; Sonnet 5.5: 2 / 10; Opus 5.5: 4 / 20. Fable 5.2: 8 / 40 według README repozytorium. **Sprawdź cennik przed liczeniem budżetu** | [~] | Z26 |

Przykłady kodu w `hn-llm-w-produkcie/references/claude-api.md` są przepisane z dokumentacji z tego dnia. Nie zostały uruchomione, bo sesja nie miała klucza API, dlatego są w `references/`, a nie w `scripts/`.
