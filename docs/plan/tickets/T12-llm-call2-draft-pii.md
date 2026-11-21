# T12 – Call 2: draft_and_semantic_pii

**Lane:** C – LLM & eval · **Status:** dropped: team decision 21.11 21:40 – local Bielik only, no cloud API · **Estimate:** 1.5 h · **Blocked by:** T10, T01, T24

**Owns:** `udip/llm_tasks/draft_pii.py`

## Goal

One cached call that maps reply sentences to Ad by index and proposes semantic PII, never rewriting facts.

## Scope

- Input: letter type, numbered questions [Q1..Qm], numbered reply sentences [S1..Sk] (from T24 tier 2), legal hits. Output JSON: `{ad_map: {"1": ["S1","S2"], …, "unassigned": ["S5"]}, connective_text: {...}, semantic_pii: [{text, category}]}`.
- Paragraphs are assembled from the original sentences (numbers never retyped); any model-written connective text passes the number check; semantic PII returns only as `review`.

## Acceptance criteria

- [ ] 543 raw replies: Ad placement matches BKS's real letter.
- [ ] Mock bad provider rejected; omitted numbers reported.
