# test-run: udip-projekty-odpowiedzi

Uruchomione 2026-11-21, Python 3.13.18, w katalogu głównym repozytorium (`bash scripts/smoke.sh` uruchamia skrót tych testów).

```
$ python3 .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py --request data-partner/umb/przypadek_543/wniosek.txt --answer data-partner/umb/przypadek_543/SCHRONISKO.txt --answer data-partner/umb/przypadek_543/WGK.txt --number BKS.IV.1431.543.2026 --received 2026-08-14 --today 2026-09-22 --out-dir /tmp/d543 && cat /tmp/d543/projekt.txt && ls /tmp/d543
{"type": "udostepnienie", "mode_requested": "template", "mode_used": "template", "questions": 5, "gaps": [], "uncertain_assignment": [{"sentence": "Opiekę nad domowymi zwierzętami bezdomnymi sprawuje Schronisko dla Zwierząt w Bydgoszczy, które jest jednostką budżetową", "assigned_to": 2, "source": "SCHRONISKO.txt", "candidates": [1, 2, 3, 4, 5]}, {"question": 2, "expected_department": ["WGK", "WMG"], "answer_from": ["SCHRONISKO"], "note": "pytanie wygląda na właściwość innej komórki – czy brakuje jej odpowiedzi?"}], "number_check": [], "warnings": [], "sources": ["SCHRONISKO.txt", "WGK.txt"], "departments": ["SCHRONISKO", "WGK"], "salutation": "Szanowni Państwo,", "internal_notes": ["Dz.U. cytuj tak jak BKS w piśmie 509.2026 („Dz. U. z 2022 r. poz. 902, z 2025 r. poz. 1844”), jeśli w ogóle."], "number_check_template": [], "omitted_numbers_template": [], "anonymization_suggestions": 0}
Bydgoszcz, dnia 22 września 2026 r.
BKS.IV.1431.543.2026

[adresat – uzupełnij z rejestru]

Szanowni Państwo,
w odpowiedzi na wystosowany przez Państwa wniosek o udostępnienie informacji publicznej w zakresie sposobu i skutków wykonywania zadania „opieka nad bezdomnymi zwierzętami i ich wyłapywanie", przewidzianego ustawą o ochronie zwierząt, na podstawie materiału przygotowanego przez jednostki merytoryczne, tj. Schronisko dla Zwierząt w Bydgoszczy oraz Wydział Zieleni i Gospodarki Komunalnej Urzędu Miasta Bydgoszczy informuję, co następuje.
Ad 1
Wyłapywanie bezdomnych zwierząt w 2025 r. realizowało Schronisko dla Zwierząt w Bydgoszczy; Wydział nie udzielał w tym zakresie zleceń podmiotom zewnętrznym.
Ad 2
Opiekę nad domowymi zwierzętami bezdomnymi sprawuje Schronisko dla Zwierząt w Bydgoszczy, które jest jednostką budżetową Miasta Bydgoszczy.
Ad 3
Schronisko zapewniło opiekę w 2025 r. 839 psom oraz 560 kotom.
Ad 4
Budżet schroniska w 2025 r. wyniósł 3.143.761,14 zł. W 2025 r. realizowana była Umowa 1/2022/SZ zawarta między Schroniskiem a Kliniką Weterynaryjną.
Ad 5
Miasto nie zawierało umów z podmiotami zewnętrznymi w zakresie opieki nad domowymi zwierzętami bezdomnymi.

Łączę wyrazy szacunku,

[podpis AIP]
Biuro Komunikacji Społecznej
Urząd Miasta Bydgoszczy
e-mail: bip@um.bydgoszcz.pl

Podstawa prawna: art. 10 ust. 1 i art. 13 ust. 1 ustawy z dnia 6 września 2001 r. o dostępie do informacji publicznej.podglad.html
projekt.docx
projekt.txt
raport.json
spans.json
```

```
$ python3 .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py --request data-samples/syntetyczne/testy/wniosek_03.txt --answer data-samples/syntetyczne/testy/odp_wydzialu_03.txt --number BKS.IV.1431.703.2026 --received 2026-11-20 --today 2026-11-22 --out-dir /tmp/s03 && python3 .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py --finalize /tmp/s03 --accept-all-suggested && head -8 /tmp/s03/odpowiedz_do_wysylki.txt && echo ---- && head -8 /tmp/s03/odpowiedz_zanonimizowana.txt
{"type": "udostepnienie", "mode_requested": "template", "mode_used": "template", "questions": 1, "gaps": [], "uncertain_assignment": [], "number_check": [], "warnings": [], "sources": ["odp_wydzialu_03.txt"], "departments": ["WGK"], "salutation": "Szanowna Pani,", "internal_notes": ["Dz.U. cytuj tak jak BKS w piśmie 509.2026 („Dz. U. z 2022 r. poz. 902, z 2025 r. poz. 1844”), jeśli w ogóle."], "number_check_template": [], "omitted_numbers_template": [], "anonymization_suggestions": 5}
Zapisano odpowiedz_zanonimizowana.* i odpowiedz_do_wysylki.*; zaczernione: 5
Bydgoszcz, dnia 22 listopada 2026 r.
BKS.IV.1431.703.2026

Zofia Krawczyk
ul. Toruńska 73/21
85-046 Bydgoszcz
e-mail: z.krawczyk13@example.com
tel. 713 637 434
----
Bydgoszcz, dnia 22 listopada 2026 r.
BKS.IV.1431.703.2026

[imię i nazwisko]
[adres]
[adres]
e-mail: [e-mail]
tel. [telefon]
```

