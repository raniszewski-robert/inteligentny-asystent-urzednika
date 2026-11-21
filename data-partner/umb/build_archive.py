"""Buduje archiwum_umb.jsonl z próbek UMB (tekst wyciągnięty ingest.py) i arkusza kalendarium."""
import json, re, glob, sys
from pathlib import Path
import openpyxl
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else 'txt'); OUT = Path('.')  # katalog z JSON-ami z ingest.py --json
deps = json.load(open(Path(__file__).resolve().parents[2] / '.claude/skills/udip-archiwum-i-wydzialy/data/departments.json'))
deps = deps['departments'] if isinstance(deps, dict) else deps
def found_deps(t):
    t1 = re.sub(r'\s+', ' ', t)
    out = []
    for d in deps:
        stem = d['name'].split(' Sp.')[0].replace(' w Bydgoszczy', '')
        key = stem[:-2] if len(stem) > 14 else stem
        if d['id'] != 'BKS' and len(key) >= 9 and key in t1:  # BKS = nadawca (nagłówek), nie wydział merytoryczny
            out.append(d['id'])
    return out
wb = openpyxl.load_workbook(Path(sys.argv[2] if len(sys.argv) > 2 else 'WNIOSKI O UDOSTĘPNIANIE INFORMACJI PUBLICZNEJ.xlsx'))
rows = [r for r in wb.active.iter_rows(min_row=3, values_only=True) if r[0]]
recs = []
for r in rows:
    num = r[1]; short = num.replace('BKS.IV.1431.', '')
    req = json.load(open(SRC / f'Wniosek - {num}.json'))
    resp_parts, kinds = [], []
    for kind in ['Doprecyzowanie', 'Kwerenda', 'Odpowiedź']:
        f = SRC / f'{kind} - {num}.anonymised.json'
        if f.exists():
            resp_parts.append(f'[{kind}]\n' + json.load(open(f))['text']); kinds.append(kind)
    resp = '\n\n'.join(resp_parts)
    req_text = req['text']
    note = None
    if req.get('warning'):
        # rękopis: treść przepisana ręcznie z obrazu skanu (Claude, 21.11.2026), por. cytat w odpowiedzi BKS
        req_text = ('JERZY [nazwisko]\nBydgoszcz 09.01.2026\nUrząd Miasta Bydgoszczy, Kancelaria Ogólna, data wpływu 09.01.2026, nr wpływu 3468/2026\n'
                    'Szanowny Prezydent Bydgoszczy\nIle punktów sprzedaży alkoholu przybyło w Bydgoszczy od czasu objęcia funkcji '
                    'Prezydenta przez Bruskiego do dnia dzisiejszego? Odpowiedź w trybie administracyjnym.\nJERZY')
        note = 'rękopis; OCR nieczytelny (quality %.2f) – treść przepisana ręcznie z obrazu' % req['quality']
    flat = re.sub(r'\s+', ' ', resp)
    outcome = ('odeslanie_art_4_ust_3' if 'nie jest dysponentem' in flat else
               'brak_danych' if 'nie prowadzi statystyk' in flat else
               'doprecyzowanie' if 'Doprecyzowanie' in kinds else 'udostepnienie')
    if 'Kwerenda' in kinds: outcome += '+kwerenda'
    recs.append({'id': num, 'date': r[4].date().isoformat(), 'title': r[3].strip(), 'applicant_type': None,
                 'request_text': req_text, 'response_text': resp, 'departments': found_deps(resp) or [],
                 'outcome': outcome, 'response_kinds': kinds, 'answered': r[6].date().isoformat() if hasattr(r[6], 'date') else None,
                 'source_files': [f'Wniosek - {num}'] + [f'{k} - {num}.anonymised.pdf' for k in kinds], 'note': note})
MANUAL = {  # ręczne uzupełnienia (Claude, 21.11.2026)
    'BKS.IV.1431.599.2026': (['WE'], 'brak odpowiedzi w próbkach UMB; wydział przyjęty z analogii do sprawy 307.2025'),
    'BKS.IV.1431.15.2026': (['ZEWN-WKZ'], 'odesłanie do Kujawsko-Pomorskiego Wojewódzkiego Konserwatora Zabytków (art. 4 ust. 3 UDIP); data wpływu w arkuszu (12.09) niezgodna z datą odpowiedzi (14.01)'),
}
for x in recs:
    if x['id'] in MANUAL:
        x['departments'], x['note'] = MANUAL[x['id']]
with open(OUT / 'archiwum_umb.jsonl', 'w', encoding='utf-8') as f:
    for x in recs: f.write(json.dumps(x, ensure_ascii=False) + '\n')
for x in recs: print(x['id'], x['date'], x['outcome'], x['departments'], x['title'][:50])
