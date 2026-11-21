#!/usr/bin/env bash
# T16: Bielik-4.5B-v3.0-Instruct on CPU behind an OpenAI-compatible API, then the 20-item eval.
#
#   bash scripts/bielik_server.sh            # Ollama if installed, else llama-cpp-python (MIT) + GGUF from Hugging Face
#   bash scripts/bielik_server.sh --eval     # same, then: python scripts/eval_llm.py --provider openai_compat:bielik --limit 20
#
# Needs network access to huggingface.co (GGUF) or registry.ollama.ai (Ollama). Model files go to $UDIP_DATA_DIR/models
# (Ollama: $OLLAMA_MODELS) – on Windows keep both on D:. Port: $BIELIK_PORT (default 8104).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${UDIP_DATA_DIR:-$ROOT/var}"
PORT="${BIELIK_PORT:-8104}"
QUANT="${BIELIK_QUANT:-Q4_K_M}"            # Q4_K_M ≈ 2.9 GB, Q8_0 ≈ 4.8 GB
OLLAMA_TAG="${BIELIK_OLLAMA_TAG:-SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0}"
HF_REPO="speakleash/Bielik-4.5B-v3.0-Instruct-GGUF"
GGUF="Bielik-4.5B-v3.0-Instruct.${QUANT}.gguf"
RUN_EVAL=0; [[ "${1:-}" == "--eval" ]] && RUN_EVAL=1

if command -v ollama >/dev/null 2>&1; then
  echo "== Ollama: $OLLAMA_TAG (OLLAMA_MODELS=${OLLAMA_MODELS:-default})"
  pgrep -x ollama >/dev/null || (ollama serve >"$DATA/ollama.log" 2>&1 &) ; sleep 2
  ollama pull "$OLLAMA_TAG"
  BASE="http://localhost:11434/v1"; MODEL="$OLLAMA_TAG"
  echo "== tokens/s (eval rate):"; ollama run --verbose "$OLLAMA_TAG" "Napisz jedno zdanie o Bydgoszczy." 2>&1 | grep -E "eval rate|^[^ ]" | tail -4
else
  mkdir -p "$DATA/models"
  if [[ ! -f "$DATA/models/$GGUF" ]]; then
    echo "== download $HF_REPO/$GGUF"
    curl -fL --retry 3 -o "$DATA/models/$GGUF.part" "https://huggingface.co/$HF_REPO/resolve/main/$GGUF"
    mv "$DATA/models/$GGUF.part" "$DATA/models/$GGUF"
  fi
  python3 -c "import llama_cpp.server" 2>/dev/null || pip install "llama-cpp-python[server]"   # MIT
  echo "== llama-cpp-python server on :$PORT ($(nproc) threads)"
  python3 -m llama_cpp.server --model "$DATA/models/$GGUF" --host 127.0.0.1 --port "$PORT" --n_ctx 8192 --model_alias bielik \
      --n_threads "$(nproc)" >"$DATA/bielik_server.log" 2>&1 &
  for _ in $(seq 60); do curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null && break; sleep 2; done
  BASE="http://127.0.0.1:$PORT/v1"; MODEL="bielik"
  echo "== tokens/s:"
  python3 - "$BASE" <<'PY'
import json, sys, time, urllib.request
t0 = time.time()
req = urllib.request.Request(sys.argv[1] + "/chat/completions", data=json.dumps({"model": "bielik", "max_tokens": 128,
      "messages": [{"role": "user", "content": "Opisz w trzech zdaniach, czym jest informacja publiczna."}]}).encode(),
      headers={"Content-Type": "application/json"})
d = json.loads(urllib.request.urlopen(req, timeout=600).read())
n = d.get("usage", {}).get("completion_tokens", 0)
print(f"{n} tokens in {time.time() - t0:.1f} s = {n / max(1e-9, time.time() - t0):.1f} tok/s (incl. prompt)")
PY
fi

echo; echo "Ustaw w .env: LLM_BASE_URL=$BASE  LLM_MODEL=$MODEL  LLM_TIMEOUT=600"
if [[ $RUN_EVAL == 1 ]]; then
  LLM_BASE_URL="$BASE" LLM_MODEL="$MODEL" LLM_TIMEOUT=600 UDIP_LLM_TAG=T16 \
    python3 "$ROOT/scripts/eval_llm.py" --provider openai_compat:bielik --limit 20
  python3 "$ROOT/scripts/eval_llm.py" --report
fi
