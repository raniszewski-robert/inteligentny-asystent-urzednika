#!/usr/bin/env bash
# Sprawdza i przygotowuje wideo demo do zgloszenia: dlugosc (limit 2:00), rozdzielczosc, rozmiar, dzwiek.
#
#   bash video_check.sh demo.mov                 # tylko sprawdzenie
#   bash video_check.sh demo.mov --fix out.mp4   # H.264 + AAC, max 1920 px szerokosci, ciecie do 1:58, faststart
#   bash video_check.sh demo.mov --fix out.mp4 --max 115
#
# Kod wyjscia: 0 = gotowe do wyslania, 1 = trzeba poprawic, 2 = blad.
# Zaleznosci: ffmpeg i ffprobe (LGPL/GPL; uzywane jako narzedzie, nie wchodza do rozwiazania).
set -u
IN="${1:-}"; shift || true
OUT=""; MAX=118
while [ $# -gt 0 ]; do
  case "$1" in
    --fix) [ $# -ge 2 ] || { echo "BLAD: --fix wymaga nazwy pliku wynikowego, np. --fix demo.mp4" >&2; exit 2; }; OUT="$2"; shift 2;;
    --max) [ $# -ge 2 ] || { echo "BLAD: --max wymaga liczby sekund" >&2; exit 2; }; MAX="$2"; shift 2;;
    *) echo "Nieznany argument: $1" >&2; exit 2;;
  esac
done
[ -f "$IN" ] || { echo "Uzycie: bash video_check.sh plik_wideo [--fix wynik.mp4] [--max sekundy]" >&2; exit 2; }
command -v ffprobe >/dev/null || { echo "Brak ffprobe: zainstaluj ffmpeg" >&2; exit 2; }

probe() {
  local f="$1"
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$f")
  H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$f")
  VC=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$f")
  AC=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$f")
  SIZE=$(( $(stat -c %s "$f" 2>/dev/null || stat -f %z "$f") / 1000000 ))
}

report() {
  local f="$1" bad=0
  probe "$f"
  printf 'Plik: %s\n  dlugosc %.1f s | %sx%s | wideo %s | dzwiek %s | %s MB\n' "$f" "$DUR" "$W" "$H" "$VC" "${AC:-BRAK}" "$SIZE"
  if awk "BEGIN{exit !($DUR > 120)}"; then echo "  BLAD: dluzsze niz 2:00 (zalecany limit organizatora). Skroc albo uzyj --fix."; bad=1; fi
  if awk "BEGIN{exit !($DUR < 30)}"; then echo "  UWAGA: krocej niz 30 s; czy pokazuje caly scenariusz?"; fi
  if [ "${W:-0}" -lt 1280 ]; then echo "  UWAGA: szerokosc ponizej 1280 px; tekst na ekranie moze byc nieczytelny."; fi
  if [ "$VC" != "h264" ]; then echo "  UWAGA: kodek $VC; H.264 (mp4) odtworzy sie wszedzie. Uzyj --fix."; bad=1; fi
  if [ -z "$AC" ]; then echo "  UWAGA: brak sciezki dzwiekowej; dodaj lektora albo napisy."; fi
  if [ "$SIZE" -gt 200 ]; then echo "  UWAGA: ponad 200 MB; wgrywanie przez Wi-Fi na sali potrwa. Uzyj --fix."; fi
  return $bad
}

report "$IN"; STATUS=$?
IN_DUR="$DUR"
if [ -n "$OUT" ]; then
  if awk "BEGIN{exit !($IN_DUR > $MAX)}"; then
    CUT=$(awk "BEGIN{printf \"%.1f\", $IN_DUR - $MAX}")
    echo "UWAGA: --fix utnie ostatnie $CUT s nagrania (od ${MAX} s). Jesli tam jest zakonczenie (plansza z wdrozeniem i repozytorium), skroc srodek nagrania i nagraj ponownie zamiast ciac koniec."
  fi
  echo "Konwersja do $OUT (max ${MAX} s)..."
  ffmpeg -v error -y -i "$IN" -t "$MAX" -vf "scale='min(1920,iw)':-2" -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
         -c:a aac -b:a 128k -movflags +faststart "$OUT" || { echo "BLAD konwersji" >&2; exit 2; }
  report "$OUT"; STATUS=$?
fi
[ $STATUS -eq 0 ] && echo "OK: wideo gotowe. Wgraj je (YouTube niepubliczny albo dysk z dostepem dla kazdego z linkiem) i otworz link w oknie incognito."
exit $STATUS
