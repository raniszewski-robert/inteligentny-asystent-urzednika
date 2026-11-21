# Lane C – LLM & evaluation

Owns: CONTRACTS §1 row C. Follow `_rules.md`. Budget: global `LLM_BUDGET_USD=15`; your share ≈ $9 (dev $2, T14 $2, T15 $4, vision $1). Cache and usage are shared across worktrees through `UDIP_DATA_DIR`; repeated runs must hit the cache. Model IDs: check the installed `anthropic` SDK / Anthropic docs, not memory.

## Phase C1 (after T00)

1. **T10** client: modes, offline enforcement, cache, budget, sanitising via `udip.security.sanitize_for_llm` (stub until T26). *Report early.*
2. **T16** in the background right away: Bielik download/server if Hugging Face is reachable (`curl -sI https://huggingface.co`) or Ollama exists; otherwise write the "nie zmierzono" note. Never block other tickets on it.
3. **T11** Call 1 analyze_and_route. *Report early.*
4. **T12** Call 2 draft_and_semantic_pii (needs T24's sentence numbering). *Report early.*
5. **T13** vision transcription (cloud demo only). *Report early.*
6. **T14** ~20 synthetic cases + 5 adversarial cases (also `tests/fixtures/pii_torture_test.docx`).
7. **T15** benchmark rules vs Bielik vs Sonnet on 10 UMB + 5 adversarial → `docs/eval/RESULTS.md` + chart.
