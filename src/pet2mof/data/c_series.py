"""T011 JSON contract. Select whole series before opening any data files."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROLES = {'C', 'C_candidate', 'context_GO', 'sensitivity_only'}
SOURCES = {'S100', 'S105', 'S106'}
SENSITIVITY_PREFIXES = {
    'NIST-10.1021acs.inorgchem.5b00435': 'SENS-NIST-10-1021acs-inorgchem-5b00435-',
    'NIST-10.1039C2cp23839j': 'SENS-NIST-10-1039C2cp23839j-',
    'NIST-10.1021Ie202325p': 'SENS-NIST-10-1021Ie202325p-',
}


def load_series(root, *, sources, roles=('C', 'C_candidate'), debug=False):
    root = Path(root).resolve()
    if not set(sources) <= SOURCES | set(SENSITIVITY_PREFIXES) or not set(roles) <= ROLES:
        raise ValueError('explicit permitted C source/role selection required')
    folder = root / 'data/processed/c_series'
    manifest = json.loads((folder / 'manifest.json').read_text())
    frames = []
    for key, item in manifest['series'].items():
        if item['role'] not in roles:
            continue
        # T011 series_id encodes source; no discovery of external numerical data.
        if not any(key.startswith(SENSITIVITY_PREFIXES.get(source, 'C-' + source + '-')) for source in sources):
            continue
        path = (folder / (key + '.csv')).resolve()
        path.relative_to(folder)
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['csv_sha256']:
            raise ValueError('C CSV hash mismatch: ' + key)
        f = pd.read_csv(path)
        if list(f.columns) != manifest['fields'] or len(f) != item['rows']:
            raise ValueError('T011 CSV schema/row mismatch')
        if set(f.series_id) != {key} or not set(f.source_id) <= set(sources):
            raise ValueError('C identity mismatch')
        if not set(f.status) <= {'verified', 'provisional', 'excluded'}:
            raise ValueError('unknown C status')
        if not debug and (item['role'] != 'C' or set(f.status) != {'verified'}):
            raise ValueError('unverified/candidate series requires explicit debug mode')
        if f[['extraction_id', 'material', 'gas', 'data_kind']].isna().any().any():
            raise ValueError('C provenance missing')
        numeric = f[['p_bar', 'T_K', 'q_mmol_g']].to_numpy(float)
        if not np.isfinite(numeric).all() or np.any(numeric < 0) or np.any(f.T_K <= 0):
            raise ValueError('invalid C coordinates')
        f['role'] = item['role']
        f['input_path'] = path.relative_to(root).as_posix()
        f['input_sha256'] = item['csv_sha256']
        frames.append(f)
    if not frames:
        raise ValueError('no permitted C series selected')
    return pd.concat(frames, ignore_index=True)


def standard_errors(frame, derivative):
    """CSV errors are bounds of uniform laws, never fabricated standard errors."""
    q, p = (frame[k].to_numpy(float) for k in ('q_err_mmol_g', 'p_err_bar'))
    if not np.isfinite([q, p]).all() or np.any(q <= 0) or np.any(p < 0):
        raise ValueError('unknown or invalid CSV uncertainty; sensitivity only')
    return np.sqrt((q*q + (np.asarray(derivative)*p)**2)/3)
