# T13 – Handwriting transcription (Claude Vision, cloud demo only)

**Lane:** C – LLM & eval · **Status:** dropped: team decision 21.11 21:40 – local Bielik only, no cloud API · **Estimate:** 45 min · **Blocked by:** T10

**Owns:** `udip/llm_tasks/vision.py`

## Goal

Turn the handwritten UMB scan into an editable transcript in cloud mode.

## Scope

- `transcribe(page_pngs) -> {text, confidence_note}` via Claude Vision, cached; refuses in offline modes.
- For the deck: name an offline VLM for the target server only after verifying its licence on the model card (candidate Qwen2.5-VL-7B-Instruct).

## Acceptance criteria

- [ ] 16.2026 scan → transcript containing the alcohol-outlets question.
- [ ] Offline mode returns None.
