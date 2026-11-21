# T23 – Wire LLM modes into the UI

**Lane:** B2 – UI: letters & redaction · **Status:** done · **Estimate:** 1 h · **Blocked by:** T08, T11, T12, T13

**Owns:** `app/routes/ustawienia.py`, `app/templates/ustawienia.html`, LLM elements in screen templates

## Goal

Show the three modes honestly; rules always visible as fallback.

## Scope

- Ustawienia: mode select Offline – reguły / Offline – lokalny Bielik / Cloud demo – Claude; usage and budget; Bielik server status (fallback message if not running).
- Mode pill: offline modes say „połączenia zewnętrzne zablokowane” (true because `UDIP_OFFLINE` blocks the client), cloud says „Claude Sonnet · cache”.
- Screens use Call 1 / Call 2 results when available (summary, routing reasons, Ad mapping, semantic PII as review).
- unslop-ui pass.

## Acceptance criteria

- [ ] Offline mode: complete case with Wi-Fi off, no errors or timeouts.
- [ ] Cloud mode: 543 draft shows the number badge; forced bad answer shows „odrzucono”.
