# Bielik-4.5B-v3.0-Instruct lokalnie przez Ollama

Pomiar z 2026-11-21 na laptopie (Windows, Ollama, `SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0`, 5,4 GB, 59% CPU / 41% GPU, kontekst `num_ctx=8192`). Kolumna „Bielik 4.5B” jest wpisana do `docs/eval/RESULTS.md` oraz `docs/eval/chart.png` (szczegóły: `docs/eval/results/openai_compat_bielik.json`).

`udip/llm.py` obsługuje dostawcę `openai_compat:<model>` (Ollama przez natywne `/api/chat` z `num_ctx=8192` i gramatyką JSON, pozostałe serwery przez `/v1/chat/completions`) z tym samym schematem JSON, walidacją i pamięcią podręczną co pozostali dostawcy (koszt $0). Ewaluacja: `scripts/eval_llm.py --provider openai_compat:bielik --limit 20`.

Licencja modelu: według karty modelu SpeakLeash – Apache-2.0.

## Windows (komputer Urzędu, wszystko na D:)

```powershell
# 1. Ollama (MIT): https://ollama.com/download – instalator, potem w nowym oknie PowerShell:
setx OLLAMA_MODELS "D:\ollama\models"          # modele na D:, nie na C:
# zamknij i otwórz PowerShell ponownie, żeby zmienna zadziałała; uruchom ponownie aplikację Ollama
ollama pull SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0     # ok. 4,8 GB; Q4_K_M jest mniejszy i szybszy
ollama run --verbose SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0 "Napisz jedno zdanie o Bydgoszczy."
#    ostatnie linie: "eval rate: … tokens/s" – szybkość generowania

# 2. W pliku .env (ten wskazany przez UDIP_ENV_FILE):
#    LLM_BASE_URL=http://localhost:11434/v1
#    LLM_MODEL=SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0
#    LLM_TIMEOUT=600

# 3. Ewaluacja (venv z UDIP_VENV, katalog repozytorium):
python scripts\eval_llm.py --provider openai_compat:bielik --limit 20
python scripts\eval_llm.py --report            # dopisuje kolumnę Bielik do docs\eval\RESULTS.md i wykres
```

Aby aplikacja używała Bielika: `UDIP_PROVIDER=openai_compat:bielik` w `.env` (wymaga działającej Ollamy;
gdy serwer nie odpowiada, każde wywołanie wraca do reguł).

## Linux

```bash
# Ollama, jeśli jest zainstalowana; w przeciwnym razie GGUF z Hugging Face + llama-cpp-python (MIT) na porcie 8104:
export UDIP_DATA_DIR=/ścieżka/do/var            # tam trafi models/*.gguf
BIELIK_QUANT=Q4_K_M bash scripts/bielik_server.sh --eval
# skrypt wypisze tokeny/s, ustawienia LLM_BASE_URL/LLM_MODEL i uruchomi ewaluację na 20 pozycjach
```

Ręcznie (bez skryptu):

```bash
mkdir -p "$UDIP_DATA_DIR/models"
curl -fL -o "$UDIP_DATA_DIR/models/Bielik-4.5B-v3.0-Instruct.Q4_K_M.gguf" \
  https://huggingface.co/speakleash/Bielik-4.5B-v3.0-Instruct-GGUF/resolve/main/Bielik-4.5B-v3.0-Instruct.Q4_K_M.gguf
pip install "llama-cpp-python[server]"
python -m llama_cpp.server --model "$UDIP_DATA_DIR/models/Bielik-4.5B-v3.0-Instruct.Q4_K_M.gguf" \
  --host 127.0.0.1 --port 8104 --n_ctx 8192 --model_alias bielik &
LLM_BASE_URL=http://127.0.0.1:8104/v1 LLM_MODEL=bielik LLM_TIMEOUT=600 \
  python scripts/eval_llm.py --provider openai_compat:bielik --limit 20 && python scripts/eval_llm.py --report
```

Nazwy pliku GGUF i tagu Ollamy sprawdź na stronie repozytorium `speakleash/Bielik-4.5B-v3.0-Instruct-GGUF`, jeśli
pobieranie zwróci 404 (wydawca bywa, że zmienia nazwy kwantyzacji).

## Wyniki (2026-11-21)

| Miara | Wartość |
|---|---|
| Sprzęt (CPU, RAM, GPU) | Intel Core i5-10300H @ 2.50 GHz, 15.8 GB RAM, NVIDIA GTX 1650 Ti (Ollama: 59% CPU / 41% GPU, `num_ctx=8192`) |
| Kwantyzacja | `SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0` (5.4 GB) |
| Tokeny/s (generowanie / prompt) | 7.27 tok/s / 13.73 tok/s (`ollama run --verbose`) |
| Czas na wniosek (analiza + routing + projekt) | 165.6 s (średnio na 10 sprawach UMB; ponowne wywołania z pamięci podręcznej: 0 s) |
| Liczba pytań / Wydział top-1 / Ad n (543) | 60% / 56% / 83% (5/6, `llm`, 0 błędnych i 0 pominiętych liczb) |
| Anonimizacja (20 dok., 64 złote spany) | recall 100%, precyzja 67%, 0 wycieków, 0 spanów zaakceptowanych domyślnie |
| Wstrzyknięcie poleceń (`injection_pl.txt`) | schemat zachowany, brak wycieku kanarka (28.1 s) |
| Koszt | $0.00 (62 wywołania, 1 błąd schematu → fallback do reguł) |
| Pozostałe miary | kolumna „Bielik 4.5B” w `docs/eval/RESULTS.md` i `docs/eval/chart.png` |
