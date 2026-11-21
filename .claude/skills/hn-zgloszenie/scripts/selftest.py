#!/usr/bin/env python3
"""Test preflight.py na dwoch tymczasowych repozytoriach: zle przygotowanym i gotowym do zgloszenia.

Falszywe klucze sa skladane w czasie testu, zeby w plikach pakietu nie bylo niczego, co wyglada na klucz.
  python3 selftest.py
Kod wyjscia 0 = wszystkie testy przeszly. Zaleznosci: biblioteka standardowa, git.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
results = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append(cond)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def sh(cwd: Path, *cmd: str) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def init_repo(path: Path, remote: Path) -> None:
    path.mkdir(parents=True)
    sh(path, "git", "init", "-q", "-b", "main")
    sh(path, "git", "config", "user.email", "test@example.com")
    sh(path, "git", "config", "user.name", "Test")
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    sh(path, "git", "remote", "add", "origin", str(remote))


def preflight(repo: Path, *extra: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(HERE / "preflight.py"), str(repo), *extra], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="hn-pre-"))
    fake_ant = "sk-" + "ant-" + "api03-" + "A1b2C3d4" * 5
    fake_gh = "gh" + "p_" + "Z9y8X7w6" * 5

    # ---------------- repozytorium zle przygotowane
    bad = tmp / "zle"
    init_repo(bad, tmp / "zle.git")
    (bad / "README.md").write_text("# Projekt\n\nTODO opis\n\nUruchom lokalnie: http://localhost:8000\n", encoding="utf-8")
    (bad / ".env").write_text(f"ANTHROPIC_API_KEY={fake_ant}\n", encoding="utf-8")
    (bad / "config.py").write_text(f'GITHUB = "{fake_gh}"\nDB = "postgres://admin:' + "Super" + "Tajne1" + '@db.example.com/x"\n', encoding="utf-8")
    (bad / "requirements.txt").write_text("python-apt\nimg2pdf\n", encoding="utf-8")
    nm = bad / "node_modules"
    for name, lic in (("left-pad", "WTFPL"), ("gpl-lib", "GPL-3.0-only"), ("@scope/nc-lib", "CC-BY-NC-4.0"), ("no-license", "")):
        d = nm / name
        d.mkdir(parents=True)
        (d / "package.json").write_text(json.dumps({"name": name, "version": "1.0.0", "license": lic}), encoding="utf-8")
    (bad / "package.json").write_text('{"name": "front"}', encoding="utf-8")
    (bad / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    sh(bad, "git", "add", "-A")
    sh(bad, "git", "commit", "-qm", "init")
    (bad / "config.py").write_text("GITHUB = None\n", encoding="utf-8")       # klucz usuniety, ale zostaje w historii
    sh(bad, "git", "commit", "-qam", "usun klucz")

    code, out = preflight(bad, "--history")
    print("----- preflight na zlym repozytorium -----")
    print(out)
    check("zle repo: kod wyjscia 1", code == 1)
    check("wykryto klucz Anthropic w .env, bez duplikatu jako OpenAI", "klucz Anthropic" in out and "klucz OpenAI" not in out)
    check("wykryto .env w repozytorium", "plik .env jest w repozytorium" in out)
    check("wykryto haslo w URL", "haslo w URL" in out)
    check("wykryto klucz w historii gita (uwaga)", "UWAGA   [sekrety] w historii gita" in out)
    check("README: brak polecenia uruchomienia i linku do demo (blokery)", "BLOKER  [README] brak: uruchomienie" in out and "BLOKER  [README] brak: link do demo" in out)
    check("README: TODO i tylko localhost", "TODO" in out and "localhost" in out)
    check("licencje: GPL z python-apt i npm jako bloker", "python python-apt" in out and "npm gpl-lib" in out)
    check("licencje: CC-BY-NC jako niekomercyjna", "@scope/nc-lib" in out and "niekomercyjna" in out)
    check("licencje: LGPL jako slaby copyleft", "img2pdf" in out and "slaby copyleft" in out)
    check("licencje: pusta licencja npm jako nieznana", "no-license" in out and "nieznana" in out)
    check("git: niewypchniete commity albo brak sledzenia", "commitow niewypchnietych" in out or "nie sledzi" in out)
    check("zapisano LICENSES-THIRD-PARTY.md", (bad / "LICENSES-THIRD-PARTY.md").is_file())

    # ---------------- repozytorium gotowe
    good = tmp / "dobre"
    init_repo(good, tmp / "dobre.git")
    srv = HTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(good)))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    readme = (ASSETS / "README-szablon.md").read_text(encoding="utf-8")
    readme = readme.replace("{{DEMO_URL}}", f"http://127.0.0.1:{port}/demo.html").replace("{{REPO_URL}}", f"http://127.0.0.1:{port}/README.md")
    readme = readme.replace("{{Kryterium 1}}", "Użyteczność dla Partnera").replace("{{Kryterium 2}}", "Jakość techniczna")
    readme = readme.replace("## Wyniki", "| Innowacyjność | 30% | tryb offline | wideo 1:30 |\n\n## Wyniki", 1)
    readme_template_only = readme
    readme = re.sub(r"\{\{[^}]*\}\}", "wypelnione", readme)
    (good / "docs").mkdir()
    (good / "docs" / "screenshot.png").write_bytes(b"png")
    (good / "README.md").write_text(readme, encoding="utf-8")
    (good / "demo.html").write_text("<p>demo</p>", encoding="utf-8")
    (good / ".gitignore").write_text(".env\n.venv/\ndata/\n", encoding="utf-8")
    (good / ".env.example").write_text("ANTHROPIC_API_KEY=\nLLM_MODE=replay\n", encoding="utf-8")
    (good / ".env").write_text(f"ANTHROPIC_API_KEY={fake_ant}\n", encoding="utf-8")   # lokalny, ignorowany
    (good / "requirements.txt").write_text("requests\n", encoding="utf-8")
    (good / "app.py").write_text('import os\nKEY = os.getenv("ANTHROPIC_API_KEY")\n', encoding="utf-8")
    decision = tmp / "decyzja.md"
    decision.write_text("| Kryterium | Waga | Funkcja |\n|---|---|---|\n| Użyteczność dla Partnera | 40% | x |\n| Jakość techniczna | 30% | y |\n| Innowacyjność | 30% | z |\n", encoding="utf-8")
    sh(good, "git", "add", "-A")
    sh(good, "git", "commit", "-qm", "init")
    sh(good, "git", "push", "-q", "-u", "origin", "main")

    code, out = preflight(good, "--history", "--decision", str(decision), "--check-links", "--allow-localhost")
    print("----- preflight na gotowym repozytorium -----")
    print(out)
    check("dobre repo: kod wyjscia 0", code == 0)
    check("lokalny .env (ignorowany) nie jest zgloszony", "klucz Anthropic" not in out)
    check("README z szablonu przechodzi wszystkie kontrole", out.count("OK      [README] jest:") == 7)
    check("git: OK, gdy wszystko wypchniete", "OK      [git] wszystko zacommitowane i wypchniete" in out)
    check("LICENSES-THIRD-PARTY.md nie psuje kontroli git", "niezacommitowane" not in out)
    check("kryteria z pliku decyzji obecne w README", "kryteria z pliku decyzji obecne w README: 3/3" in out)
    check("linki z README dzialaja", "200 http://127.0.0.1" in out)
    check("licencje: requests z przechodnimi, certifi MPL jako uwaga", "certifi" in out and "slaby copyleft" in out)
    check("brak sekretow, takze w historii", "nie znaleziono kluczy" in out)
    # README prosto z szablonu: pola {{...}} to bloker
    (good / "README.md").write_text(readme_template_only, encoding="utf-8")
    code, out = preflight(good, "--only", "readme", "--decision", str(tmp / "literowka.md"))
    check("szablon bez wypelnienia: bloker {{...}}", code == 1 and "niewypelnionych pol szablonu" in out)
    check("bledna sciezka --decision: uwaga", "nie ma pliku decyzji" in out)
    srv.shutdown()

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nWynik: {sum(results)} PASS, {len(results) - sum(results)} FAIL.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
