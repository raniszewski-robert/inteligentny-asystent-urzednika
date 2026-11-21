# T19 – End-to-end tests of the app

**Lane:** A – core · **Status:** done · **Estimate:** 45 min · **Blocked by:** T06, T08

**Owns:** `tests/e2e/`, `scripts/smoke.sh`

## Goal

The jury path never breaks.

## Scope

- TestClient: upload request → security findings → confirm → dispatch packet → upload filled reply form → draft (no unassigned) → anonymize → export → audit 0 → status e → archive search finds it; learning loop round-trip.
- Add to `smoke.sh`; run with `UDIP_OFFLINE=1`.

## Acceptance criteria

- [ ] `smoke.sh` green including e2e, offline.
