# T01 – Move the core into a `udip/` package

**Lane:** A – core · **Status:** done · **Estimate:** 45 min · **Blocked by:** T00

**Owns:** `udip/*` core modules, `udip/data/`, skill script wrappers, `tests/core/`

## Goal

One importable source of truth for the app; skills keep working.

## Scope

- Move the code behind the T00 stubs into real modules: deadlines, register, importer (xlsx), ingest, textpl, search, analyze, anonymize, draft, letters; data files under `udip/data/`.
- Skill scripts become thin CLI wrappers (same flags). Keep the T00 hook points unchanged.

## Acceptance criteria

- [ ] `bash scripts/smoke.sh` green (11/11 acceptance).
- [ ] No logic duplicated between `udip/` and `.claude/skills/*/scripts`.
