# T16 – Bielik-4.5B offline: benchmark row and live mode

**Lane:** C – LLM & eval · **Status:** done · **Estimate:** background · **Blocked by:** T10

**Owns:** `scripts/bielik_server.sh`, `docs/eval/bielik.md`

## Goal

Real local-model numbers; live offline LLM mode if the demo laptop can run it.

## Scope

- Sandbox (needs HF allowlist) or Windows with Ollama (`OLLAMA_MODELS` on D:): Bielik-4.5B-v3.0-Instruct Q4_K_M; measure tokens/s; run T15 subset.
- Deck model for a city GPU server: Bielik-11B-v3.1-Instruct (Apache-2.0, verified on Ollama 21.11).
- If neither is possible: `docs/eval/bielik.md` says „nie zmierzono”, with exact commands.

## Acceptance criteria

- [ ] Bielik row or explicit „nie zmierzono”.
- [ ] If installed on the laptop: offline Bielik mode completes a case.
