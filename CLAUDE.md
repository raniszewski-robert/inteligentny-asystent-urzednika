# Asystent UDIP (UMB): contributor rules

App for Bydgoszcz City Hall clerks handling public-information requests: calendar, archive search, department routing, letter drafts, anonymization. Python 3.11+, FastAPI, SQLite, Jinja2 + htmx.

## Where things are

- Interfaces between modules: `docs/plan/CONTRACTS.md` – read it before changing code that other modules call.
- Domain facts (law, deadlines, UMB process): `research/` and `.claude/skills/udip-wiedza-domenowa/`. Real partner data: `data-partner/umb/` (read-only).

## Rules

- **Green before done.** A change is done when `bash scripts/smoke.sh` is green. Add a test for each new behaviour.
- **Small commits** with a short message saying what changed.
- **Secrets stay in `.env`.** Read the key via `udip.llm` only; keep it out of code, logs and commits.
- **LLM calls go through `udip.llm`**, which caches and enforces the budget (`LLM_BUDGET_USD`).
- **Polish in the UI and in letters**, plain official tone. After a template change run `python3 .claude/skills/unslop-ui/scripts/count_tells.py --surface <files>` and apply the rules in `.claude/skills/unslop-ui/SKILL.md`.
- **Licences:** MIT, BSD or Apache-2.0 only (the city takes over copyright). Append new packages to `requirements.txt` with a licence comment.
- **Windows host:** keep everything on the repo's drive (D:). Use the venv and data dir named in `.env` (`UDIP_VENV`, `UDIP_DATA_DIR`).
