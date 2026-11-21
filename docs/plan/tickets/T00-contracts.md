# T00 – Freeze contracts and scaffold stubs

**Lane:** 0 – coordinator · **Status:** done · **Estimate:** 40 min · **Blocked by:** —

**Owns:** `docs/plan/CONTRACTS.md`, `udip/` stubs, `udip/llm*` stubs, `tests/fixtures/`

## Goal

Let five lanes start at the same time without touching each other's files.

## Scope

- Review `CONTRACTS.md` once more and freeze it.
- Create `udip/` with stub modules whose functions delegate to today's `.claude/skills/udip-*/scripts`; new modules from CONTRACTS (`security`, `dispatch`, `learning`, `export`) as stubs returning neutral defaults (empty findings, no learned rules, unchanged spans).
- Hook points written once here (CONTRACTS §2): LLM calls in `draft`/`analyze`/`anonymize`; `learning.apply_rules` in `anonymize.detect` and `learning.boost` in `analyze.route`; `export.harden_docx`/`export.audit_docx`/`export.metryczka` in `draft.write_docx`/`finalize`; `security.scan` in `ingest.read_any`. Stubs: `udip/llm.py`, `udip/llm_tasks/*` → `None`; `security`, `export`, `learning`, `dispatch` → neutral defaults.
- Offline switch: `UDIP_OFFLINE=1` makes `udip.llm` refuse any network call (stub already honours it).
- Fixtures: `tests/fixtures/analysis_599.json`, `draft_543.json`, `rows_demo.json`, `security_findings_demo.json`, `dispatch_543.json`.
- Create lane branches from `main` and push.

## Acceptance criteria

- [ ] `python -c "import udip.analyze, udip.draft, udip.register, udip.llm, udip.security, udip.dispatch, udip.learning, udip.export"` works.
- [ ] `bash scripts/smoke.sh` still green.
- [ ] Lane branches exist on the remote.
