# T15 – Benchmark: rules vs Bielik (offline) vs Sonnet

**Lane:** C – LLM & eval · **Status:** dropped: team decision 21.11 21:40 – local Bielik only, no cloud API · **Estimate:** 1 h · **Blocked by:** T11, T12, T14

**Owns:** `scripts/eval_llm.py`, `docs/eval/RESULTS.md`, `docs/eval/chart.png`

## Goal

One honest slide.

## Scope

- 10 real UMB cases + 5 adversarial: PII leak rate, false alarms on public data, routing top-1/top-3, Ad placement, numeric accuracy (invented/swapped/omitted), latency, cost.
- Bielik row from T16 or „nie zmierzono” with the reason.

## Acceptance criteria

- [ ] Table + chart committed; spend < $4.
