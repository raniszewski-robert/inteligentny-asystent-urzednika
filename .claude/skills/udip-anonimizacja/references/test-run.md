# test-run: udip-anonimizacja

Uruchomione 2026-11-21, Python 3.13.18, w katalogu głównym repozytorium (`bash scripts/smoke.sh` uruchamia skrót tych testów).

```
$ python3 .claude/skills/udip-anonimizacja/scripts/anonymize.py --selftest
OK   ADRES      ul. Długa 15/4
OK   DOWOD      ABA300000
OK   EMAIL      anna.kw@example.com
OK   IBAN       PL61 1090 1014 0000 0712 1981 2874
OK   KOD_MIEJSC 85-034 Bydgoszcz
OK   NIP        526-104-08-28
OK   OSOBA      Anna Kowalska-Wiśniewska
OK   OSOBA      Janem Nowakiem
OK   OSOBA      Kowalska-Wiśniewska
OK   PESEL      44051401359
OK   TELEFON    +48 601 234 567
OK   Rafał Bruski → review (art. 5 ust. 2)
Wycieki po redakcji: brak
Spanów: 14; wynik: OK
```

```
$ cat /tmp/anon_demo.txt; python3 .claude/skills/udip-anonimizacja/scripts/anonymize.py detect /tmp/anon_demo.txt --out /tmp/a.json --html /tmp/a.html && python3 -c "import json;[print(s['id'],s['type'],repr(s['text']),s['status']) for s in json.load(open('/tmp/a.json'))['spans']]"
Pan Jan Kowalski, ur. 12.03.1980 r. w Toruniu, korzysta z zasiłku z MOPS. Właściciel działki nr 123/4 jest chory. Sprawę zgłosił J. Nowak. Kontakt: bip@um.bydgoszcz.pl, ul. Jezuicka 1. Parafia św. Maksymiliana Kolbego.
Wykryto 6 fragmentów: DZIALKA×1, OSOBA×2, SZCZEGOLNE_POMOC_SPOLECZNA×1, SZCZEGOLNE_ZDROWIE×1, URODZENIE×1
s1 SZCZEGOLNE_POMOC_SPOLECZNA 'Pan Jan Kowalski, ur. 12.03.1980 r. w Toruniu, korzysta z zasiłku z MOPS.' review
s2 OSOBA 'Jan Kowalski' suggested
s3 URODZENIE 'ur. 12.03.1980 r. w Toruniu' suggested
s4 SZCZEGOLNE_ZDROWIE 'Właściciel działki nr 123/4 jest chory.' review
s5 DZIALKA '123/4' review
s6 OSOBA 'J. Nowak' review
```

```
$ python3 .claude/skills/udip-anonimizacja/scripts/anonymize.py apply /tmp/anon_demo.txt /tmp/a.json --out /tmp/a_out.txt --accept-all && cat /tmp/a_out.txt
Pan [imię i nazwisko], [data i miejsce urodzenia], korzysta z zasiłku z MOPS. Właściciel działki nr 123/4 jest chory. Sprawę zgłosił J. Nowak. Kontakt: bip@um.bydgoszcz.pl, ul. Jezuicka 1. Parafia św. Maksymiliana Kolbego.
```

```
$ python3 -c "import json,sys;sys.path.insert(0,'.claude/skills/udip-anonimizacja/scripts');from anonymize import detect;[print(json.loads(l)['id'], [(s.type,s.text[:30],s.status) for s in detect(json.loads(l)['request_text'])]) for l in open('data-partner/umb/archiwum_umb.jsonl')]"
BKS.IV.1431.293.2025 []
BKS.IV.1431.307.2025 [('OSOBA', 'Ewa Góra', 'suggested')]
BKS.IV.1431.15.2026 []
BKS.IV.1431.16.2026 [('OSOBA', 'JERZY', 'review'), ('OSOBA', 'Bruskiego', 'review'), ('OSOBA', 'JERZY', 'review')]
BKS.IV.1431.17.2026 [('EMAIL', 'abcxyz@jahu.komm', 'suggested')]
BKS.IV.1431.18.2026 []
BKS.IV.1431.509.2026 [('OSOBA', 'E. Góra', 'suggested')]
BKS.IV.1431.543.2026 []
BKS.IV.1431.590.2026 [('ADRES', 'ul. Królowej Jadwigi 23', 'review')]
BKS.IV.1431.599.2026 [('OSOBA', 'E. Góra', 'suggested')]
```

