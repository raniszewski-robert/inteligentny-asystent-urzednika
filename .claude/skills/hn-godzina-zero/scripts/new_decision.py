#!/usr/bin/env python3
"""Tworzy plik decyzji (i porownanie) dla zadania HackNation z szablonu.

Zbiera w jednym pliku to, co pakiet prep/<slug>/ juz wie (Karta zadania, warianty
z research/06, lista skilli), i liczy czas do terminow. Reszte wypelnia zespol
z Claude'em wedlug SKILL.md.

Przyklady:
  python3 new_decision.py --slug risk_miner --tresc pelne_tresci/risk_miner.md
  python3 new_decision.py --slug risk_miner --slug prawdowid          # + porownanie.md
  python3 new_decision.py --slug nowe_zadanie --nazwa "NOWE ZADANIE"   # bez pakietu

Zaleznosci: tylko biblioteka standardowa (Python 3.9+).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")
DEADLINE_CHOICE = datetime(2026, 11, 21, 20, 0, tzinfo=TZ)
DEADLINE_SUBMIT = datetime(2026, 11, 22, 11, 0, tzinfo=TZ)
ASSETS = Path(__file__).resolve().parent.parent / "assets"

NO_PACKAGE_BLOCK = """## Z pakietu

**BRAK PAKIETU dla tego zadania.** Nie ma `prep/{slug}/`, wiec sekcje 3 pomin, a zamiast niej zrob w 45 minut:

1. Partner: kim jest, co juz ma w tym obszarze, kto bedzie uzytkownikiem (strona Partnera, 10 minut).
2. Dane: czy pelna tresc daje dane; jesli nie, jedno publiczne zrodlo, ktore da sie pobrac teraz (15 minut, sprawdz pobraniem probki).
3. Istniejace rozwiazania: dwa przyklady, zeby nie budowac kopii (10 minut).
4. Ryzyko prawne: dane osobowe, prawa do danych, regulamin zadania (10 minut).

