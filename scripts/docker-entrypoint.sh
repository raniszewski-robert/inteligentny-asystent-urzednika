#!/usr/bin/env sh
# Entrypoint kontenera Asystenta UDIP: przy pierwszym starcie wczytuje dane startowe UMB
# (scripts/seed.py), a następnie uruchamia serwer FastAPI (uvicorn).
set -eu

DATA="${UDIP_DATA_DIR:-/data}"
PORT="${UDIP_PORT:-8000}"
HOST="${UDIP_HOST:-0.0.0.0}"
APP="${UDIP_APP:-app.main:app}"

mkdir -p "$DATA"

seed_db() {
  MARK="$DATA/.seeded"
  if [ "${UDIP_RESEED:-0}" = "1" ] || [ ! -f "$MARK" ] || [ ! -f "$DATA/udip.sqlite" ]; then
    set --
    if [ "${UDIP_REAL_DATES:-0}" != "1" ]; then
      DEMO_DAY="${UDIP_TODAY:-$(date +%F)}"
      set -- "$@" --demo-today "$DEMO_DAY"
    fi
    if [ "${UDIP_RESEED:-0}" = "1" ]; then
      set -- "$@" --reset
    fi
    if [ -n "${UDIP_SEED_ARGS:-}" ]; then
      # shellcheck disable=SC2086
      set -- "$@" $UDIP_SEED_ARGS
    fi
    echo "Wczytuję dane startowe: scripts/seed.py $*"
    python /app/scripts/seed.py "$@"
    date '+%Y-%m-%d %H:%M:%S' > "$MARK"
  fi
}

if [ "${UDIP_SKIP_SEED:-0}" != "1" ] && [ -f /app/scripts/seed.py ]; then
  seed_db
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec python -m uvicorn "$APP" --host "$HOST" --port "$PORT"
