# T10 – LLM client: modes, offline enforcement, cache, budget

**Lane:** C – LLM & eval · **Status:** done · **Estimate:** 1 h · **Blocked by:** T00

**Owns:** `udip/llm.py`, `tests/llm/`

## Goal

Safe, cheap, swappable LLM access with an honest offline mode.

## Scope

- Providers: `anthropic:sonnet` (Sonnet 5.5), `openai_compat:bielik` (Ollama/llama.cpp at `LLM_BASE_URL`), `rules`. Model IDs from the installed SDK/docs.
- `mode()` for the pill; `UDIP_OFFLINE=1` → refuse any non-localhost connection (raise, caller falls back).
- Disk cache (SQLite `llm_cache` or files) keyed by provider+model+prompt hash; usage and $ in `llm_usage.json`; hard `LLM_BUDGET_USD`.
- All untrusted text via `security.sanitize_for_llm` and inside `<untrusted_citizen_request>`/`<untrusted_department_reply>` tags; JSON schema validation with one retry, then `None`.

## Acceptance criteria

- [ ] Repeat call costs $0.
- [ ] Budget stop → fallback.
- [ ] Injection fixture cannot change the output schema.
- [ ] Offline flag blocks api.anthropic.com in a test.
