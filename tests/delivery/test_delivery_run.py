"""T09: run.sh starts the app from a fresh copy of the repo layout; Windows scripts pass static checks.

run.sh is exercised for real in a temporary repo (stub app, stub seed, CRLF .env as written by Windows editors).
setup.ps1 / run.ps1 cannot run here (no PowerShell), so they get checks for the mistakes that break them on
Windows PowerShell 5.1: missing BOM with Polish text, PowerShell 7-only syntax, a BOM in .env, touching the API key.
"""
from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = None if sys.platform == "win32" else shutil.which("bash")

STUB_APP = '''from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os
app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def index():
    return "<h1>Kalendarz</h1>" + os.environ.get("UDIP_DATA_DIR", "")
'''

STUB_SEED = '''import os, pathlib, sys
d = pathlib.Path(os.environ["UDIP_DATA_DIR"])
with open(d / "seed_runs.txt", "a") as f:          # one line per run: the arguments run.sh passed
    f.write(" ".join(sys.argv[1:]) + "\\n")
(d / "udip.sqlite").touch()
'''


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _get(url: str) -> str:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(url, timeout=2).read().decode("utf-8")


@pytest.fixture
def fake_repo(tmp_path):
    root = tmp_path / "repo z spacja"          # Windows paths often have spaces; bash must cope too
    (root / "app").mkdir(parents=True)
    (root / "scripts").mkdir()
    shutil.copy(REPO / "run.sh", root / "run.sh")
    shutil.copy(REPO / "requirements.txt", root / "requirements.txt")
    (root / "app" / "__init__.py").write_text("")
    (root / "app" / "main.py").write_text(STUB_APP)
    (root / "scripts" / "seed.py").write_text(STUB_SEED)
    venv = Path(sys.prefix)                    # the shared venv that runs the tests
    # CRLF line endings, quotes and a relative data dir: what setup.ps1 or Notepad leave behind
    (root / ".env").write_bytes(
        f'# komentarz\r\nUDIP_VENV="{venv}"\r\nUDIP_DATA_DIR=dane\r\nUDIP_TODAY=2026-11-22\r\nANTHROPIC_API_KEY=\r\n'.encode()
    )
    return root


def _env() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("UDIP_")}
    env["UDIP_NO_BROWSER"] = "1"
    return env


def _run_until_up(root: Path, *args: str) -> tuple[str, str]:
    port = _free_port()
    p = subprocess.Popen([BASH, str(root / "run.sh"), "--port", str(port), *args], cwd="/",
                         env=_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    try:
        body = ""
        for _ in range(80):
            if p.poll() is not None:
                break
            try:
                body = _get(f"http://127.0.0.1:{port}/")
                break
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.25)
    finally:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGINT)
        out = p.communicate(timeout=15)[0]
    return body, out


@pytest.mark.skipif(not BASH, reason="bash not available")
def test_run_sh_starts_app_and_seeds_once(fake_repo):
    data = fake_repo / "dane"
    runs = lambda: (data / "seed_runs.txt").read_text().splitlines()  # noqa: E731
    body, out = _run_until_up(fake_repo)
    assert "Kalendarz" in body, out
    assert str(data) in body, "UDIP_DATA_DIR from .env must be resolved against the repo and exported"
    assert runs() == ["--demo-today 2026-11-22"], "demo dates around UDIP_TODAY from .env"
    assert (data / ".seeded").is_file()

    body, out = _run_until_up(fake_repo)
    assert "Kalendarz" in body, out
    assert len(runs()) == 1, "seed must not rerun on every start"

    (data / "udip.sqlite").unlink()                   # database deleted: seed again
    body, out = _run_until_up(fake_repo, "--real-dates")
    assert "Kalendarz" in body, out
    assert runs()[-1] == ""

    body, out = _run_until_up(fake_repo, "--reseed")
    assert "Kalendarz" in body, out
    assert runs()[-1] == "--demo-today 2026-11-22 --reset"


@pytest.mark.skipif(not BASH, reason="bash not available")
def test_run_sh_without_app_says_so(fake_repo):
    shutil.rmtree(fake_repo / "app")
    r = subprocess.run([BASH, str(fake_repo / "run.sh")], env=_env(), capture_output=True, text=True, timeout=30)
    assert r.returncode == 1
    assert "app/main.py" in r.stderr


@pytest.mark.skipif(not BASH, reason="bash not available")
def test_run_sh_refuses_busy_port(fake_repo):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    try:
        port = s.getsockname()[1]
        r = subprocess.run([BASH, str(fake_repo / "run.sh"), "--port", str(port)], env=_env(),
                           capture_output=True, text=True, timeout=30)
    finally:
        s.close()
    assert r.returncode == 1
    assert f"port {port}" in r.stderr


def test_shell_script_has_lf_only():
    assert b"\r" not in (REPO / "run.sh").read_bytes()


# --- Windows scripts: static checks -------------------------------------------------------------

PS_FILES = ["setup.ps1", "run.ps1"]


@pytest.mark.parametrize("name", PS_FILES)
def test_ps1_has_bom_when_not_ascii(name):
    # Windows PowerShell 5.1 reads a BOM-less script in the ANSI code page: Polish letters turn to garbage
    raw = (REPO / name).read_bytes()
    if any(b > 127 for b in raw):
        assert raw.startswith(b"\xef\xbb\xbf"), f"{name}: save as UTF-8 with BOM"


@pytest.mark.parametrize("name", PS_FILES)
def test_ps1_avoids_powershell7_only_syntax(name):
    code = "\n".join(
        line for line in (REPO / name).read_text(encoding="utf-8-sig").splitlines()
        if not line.lstrip().startswith("#")
    )
    code = re.sub(r"'[^'\n]*'", "''", code)        # ignore literal strings
    code = re.sub(r'"[^"\n]*"', '""', code)
    for token in ("??", "?.", "&&", "||", "-Parallel", "ConvertFrom-Json -AsHashtable"):
        assert token not in code, f"{name}: '{token}' needs PowerShell 7; the laptop runs 5.1"


def test_setup_ps1_env_handling():
    src = (REPO / "setup.ps1").read_text(encoding="utf-8-sig")
    for key in ("UDIP_ENV_FILE", "UDIP_VENV", "UDIP_DATA_DIR", "LLM_BUDGET_USD", "UDIP_PROVIDER"):
        assert key in src
    for key in ("PIP_CACHE_DIR", "TEMP", "TMP"):
        assert f"$env:{key}" in src
    # .env must be written without BOM (udip/config.py reads it as plain utf-8) and only appended to
    assert "UTF8Encoding($false)" in src
    assert "Set-Content" not in src and "Out-File" not in src
    # the API key line is never written or printed
    assert not re.search(r"ANTHROPIC_API_KEY\s*=", src)
    assert "winget install" in src and "Python.Python" in src and "Git.Git" in src


def test_run_ps1_contract():
    src = (REPO / "run.ps1").read_text(encoding="utf-8-sig")
    assert "app.main:app" in src and "127.0.0.1" in src and "8000" in src
    assert "seed.py" in src and "TESSERACT_CMD" in src
