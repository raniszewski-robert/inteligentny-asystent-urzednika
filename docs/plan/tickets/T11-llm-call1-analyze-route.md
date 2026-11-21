# T11 – Call 1: analyze_and_route

**Lane:** C – LLM & eval · **Status:** dropped: team decision 21.11 21:40 – local Bielik only, no cloud API · **Estimate:** 1 h · **Blocked by:** T10, T01

**Owns:** `udip/llm_tasks/analyze_route.py`

## Goal

One cached call for questions, other-procedure flags, routing per question with a one-line Polish reason.

## Scope

- Input: sanitised request, department catalogue, top-3 similar archive cases. Output JSON: `questions[]`, `other_procedure_flags[]`, `routing_per_question[{question_no, department, reason}]`, `summary`.
- Rules validate (department ids exist, question count sane) and stay the fallback.

## Acceptance criteria

- [ ] 10 UMB requests: valid JSON, summary filled, routing top-1 recorded for T15.
- [ ] Fallback path tested.
