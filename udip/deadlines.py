"""Terminy UDIP: dni wolne w Polsce i liczenie terminów wg art. 57 KPA.

Zasady (źródła: research/05_prawo_etyka_ryzyka.md):
- art. 13 ust. 1 UDIP: udostępnienie „bez zbędnej zwłoki, nie później niż w terminie 14 dni od dnia złożenia wniosku”;
- art. 13 ust. 2 UDIP: przedłużenie (u nas „kwerenda”) do 2 miesięcy od dnia złożenia wniosku, z powiadomieniem o powodach;
- art. 57 § 1 KPA: dnia, w którym nastąpiło zdarzenie, nie wlicza się; termin w dniach kończy się z upływem ostatniego dnia;
- art. 57 § 3 KPA: termin w miesiącach kończy się w dniu odpowiadającym początkowemu, a gdy go nie ma – w ostatnim dniu miesiąca;
- art. 57 § 4 KPA: koniec terminu w dzień ustawowo wolny od pracy lub w sobotę → następny dzień, który nie jest wolny ani sobotą.

Tylko biblioteka standardowa. CLI i selftest: `.claude/skills/udip-kalendarz-terminy/scripts/deadlines.py --selftest`.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from functools import lru_cache

UDIP_DAYS = 14
MAX_EXTENSION_MONTHS = 2


def easter_sunday(year: int) -> date:
    """Wielkanoc (algorytm Meeusa/Jonesa/Butchera, kalendarz gregoriański)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


@lru_cache(maxsize=None)
def polish_holidays(year: int) -> dict[date, str]:
    """Dni ustawowo wolne od pracy (ustawa z 18.01.1951 o dniach wolnych od pracy).

    Wigilia (24.12) jest dniem wolnym od 2025 r. (nowelizacja z 2024 r.; patrz research/05).
    """
    e = easter_sunday(year)
    h = {
        date(year, 1, 1): "Nowy Rok",
        date(year, 1, 6): "Trzech Króli",
        e: "Wielkanoc",
        e + timedelta(days=1): "Poniedziałek Wielkanocny",
        date(year, 5, 1): "Święto Pracy",
        date(year, 5, 3): "Święto Konstytucji 3 Maja",
        e + timedelta(days=49): "Zielone Świątki",
        e + timedelta(days=60): "Boże Ciało",
        date(year, 8, 15): "Wniebowzięcie NMP",
        date(year, 11, 1): "Wszystkich Świętych",
        date(year, 11, 11): "Narodowe Święto Niepodległości",
        date(year, 12, 25): "Boże Narodzenie (1. dzień)",
        date(year, 12, 26): "Boże Narodzenie (2. dzień)",
    }
    if year >= 2025:
        h[date(year, 12, 24)] = "Wigilia"
    return h


def is_free_day(d: date) -> bool:
    """Sobota, niedziela albo dzień ustawowo wolny (niedziela jest wolna z mocy ustawy)."""
    return d.weekday() >= 5 or d in polish_holidays(d.year)


def is_working_day(d: date) -> bool:
    return not is_free_day(d)


def shift_to_working_day(d: date) -> date:
    """art. 57 § 4 KPA."""
    while is_free_day(d):
        d += timedelta(days=1)
    return d


def previous_working_day(d: date) -> date:
    d -= timedelta(days=1)
    while is_free_day(d):
        d -= timedelta(days=1)
    return d


def add_months(d: date, months: int) -> date:
    """art. 57 § 3 KPA: dzień odpowiadający początkowemu albo ostatni dzień miesiąca."""
    y, m = divmod(d.month - 1 + months, 12)
    y += d.year
    m += 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def deadline_days(received: date, days: int = UDIP_DAYS) -> date:
    """Termin w dniach od dnia wpływu (dzień wpływu się nie liczy)."""
    return shift_to_working_day(received + timedelta(days=days))


def deadline_safe(received: date, days: int = UDIP_DAYS) -> date:
    """Wariant ostrożny: orzecznictwo nie przesądza, czy art. 57 § 4 KPA stosuje się do art. 13 UDIP
    (NSA III OSK 754/25; research/05). Gdy 14. dzień jest wolny, planuj na ostatni dzień roboczy PRZED nim."""
    d = received + timedelta(days=days)
    return d if is_working_day(d) else previous_working_day(d)


def deadline_extended(received: date, extension_days: int | None = None, months: int | None = None) -> tuple[date, list[str]]:
    """Termin po przedłużeniu (art. 13 ust. 2 UDIP).

    Podaj albo `extension_days` (kwerenda „+N dni” liczone od pierwotnego terminu przed przesunięciem),
    albo `months` (np. 2 = maksimum ustawowe). Zwraca (termin, ostrzeżenia).
    """
    warnings: list[str] = []
    cap = shift_to_working_day(add_months(received, MAX_EXTENSION_MONTHS))
    if months is not None:
        if months > MAX_EXTENSION_MONTHS:
            warnings.append("Przedłużenie ponad 2 miesiące od złożenia wniosku jest niezgodne z art. 13 ust. 2 UDIP.")
        result = shift_to_working_day(add_months(received, months))
    elif extension_days is not None:
        result = shift_to_working_day(received + timedelta(days=UDIP_DAYS + extension_days))
    else:
        result = cap
    if result > cap:
        warnings.append(f"Termin {result.isoformat()} przekracza maksimum 2 miesięcy ({cap.isoformat()}); przyjęto {cap.isoformat()}.")
        result = cap
    warnings.append("Przed upływem 14 dni wyślij wnioskodawcy powiadomienie o przedłużeniu z podaniem powodów (art. 13 ust. 2 UDIP).")
    return result, warnings


def urgency(due: date, today: date, done: bool = False) -> str:
    """Poziom pilności do podświetlenia w kalendarzu.

    - done: odpowiedź wysłana;
    - overdue: termin minął;
    - today: termin dziś;
    - tomorrow: dziś jest ostatni dzień roboczy przed terminem („dzień poprzedzający” z treści zadania);
    - soon: do 3 dni roboczych;
    - ok: reszta.
    """
    if done:
        return "done"
    if due < today:
        return "overdue"
    if due == today:
        return "today"
    if today == previous_working_day(due) or due - today == timedelta(days=1):
        return "tomorrow"
    wd, d = 0, today
    while d < due:
        d += timedelta(days=1)
        if is_working_day(d):
            wd += 1
    return "soon" if wd <= 3 else "ok"


def working_days_left(due: date, today: date) -> int:
    if due <= today:
        return -sum(1 for i in range((today - due).days) if is_working_day(due + timedelta(days=i + 1)))
    return sum(1 for i in range((due - today).days) if is_working_day(today + timedelta(days=i + 1)))
