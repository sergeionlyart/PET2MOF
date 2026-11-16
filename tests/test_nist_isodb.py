"""Offline checks against saved NIST responses and independent unit examples."""
import csv
import hashlib
import json
import socket
import sys
import warnings
from pathlib import Path

import pandas as pd
import pytest

from pet2mof.data.nist_isodb import ROOT, fetch, load_isotherm, verify_manifest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Network forbidden in offline tests')
    monkeypatch.setattr(socket.socket, 'connect', blocked)


def test_manifest():
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='Non-redistributed file absent')
        assert verify_manifest()
    rows = list(csv.DictReader((ROOT / 'manifest.csv').open()))
    assert len([r for r in rows if r['filename'].startswith('isotherms/')]) == 296


def test_saved_isotherms():
    rows = list(csv.DictReader((ROOT / 'manifest.csv').open()))
    examples = [next(r for r in rows if r['filename'].startswith('isotherms/')
                and r['pressure_units'] == 'bar' and r['adsorption_units'] == unit
                and ';' not in r['adsorbate']) for unit in ['mmol/g', 'mol/g']]
    assert len(examples) == 2
    for row in examples:
        path = ROOT / row['filename']
        raw = json.loads(path.read_bytes())
        result = load_isotherm(path)
        assert len(result) == len(raw['isotherm_data']) == int(row['n_points'])
        assert result.iloc[0].pressure_bar == raw['isotherm_data'][0]['pressure']
        factor = 1000 if row['adsorption_units'] == 'mol/g' else 1
        assert result.iloc[0].adsorption_mmol_g == pytest.approx(
            raw['isotherm_data'][0]['species_data'][0]['adsorption'] * factor)
        assert result.attrs['DOI'] == row['DOI']


@pytest.fixture
def example(tmp_path):
    raw = json.loads(next(p for p in (ROOT / 'isotherms').glob('*.json')
                         if '.receipt.' not in p.name).read_bytes())
    raw['adsorbates'] = [{'InChIKey': 'CO2', 'name': 'Carbon Dioxide'}]
    raw['isotherm_data'] = [{'pressure': 100, 'total_adsorption': 999,
                             'species_data': [{'InChIKey': 'CO2', 'adsorption': 0.002,
                                               'composition': 1}]}]
    return tmp_path / 'example.json', raw


@pytest.mark.parametrize('unit,value', [('Pa', .001), ('kPa', 1), ('MPa', 1000),
                                        ('atm', 101.325), ('mbar', .1)])
def test_explicit_pressure_units(example, unit, value):
    path, raw = example
    raw.update(pressureUnits=unit, adsorptionUnits='mol/g')
    path.write_text(json.dumps(raw))
    result = load_isotherm(path)
    assert result.iloc[0].pressure_bar == pytest.approx(value)
    assert result.iloc[0].adsorption_mmol_g == pytest.approx(2)


@pytest.mark.parametrize('field,value', [('pressureUnits', 'P/P0'),
    ('pressureUnits', 'mystery'), ('adsorptionUnits', 'cm3/g'),
    ('adsorptionUnits', 'cm3/m2'), ('adsorptionUnits', 'wt%')])
def test_unknown_units_rejected(example, field, value):
    path, raw = example
    raw.update(pressureUnits='bar', adsorptionUnits='mmol/g')
    raw[field] = value
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match='units'):
        load_isotherm(path)


def test_mixture_and_missing_values(example):
    path, raw = example
    raw.update(pressureUnits='bar', adsorptionUnits='mol/kg')
    raw['adsorbates'].append({'InChIKey': 'N2', 'name': 'Nitrogen'})
    raw['isotherm_data'][0]['species_data'].append(
        {'InChIKey': 'N2', 'adsorption': None, 'composition': .9})
    path.write_text(json.dumps(raw))
    result = load_isotherm(path)
    assert len(result) == 2
    assert result.iloc[0].adsorption_mmol_g == .002  # never total_adsorption=999
    assert pd.isna(result.iloc[1].adsorption_mmol_g)
    assert result.iloc[1].composition == .9


@pytest.mark.parametrize('redistributed', ['true', 'false'])
def test_tampering_detected(tmp_path, redistributed):
    payload = b'original response'
    (tmp_path / 'data.json').write_bytes(payload)
    manifest = tmp_path / 'manifest.csv'
    with manifest.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['filename', 'sha256', 'bytes',
                                                    'redistributed', 'reason'])
        writer.writeheader()
        writer.writerow(dict(filename='data.json', sha256=hashlib.sha256(payload).hexdigest(),
                             bytes=len(payload), redistributed=redistributed, reason='Test fixture'))
    assert verify_manifest(manifest)
    (tmp_path / 'data.json').write_bytes(b'changed response')
    with pytest.raises(ValueError, match='Integrity'):
        verify_manifest(manifest)


@pytest.mark.parametrize('redistributed', ['true', 'false'])
def test_manifest_missing_file(tmp_path, redistributed):
    manifest = tmp_path / 'manifest.csv'
    with manifest.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['filename', 'sha256', 'bytes',
                                                    'redistributed', 'reason'])
        writer.writeheader()
        writer.writerow(dict(filename='missing.json', sha256='0' * 64, bytes=0,
                             redistributed=redistributed, reason='Not shipped'))
    if redistributed == 'true':
        with pytest.raises(FileNotFoundError):
            verify_manifest(manifest)
    else:
        with pytest.warns(UserWarning, match='missing.json; Not shipped'):
            assert verify_manifest(manifest)


def test_exact_308_stp_isotherms():
    with (ROOT / 'manifest.csv').open() as stream:
        rows = [r for r in csv.DictReader(stream)
                if r['DOI'] == '10.1016/j.memsci.2012.04.003'
                and r['T_K'] == '308' and r['adsorption_units'] == 'cm3(STP)/g']
    assert rows
    for row in rows:
        path = ROOT / row['filename']
        raw = json.loads(path.read_bytes())
        result = load_isotherm(path)
        expected = [s['adsorption'] / 22.414 for point in raw['isotherm_data']
                    for s in point['species_data']]
        assert result['adsorption_mmol_g'].tolist() == pytest.approx(expected)
        assert result.attrs['temperature'] == 308


def test_fetch_restricts_host(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'requests', None)
    with pytest.raises(ValueError, match='NIST'):
        fetch('https://example.org/no-request', tmp_path / 'data.json')
