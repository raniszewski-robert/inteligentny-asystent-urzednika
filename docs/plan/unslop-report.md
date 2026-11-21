# unslop-ui audit (T18), 21.11.2026

Scope: every template in `app/templates/` plus `app/static/app.css` and `app/static/b2.css`, run with `--surface`.
Counter: `python3 .claude/skills/unslop-ui/scripts/count_tells.py --surface app/templates app/static/app.css app/static/b2.css`.

| Stage | Counter total | Notes |
|---|---|---|
| Before (no taste file) | 0 | Screens were written with unslop passes per ticket (T03–T08, T17) |
| After (with `.unslop-ui/taste.md`) | 1 | The single hit is T3 in `base.html:13`, the office name in the header, kept on purpose (below) |

## Reading pass (rules the counter cannot see)

| File | Rule | Before | After |
|---|---|---|---|
| `wniosek_nowy.html` | U5 design note | "Analiza: reguły i model (…). Wydziały i podobne sprawy liczą reguły; model dodał streszczenie i uzasadnienia." | "Analiza: reguły i model (…)." |
| `ustawienia.html` | U3/U5 long intro | Three-clause intro listing every model use | One sentence: rules always work offline; the model proposes, rules check, the clerk approves |
| `ustawienia.html` | U4 narration | "Wyniki modelu są oznaczone na ekranach sprawy, projektu i anonimizacji." | deleted |
| `archiwum.html` | U4 narration | "Wynik poniżej uwzględnia nowe sprawy." | deleted |

## Kept on purpose

| Where | Rule | Why |
|---|---|---|
| `base.html` header "Urząd Miasta Bydgoszczy · Biuro Komunikacji Społecznej" | U6/T3 | Fixed by the plan; it is the office's name, not a status chain |
| `anonimizacja.html` "Serwer zapisuje tylko odczytany tekst i decyzje. Plik źródłowy jest usuwany zaraz po odczycie." | U5 | A data-protection fact the clerk needs before uploading personal data |
| `anonimizacja.html` "Po zmianie treści asystent wykryje fragmenty od nowa i zachowa podjęte decyzje." | U5 | Tells the clerk an edit does not lose decisions; without it the edit box looks risky |
| `projekt.html` "Notatki dla urzędnika (nie trafiają do pisma):" | U5 parenthetical | Prevents the notes from being mistaken for letter text |
| Model badges (`badge-analiza`, `badge-llm`) | U9 | Render only from result fields (`analysis.llm_used`, `report.mode_used`, `report.llm_rejected`, span `source == "llm"`), tested in `tests/app/test_b2_t23.py` |
| `ustawienia.html` "Dane UMB trafiają do zewnętrznego API tylko po wybraniu modelu Anthropic…" | U5 | Data-flow fact relevant to the 20 % security criterion |
