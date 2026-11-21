#!/usr/bin/env bash
# Uruchamia asystenta UDIP lokalnie (Linux, macOS, WSL): http://127.0.0.1:8000
#
#   bash run.sh                 # przy pierwszym starcie tworzy .venv i instaluje paczki
#   bash run.sh --port 8105     # inny port (albo UDIP_PORT=8105)
#   bash run.sh --no-browser    # bez otwierania przeglądarki (albo UDIP_NO_BROWSER=1)
#   bash run.sh --reseed        # sprawy z arkusza UMB od nowa, daty demo przesunięte na dziś (kasuje ich historię)
#   bash run.sh --real-dates    # przy wczytywaniu danych: prawdziwe daty z arkusza zamiast trybu demo
#
# Ustawienia: zmienne środowiskowe, potem plik .env (UDIP_ENV_FILE, domyślnie <repo>/.env), potem wartości domyślne.
# UDIP_VENV (domyślnie <repo>/.venv), UDIP_DATA_DIR (domyślnie <repo>/var), UDIP_TODAY (dzień demo, domyślnie dziś),
# UDIP_SEED_ARGS (dodatkowe argumenty seed.py, np. --with-synthetic), UDIP_APP (domyślnie app.main:app).
# Aplikacja działa bez internetu; serwer słucha tylko na 127.0.0.1.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PORT="${UDIP_PORT:-8000}"
HOST="127.0.0.1"
OPEN_BROWSER=1
[ "${UDIP_NO_BROWSER:-0}" = "1" ] && OPEN_BROWSER=0
RESEED=0
REAL_DATES=0

while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="${2:?--port wymaga numeru}"; shift 2 ;;
    --port=*) PORT="${1#--port=}"; shift ;;
    --no-browser) OPEN_BROWSER=0; shift ;;
    --reseed) RESEED=1; shift ;;
    --real-dates) REAL_DATES=1; shift ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Nieznana opcja: $1 (zobacz: bash run.sh --help)" >&2; exit 2 ;;
  esac
done

fail() { echo "BŁĄD: $*" >&2; exit 1; }

ENV_FILE="${UDIP_ENV_FILE:-$ROOT/.env}"

