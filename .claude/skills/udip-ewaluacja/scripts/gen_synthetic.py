#!/usr/bin/env python3
"""Generator syntetycznych danych UDIP dla Bydgoszczy (deterministyczny, seed).

Tworzy w katalogu wyjściowym:
  archiwum.jsonl          ~N archiwalnych spraw (wniosek + odpowiedź + wydział), daty z ostatnich 2 lat
  testy/wniosek_XX.txt    wnioski testowe (parafrazy tematów z archiwum, inne słowa) + testy/gold.json
  testy/odp_wydzialu_XX.txt  odpowiedzi wydziałów do testów generatora pism
  pii/doc_XX.txt + pii/gold.json  dokumenty z danymi osobowymi i złotymi spanami (do P/R/F1 anonimizacji)
  kalendarz_demo.json     10 wniosków do kalendarza z rozkładem pilności względem --today

Wszystkie dane są fikcyjne. Domeny e-mail: example.com/example.org (RFC 2606). PESEL-e mają poprawną sumę kontrolną,
ale są losowe. Nazwiska z listy częstych nazwisk; kombinacje fikcyjne.

  python3 gen_synthetic.py --out ../../../../data-samples/syntetyczne --today 2026-11-22 --n 90
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))  # repo: pakiet udip
from udip.deadlines import deadline_days, is_working_day, urgency  # noqa: E402

FIRST_M = ["Jan", "Piotr", "Tomasz", "Marek", "Paweł", "Krzysztof", "Michał", "Andrzej", "Łukasz", "Adam", "Rafał", "Wojciech"]
FIRST_F = ["Anna", "Katarzyna", "Maria", "Agnieszka", "Joanna", "Ewa", "Magdalena", "Monika", "Barbara", "Zofia", "Natalia", "Justyna"]
SUR = [("Kowalski", "Kowalska"), ("Wiśniewski", "Wiśniewska"), ("Wójcik", "Wójcik"), ("Kamiński", "Kamińska"), ("Lewandowski", "Lewandowska"),
       ("Zieliński", "Zielińska"), ("Szymański", "Szymańska"), ("Woźniak", "Woźniak"), ("Dąbrowski", "Dąbrowska"), ("Kozłowski", "Kozłowska"),
       ("Jankowski", "Jankowska"), ("Mazur", "Mazur"), ("Krawczyk", "Krawczyk"), ("Piotrowski", "Piotrowska"), ("Grabowski", "Grabowska")]
STREETS = ["Gdańska", "Dworcowa", "Fordońska", "Wojska Polskiego", "Kujawska", "Szubińska", "Nakielska", "Toruńska", "Grunwaldzka", "Jagiellońska"]
DISTRICTS = ["Fordon", "Szwederowo", "Bartodzieje", "Wyżyny", "Kapuściska", "Błonie", "Górzyskowo", "Śródmieście", "Bielawy", "Miedzyń"]

# (dział, warianty tytułu, warianty treści pytań, szablon odpowiedzi) — parafrazy rozdzielone na archiwum i testy
TOPICS = [
    ("ZDMiKP", "remont ulicy",
     ["Proszę o informację, jaki był koszt remontu ulicy {street} w {year} r. i kto był wykonawcą.",
      "Wnoszę o podanie kosztu przebudowy nawierzchni ul. {street} wykonanej w {year} r. oraz nazwy firmy wykonawczej.",
      "Ile miasto zapłaciło za modernizację jezdni i chodników przy ul. {street} w {year} roku? Kto realizował roboty drogowe?"],
     "Koszt robót drogowych na ul. {street} w {year} r. wyniósł {amount} zł brutto. Wykonawcą była firma Drogbud Sp. z o.o."),
    ("ZDMiKP", "oświetlenie uliczne",
     ["Proszę o informację, ile wyniosły wydatki na oświetlenie uliczne na osiedlu {district} w {year} r.",
      "Wnoszę o udostępnienie kwoty wydanej na latarnie i energię do oświetlenia ulic w dzielnicy {district} za {year} r.",
      "Ile kosztowało utrzymanie oświetlenia dróg publicznych na terenie {district} w roku {year}?"],
     "Wydatki na oświetlenie uliczne na terenie osiedla {district} w {year} r. wyniosły {amount} zł."),
    ("WGK", "wycinka drzew",
     ["Proszę o informację, ile drzew usunięto w parku przy ul. {street} w {year} r. i ile nowych nasadzeń wykonano.",
      "Wnoszę o udostępnienie liczby drzew wyciętych na terenie zieleni miejskiej przy ul. {street} w {year} r. oraz liczby nasadzeń zastępczych.",
      "Ile drzew wycięło miasto na skwerze przy ulicy {street} w roku {year}? Czy posadzono nowe drzewa?"],
     "W {year} r. przy ul. {street} usunięto {count} drzew z uwagi na zły stan sanitarny; wykonano {count2} nasadzeń zastępczych."),
    ("WE", "liczba uczniów i nauczycieli",
     ["Proszę o podanie liczby uczniów i nauczycieli w szkołach podstawowych prowadzonych przez Miasto Bydgoszcz w roku szkolnym {year}/{year1}.",
      "Wnoszę o informację, ilu uczniów uczęszczało do miejskich szkół podstawowych w Bydgoszczy w roku szkolnym {year}/{year1} i ilu było nauczycieli.",
      "Jaka była liczba uczniów oraz etatów nauczycielskich w bydgoskich podstawówkach w roku {year}/{year1}?"],
     "W roku szkolnym {year}/{year1} do szkół podstawowych prowadzonych przez Miasto uczęszczało {count} uczniów; zatrudniono {count2} nauczycieli."),
    ("BP", "wydatki na promocję i sponsoring",
     ["Proszę o informację, jakie kwoty Miasto przekazało w {year} r. klubom sportowym w ramach umów promocyjnych.",
      "Wnoszę o wykaz umów promocyjnych zawartych w {year} r. z klubami sportowymi wraz z kwotami.",
      "Ile miasto wydało na promocję poprzez sponsoring drużyn sportowych w roku {year}?"],
     "W {year} r. zawarto {count} umów promocyjnych z klubami sportowymi na łączną kwotę {amount} zł brutto."),
    ("WZP", "przetarg i umowa",
     ["Proszę o kopię umowy zawartej w wyniku przetargu na {thing} w {year} r. wraz z protokołem odbioru.",
      "Wnoszę o udostępnienie skanu umowy na {thing} podpisanej przez Miasto w {year} r. oraz protokołu odbioru prac.",
      "Proszę przesłać umowę z wykonawcą zamówienia publicznego na {thing} z {year} roku i dokument odbioru."],
     "W załączeniu przekazujemy kopię umowy nr WZP.{count}.{year} na {thing} wraz z protokołem odbioru (dane osobowe zanonimizowano)."),
    ("WGO", "odpady komunalne",
     ["Proszę o informację, ile ton odpadów komunalnych zebrano w Bydgoszczy w {year} r. i jaki był koszt systemu.",
      "Wnoszę o podanie masy odebranych odpadów komunalnych w {year} r. oraz łącznych kosztów gospodarki odpadami.",
      "Jaki był koszt odbioru śmieci w mieście w roku {year} i ile ton odpadów odebrano od mieszkańców?"],
     "W {year} r. odebrano {count} ton odpadów komunalnych; koszt funkcjonowania systemu wyniósł {amount} zł."),
    ("WAB", "pozwolenie na budowę",
     ["Proszę o informację, czy wydano pozwolenie na budowę budynku przy ul. {street} {num} oraz o numer decyzji.",
      "Wnoszę o udostępnienie informacji o decyzji o pozwoleniu na budowę obiektu przy ul. {street} {num} (data, numer, inwestor).",
      "Czy dla nieruchomości przy ulicy {street} {num} wydano decyzję budowlaną? Proszę o numer i datę."],
     "Dla inwestycji przy ul. {street} {num} wydano decyzję o pozwoleniu na budowę nr WAB.{count}.{year} z dnia {dt}."),
    ("SCHRONISKO", "schronisko dla zwierząt",
     ["Proszę o informację, ile psów i kotów przyjęto do schroniska w Bydgoszczy w {year} r. i ile adoptowano.",
      "Wnoszę o podanie liczby zwierząt przyjętych do miejskiego schroniska w {year} r. oraz liczby adopcji.",
      "Ile zwierząt trafiło do schroniska w roku {year} i ile z nich znalazło nowy dom?"],
     "W {year} r. do Schroniska przyjęto {count} zwierząt; adoptowano {count2}."),
    ("SM", "straż miejska interwencje",
     ["Proszę o informację, ile mandatów za parkowanie wystawiła Straż Miejska w {year} r. na osiedlu {district}.",
      "Wnoszę o udostępnienie liczby mandatów karnych za nieprawidłowe parkowanie nałożonych przez strażników miejskich w {district} w {year} r.",
      "Ile razy strażnicy miejscy karali kierowców za złe parkowanie w dzielnicy {district} w roku {year}?"],
     "W {year} r. Straż Miejska nałożyła na terenie {district} {count} mandatów za nieprawidłowe parkowanie."),
    ("BRM", "diety radnych",
     ["Proszę o informację o wysokości diet wypłaconych radnym Rady Miasta Bydgoszczy w {year} r.",
      "Wnoszę o podanie łącznej kwoty diet radnych miejskich za {year} r. oraz zasad ich naliczania.",
      "Ile wyniosły diety członków Rady Miasta w roku {year}?"],
     "Łączna kwota diet wypłaconych radnym w {year} r. wyniosła {amount} zł; zasady określa uchwała Rady Miasta."),
    ("WOA", "zatrudnienie w urzędzie",
     ["Proszę o informację, ile osób było zatrudnionych w Urzędzie Miasta Bydgoszczy na koniec {year} r.",
      "Wnoszę o podanie stanu zatrudnienia w UMB (liczba etatów) według stanu na 31 grudnia {year} r.",
      "Ilu pracowników miał urząd miasta na koniec roku {year}?"],
     "Według stanu na 31.12.{year} r. w Urzędzie zatrudnionych było {count} osób na {count2} etatach."),
    ("WMG", "sprzedaż nieruchomości",
     ["Proszę o informację, ile działek gminnych sprzedano w {year} r. i za jaką łączną kwotę.",
      "Wnoszę o udostępnienie liczby nieruchomości miejskich zbytych w {year} r. wraz z łączną ceną sprzedaży.",
      "Ile gruntów należących do miasta sprzedano w roku {year}? Jaki był przychód?"],
     "W {year} r. sprzedano {count} nieruchomości gminnych za łączną kwotę {amount} zł."),
    ("ADM", "mieszkania komunalne",
     ["Proszę o informację, ile lokali komunalnych pozostawało pustych na koniec {year} r. i ile osób czeka na mieszkanie.",
      "Wnoszę o podanie liczby pustostanów w zasobie komunalnym na koniec {year} r. oraz długości listy oczekujących.",
      "Ile mieszkań miejskich stało pustych w roku {year} i ile rodzin oczekuje na przydział?"],
     "Na koniec {year} r. w zasobie było {count} pustostanów; na liście oczekujących znajdowało się {count2} gospodarstw."),
    ("WOS", "jakość powietrza i dotacje",
     ["Proszę o informację, ile dotacji na wymianę pieców węglowych udzielono w {year} r. i na jaką kwotę.",
      "Wnoszę o podanie liczby i łącznej wartości dotacji do wymiany źródeł ciepła przyznanych mieszkańcom w {year} r.",
      "Ilu mieszkańców dostało dofinansowanie na likwidację kopciuchów w roku {year}?"],
     "W {year} r. udzielono {count} dotacji na wymianę źródeł ciepła na łączną kwotę {amount} zł."),
    ("WI", "wydatki na informatykę",
     ["Proszę o informację, jakie były wydatki Urzędu na licencje oprogramowania w {year} r.",
      "Wnoszę o podanie kwoty wydanej przez UMB na zakup i utrzymanie licencji programów komputerowych w {year} r.",
      "Ile urząd zapłacił za oprogramowanie i licencje IT w roku {year}?"],
     "Wydatki na licencje oprogramowania w {year} r. wyniosły {amount} zł brutto."),
]
THINGS = ["dostawę ławek parkowych", "remont boiska szkolnego", "budowę placu zabaw", "dostawę sprzętu komputerowego", "usługę sprzątania urzędu"]


def pesel(rng: random.Random) -> str:
    y = rng.randint(1950, 2004)
    m = rng.randint(1, 12) + (20 if y >= 2000 else 0)
    d = rng.randint(1, 28)
    s = f"{y % 100:02d}{m:02d}{d:02d}{rng.randint(0, 9999):04d}"
    w = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    return s + str((10 - sum(int(s[i]) * w[i] for i in range(10)) % 10) % 10)


def person(rng: random.Random) -> tuple[str, str, str]:
    female = rng.random() < 0.5
    fn = rng.choice(FIRST_F if female else FIRST_M)
    sm, sf = rng.choice(SUR)
    return fn, (sf if female else sm), ("f" if female else "m")


def params(rng: random.Random, year: int) -> dict:
    """Jeden zestaw parametrów na sprawę: pytanie i odpowiedź dotyczą tej samej ulicy/dzielnicy/rzeczy."""
    return dict(street=rng.choice(STREETS), district=rng.choice(DISTRICTS), year=year, year1=year + 1,
                amount=f"{rng.randint(50, 9000) * 1000 + rng.randint(0, 999):,}".replace(",", " "),
                count=rng.randint(3, 900), count2=rng.randint(2, 400), num=rng.randint(1, 120),
                thing=rng.choice(THINGS), dt=f"{rng.randint(1, 28):02d}.{rng.randint(1, 12):02d}.{year}")


def fill(t: str, rng: random.Random, year: int, ctx: dict | None = None) -> str:
    return t.format(**(ctx or params(rng, year)))


def letter(rng: random.Random, body: str, when: date) -> tuple[str, list[dict]]:
    """Wniosek z nagłówkiem danych wnioskodawcy; zwraca też złote spany PII."""
    fn, sn, _ = person(rng)
    street, num = rng.choice(STREETS), f"{rng.randint(1, 99)}/{rng.randint(1, 40)}"
    email = f"{fn.lower()[0]}.{sn.lower()}{rng.randint(1, 99)}@example.com".translate(str.maketrans("ąćęłńóśźż", "acelnoszz"))
    phone = f"{rng.randint(500, 799)} {rng.randint(100, 999)} {rng.randint(100, 999)}"
    parts = [(f"Bydgoszcz, {when.day:02d}.{when.month:02d}.{when.year} r.\n\n", None), (f"{fn} {sn}", "OSOBA"), ("\n", None),
             (f"ul. {street} {num}", "ADRES"), ("\n", None), ("85-0" + f"{rng.randint(10, 99)} Bydgoszcz", "KOD_MIEJSC"), ("\n", None)]
    if rng.random() < 0.7:
        parts += [("e-mail: ", None), (email, "EMAIL"), ("\n", None)]
    if rng.random() < 0.5:
        parts += [("tel. ", None), (phone, "TELEFON"), ("\n", None)]
    parts += [("\nPrezydent Miasta Bydgoszczy\nUrząd Miasta Bydgoszczy\nul. Jezuicka 1, 85-102 Bydgoszcz\n\n"
               "Wniosek o udostępnienie informacji publicznej\n\n"
               "Na podstawie art. 2 ust. 1 ustawy o dostępie do informacji publicznej zwracam się z prośbą o udostępnienie następujących informacji:\n", None),
              (body + "\n", None), ("\nOdpowiedź proszę przesłać na adres e-mail.\n\nZ poważaniem\n", None), (f"{fn} {sn}", "OSOBA"), ("\n", None)]
    if rng.random() < 0.3:
        parts += [("PESEL: ", None), (pesel(rng), "PESEL"), ("\n", None)]
    text, gold, pos = "", [], 0
    for chunk, typ in parts:
        if typ:
            gold.append({"start": pos, "end": pos + len(chunk), "type": typ, "text": chunk})
        text += chunk
        pos += len(chunk)
    return text, gold


def dept_answer(rng: random.Random, dep: str, answer: str, when: date) -> tuple[str, list[dict]]:
    fn, sn, _ = person(rng)
    head = f"Bydgoszcz, {when.isoformat()}\n{dep}.1431.{rng.randint(1, 300)}.{when.year}\n\nBiuro Komunikacji Społecznej\nw miejscu\n\nW odpowiedzi na prośbę o przygotowanie informacji uprzejmie informuję:\n"
    tail = "\n\nSprawę prowadzi: "
    name = f"{fn} {sn}"
    tel = f"52 58 {rng.randint(10, 99)} {rng.randint(100, 999)}"
    text = head + answer + tail + name + ", tel. " + tel + "\n"
    s = len(head + answer + tail)
    gold = [{"start": s, "end": s + len(name), "type": "OSOBA", "text": name, "note": "pracownik merytoryczny – decyzja urzędnika (art. 5 ust. 2)"}]
    return text, gold


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--today", default="2026-11-22")
    p.add_argument("--n", type=int, default=90, help="liczba spraw w archiwum")
    p.add_argument("--seed", type=int, default=2026)
    a = p.parse_args(argv)
    rng = random.Random(a.seed)
    today = date.fromisoformat(a.today)
    out = a.out
    (out / "testy").mkdir(parents=True, exist_ok=True)
    (out / "pii").mkdir(parents=True, exist_ok=True)

    # archiwum: warianty 0–1 treści; test: wariant 2 (inne słowa)
    arch = []
    for i in range(a.n):
        ti = i % len(TOPICS)
        dep, title, variants, ans = TOPICS[ti]
        when = today - timedelta(days=rng.randint(5, 730))
        year = when.year - 1
        ctx = params(rng, year)
        body = "1. " + fill(rng.choice(variants[:2]), rng, year, ctx)
        req, _ = letter(rng, body, when)
        resp = fill(ans, rng, year, ctx)
        arch.append({"id": f"UDIP-{when.year}-{i + 1:03d}", "date": when.isoformat(), "title": f"{title} ({year})",
                     "request_text": req, "response_text": "Odpowiedź na wniosek:\n" + resp, "departments": [dep], "topic": ti})
    arch.sort(key=lambda r: r["date"])
    with (out / "archiwum.jsonl").open("w", encoding="utf-8") as f:
        for r in arch:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    gold_tests, pii_gold = [], []
    for ti, (dep, title, variants, ans) in enumerate(TOPICS):
        when = today - timedelta(days=rng.randint(0, 3))
        ctx = params(rng, today.year - 1)
        body = "1. " + fill(variants[2], rng, today.year - 1, ctx)
        multi = ti % 4 == 0  # co czwarty test ma drugie pytanie z innego wydziału
        deps = [dep]
        if multi:
            oti = (ti + 5) % len(TOPICS)
            body += "\n2. " + fill(TOPICS[oti][2][2], rng, today.year - 1)
            deps.append(TOPICS[oti][0])
        txt, gold = letter(rng, body, when)
        name = f"wniosek_{ti + 1:02d}.txt"
        (out / "testy" / name).write_text(txt, encoding="utf-8")
        since = today - timedelta(days=365)
        relevant = [r["id"] for r in arch if r["topic"] == ti and date.fromisoformat(r["date"]) >= since]
        da, da_gold = dept_answer(rng, dep, fill(ans, rng, today.year - 1, ctx), today)
        (out / "testy" / f"odp_wydzialu_{ti + 1:02d}.txt").write_text(da, encoding="utf-8")
        gold_tests.append({"file": name, "departments": deps, "relevant_archive_ids_last_year": relevant, "topic": title,
                           "answer_file": f"odp_wydzialu_{ti + 1:02d}.txt"})
        pii_gold.append({"file": f"testy/{name}", "spans": gold})
        pii_gold.append({"file": f"testy/odp_wydzialu_{ti + 1:02d}.txt", "spans": da_gold})
    (out / "testy" / "gold.json").write_text(json.dumps(gold_tests, ensure_ascii=False, indent=2), encoding="utf-8")

    # dodatkowe dokumenty „trudne” dla anonimizacji (odmiana, dane w zdaniu, numery z sumą kontrolną)
    hard = []
    for k in range(8):
        fn, sn, g = person(rng)
        pes = pesel(rng)
        segs = [("W dniu 3.10.2026 r. wpłynęło pismo od ", None),
                ((f"Pani {fn} {sn}" if g == "f" else f"Pana {fn} {sn}"), None), (", zam. ", None), (f"ul. {rng.choice(STREETS)} {rng.randint(1, 90)}", "ADRES"),
                (", PESEL ", None), (pes, "PESEL"), (". Wnioskodawca prosi o kontakt pod nr ", None),
                (f"+48 {rng.randint(500, 799)} {rng.randint(100, 999)} {rng.randint(100, 999)}", "TELEFON"), (". Rozmawiano również z ", None)]
        fn2, sn2, _ = person(rng)
        segs += [(f"{fn2} {sn2}", "OSOBA"), (" – sąsiadem. Decyzję podpisał Prezydent Miasta Bydgoszczy.\n", None)]
        text, gold, pos = "", [], 0
        for chunk, typ in segs:
            if chunk.startswith(("Pani ", "Pana ")):
                nm = chunk.split(" ", 1)[1]
                gold.append({"start": pos + len(chunk) - len(nm), "end": pos + len(chunk), "type": "OSOBA", "text": nm})
            elif typ:
                gold.append({"start": pos, "end": pos + len(chunk), "type": typ, "text": chunk})
            text += chunk
            pos += len(chunk)
        fname = f"pii/doc_{k + 1:02d}.txt"
        (out / fname).write_text(text, encoding="utf-8")
        hard.append({"file": fname, "spans": gold})
    (out / "pii" / "gold.json").write_text(json.dumps(pii_gold + hard, ensure_ascii=False, indent=2), encoding="utf-8")

    # kalendarz: 10 wniosków; dobieramy daty wpływu tak, by pokazać każdy poziom pilności
    targets = ["overdue", "today", "tomorrow", "soon", "soon", "ok", "ok", "ok", "done", "kwerenda"]
    statuses = {"overdue": "b_zapytania_wyslane", "today": "d_odpowiedz_przygotowana", "tomorrow": "b_zapytania_wyslane",
                "soon": "a_brak_dzialan", "ok": "a_brak_dzialan", "done": "e_odpowiedz_wyslana", "kwerenda": "c_kwerenda"}
    initials = ["AK", "MW", "JN", "AK", "PZ", "MW", "JN", "PZ", "AK", "MW"]
    cal, used = [], set()
    for n, t in enumerate(targets):
        chosen = None
        for back in range(1, 70):
            rec = today - timedelta(days=back)
            if rec in used or not is_working_day(rec):
                continue
            due = deadline_days(rec)
            if t in ("done", "kwerenda"):
                if back > 20:
                    chosen = rec
                    break
                continue
            if urgency(due, today) == t:
                chosen = rec
                break
        if not chosen:
            chosen = today - timedelta(days=n + 1)  # dziś (np. niedziela) dany poziom może być niemożliwy
        used.add(chosen)
        dep, title, variants, _ = TOPICS[n % len(TOPICS)]
        r = {"number": f"BKS.IV.1431.{100 + n}.{chosen.year}", "received": chosen.isoformat(), "summary": title.capitalize(),
             "initials": initials[n], "status": statuses[t], "departments": [dep], "channel": rng.choice(["e-mail", "ePUAP", "papier"])}
        if t == "kwerenda":
            r["extension_days"] = 30
        if t == "done":
            r["answered"] = (deadline_days(chosen) - timedelta(days=2)).isoformat()
        cal.append(r)
    (out / "kalendarz_demo.json").write_text(json.dumps({"today": today.isoformat(), "requests": cal}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"archiwum: {len(arch)} spraw; testy: {len(gold_tests)} wniosków; PII: {len(pii_gold) + len(hard)} dokumentów; kalendarz: {len(cal)} wniosków → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
