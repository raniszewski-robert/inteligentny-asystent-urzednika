# Rules for every lane assignment

- Do only the tickets of the phase you were given, in the listed order. Read each ticket file before starting it.
- **Waiting on another lane:** if a ticket's "Blocked by" tickets are not on `main` yet (`git fetch && git log origin/main --oneline | grep T<nn>`), build against the T00 stubs and fixtures where the ticket allows it; otherwise do the next unblocked ticket of your phase and come back after rebasing on `origin/main`. When nothing in the phase is unblocked, stop and report `blocked: T<nn> needs T<mm>`.
- Rebase on `origin/main` before each ticket.
- Interim report (same format) whenever a ticket that other lanes wait for is committed – listed as "report early" below – then continue.
- End with the report in `_report.md`.