# Pierwsza wartość klucza z pliku .env (tak jak udip/config.py): bez komentarzy, bez \r z Windows, bez cudzysłowów.
env_get() {
  [ -f "$ENV_FILE" ] || return 0
  { grep -E "^[[:space:]]*$1[[:space:]]*=" "$ENV_FILE" || true; } | head -n1 | cut -d= -f2- | tr -d '\r' \
    | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

# Ścieżka względna liczy się od katalogu repozytorium.
abspath() { case "$1" in /*) printf '%s\n' "$1" ;; *) printf '%s\n' "$ROOT/$1" ;; esac; }

VENV="$(abspath "${UDIP_VENV:-$(env_get UDIP_VENV)}")"
[ "$VENV" = "$ROOT/" ] && VENV="$ROOT/.venv"
DATA="$(abspath "${UDIP_DATA_DIR:-$(env_get UDIP_DATA_DIR)}")"
[ "$DATA" = "$ROOT/" ] && DATA="$ROOT/var"
export UDIP_ENV_FILE="$ENV_FILE" UDIP_DATA_DIR="$DATA"
mkdir -p "$DATA"

PY="$VENV/bin/python"
if [ ! -x "$PY" ]; then
  BASE_PY=""
  for c in python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
      BASE_PY="$c"; break
    fi
  done
  [ -n "$BASE_PY" ] || fail "potrzebny Python 3.11 lub nowszy (Debian/Ubuntu: sudo apt install python3 python3-venv)."
  echo "Tworzę środowisko Pythona w $VENV i instaluję paczki z requirements.txt (jednorazowo, potrzebny internet)…"
  "$BASE_PY" -m venv "$VENV" || fail "nie udało się utworzyć $VENV (Debian/Ubuntu: sudo apt install python3-venv)."
  "$PY" -m pip install --disable-pip-version-check -q -r "$ROOT/requirements.txt" || fail "instalacja paczek nie powiodła się."
fi

APP="${UDIP_APP:-app.main:app}"
if [ "$APP" = "app.main:app" ] && [ ! -f "$ROOT/app/main.py" ]; then
  fail "brak app/main.py: aplikacja webowa nie jest jeszcze w tej gałęzi."
fi

# Dane startowe UMB (scripts/seed.py → udip.db.seed): przy pierwszym starcie, gdy brak bazy, albo na żądanie (--reseed).
# Domyślnie tryb demo: daty wpływu przesunięte wokół dnia UDIP_TODAY (albo dziś), żeby kalendarz pokazał wszystkie kolory.
# Ponowne uruchomienie seed.py jest bezpieczne: istniejące sprawy zostają, chyba że --reseed (seed.py --reset).
MARK="$DATA/.seeded"
if [ -f "$ROOT/scripts/seed.py" ]; then
  if [ "$RESEED" = "1" ] || [ ! -f "$MARK" ] || [ ! -f "$DATA/udip.sqlite" ]; then
    SEED_ARGS=()
    if [ "$REAL_DATES" != "1" ]; then
      DEMO_DAY="${UDIP_TODAY:-$(env_get UDIP_TODAY)}"
      SEED_ARGS+=(--demo-today "${DEMO_DAY:-$(date +%F)}")
    fi
    [ "$RESEED" = "1" ] && SEED_ARGS+=(--reset)
    # shellcheck disable=SC2206  # UDIP_SEED_ARGS to celowo kilka słów
    SEED_ARGS+=(${UDIP_SEED_ARGS:-})
    # ${a[@]+"${a[@]}"}: pusta tablica bez błędu „unbound variable” w bash 3.2 (macOS)
    echo "Wczytuję dane startowe: scripts/seed.py ${SEED_ARGS[*]+${SEED_ARGS[*]}}"
    "$PY" "$ROOT/scripts/seed.py" ${SEED_ARGS[@]+"${SEED_ARGS[@]}"} || fail "scripts/seed.py zakończył się błędem."
    date '+%Y-%m-%d %H:%M:%S' > "$MARK"
  fi
fi

port_busy() {
  "$PY" -c 'import socket, sys
s = socket.socket(); s.settimeout(0.5)
sys.exit(0 if s.connect_ex((sys.argv[1], int(sys.argv[2]))) == 0 else 1)' "$HOST" "$PORT"
}
port_busy && fail "port $PORT jest zajęty (może aplikacja już działa: http://$HOST:$PORT). Inny port: bash run.sh --port 8001"

URL="http://$HOST:$PORT/"

# Czeka, aż serwer odpowie (bez proxy: to adres lokalny), i dopiero wtedy otwiera przeglądarkę.
wait_ready() {
  "$PY" -c 'import sys, time, urllib.request, urllib.error
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for _ in range(120):
    try:
        opener.open(sys.argv[1], timeout=1); sys.exit(0)
    except urllib.error.HTTPError:
        sys.exit(0)
    except Exception:
        time.sleep(0.5)
sys.exit(1)' "$URL"
}

open_url() {
  if [ "$(uname -s)" = "Darwin" ]; then open "$URL"
  elif grep -qi microsoft /proc/version 2>/dev/null && command -v explorer.exe >/dev/null 2>&1; then explorer.exe "$URL" || true
  elif [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1
  fi
}

if [ "$OPEN_BROWSER" = "1" ]; then
  ( wait_ready && open_url ) >/dev/null 2>&1 &
fi

echo "Asystent UDIP: $URL  (dane: $DATA; Ctrl+C zatrzymuje)"
exec "$PY" -m uvicorn "$APP" --host "$HOST" --port "$PORT"
