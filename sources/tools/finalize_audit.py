"""Classify saved responses and write audit provenance, without network requests."""
import csv
import hashlib
import json
import platform
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import fitz
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / 'sources'
DATE = '2026-11-16'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(path):
    raw = path.read_bytes()
    if path.suffix == '.json':
        json.loads(raw)
        return 'validated_json'
    if path.suffix == '.xml':
        root = ElementTree.fromstring(raw)
        assert root.tag == 'article', 'not a JATS article'
        return 'validated_article_xml'
    if path.suffix == '.pdf':
        if not raw.startswith(b'%PDF-'):
            return 'rejected_non_pdf_response'
        with fitz.open(path) as doc:
            assert len(doc) > 0
        return 'validated_pdf'
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
        return 'validated_zip'
    if path.suffix == '.jpg':
        assert raw.startswith(b'\xff\xd8\xff')
        return 'validated_jpeg'
    return 'rejected_challenge_html'


attempts_path = SOURCES / 'access_attempts.csv'
manifest_path = SOURCES / 'downloads_manifest.csv'
# Preserve the complete original request log. Reruns use it rather than the
# filtered manifest, so failed attempts remain visible.
origin = attempts_path if attempts_path.exists() else manifest_path
with origin.open(newline='') as handle:
    reader = csv.DictReader(handle)
    fields = reader.fieldnames
    attempts = list(reader)
accepted = {}
for row in attempts:
    row['accessed'] = row['accessed'] or DATE
    if not row['path']:
        continue
    path = ROOT / row['path']
    assert path.is_relative_to(ROOT) and path.exists()
    assert digest(path) == row['sha256'], f'Changed download: {path}'
    row['status'] = classify(path)
    if row['status'].startswith('validated_'):
        canonical = dict(row)
        canonical['source_id'] = re.match(r'S\d+', row['source_id']).group()
        accepted[row['path']] = canonical
for target, rows in [(attempts_path, attempts), (manifest_path, list(accepted.values()))]:
    with target.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

registry_path = SOURCES / 'registry.yaml'
registry = yaml.safe_load(registry_path.read_text())
visual = {
    'S2': 'Original publisher Fig. 6 and Fig. 9 JPEGs inspected; Table 1/2 JATS text only, page QA pending.',
    'S100': 'Rendered SI PDF pages 3,7,8,9 inspected: methods, S4-S8, Table S1.',
    'S103': 'Original Fig. 2 JPEG inspected; experimental panel a versus simulation b; cm3(STP)/g axis.',
    'S106': 'Rendered PDF page 5 inspected (article p. 4): Fig. 3/4, Table 1.',
    'S113': 'Original Fig. 5 JPEG inspected; SI not downloaded.',
    'S116': 'Rendered PDF pages 3,5,6 inspected: Table 2, Fig. 6, Table 3.',
}
passports = []
for source in registry:
    sid = source['source_id']
    inputs = [{k: entry[k] for k in ('path', 'url', 'sha256', 'status')}
              for entry in accepted.values() if entry['source_id'] == sid]
    derivatives = []
    for folder in ['data/raw/html', 'data/raw/figures_full']:
        for path in sorted((ROOT / folder).glob(sid + '*')):
            if re.match(rf'{sid}(?:_|\.)', path.name) and (
                path.suffix == '.png' or path.name.endswith('.text.txt')
            ):
                derivatives.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path)})
    for record in [source] + source['data_items']:
        is_audit = record is source
        canonical = json.dumps(record, sort_keys=True, ensure_ascii=False).encode()
        passports.append({
            'extraction_id': record['extraction_id'],
            'source_id': sid,
            'doi': source['doi'],
            'url': source['url'],
            'evidence_urls': source.get('evidence_urls', [source['url']]),
            'date': DATE,
            'operation': 'source_metadata_and_applicability_audit' if is_audit else 'locate_data_and_read_conditions',
            'locator': 'Crossref; source methods and locators enumerated in registry' if is_audit else record['where'],
            'pdf_page_mapping': 'Explicit page numbers retained in locator where inspected; otherwise unknown/not applicable (HTML/JATS).',
            'api_page_mapping': 'not applicable; no OCR API',
            'inputs': inputs,
            'unhashed_web_inputs': 'Browser-rendered/indexed publisher text has no retained raw response hash; use evidence URLs. Metadata hash does not authenticate full text.',
            'tools': {
                'python': platform.python_version(), 'PyMuPDF': fitz.VersionBind,
                'PyYAML': yaml.__version__,
                'web_search_and_open': 'provider version not disclosed',
                'manual_review': 'source text and original figures; no digitization',
            },
            'parameters': {'paid_OCR': False, 'coordinate_extraction': False,
                           'unit_conversion': False, 'model_fitting': False,
                           'pdf_preview': 'PyMuPDF page rendering, unmodified science content'},
            'original_responses': 'Immutable downloaded bytes listed in inputs; failed/challenge responses recorded in access_attempts.csv.',
            'local_derivatives': derivatives,
            'output': {'path': 'sources/registry.yaml', 'registry_sha256': digest(registry_path),
                       'record_canonical_json_sha256': hashlib.sha256(canonical).hexdigest()},
            'unit_conversions': [],
            'error_estimate': 'No numeric capacity or figure coordinates extracted. Reading/metadata uncertainties remain categorical and are listed in limitations.',
            'visual_QA': visual.get(sid, 'Original page/figure visual QA not completed; text or metadata audit only.'),
            'status': 'provisional', 'reviewer': 'T004 (assigned, not executed in T001)',
            'corrections': source['limitations'] if is_audit else [],
        })
output = ROOT / 'data/extraction/T001-source-audit.yaml'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(yaml.safe_dump({'task_id': 'T001-source-audit', 'passports': passports},
                                 allow_unicode=True, sort_keys=False, width=110))
print(json.dumps({'accepted_downloads': len(accepted), 'access_attempts': len(attempts),
                  'passports': len(passports)}, ensure_ascii=False))
