# Asystent UDIP (UMB, HackNation 2026): rules for every agent

App for Bydgoszcz City Hall clerks handling public-information requests: calendar, archive search, department routing, letter drafts, anonymization. Python 3.11+, FastAPI, SQLite, Jinja2 + htmx.

## Where things are

- Plan and status: `docs/plan/PLAN.md`. Interfaces between lanes: `docs/plan/CONTRACTS.md` – read it before writing code that another lane calls or is called by.
- Your lane brief (if you were dispatched for one): `docs/plan/lanes/<lane>.md`, plus `docs/plan/lanes/_rules.md` for waiting on other lanes and reporting. Your tickets: `docs/plan/tickets/`.
- Domain facts (law, deadlines, UMB process): `research/` and `.claude/skills/udip-wiedza-domenowa/`. Real partner data: `data-partner/umb/` (read-only).

## Rules

- **Ownership.** Edit only the paths your lane owns (CONTRACTS §1). Need a change elsewhere? Write it in your report as a request to the coordinator.
- **Green before done.** A ticket is done when its acceptance criteria hold and `bash scripts/smoke.sh` is green on your branch. Add a test for each new behaviour.
- **Commit small, on your branch.** One commit per ticket at least, message `T<nn>: <what>`. The coordinator alone merges to `main` and pushes.
- **Status line.** When you start and finish a ticket, update only its `**Status:**` field (`in progress`, `done`, `dropped: <reason>`).
- **Secrets stay in `.env`.** Read the key via `udip.llm` only; keep it out of code, logs, commits and reports.
- **LLM spend goes through `udip.llm`**, which caches and enforces the shared budget (`LLM_BUDGET_USD`). Prefer cached runs; report spend per ticket.
- **Polish in the UI and in letters**, plain official tone. Every template change ends with an unslop-ui pass: run `python3 .claude/skills/unslop-ui/scripts/count_tells.py --surface <files>` and apply the rules in `.claude/skills/unslop-ui/SKILL.md` (the skill does not auto-trigger).
- **Licences:** MIT, BSD or Apache-2.0 only (the city takes over copyright). Append new packages to `requirements.txt` with a licence comment.
- **Windows host:** keep everything on the repo's drive (D:). Use the shared venv and data dir named in `.env` (`UDIP_VENV`, `UDIP_DATA_DIR`).
