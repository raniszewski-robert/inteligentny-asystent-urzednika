# Orchestrator prompt

Paste everything below the line into one Claude Code session opened in the repository root (on Windows: the clone on D:). It runs the whole plan with subagents and stops when the project is submitted-ready or at the 09:30 freeze.

---

You are the **coordinator** of a hackathon build. You run it end to end in this session: you do T00 yourself, dispatch subagents for the lanes, merge their work, keep `main` green, and finish with a submission-ready repository. The team is not watching; report at the three checkpoints and at the end, and keep working in between. Ask the human only when blocked on something only they can give (an API key, a decision that can't be undone).

**Read first:** `CLAUDE.md`, `docs/plan/PLAN.md`, `docs/plan/CONTRACTS.md`, and the lane briefs in `docs/plan/lanes/`. The plan's decisions are settled; carry them out.

**Deadline:** Sunday 22.11.2026, code freeze 09:30 Europe/Warsaw, submission 11:00. Check the clock (`date`) whenever a dispatch returns.

## 1. Preflight

Detect and fix the environment, then print a short preflight report.

- OS. **On Windows:** everything lives on the repo's drive (D:). Set in `.env` and in the session: `UDIP_VENV=<repo>\.venv`, `UDIP_DATA_DIR=<repo>\var`, `PIP_CACHE_DIR=<repo>\var\pip-cache`, `TEMP`/`TMP=<repo>\var\tmp`. Nothing new goes on C:.
- Python ≥ 3.11 and Git present; create the shared venv at `UDIP_VENV` and install `requirements.txt` + `fastapi uvicorn jinja2 python-multipart httpx anthropic python-pptx Pillow` (append each to `requirements.txt` with its licence).
- `.env` at the repo root with `ANTHROPIC_API_KEY` (if missing, look for `_dla_claude/.env` in the UMB materials folder the human named; if still missing, ask the human once and continue with lanes that don't need it). Add `UDIP_ENV_FILE=<absolute path of this .env>`, `LLM_BUDGET_USD=15`, `UDIP_PROVIDER=rules` for now. Never print the key.
- Reachability: `api.anthropic.com` (needed), `huggingface.co` (T16), `dane.gov.pl` (T28). Look for name lists the team downloaded into the UMB materials folder (`_dla_claude/`). Tesseract present or not (optional).
- `bash scripts/smoke.sh` is green on `main`.

Done when the report lists each item as ok / missing-with-consequence.

## 2. T00 (you, before any dispatch)

Do `docs/plan/tickets/T00-contracts.md` exactly: stub `udip/` modules delegating to today's skill scripts, LLM hook points, `udip/llm.py` stub, fixtures, `UDIP_ENV_FILE` loading. Done when its acceptance criteria hold, smoke is green, and the work is committed and pushed to `main`.

## 3. Dispatch and merge loop

Dispatch each **phase** as a background subagent with worktree isolation (`isolation: "worktree"`). Prompt for every dispatch, filled in:

> You are lane `<X>`, phase `<P>`, in the HackNation UDIP project. Read `CLAUDE.md`, then `docs/plan/lanes/<X>.md` (do only phase `<P>`), then `docs/plan/CONTRACTS.md` and each ticket file before you start it. Shared settings: read `UDIP_ENV_FILE=<abs path>`; use the venv at `<UDIP_VENV>`. Work only on your owned paths, commit on your worktree branch, do not merge or push. Finish every ticket of the phase to its acceptance criteria with `bash scripts/smoke.sh` green, then end with the report in `docs/plan/lanes/_report.md`. Current `main` head: `<sha>`.

Dispatch rules (a phase starts when everything it waits for is merged on `main`; inside a phase the agent handles tickets that wait on other lanes per `docs/plan/lanes/_rules.md`):

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

Agents send interim reports after tickets other lanes wait for; merge those immediately so dependants can rebase. When an agent reports `blocked`, re-dispatch the rest of its phase once the blocker is merged.

On every report:

1. Read it. A `blocked`, `red` or contract request is yours to resolve now: change `CONTRACTS.md` yourself in a small commit on `main` (and the stub it describes), or answer the lane via SendMessage with the decision. A red smoke or unmet criterion goes back to the same agent via SendMessage with the failing output; it fixes it on its branch.
2. Merge the branch into `main` in lane order A → E → B1 → B2 → C → D when several are ready. Resolve conflicts in favour of the owning lane (CONTRACTS §1). Run `bash scripts/smoke.sh` on the merged `main`; if red, revert the merge and send the failure to the lane.
3. Push `main` (one push at a time; on HTTP 429 wait 5 s and retry once). Update the ticket table in `PLAN.md`.
4. Dispatch every phase whose start condition is now met.
5. Check the LLM spend in `$UDIP_DATA_DIR/llm_usage.json`; above $12, tell lane C to stop non-essential calls (keep T15's Sonnet row).

Keep at most six subagents running at once. If a subagent stops without a report or loops on the same failure twice, dispatch a fresh one for the remaining tickets of that phase with the previous agent's branch as the starting point.

## 4. Checkpoints (report, then continue)

Print a five-line status for the human – what works, what's next, anything only they can do:

1. **T05 and T09 merged:** "Kalendarz and Nowy wniosek work. On Windows run `setup.ps1` then `run.ps1` and open http://127.0.0.1:8000." Set `UDIP_PROVIDER=anthropic:sonnet` in `.env` once T10 is merged and the key works.
2. **T06 and T08 merged:** the full jury path works offline with rules: dispatch packet → reply form → draft → verified export (name the demo assets to try it with).
3. **T15 and T21 final merged:** eval table, deck and video script ready for review (paths).

## 5. Time guard

- **From 06:30:** no new features; finish open tickets or drop them in the order listed in `PLAN.md` ("If time runs short"). Record each drop on its ticket.
- **09:00:** stop dispatching. Merge what is green, then final `bash scripts/smoke.sh`, `python3 .claude/skills/hn-zgloszenie/scripts/preflight.py .`, tag `v1.0`, push.
- **09:30:** freeze. Only README fixes after this.

## 6. Finish

You are done when every ticket in `PLAN.md` is `done` or `dropped: <reason>`, `main` is pushed, smoke is green, preflight shows 0 blockers, and the app starts with `run.ps1` / `run.sh` from a fresh clone. Then write the final report for the human (≤ 20 lines): what works with the command to run it, eval headline numbers, LLM spend, what was dropped and why, and what the human must still do before 11:00 (record the video from `docs/video_script.md`, make the repo public, submit in HackTribe).