Skille wspolne dzialaja bez pakietu: `hn-dane-od-partnera`, `hn-llm-w-produkcie`, `hn-zgloszenie`, `hn-pitch-final`.
"""


def find_prep(start: Path) -> Path | None:
    """Szuka pakietow: zmienna HN_PREP, .claude/hn-prep/ (kopia z install.sh), potem prep/ tu i wyzej."""
    env = os.getenv("HN_PREP")
    if env and Path(env).is_dir():
        return Path(env)
    for base in [start, *start.parents]:
        if (base / ".claude" / "hn-prep").is_dir():
            return base / ".claude" / "hn-prep"
        if (base / "prep").is_dir():
            return base / "prep"
    return None


def left(deadline: datetime, now: datetime) -> str:
    delta = deadline - now
    if delta.total_seconds() <= 0:
        return "termin minal"
    minutes = int(delta.total_seconds() // 60)
    days, rem = divmod(minutes, 1440)
    hours, mins = divmod(rem, 60)
    return f"{days} d {hours} h {mins:02d} min" if days else f"{hours} h {mins:02d} min"


def section(text: str, pattern: str, max_lines: int = 60) -> str:
    """Zwraca tresc sekcji, ktorej naglowek pasuje do wzorca (do nastepnego naglowka tego samego lub wyzszego poziomu)."""
    lines = text.splitlines()
    out: list[str] = []
    level = None
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if level is None:
            if m and re.search(pattern, m.group(2), re.I):
                level = len(m.group(1))
            continue
        if m and len(m.group(1)) <= level:
            break
        out.append(line)
    body = "\n".join(out).strip()
    body_lines = body.splitlines()
    if len(body_lines) > max_lines:
        body = "\n".join(body_lines[:max_lines]) + "\n[... skrocono, reszta w pliku pakietu]"
    return body


def skill_list(skills_dir: Path) -> list[str]:
    rows = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^description:\s*(.+)$", text, re.M)
        desc = (m.group(1).strip().strip("\"'") if m else "")[:160]
        rows.append(f"- `{skill_md.parent.name}`: {desc}")
    return rows


def package_block(prep: Path | None, slug: str) -> tuple[str, str]:
    """Zwraca (stan pakietu w jednym zdaniu, blok markdown z wyciagiem z pakietu)."""
    pkg = prep / slug if prep else None
    if not pkg or not pkg.is_dir():
        return "**BRAK** (tryb bez pakietu)", NO_PACKAGE_BLOCK.format(slug=slug)

    parts = [f"## Z pakietu `{pkg}`", "",
             "Wyciag wygenerowany automatycznie. To zalozenia sprzed publikacji pelnej tresci; pelna tresc ma pierwszenstwo."]
    missing = []

    readme = pkg / "README.md"
    karta = section(readme.read_text(encoding="utf-8", errors="replace"), r"karta zadania") if readme.is_file() else ""
    if karta:
        parts += ["", "### Karta zadania", "", karta]
    else:
        missing.append("Karta zadania w README.md")

    variants_files = sorted((pkg / "research").glob("06*.md")) if (pkg / "research").is_dir() else []
    if variants_files:
        text = variants_files[0].read_text(encoding="utf-8", errors="replace")
        heads = [m.group(2).strip() for m in re.finditer(r"^(#{1,6})\s+(.*)$", text, re.M)
                 if re.search(r"\bwariant\b", m.group(2), re.I)]
        parts += ["", f"### Warianty z `research/{variants_files[0].name}`", ""]
        parts += [f"- {h}" for h in heads] or ["- (nie znaleziono naglowkow ze slowem 'wariant'; przeczytaj plik)"]
        rec = section(text, r"rekomendac", max_lines=15)
        if rec:
            parts += ["", "Rekomendacja pakietu:", "", rec]
    else:
        missing.append("research/06 z wariantami")

    skills_dir = pkg / ".claude" / "skills"
    installed = not skills_dir.is_dir() and pkg.parent.name == "hn-prep"
    if installed:  # kopia z install.sh: skille zadan leza w .claude/skills/ obok hn-*
        skills_dir = pkg.parent.parent / "skills"
    skills = skill_list(skills_dir) if skills_dir.is_dir() else []
    if installed:
        skills = [s for s in skills if not s.startswith("- `hn-")]
    if skills:
        title = "### Skille zadan zainstalowane w .claude/skills/" if installed else "### Skille pakietu"
        parts += ["", title, "", *skills]
    else:
        missing.append("skille w .claude/skills/")

    samples = pkg / "data-samples"
    if samples.is_dir():
        files = [p for p in samples.rglob("*") if p.is_file()]
        size_mb = sum(p.stat().st_size for p in files) / 1e6
        parts += ["", f"### Probki danych", "", f"{len(files)} plikow, {size_mb:.1f} MB w `prep/{slug}/data-samples/`."]

    if missing:
        parts += ["", "**Brakuje w pakiecie:** " + "; ".join(missing) + ". Uwzglednij to w ocenie gotowosci."]
        state = "jest, niekompletny (" + "; ".join(missing) + ")"
    else:
        state = f"jest (`{pkg}`)"
    return state, "\n".join(parts) + "\n"


def write(path: Path, content: str, force: bool) -> bool:
    if path.exists() and not force:
        print(f"POMINIETO  {path} juz istnieje (uzyj --force, zeby nadpisac)")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"ZAPISANO   {path}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", action="append", required=True, help="slug zadania (powtorz 2-3 razy, zeby dostac tez porownanie.md)")
    ap.add_argument("--nazwa", action="append", default=[], help="nazwa zadania do naglowka (w kolejnosci slugow)")
    ap.add_argument("--tresc", action="append", default=[], help="plik z pelna trescia (w kolejnosci slugow); domyslnie pelne_tresci/<slug>.md")
    ap.add_argument("--prep", help="katalog z pakietami: prep/ repozytorium przygotowawczego albo .claude/hn-prep/ (domyslnie: HN_PREP, potem szukany tu i wyzej)")
    ap.add_argument("--out", default="godzina-zero", help="katalog wyjsciowy (domyslnie ./godzina-zero)")
    ap.add_argument("--now", help="czas w formacie ISO, do testow (domyslnie teraz, Europe/Warsaw)")
    ap.add_argument("--force", action="store_true", help="nadpisz istniejace pliki")
    args = ap.parse_args()

    if len(args.slug) > 3:
        print("BLAD: porownuj najwyzej 3 zadania; zespol moze wybrac najwyzej dwa.", file=sys.stderr)
        return 2

    if args.now:
        parsed = datetime.fromisoformat(args.now)
        now = parsed.astimezone(TZ) if parsed.tzinfo else parsed.replace(tzinfo=TZ)
    else:
        now = datetime.now(TZ)
    if args.prep and not Path(args.prep).is_dir():
        print(f"BLAD: --prep {args.prep} nie istnieje. Podaj katalog prep/ repozytorium przygotowawczego albo .claude/hn-prep/.", file=sys.stderr)
        return 2
    prep = Path(args.prep) if args.prep else find_prep(Path.cwd())
    if prep is None:
        print("UWAGA: nie znaleziono pakietow (.claude/hn-prep/ ani prep/). Podaj --prep <sciezka do prep/> albo uruchom install.sh;"
              " bez tego wszystkie zadania pojda trybem bez pakietu.")
    else:
        print(f"Pakiety: {prep}")
    out = Path(args.out)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    template = (ASSETS / "decyzja-szablon.md").read_text(encoding="utf-8")

    blocks = []
    for i, slug in enumerate(args.slug):
        name = args.nazwa[i] if i < len(args.nazwa) else slug
        tresc = Path(args.tresc[i]) if i < len(args.tresc) else Path("pelne_tresci") / f"{slug}.md"
        tresc_note = str(tresc) if tresc.is_file() else f"{tresc} (BRAK PLIKU: zapisz tam pelna tresc i kryteria)"
        state, block = package_block(prep, slug)
        blocks.append(block)
        content = (template.replace("{{ZADANIE}}", name).replace("{{TERAZ}}", stamp)
                   .replace("{{DO_20}}", left(DEADLINE_CHOICE, now)).replace("{{DO_11}}", left(DEADLINE_SUBMIT, now))
                   .replace("{{PLIK_TRESCI}}", tresc_note).replace("{{STAN_PAKIETU}}", state)
                   .replace("{{Z_PAKIETU}}", block))
        write(out / f"decyzja_{slug}.md", content, args.force)

    if len(args.slug) >= 2:
        names = [args.nazwa[i] if i < len(args.nazwa) else s for i, s in enumerate(args.slug)]
        cmp_t = (ASSETS / "porownanie-szablon.md").read_text(encoding="utf-8")
        n = len(names)
        content = (cmp_t.replace("{{ZADANIA}}", ", ".join(names)).replace("{{TERAZ}}", stamp)
                   .replace("{{DO_20}}", left(DEADLINE_CHOICE, now))
                   .replace("{{KOLUMNY}}", " | ".join(names)).replace("{{SEPARATORY}}", "|".join(["---"] * n))
                   .replace("{{PUSTE}}", " | ".join([""] * n))
                   .replace("{{Z_PAKIETOW}}", "Szczegoly kazdego zadania: " + ", ".join(f"`decyzja_{s}.md`" for s in args.slug) + "."))
        write(out / "porownanie.md", content, args.force)

    print(f"Czas: do wyboru zadania {left(DEADLINE_CHOICE, now)}, do zgloszenia {left(DEADLINE_SUBMIT, now)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
