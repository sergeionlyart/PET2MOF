#!/usr/bin/env python3
"""Fetch only the pinned, lawful source inputs needed by extract_holdout_v1.py.

No credentials, browser challenge handling, model imports or reviewer exports.
Cached inputs are accepted only by SHA-256. An HTTP error stops the fetch.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'data/extraction/digitization/T019-work/access.json'
LOG = ROOT / 'private/T019b/fetch-log.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    entries = json.loads(MANIFEST.read_text())
    log = []
    LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        for source in ['S113', 'S103', 'S102', 'S2_xml', 'S117_SI']:
            entry = next(e for e in entries if e['source_id'] == source and
                         (e.get('valid_pdf') or source == 'S2_xml'))
            dest = ROOT / entry['path']
            if dest.exists() and sha(dest) == entry['sha256']:
                log.append(dict(source=source, status='cached_hash_verified', sha256=sha(dest)))
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = LOG.parent / (source + '-fetch.download')
            run = subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                '--max-time', '60', '--output', str(temp), entry['url']], capture_output=True, text=True)
            event = dict(source=source, url=entry['url'], exit_code=run.returncode,
                         downloaded_sha256=sha(temp) if temp.exists() else None)
            log.append(event)
            if run.returncode:
                raise RuntimeError(f'{source}: download failed (exit {run.returncode}); no bypass attempted')
            if entry.get('archive_member'):
                with zipfile.ZipFile(temp) as archive:
                    payload = archive.read(entry['archive_member'])
            else:
                payload = temp.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != entry['sha256']:
                raise RuntimeError(f'{source}: source hash mismatch; extraction refused')
            dest.write_bytes(payload)
            event.update(status='downloaded_hash_verified', input_sha256=digest)
    finally:
        LOG.write_text(json.dumps(log, indent=2) + '\n')
    print('All required source hashes verified; fetch log: private/T019b/fetch-log.json')


if __name__ == '__main__':
    main()
