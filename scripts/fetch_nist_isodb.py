#!/usr/bin/env python3
"""Explicit acquisition: python scripts/fetch_nist_isodb.py (NIST hosts only).

Resume uses per-file receipts and never overwrites existing raw responses.
"""
import csv
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pet2mof.data.nist_isodb import ROOT, fetch

API = 'https://adsorption.nist.gov/isodb/api/'
FIELDS = ['filename', 'url', 'sha256', 'bytes', 'accessed_utc', 'DOI',
          'articleSource', 'material', 'adsorbate', 'T_K', 'pressure_units',
          'adsorption_units', 'n_points', 'category', 'digitizer', 'tabular_data',
          'extraction_id', 'status', 'http_method', 'request_body',
          'redistributed', 'reason']
GASES = {'CURLTUGMZLYLDI-UHFFFAOYSA-N', 'IJGRMHOSHXDMSA-UHFFFAOYSA-N',
         'XLYOFNOQVPJJNP-UHFFFAOYSA-N'}


def acquire(relative, url, data=None):
    path = ROOT / relative
    receipt = path.with_suffix('.receipt.json')
    if path.exists():
        if not receipt.exists():
            manifest = ROOT / 'manifest.csv'
            if manifest.exists():
                with manifest.open(newline='', encoding='utf-8') as stream:
                    for row in csv.DictReader(stream):
                        if row['filename'] == relative:
                            payload = path.read_bytes()
                            if (hashlib.sha256(payload).hexdigest() != row['sha256'] or
                                    len(payload) != int(row['bytes'])):
                                raise ValueError(f'Integrity mismatch: {relative}')
                            return {key: row[key] for key in FIELDS[:5] + ['http_method', 'request_body']}
            raise RuntimeError(f'Missing acquisition receipt: {relative}')
        row = json.loads(receipt.read_text())
        payload = path.read_bytes()
        if (hashlib.sha256(payload).hexdigest() != row['sha256'] or
                len(payload) != int(row['bytes'])):
            raise ValueError(f'Integrity mismatch: {relative}')
        return row
    for attempt in range(3):
        try:
            row = fetch(url, path, data=data)
            row['filename'] = relative
            receipt.write_text(json.dumps(row, indent=2) + '\n')
            return row
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def main():
    rows = [acquire(f'catalogs/{n}.json', API + n + '.json')
            for n in ['materials', 'gases', 'isotherms', 'version']]
    materials = json.loads((ROOT / 'catalogs/materials.json').read_bytes())
    catalog = json.loads((ROOT / 'catalogs/isotherms.json').read_bytes())
    selected = []
    for m in materials:
        names = ' '.join([m['name']] + m['synonyms'])
        norm = re.sub('[^a-z0-9]', '', names.lower())
        if 'uio66' in norm or re.search(r'zr.?bdc', names, re.I):
            selected.append(m)
    hashes = {m['hashkey'] for m in selected}
    isotherms = [x for x in catalog if x['adsorbent']['hashkey'] in hashes
                 and 273 <= float(x['temperature'] or 0) <= 323
                 and any(g['InChIKey'] in GASES for g in x['adsorbates'])]
    jobs = [(f'materials/{m["hashkey"]}.json', API + 'material/' + m['hashkey'] + '.json')
            for m in selected]
    jobs += [(f'isotherms/{x["filename"]}.json', API + 'isotherm/' + quote(x['filename'], safe='') + '.json')
             for x in isotherms]
    jobs += [(f'bibliography/{doi.replace("/", "_")}.json', API + 'biblio/' + quote(doi, safe='/') + '.json')
             for doi in sorted({x['DOI'] for x in isotherms})]
    jobs += [('docs/api_reference.html', 'https://adsorption.nist.gov/isodb/functions.php?f=include_page', {'page': 'apis'}),
             ('docs/site.html', 'https://adsorption.nist.gov/isodb/index.php'),
             ('docs/project.html', 'https://www.nist.gov/programs-projects/nist-data-resources-adsorption'),
             ('docs/copyright.html', 'https://www.nist.gov/copyrights-disclaimers')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, row in enumerate(pool.map(lambda j: acquire(*j), jobs), 1):
            rows.append(row)
            if i % 40 == 0:
                print(f'{i}/{len(jobs)} responses saved', flush=True)
    for row in rows:
        if row['filename'].startswith('catalogs/'):
            row.update(redistributed='false', reason='Large catalog; reacquirable via NIST API')
        elif row['filename'].startswith('docs/'):
            row.update(redistributed='false', reason='Web documentation may embed third-party tokens; not needed for reproduction')
        else:
            row.update(redistributed='true', reason='Redistributed raw API response for offline reproduction')
        row['http_method'] = row.get('http_method') or 'GET'
        row.setdefault('request_body', '')
        if not row['filename'].startswith('isotherms/'):
            continue
        x = json.loads((ROOT / row['filename']).read_bytes())
        row.update(DOI=x.get('DOI', ''), articleSource=x.get('articleSource', ''),
                   material=x['adsorbent']['name'],
                   adsorbate=';'.join(g['name'] for g in x['adsorbates']),
                   T_K=x['temperature'], pressure_units=x.get('pressureUnits', ''),
                   adsorption_units=x.get('adsorptionUnits', ''),
                   n_points=len(x['isotherm_data']), category=x.get('category', ''),
                   digitizer=x.get('digitizer', ''), tabular_data=x.get('tabular_data', ''),
                   extraction_id='T002-' + Path(row['filename']).stem, status='provisional')
    with (ROOT / 'manifest.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: r['filename']))
    for receipt in ROOT.rglob('*.receipt.json'):
        receipt.unlink()  # generated receipts are consolidated into manifest.csv
    print(f'Manifest: {len(rows)} responses; {len(isotherms)} isotherms; {len(selected)} materials')


if __name__ == '__main__':
    main()
