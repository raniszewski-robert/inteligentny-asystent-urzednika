#!/usr/bin/env python3
"""Kontrola repozytorium przed zgloszeniem: README dla jurora, sekrety, licencje zaleznosci, git, linki.

  python3 preflight.py /sciezka/do/repo
  python3 preflight.py . --decision godzina-zero/decyzja_risk_miner.md   # kryteria z pliku decyzji w README?
  python3 preflight.py . --check-links --history                        # + linki z README, + historia gita
  python3 preflight.py . --only secrets                                 # jedna kontrola: readme|secrets|licenses|git

Kod wyjscia: 0 = brak blokerow, 1 = sa blokery (BLOKER), 2 = blad uruchomienia.
Zaleznosci: tylko biblioteka standardowa (Python 3.11+ dla pyproject.toml). Uzywa git i opcjonalnie gh.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

BLOCK, WARN, OK = "BLOKER", "UWAGA", "OK"
findings: list[tuple[str, str, str]] = []


def add(level: str, area: str, msg: str) -> None:
    findings.append((level, area, msg))


def git(repo: Path, *args: str) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def tracked_files(repo: Path) -> list[Path]:
    code, out = git(repo, "ls-files", "--cached", "--others", "--exclude-standard")
    if code != 0:
        return [p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts]
    return [repo / line for line in out.splitlines() if line and (repo / line).is_file()]


# ------------------------------------------------------------------ README

README_CHECKS = [
    ("co to jest (pierwszy akapit)", None),
    ("dla kogo", r"(?i)dla kogo|użytkownik|uzytkownik|odbiorc|urzędnik|urzednik|obywatel"),
    ("uruchomienie z poleceniem w bloku kodu", r"(?is)(uruchom|instalac|start|jak odpalić|quick ?start).{0,400}```"),
    ("link do demo lub wideo", r"(?i)(demo|wideo|video|nagranie)[^\n]{0,120}https?://|https?://\S*(youtu|vimeo|loom|drive\.google|streamable)"),
    ("mapowanie na kryteria", r"(?i)kryteri"),
    ("ujawnienie materiałów sprzed wydarzenia i narzędzi AI", r"(?i)(przygotowan\w* (przed|wcześniej|wczesniej)|ujawni|narzędzi\w* AI|narzedzi\w* AI|Claude|LLM|sztuczn\w* inteligencj)"),
    ("licencja", r"(?i)licencj|license"),
]


def check_readme(repo: Path, decision: Path | None) -> None:
    readmes = [p for p in repo.iterdir() if p.is_file() and p.name.lower() in ("readme.md", "readme.rst", "readme.txt", "readme")]
    if not readmes:
        add(BLOCK, "README", "brak README w katalogu glownym repozytorium; juror zaczyna wlasnie od niego")
        return
    text = readmes[0].read_text(encoding="utf-8", errors="replace")
    words = len(re.findall(r"\w+", text))
    body = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith(("#", "!", "[", "<", "|", ">"))]
    for name, pattern in README_CHECKS:
        if pattern is None:
            ok = bool(body) and len(body[0]) >= 40
        else:
            ok = re.search(pattern, text) is not None
        add(OK if ok else (BLOCK if name.startswith(("uruchomienie", "link do demo")) else WARN), "README", ("jest: " if ok else "brak: ") + name)
    if words > 1500:
        add(WARN, "README", f"README ma {words} slow; juror ma kilka minut. Przenies szczegoly do docs/")
    placeholders = re.findall(r"\{\{[^}]*\}\}", text)
    if placeholders:
        add(BLOCK, "README", f"{len(placeholders)} niewypelnionych pol szablonu, np. {placeholders[0][:40]}; juror zobaczy szablon")
    if re.search(r"(?i)\b(TODO|TBD|lorem ipsum)\b|\[uzupe", text):
        add(WARN, "README", "README zawiera TODO, TBD albo [UZUPELNIJ]")
    for target in re.findall(r"\]\((?!https?://|mailto:|#)([^)\s]+)\)", text):
        if not (repo / target.split("#")[0]).exists():
            add(WARN, "README", f"lokalny link albo obraz {target} nie istnieje w repozytorium")
    if re.search(r"(?i)localhost:\d+", text) and not re.search(r"https?://(?!localhost)\S+", text):
        add(WARN, "README", "jedyne linki prowadza do localhost; juror ich nie otworzy")
    if decision and not decision.is_file():
        add(WARN, "README", f"nie ma pliku decyzji {decision}; kryteria nie zostaly sprawdzone")
    if decision and decision.is_file():
        crit = []
        lines = decision.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            if re.match(r"^\|\s*Kryterium\s*\|", ln):
                for row in lines[i + 2:]:
                    if not row.startswith("|"):
                        break
                    name = row.strip("|").split("|")[0].strip()
                    if name:
                        crit.append(name)
                break
        low = text.lower()
        missing = [c for c in crit if c.lower() not in low]
        if crit:
            add(WARN if missing else OK, "README", f"kryteria z pliku decyzji obecne w README: {len(crit) - len(missing)}/{len(crit)}" + (f"; brak: {missing}" if missing else ""))


# ------------------------------------------------------------------ sekrety

SECRET_PATTERNS = {
    "klucz Anthropic": r"sk-ant-[A-Za-z0-9_\-]{20,}",
    "klucz OpenAI": r"sk-(?!ant-)(?:proj-)?[A-Za-z0-9_\-]{32,}",
    "token GitHub": r"(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{30,}",
    "token Hugging Face": r"hf_[A-Za-z0-9]{30,}",
    "klucz AWS": r"AKIA[0-9A-Z]{16}",
    "klucz Google API": r"AIza[0-9A-Za-z_\-]{35}",
    "token Slack": r"xox[baprs]-[A-Za-z0-9\-]{10,}",
    "klucz prywatny": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----",
    "haslo w URL": r"[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s:/@]{4,}@[\w.-]+",
    "przypisanie sekretu": r"(?i)\b[\w-]*(?:api[_-]?key|secret|token|passw(?:or)?d|haslo)\b[ \t]*[:=][ \t]*[\"']?(?![ \t]*$)(?!<|\$\{|os\.|process\.env|getenv|your|xxx|change|placeholder|test-not)[A-Za-z0-9_\-./+=]{12,}",
}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".parquet", ".pkl", ".joblib", ".bin", ".gguf", ".onnx", ".pt", ".ico", ".woff", ".woff2", ".lock"}


def scan_text(text: str) -> list[tuple[str, int, str]]:
    """Zwraca (rodzaj, linia, skrot). Jedna linia = jedno trafienie; wzorce szczegolowe maja pierwszenstwo."""
    hits, seen_lines = [], set()
    for name, pattern in SECRET_PATTERNS.items():
        for m in re.finditer(pattern, text):
            line = text.count("\n", 0, m.start()) + 1
            if line in seen_lines:
                continue
            seen_lines.add(line)
            val = m.group(0)
            hits.append((name, line, val[:6] + "..." + val[-3:] if len(val) > 12 else "***"))
    return hits


def check_secrets(repo: Path, history: bool) -> None:
    found = 0
    for f in tracked_files(repo):
        if f.suffix.lower() in SKIP_EXT or f.stat().st_size > 2_000_000:
            continue
        rel = f.relative_to(repo)
        if rel.name == ".env.example":
            for name, line, _ in scan_text(f.read_text(encoding="utf-8", errors="replace")):
                add(BLOCK, "sekrety", f"{rel}:{line}: {name} w .env.example; zostaw tylko nazwy zmiennych")
                found += 1
            continue
        for name, line, preview in scan_text(f.read_text(encoding="utf-8", errors="replace")):
            add(BLOCK, "sekrety", f"{rel}:{line}: {name} ({preview})")
            found += 1
    code, out = git(repo, "ls-files")
    if code == 0:
        envs = [ln for ln in out.splitlines() if re.search(r"(^|/)\.env(\.[\w-]+)?$", ln) and not ln.endswith((".example", ".sample", ".template"))]
        for e in envs:
            add(BLOCK, "sekrety", f"plik {e} jest w repozytorium; usun go (git rm --cached) i dodaj do .gitignore")
            found += 1
        code_ig, _ = git(repo, "check-ignore", "-q", ".env")
        if code_ig != 0:
            add(WARN, "sekrety", ".env nie jest w .gitignore")
    if history and code == 0:
        _, log = git(repo, "log", "-p", "--all", "--no-color", "-U0")
        hist = {(n, p) for n, _, p in scan_text(log)}
        if hist:
            add(WARN, "sekrety", f"w historii gita sa {len(hist)} podejrzane wartosci (np. {sorted(hist)[0][0]}). Usuniecie pliku nie wystarczy: "
                "jesli to prawdziwy klucz, uniewaznij go u dostawcy. Po uniewaznieniu ta uwaga moze zostac")
            found += len(hist)
    if not found:
        add(OK, "sekrety", "nie znaleziono kluczy, tokenow ani hasel" + (" (z historia gita)" if history else ""))


# ------------------------------------------------------------------ licencje

STRONG = re.compile(r"(?i)\bA?GPL\b(?!.*lesser)|GNU (?:Affero )?General Public|\bSSPL|\bEUPL|\bOSL-|CC-BY-SA|Commons Clause|BUSL|Business Source")
NONCOMM = re.compile(r"(?i)CC-BY-NC|non-?commercial|niekomerc")
WEAK = re.compile(r"(?i)\bLGPL|Lesser General|Library General|\bMPL|Mozilla Public|\bEPL|Eclipse Public|\bCDDL")
PERMISSIVE = re.compile(r"(?i)\bMIT\b|BSD|Apache|ISC|PSF|Python Software|Unlicense|CC0|0BSD|Zlib|BlueOak|HPND|MIT-CMU|WTFPL")


def classify(lic: str) -> str:
    if not lic.strip() or lic.strip().upper() in ("UNKNOWN", "NONE"):
        return "nieznana"
    if NONCOMM.search(lic):
        return "niekomercyjna"
    if WEAK.search(lic):
        return "slaby copyleft"
    if STRONG.search(lic):
        return "silny copyleft"
    if PERMISSIVE.search(lic):
        return "permisywna"
    return "nieznana"


def py_license(dist) -> str:
    md = dist.metadata
    expr = md.get("License-Expression")
    if expr:
        return expr
    cls = [c.split("::")[-1].strip() for c in (md.get_all("Classifier") or []) if c.startswith("License ::") and c.count("::") >= 2]
    raw = (md.get("License") or "").strip()
    if raw and len(raw) < 80 and "\n" not in raw:
        return raw + (f" [{cls[0]}]" if cls else "")
    return "; ".join(cls) or raw[:60]


def py_requirements(repo: Path) -> list[str]:
    names: list[str] = []
    for req in list(repo.glob("requirements*.txt")) + list(repo.glob("*/requirements*.txt")):
        for ln in req.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.split("#")[0].strip()
            if ln and not ln.startswith(("-", "git+", "http")):
                names.append(re.split(r"[<>=!~;\[ ]", ln)[0])
    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        import tomllib
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        deps = list(data.get("project", {}).get("dependencies", []))
        for group in data.get("project", {}).get("optional-dependencies", {}).values():
            deps += group
        deps += list(data.get("tool", {}).get("poetry", {}).get("dependencies", {}).keys())
        names += [re.split(r"[<>=!~;\[ ]", d)[0] for d in deps if d.lower() != "python"]
    return sorted({n for n in names if n})


def py_closure(names: list[str]) -> dict[str, tuple[str, str]]:
    """Zaleznosci bezposrednie i przechodnie z zainstalowanego srodowiska: nazwa -> (wersja, licencja)."""
    import importlib.metadata as md

    norm = lambda s: re.sub(r"[-_.]+", "-", s).lower()  # noqa: E731
    out, todo, missing = {}, [norm(n) for n in names], []
    while todo:
        n = todo.pop()
        if n in out:
            continue
        try:
            d = md.distribution(n)
        except md.PackageNotFoundError:
            missing.append(n)
            out[n] = ("?", "NIEZAINSTALOWANA")
            continue
        out[n] = (d.version, py_license(d))
        for r in d.requires or []:
            if "extra ==" in r:
                continue
            todo.append(norm(re.split(r"[<>=!~;\[ (]", r)[0]))
    return out


def npm_licenses(repo: Path) -> dict[str, tuple[str, str]]:
    out = {}
    nm = repo / "node_modules"
    if nm.is_dir():
        for pj in nm.glob("**/package.json"):
            rel = pj.relative_to(nm).parts
            if len(rel) not in (2, 3) or (len(rel) == 3 and not rel[0].startswith("@")) or "node_modules" in rel[:-1]:
                continue
            try:
                d = json.loads(pj.read_text(encoding="utf-8"))
            except Exception:
                continue
            lic = d.get("license") or ", ".join(x.get("type", "") if isinstance(x, dict) else str(x) for x in d.get("licenses", []))
            if isinstance(lic, dict):
                lic = lic.get("type", "")
            if d.get("name"):
                out[d["name"]] = (d.get("version", "?"), str(lic))
    lock = repo / "package-lock.json"
    if not out and lock.is_file():
        d = json.loads(lock.read_text(encoding="utf-8"))
        for path, info in d.get("packages", {}).items():
            if path.startswith("node_modules/"):
                out[path.split("node_modules/")[-1]] = (info.get("version", "?"), str(info.get("license", "")))
    if not out and (repo / "package.json").is_file():
        add(WARN, "licencje", "jest package.json, ale brak node_modules i package-lock.json: uruchom npm install i powtorz")
    return out


def check_licenses(repo: Path) -> None:
    report = []
    names = py_requirements(repo)
    py = py_closure(names) if names else {}
    not_installed = [n for n, (_, lic) in py.items() if lic == "NIEZAINSTALOWANA"]
    if names and len(not_installed) >= max(1, len(py) // 2):
        add(WARN, "licencje", f"{len(not_installed)} zaleznosci nie jest zainstalowanych w tym Pythonie ({sys.executable}); "
            "uruchom preflight pythonem z aktywnego srodowiska projektu (.venv/bin/python)")
    npm = npm_licenses(repo)
    if not py and not npm:
        add(WARN, "licencje", "nie znaleziono requirements*.txt, pyproject.toml ani package.json")
        return
    for eco, deps in (("python", py), ("npm", npm)):
        for name, (ver, lic) in sorted(deps.items()):
            cat = "nieznana" if lic == "NIEZAINSTALOWANA" else classify(lic)
            report.append((eco, name, ver, lic, cat))
    counts: dict[str, int] = {}
    for *_, cat in report:
        counts[cat] = counts.get(cat, 0) + 1
    add(OK, "licencje", f"zaleznosci: python {len(py)} (z przechodnimi), npm {len(npm)}; " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    for eco, name, ver, lic, cat in report:
        if cat in ("silny copyleft", "niekomercyjna"):
            add(BLOCK, "licencje", f"{eco} {name} {ver}: {lic} ({cat}). Jesli Partner przejmuje prawa albo rozwiazanie ma byc zamkniete, zamien zaleznosc albo ustal to z Partnerem i opisz w README")
        elif cat == "slaby copyleft":
            add(WARN, "licencje", f"{eco} {name} {ver}: {lic} ({cat}). Zwykle dopuszczalne jako niemodyfikowana zaleznosc; wymien w README")
        elif cat == "nieznana":
            add(WARN, "licencje", f"{eco} {name} {ver}: licencja nieznana ('{lic[:40]}'); sprawdz recznie")
    out = repo / "LICENSES-THIRD-PARTY.md"
    lines = ["# Licencje zaleznosci", "", "Wygenerowane przez preflight.py.", "", "| Ekosystem | Paczka | Wersja | Licencja | Kategoria |", "|---|---|---|---|---|"]
    lines += [f"| {e} | {n} | {v} | {lic.replace('|', '/')} | {c} |" for e, n, v, lic, c in report]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    add(OK, "licencje", f"zapisano {out.name} ({len(report)} pozycji); dolacz do repozytorium")


# ------------------------------------------------------------------ git i linki

def check_git(repo: Path) -> None:
    code, _ = git(repo, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        add(BLOCK, "git", "to nie jest repozytorium git")
        return
    n_before = sum(1 for f in findings if f[1] == "git")
    _, status = git(repo, "status", "--porcelain")
    if status:
        add(WARN, "git", f"niezacommitowane zmiany: {len(status.splitlines())} plikow; juror zobaczy tylko to, co wypchniete")
    code_r, remote = git(repo, "remote", "get-url", "origin")
    if code_r != 0:
        add(BLOCK, "git", "brak zdalnego repozytorium origin; juror nie ma czego otworzyc")
        return
    code_a, ahead = git(repo, "rev-list", "--count", "@{u}..HEAD")
    if code_a != 0:
        add(WARN, "git", "galaz nie sledzi zdalnej (git push -u origin <galaz>)")
    elif ahead.strip() != "0":
        add(BLOCK, "git", f"{ahead.strip()} commitow niewypchnietych (git push)")
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", remote)
    if m:
        p = subprocess.run(["gh", "repo", "view", m.group(1), "--json", "visibility", "-q", ".visibility"], capture_output=True, text=True)
        vis = p.stdout.strip()
        if p.returncode == 0 and vis:
            add(OK if vis == "PUBLIC" else BLOCK, "git", f"widocznosc repozytorium: {vis}" + ("" if vis == "PUBLIC" else "; juror bez dostepu zobaczy 404"))
        else:
            add(WARN, "git", f"nie sprawdzono widocznosci {m.group(1)}; otworz repozytorium w oknie incognito")
    big = [f for f in tracked_files(repo) if f.stat().st_size > 50_000_000]
    for f in big:
        add(BLOCK if f.stat().st_size > 100_000_000 else WARN, "git", f"duzy plik {f.relative_to(repo)} ({f.stat().st_size / 1e6:.0f} MB); GitHub odrzuca pliki powyzej 100 MB")
    if not any(f[1] == "git" and f[0] != OK for f in findings[n_before:]):
        add(OK, "git", "wszystko zacommitowane i wypchniete")


def check_links(repo: Path, allow_local: bool = False) -> None:
    readme = next((p for p in repo.iterdir() if p.name.lower() == "readme.md"), None)
    if not readme:
        return
    urls = sorted(set(re.findall(r"https?://[^\s)\]>\"'`]+", readme.read_text(encoding="utf-8", errors="replace"))))
    for url in urls:
        url = url.rstrip(".,;")
        if re.search(r"localhost|127\.0\.0\.1", url) and not allow_local:
            add(WARN, "linki", f"{url}: adres lokalny, juror go nie otworzy")
            continue
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0 preflight"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                add(OK, "linki", f"{resp.status} {url}")
        except urllib.error.HTTPError as exc:
            add(BLOCK if exc.code in (404, 410) else WARN, "linki", f"{exc.code} {url}" + (" (prywatne albo usuniete?)" if exc.code in (401, 403, 404) else ""))
        except Exception as exc:
            add(WARN, "linki", f"nie sprawdzono {url}: {type(exc).__name__}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--decision", help="plik decyzji z hn-godzina-zero (tabela kryteriow)")
    ap.add_argument("--check-links", action="store_true", help="otworz kazdy link z README (wymaga internetu)")
    ap.add_argument("--history", action="store_true", help="szukaj sekretow takze w historii gita")
    ap.add_argument("--only", choices=["readme", "secrets", "licenses", "git", "links"])
    ap.add_argument("--allow-localhost", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"BLAD: nie ma katalogu {repo}", file=sys.stderr)
        return 2
    steps = {"readme": lambda: check_readme(repo, Path(args.decision) if args.decision else None),
             "secrets": lambda: check_secrets(repo, args.history), "git": lambda: check_git(repo),
             "licenses": lambda: check_licenses(repo), "links": lambda: check_links(repo, args.allow_localhost)}
    for name, fn in steps.items():
        if args.only and name != args.only:
            continue
        if name == "links" and not (args.check_links or args.only == "links"):
            continue
        fn()
    order = {BLOCK: 0, WARN: 1, OK: 2}
    for level, area, msg in sorted(findings, key=lambda x: (order[x[0]], x[1])):
        print(f"{level:<7} [{area}] {msg}")
    blockers = sum(1 for f in findings if f[0] == BLOCK)
    warns = sum(1 for f in findings if f[0] == WARN)
    print(f"\nPodsumowanie: {blockers} blokerow, {warns} uwag. " + ("Napraw blokery przed wyslaniem zgloszenia." if blockers else "Mozna wysylac; przejrzyj uwagi."))
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