```
$ python3 .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py --request data-samples/syntetyczne/testy/wniosek_01.txt --answer data-samples/syntetyczne/testy/odp_wydzialu_01.txt --number BKS.IV.1431.701.2026 --received 2026-11-20 --today 2026-11-22 --out-dir /tmp/s01 >/dev/null && python3 .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py --finalize /tmp/s01 --accept-all-suggested
Zapisano odpowiedz_zanonimizowana.* i odpowiedz_do_wysylki.*; zaczernione: 4
```

```
$ python3 .claude/skills/udip-projekty-odpowiedzi/scripts/mock_llm.py 18081 good & P1=$!; python3 .claude/skills/udip-projekty-odpowiedzi/scripts/mock_llm.py 18082 bad & P2=$!; sleep 1; for u in 18081 18082 18099; do LLM_BASE_URL=http://127.0.0.1:$u/v1 python3 .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py --request data-partner/umb/przypadek_543/wniosek.txt --answer data-partner/umb/przypadek_543/SCHRONISKO.txt --received 2026-08-14 --mode llm --out-dir /tmp/dl$u | python3 -c "import json,sys;d=json.load(sys.stdin);print('port','$u','mode_used=',d['mode_used'],'| rejected=',d.get('llm_rejected'),'| error=',d.get('llm_error'))"; done; kill $P1 $P2
port 18081 mode_used= llm | rejected= None | error= None
port 18082 mode_used= template | rejected= liczby spoza odpowiedzi wydziałów albo przy innym słowie: ['999999', '999999', '999999', '999999', '999999'] | error= None
port 18099 mode_used= template | rejected= None | error= URLError: <urlopen error [Errno 111] Connection refused>
```

```
$ python3 .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py --request data-partner/umb/przypadek_543/wniosek.txt --received 2026-08-14 --today 2026-08-28 --type przedluzenie --out-dir /tmp/dp >/dev/null && sed -n 6,8p /tmp/dp/projekt.txt
UWAGA: Brak konkretnego powodu – lakoniczne uzasadnienie przedłużenia sądy uznają za bezczynność (II SAB/Ol 107/23).
Szanowni Państwo,
w odpowiedzi na wystosowany przez Państwa wniosek o udostępnienie informacji publicznej dotyczący sposobu i skutków wykonywania zadania „opieka nad bezdomnymi zwierzętami i ich wyłapywanie", przewidzianego ustawą o ochronie zwierząt, ze względu na konieczność przeprowadzenia całościowej kwerendy w zakresie wnioskowanych danych powiadamiam, że ostateczna odpowiedź nastąpi w terminie późniejszym wskazanym w art. 13 ust. 2 ustawy z dnia 6 września 2001 r. o dostępie do informacji publicznej – orientacyjny termin udzielenia odpowiedzi: 14 października 2026 r.

```

```
$ python3 -c "import json;r=[json.loads(l) for l in open('data-partner/umb/archiwum_umb.jsonl') if '509.2026' in l][0];open('/tmp/w509.txt','w').write(r['request_text'])" && python3 .claude/skills/udip-projekty-odpowiedzi/scripts/draft.py --request /tmp/w509.txt --received 2026-08-05 --today 2026-08-10 --type doprecyzowanie --dept WAB --until 2026-09-18 --reason 'wskazanie, o jakie dokładnie akta sprawy chodzi.' --out-dir /tmp/dd >/dev/null && sed -n 6,12p /tmp/dd/projekt.txt
WEZWANIE DO DOPRECYZOWANIA ZAKRESU OTRZYMANEGO WNIOSKU

Szanowni Państwo,
w związku z wystosowanym przez Państwa wnioskiem o udostępnienie informacji publicznej dotyczącym budynku nowego apartamentowca (teren po budynku Astrum), komórka merytoryczna, tj. Wydział Administracji Budowlanej Urzędu Miasta Bydgoszczy wnosi o doprecyzowanie wniosku: wskazanie, o jakie dokładnie akta sprawy chodzi.
Proszę o przesłanie doprecyzowania w terminie 7 dni od otrzymania niniejszego pisma. Po upływie tego terminu wniosek zostanie pozostawiony bez rozpoznania, o czym Wnioskodawca zostanie powiadomiony odrębnym pismem.
Jednocześnie stosownie do treści art. 13 ust. 2 ustawy z 06.09.2001 r. o dostępie do informacji publicznej (Dz. U. z 2022 r. poz. 902, z 2025 r. poz. 1844) powiadamiam, że wyznaczam nowy termin na rozpatrzenie wniosku, wskazując dzień 18 września 2026 r.

```

```
$ python3 -c "import docx;d=docx.Document('/tmp/s03/odpowiedz_zanonimizowana.docx');print([(r.text,str(r.font.highlight_color)) for p in d.paragraphs for r in p.runs if r.font.highlight_color])"
[('██████████████', 'BLACK (1)'), ('██████████████████', 'BLACK (1)'), ('████████████████', 'BLACK (1)'), ('████████████████████████', 'BLACK (1)'), ('███████████', 'BLACK (1)')]
```

```
$ draft.py --type przedluzenie --received 2026-08-14 --today 2026-10-20  (pismo po terminie, nowy termin w przeszłości)
UWAGA: Pismo datowane 2026-10-20 po upływie 14 dni (2026-08-28): powiadomienie z art. 13 ust. 2 powinno wyjść przed upływem terminu.
UWAGA: Wskazany nowy termin 2026-10-14 już minął lub jest dziś – popraw --until.
```

```
$ finalize po edycji tekstu przez urzędnika (offsety się zmieniają, decyzje przenoszone po tekście)
spanów przed: 5 po edycji: 5 zaakceptowane po edycji: 5
wycieki w wersji zanonimizowanej: brak
ostrzeżenia: []
```
