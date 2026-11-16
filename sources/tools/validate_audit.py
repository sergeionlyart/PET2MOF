"""Offline artifact integrity checks, not a substitute for scientific review."""
import csv
import hashlib
import html
import json
import re
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


def clean(value):
    text = BeautifulSoup(value, 'html.parser').get_text() if '<' in value else value
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


registry_path = ROOT / 'sources/registry.yaml'
registry = yaml.safe_load(registry_path.read_text())
required = set('source_id doi doi_verified url oa_url title authors year journal license accessed files_available materials conditions data_items role_candidate limitations'.split())
ids = set()
extractions = {}
verified = 0
core = []
for row in registry:
    sid = row['source_id']
    check(sid not in ids, f'{sid}: duplicate source_id')
    ids.add(sid)
    check(required <= set(row), f'{sid}: missing required fields {required - set(row)}')
    check(row['accessed'] == '2026-11-16', f'{sid}: wrong access date')
    check(row['role_candidate'] in {'calibration', 'validation', 'analog', 'context', 'novelty_check'}, f'{sid}: role')
    check(row['status'] == 'provisional', f'{sid}: independent review not performed')
    if row['doi_verified']:
        verified += 1
        path = ROOT / row['doi_evidence']
        evidence = json.loads(path.read_text())['message']
        check(row['doi'].lower() == evidence['DOI'].lower(), f'{sid}: DOI mismatch')
        check(row['title'] == clean(evidence['title'][0]), f'{sid}: title mismatch')
        check(row['year'] == evidence['published']['date-parts'][0][0], f'{sid}: year mismatch')
        authors = [clean(a.get('given', '') + ' ' + a.get('family', a.get('name', '')))
                   for a in evidence.get('author', [])[:3]]
        if len(evidence.get('author', [])) > 3:
            authors.append('et al.')
        check(row['authors'] == authors, f'{sid}: authors mismatch')
        journal = clean(evidence['container-title'][0]) if evidence.get('container-title') else 'SSRN preprint'
        check(row['journal'] == journal, f'{sid}: journal mismatch')
    if row.get('acceptance_core_measured_UiO_CO2'):
        core.append(sid)
        check(any('CO2' in x['what'] and x['data_type'] in {'figure_only', 'table_numeric'}
                  and x['evidence_kind'].startswith(('experimental', 'reported_experimental'))
                  for x in row['data_items']), f'{sid}: core lacks located experimental CO2')
    for record in [row] + row['data_items']:
        eid = record['extraction_id']
        check(eid not in extractions, f'{eid}: duplicate extraction_id')
        extractions[eid] = record
        if record is not row:
            check(set('what where data_type conditions normalization'.split()) <= set(record), f'{eid}: missing item fields')
            check(bool(re.search(r'Figs?\.|Table', record['where'])), f'{eid}: no figure/table locator')
            check(record['data_type'] in {'table_numeric', 'figure_only', 'author_fit', 'simulation', 'text_value'}, f'{eid}: data_type')
check(verified >= 12, 'Fewer than 12 Crossref-verified DOIs')
check(len(core) >= 6, 'Fewer than six located experimental UiO-family CO2 sources')
passports = yaml.safe_load((ROOT / 'data/extraction/T001-source-audit.yaml').read_text())['passports']
check({p['extraction_id'] for p in passports} == set(extractions), 'Passport/registry ID mismatch')
for passport in passports:
    eid = passport['extraction_id']
    check(passport['output']['registry_sha256'] == sha(registry_path), f'{eid}: stale registry hash')
    canonical = json.dumps(extractions[eid], sort_keys=True, ensure_ascii=False).encode()
    check(passport['output']['record_canonical_json_sha256'] == hashlib.sha256(canonical).hexdigest(), f'{eid}: record hash')
    for entry in passport['inputs'] + passport['local_derivatives']:
        path = ROOT / entry['path']
        check(path.exists() and sha(path) == entry['sha256'], f'{eid}: input/derivative hash {path.name}')
with (ROOT / 'sources/downloads_manifest.csv').open(newline='') as handle:
    manifest = list(csv.DictReader(handle))
for entry in manifest:
    path = ROOT / entry['path']
    check(entry['source_id'] in ids, f'Manifest unknown source {entry["source_id"]}')
    check(path.exists() and sha(path) == entry['sha256'], f'Manifest hash {entry["path"]}')
    check(path.stat().st_size == int(entry['bytes']), f'Manifest size {entry["path"]}')
    check(entry['status'].startswith('validated_'), f'Manifest contains rejected response {entry["path"]}')
    check(entry['accessed'] == '2026-11-16', f'Manifest date {entry["path"]}')
check('Отсутствующие данные' in (ROOT / 'sources/audit_report.md').read_text(), 'Missing data-gaps section')
report = {'date': '2026-11-16', 'status': 'pass' if not errors else 'fail',
          'records': len(registry), 'crossref_verified': verified,
          'located_measured_UiO_CO2_sources': core, 'data_items': sum(len(r['data_items']) for r in registry),
          'passports': len(passports), 'validated_downloads': len(manifest),
          'checks': ['required fields, roles, types, locators and unique IDs',
                     'DOI/title/authors/year/journal against saved Crossref responses',
                     'minimum source counts with located experimental CO2 evidence',
                     'complete provenance IDs and registry/record hashes',
                     'all saved input and derivative hashes; manifest sizes and dates',
                     'explicit missing-data report section'],
          'scientific_independent_review': 'T004 source review completed; T009 registry changes pending lead review', 'errors': errors}
(ROOT / 'sources/validation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(1 if errors else 0)
