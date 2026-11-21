# Coordinator runbook

How the coordinator runs the plan end to end, from the repository root (on Windows: the clone on D:), until the project is ready or the 09:30 freeze.

---

The **coordinator** does T00, assigns the lanes, merges their work, keeps `main` green and finishes with a ready repository. Report to the team at the three checkpoints and at the end.

**Read first:** `CLAUDE.md`, `docs/plan/PLAN.md`, `docs/plan/CONTRACTS.md`, and the lane briefs in `docs/plan/lanes/`. The plan's decisions are settled; carry them out.

**Deadline:** Sunday 22.11.2026, code freeze 09:30 Europe/Warsaw, submission 11:00.

## 1. Preflight

Check the environment, then write a short preflight report.

- OS. **On Windows:** everything lives on the repo's drive (D:). Set in `.env`: `UDIP_VENV=<repo>\.venv`, `UDIP_DATA_DIR=<repo>\var`, `PIP_CACHE_DIR=<repo>\var\pip-cache`, `TEMP`/`TMP=<repo>\var\tmp`. Nothing new goes on C:.
- Python ≥ 3.11 and Git present; create the shared venv at `UDIP_VENV` and install `requirements.txt` + `fastapi uvicorn jinja2 python-multipart httpx anthropic python-pptx Pillow` (append each to `requirements.txt` with its licence).
- `.env` at the repo root with `ANTHROPIC_API_KEY` (optional; lanes that don't need it continue without it). Add `UDIP_ENV_FILE=<absolute path of this .env>`, `LLM_BUDGET_USD=15`, `UDIP_PROVIDER=rules` for now. Never print the key.
- Reachability: `api.anthropic.com`, `huggingface.co` (T16), `dane.gov.pl` (T28). Tesseract present or not (optional).
- `bash scripts/smoke.sh` is green on `main`.

Done when the report lists each item as ok / missing-with-consequence.

## 2. T00 (before any lane starts)

Do `docs/plan/tickets/T00-contracts.md` exactly: stub `udip/` modules delegating to the existing scripts, LLM hook points, `udip/llm.py` stub, fixtures, `UDIP_ENV_FILE` loading. Done when its acceptance criteria hold, smoke is green, and the work is committed and pushed to `main`.

## 3. Assign and merge loop

Each **phase** runs on its own branch and worktree. Every lane: reads `CLAUDE.md`, its lane brief `docs/plan/lanes/<X>.md` (only the given phase), `docs/plan/CONTRACTS.md` and each ticket file before starting it; works only on its owned paths; commits on its branch without merging or pushing; finishes every ticket of the phase with `bash scripts/smoke.sh` green; ends with the report in `docs/plan/lanes/_report.md`.

A phase starts when everything it waits for is merged on `main`; inside a phase, tickets that wait on other lanes follow `docs/plan/lanes/_rules.md`:

| Phase | Tickets | Starts after |
|---|---|---|
| A1 | T01 → T02 → T24 → T28 | T00 |
| E1 | T27 → T26 → T25 | T00 |
| B1 | T03 → T04 → T05 → T06 → T17 | T00 |
| C1 | T10 → T16 (bg) → T11 → T12 → T13 → T14 → T15 | T00 |
| D1 | T09 → T29 → T21 draft | T00 |
| B2a | T07 → T08 | T03 merged (B1 reports early after T03) |
| B2b | T23 → T18 | T11, T12, T13, T17 merged |
| A2 | T19 | T06 and T08 merged |
| D2 | T21 final → T22 | T15 and T18 merged |

Lanes send interim reports after tickets other lanes wait for; merge those immediately so dependants can rebase. When a lane reports `blocked`, restart the rest of its phase once the blocker is merged.

On every report:

1. Read it. A `blocked`, `red` or contract request is resolved now: change `CONTRACTS.md` in a small commit on `main` (and the stub it describes), or answer the lane with the decision. A red smoke or unmet criterion goes back to the same lane with the failing output; it fixes it on its branch.
2. Merge the branch into `main` in lane order A → E → B1 → B2 → C → D when several are ready. Resolve conflicts in favour of the owning lane (CONTRACTS §1). Run `bash scripts/smoke.sh` on the merged `main`; if red, revert the merge and send the failure to the lane.
3. Push `main` (one push at a time; on HTTP 429 wait 5 s and retry once). Update the ticket table in `PLAN.md`.
4. Start every phase whose start condition is now met.
5. Check the LLM spend in `$UDIP_DATA_DIR/llm_usage.json`; above $12, lane C stops non-essential calls.

At most six lanes run at once.

## 4. Checkpoints (report, then continue)

A five-line status for the team – what works, what's next, anything only they can do:

1. **T05 and T09 merged:** "Kalendarz and Nowy wniosek work. On Windows run `setup.ps1` then `run.ps1` and open http://127.0.0.1:8000."
2. **T06 and T08 merged:** the full path works offline with rules: dispatch packet → reply form → draft → verified export (name the demo assets to try it with).
3. **T15 and T21 final merged:** eval table, deck and video script ready for review (paths).

## 5. Time guard

- **From 06:30:** no new features; finish open tickets or drop them in the order listed in `PLAN.md` ("If time runs short"). Record each drop on its ticket.
- **09:00:** no new phases. Merge what is green, then final `bash scripts/smoke.sh`, tag `v1.0`, push.
- **09:30:** freeze. Only README fixes after this.

## 6. Finish

Done when every ticket in `PLAN.md` is `done` or `dropped: <reason>`, `main` is pushed, smoke is green, and the app starts with `run.ps1` / `run.sh` from a fresh clone. Final report (≤ 20 lines): what works with the command to run it, eval headline numbers, LLM spend, what was dropped and why.
