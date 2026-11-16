"""Explicit NIST downloads and offline ISODB loading; no network at import time."""
from __future__ import annotations

import csv
import hashlib
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin, urlencode

import pandas as pd

from pet2mof.units import convert_capacity, convert_pressure

ROOT = Path(__file__).resolve().parents[3] / 'data/raw/nist_isodb'
PRESSURE_TO_BAR = {unit: convert_pressure(1, unit, 'bar') for unit in
                   ('bar', 'Pa', 'kPa', 'MPa', 'mbar', 'atm', 'Torr', 'mmHg')}
ADSORPTION_TO_MMOL_G = {unit: convert_capacity(1, unit, 'mmol/g') for unit in
                         ('mmol/g', 'mol/kg', 'mol/g', 'mmol/kg', 'cm3(STP)/g')}


def fetch(url: str, path: str | Path, *, timeout: float = 60, data: dict | None = None) -> dict:
    """Save response bytes unchanged, refusing overwrite and non-NIST redirects.

    Requires the optional ``fetch`` extra. Returns provenance for manifest.csv;
    never called implicitly.
    TLS verification remains enabled. Hosts are restricted to the task's NIST scope.
    """
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    original_url = url
    for _ in range(6):
        parsed = urlparse(url)
        if (parsed.scheme != 'https' or parsed.hostname not in
                {'adsorption.nist.gov', 'www.nist.gov'} or parsed.username or
                parsed.password or parsed.port not in (None, 443)):
            raise ValueError('Only HTTPS NIST URLs without credentials are permitted')
        import requests

        response = requests.request('POST' if data is not None else 'GET', url,
                                    data=data, timeout=timeout, allow_redirects=False)
        response.raise_for_status()
        if response.is_redirect:
            url = urljoin(url, response.headers['Location'])
            continue
        payload = response.content
        if path.suffix == '.json':
            json.loads(payload)  # reject HTML error pages before writing
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(payload)
        return {'filename': path.name, 'url': original_url,
                'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
                'accessed_utc': datetime.now(timezone.utc).isoformat(),
                'http_method': 'POST' if data is not None else 'GET',
                'request_body': '' if data is None else urlencode(data)}
    raise ValueError('Too many redirects')


def load_isotherm(path: str | Path) -> pd.DataFrame:
    """Long-form species uptake, preserving input order and mixture composition.

    pressure_bar is TOTAL pressure (not partial pressure). adsorption_mmol_g is
    species uptake, never total mixture uptake. Original metadata lives in attrs.
    Explicit cm3(STP)/g uses pet2mof.units' ideal-gas convention: 273.15 K,
    101.325 kPa, V_m = RT/P rounded to 22.414 cm3/mmol. This reference
    temperature is independent of the isotherm measurement temperature.
    Unsupported/ambiguous units (including relative pressure, cm3/g and cm3/m2)
    raise ValueError. Missing numerical values stay NaN; no smoothing or sorting.
    """
    raw = json.loads(Path(path).read_bytes())
    try:
        pf = PRESSURE_TO_BAR[raw['pressureUnits']]
        qf = ADSORPTION_TO_MMOL_G[raw['adsorptionUnits']]
    except KeyError as exc:
        raise ValueError(f'Unsupported or missing units: {raw.get("pressureUnits")!r}, '
                         f'{raw.get("adsorptionUnits")!r}') from exc
    names = {s['InChIKey']: s['name'] for s in raw['adsorbates']}
    rows = []
    for i, point in enumerate(raw['isotherm_data']):
        for species in point['species_data']:
            key = species['InChIKey']
            rows.append({'point_index': i, 'pressure_bar': point['pressure'],
                         'adsorption_mmol_g': species.get('adsorption'),
                         'adsorbate': names[key], 'InChIKey': key,
                         'composition': species.get('composition')})
    frame = pd.DataFrame(rows, columns=['point_index', 'pressure_bar',
                         'adsorption_mmol_g', 'adsorbate', 'InChIKey', 'composition'])
    frame['pressure_bar'] = pd.to_numeric(frame['pressure_bar'], errors='raise') * pf
    frame['adsorption_mmol_g'] = pd.to_numeric(frame['adsorption_mmol_g'], errors='raise') * qf
    frame.attrs = {k: v for k, v in raw.items() if k != 'isotherm_data'}
    frame.attrs['conversion'] = {'pressure_to_bar': pf, 'adsorption_to_mmol_g': qf}
    return frame


def verify_manifest(path: str | Path | None = None) -> bool:
    """Verify SHA-256 and lengths offline; required missing files raise.

    Missing non-redistributed files emit a warning. If present, their integrity
    is checked too. Redistribution flags must be explicit lowercase booleans.
    """
    path = Path(path) if path is not None else ROOT / 'manifest.csv'
    root = path.parent.resolve()
    seen = set()
    with path.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError('Empty manifest')
    for row in rows:
        target = (root / row['filename']).resolve()
        if not target.is_relative_to(root) or target in seen:
            raise ValueError('Duplicate or out-of-root manifest path')
        seen.add(target)
        if row['redistributed'] not in ('true', 'false'):
            raise ValueError(f'Invalid redistributed flag: {row["filename"]}')
        if row['redistributed'] == 'false' and not target.exists():
            warnings.warn(f'Non-redistributed file absent: {row["filename"]}; '
                          f'{row["reason"]}', UserWarning, stacklevel=2)
            continue
        payload = target.read_bytes()
        if (hashlib.sha256(payload).hexdigest() != row['sha256'] or
                len(payload) != int(row['bytes'])):
            raise ValueError(f'Integrity mismatch: {row["filename"]}')
    return True
