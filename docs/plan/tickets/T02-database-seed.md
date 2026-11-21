# T02 – SQLite schema + seed from UMB data

**Lane:** A – core · **Status:** done · **Estimate:** 1 h · **Blocked by:** T01

**Owns:** `udip/db.py`, `scripts/seed.py`

## Goal

Persistent cases, history, documents, drafts, dispatches, learned rules and security events.

## Scope

- Schema exactly as CONTRACTS §4 (incl. `department_dispatches`, `learned_pii_rules`, `routing_feedback`, `security_events`, `office_days_off`, `legal_chunks`, `llm_cache` optional) and the helper functions listed there.
- `scripts/seed.py`: import `kalendarium_umb.xlsx` (with `--archive`), archive from `archiwum_umb.jsonl`, statutory holidays into `office_days_off`, optional `--demo-today` and `--with-synthetic`.
- DB path from `UDIP_DATA_DIR`.

## Acceptance criteria

- [ ] Fresh seed: 10 UMB cases, 10 archive cases, holidays 2025–2027.
- [ ] Re-seed idempotent.
- [ ] Tests for status history and learned rules round-trip.
