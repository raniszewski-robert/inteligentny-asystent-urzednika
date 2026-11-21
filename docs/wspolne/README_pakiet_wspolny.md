# Pakiet wspólny HackNation 2026 (21–22.11, Bydgoszcz)

Pięć skilli `hn-*` dla Claude Code, które prowadzą zespół od publikacji zadań do finału. Działają z pakietem zadania `prep/<slug>/` i bez niego. Stan zasad: 2026-11-17, źródła w `research/`.

## Oś czasu i skille

| Kiedy | Co się dzieje | Skill |
|---|---|---|
| sob. **11:00** | Publikacja pełnych treści i kryteriów, start kodowania | `hn-godzina-zero`: decyzja „bierzemy albo nie", kryteria → funkcja → dowód, plan |
| sob. do 13:00 | Projekt w HackTribe (nazwa, zespół, repozytorium, stolik, opis), publiczne repozytorium | `hn-zgloszenie` (część sobotnia) |
| sob. 11:00–16:00 | Dane od Partnera: profil, podział, baseline, metryka | `hn-dane-od-partnera` |
| sob. i noc | Funkcje z LLM: schemat, cytaty, injection, koszt, tryb offline | `hn-llm-w-produkcie` |
| **sob. 20:00** | **Koniec wyboru zadania i zakładania projektów** (edycja do niedz. 11:00) | `hn-zgloszenie`: kontrola o 19:30 |
| niedz. 07:00–10:30 | Koniec funkcji 07:00, wideo, README, **zamrożenie kodu 09:30**, zgłoszenie gotowe 10:30 | `hn-zgloszenie`: `preflight.py`, `video_check.sh` |
| **niedz. 11:00** | **Termin zgłoszenia**, start oceny etapu 1 | — |
| niedz. 14:45 | Ogłoszenie finalistów (pięć zespołów z zadania) | `hn-pitch-final` |
| niedz. 15:15 | Pitching, etap 2 (wyniki etapu 1 nie przechodzą) | `hn-pitch-final` + `<prefix>-demo-i-pitch` z pakietu zadania |
| niedz. 17:15 | Zamknięcie, zwycięzcy | — |

## Instalacja w repozytorium rozwiązania

```bash
bash prep/_wspolne/install.sh --list                                      # dostępne pakiety zadań
bash prep/_wspolne/install.sh ../nasze-rozwiazanie <slug> [<slug2>] --gitignore
```

Kopiuje `hn-*` i skille zadań do `../nasze-rozwiazanie/.claude/skills/`, a dokumenty, na które się powołują (ten `research/`, README i `research/` pakietów), do `.claude/hn-prep/`. Najwyżej dwa zadania. Claude Code uruchamiaj potem w repozytorium rozwiązania. Skille w publicznym repozytorium to materiały sprzed wydarzenia: wymień je w sekcji „Ujawnienie" README.

## Przed wyjazdem

- [ ] Laptop demo: `bash .claude/skills/hn-dane-od-partnera/scripts/smoke_test.sh` i `python3 .claude/skills/hn-llm-w-produkcie/scripts/selftest.py` przechodzą (paczki: `references/zaleznosci.md` w `hn-dane-od-partnera`).
- [ ] ffmpeg zainstalowany (`video_check.sh`); git, `gh` zalogowany.
- [ ] Konta: GitHub, HackTribe, Discord HackNation, Hugging Face (warunki Bielika zaakceptowane), konsola API z limitem wydatków.
- [ ] Klucze API w menedżerze haseł, **nie** w repozytorium; `.env.example` gotowe.
- [ ] Model lokalny (GGUF PLLuM albo Bielik) i Ollama albo llama.cpp pobrane i sprawdzone jednym zapytaniem; Wi-Fi na sali może nie wystarczyć.
- [ ] PDF „Tutorial HackTribe PL" i regulamin pobrane z hacknation.pl.
- [ ] Adaptery USB-C/HDMI, ładowarki, przedłużacz, hotspot w telefonie, słuchawki z mikrofonem.
- [ ] Na Discordzie `#zapytaj-organizatora`: gotowy kod i narzędzia AI (czy można, jak ujawnić), limit zadań na zespół, czas pitchu, forma wideo w HackTribe.

## Różnice względem kontekstu promptu (odczyt hacknation.pl 2026-11-17)

1. Na stronie jest **12 zadań, nie 10**: doszły CYFROWY ASYSTENT OCEN OKRESOWYCH (KPRM) i #INVESTWATCH (UKNF). Strona zapowiada 15 wyzwań, więc w sobotę mogą dojść kolejne. Bez pakietu działa tryb „bez pakietu" w `hn-godzina-zero`.
2. Łączna pula nagród: **350 000 zł**.
3. Godziny finału: finaliści **14:45**, pitching **15:15**, zamknięcie **17:15**.
4. Pola projektu w HackTribe są znane (nazwa projektu i zespołu, repozytorium, numer stolika, wstępny opis). Adresu platformy strona nie podaje.
5. Próg 50% punktów do przyznania nagrody jest w regulaminie (§5.4) i regulamin zadania może go zmienić (§5.1).
6. **Limit zadań:** przewodnik mówi o najwyżej dwóch zadaniach na zespół, ogłoszenia zewnętrzne o dowolnej liczbie. Przyjmujemy przewodnik; potwierdź na Discordzie.
7. W 2025 r. do finału wchodziły trzy zespoły z zadania, w 2026 r. pięć.
8. Wysłanie rozwiązania oznacza akceptację regulaminu zadania, a nagrody są opodatkowane. Regulamin zadania czytaj przed 20:00.
9. Odpowiedzi w FAQ (m.in. o materiałach przygotowanych wcześniej) są zwinięte i nie zostały odczytane automatycznie; zasada z kontekstu wymaga potwierdzenia.

Szczegóły i źródła: `research/01_zasady_hacknation_2026.md`, wnioski z 2025 r.: `research/02_wnioski_z_2025.md`, modele i API: `research/03_llm_modele_i_api.md`.
