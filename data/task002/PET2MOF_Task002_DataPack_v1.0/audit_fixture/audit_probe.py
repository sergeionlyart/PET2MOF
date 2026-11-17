"""Synthetic interface regression probe. NOT new scientific measurements.
Run: python audit_probe.py. Uses the unmodified evaluate function in the excerpt.
"""
import json
import math
from pathlib import Path
from prediction_excerpt import evaluate

sample = {
    'fits': [{'model_version': 'v1', 'interpretation': 'composite', 'T_fit': 298.,
              'models': {'M1': {'parameters': {'kappa': 0.5}}}}],
    'c_fits': {'carriers': [{'material': 'UiO-66-NH2', 'gas': 'CO2',
                           'Q': 20000., 'T_ref': 298., 'b': 1., 'q_sat': 2.}]}
}
row = {'material': 'PEI@UiO-66-NH2', 'gas': 'CO2', 'observable': 'Vp_ratio_to_w0',
       'basis': 'dry_sorbent', 'unit': '1', 'w_PEI': 0.2, 'w_reading': 'retained',
       'source_id': 'synthetic_audit', 'T_K': 298.}
results = []
for name, changes in [
    ('missing_RH_and_pressure', {}),
    ('missing_pressure', {'RH_fraction': 0.}),
    ('complete_pressure_0.01', {'RH_fraction': 0., 'p_partial_bar': 0.01}),
    ('complete_pressure_100', {'RH_fraction': 0., 'p_partial_bar': 100.}),
    ('porosimetry_temperature_77K', {'RH_fraction': 0., 'p_partial_bar': 1., 'T_K': 77.}),
]:
    try:
        value = evaluate(dict(row, **changes), sample, 'M1/v1/composite')
        results.append({'case': name, 'status': 'computed', 'value': value})
    except ValueError as exc:
        results.append({'case': name, 'status': 'blocked', 'reason': str(exc)})
expected = 1 - row['w_PEI'] - 0.5 * row['w_PEI']
assert results[0]['reason'] == 'unknown RH_fraction'
assert results[1]['reason'] == 'unknown p_partial_bar'
assert math.isclose(results[2]['value'], expected)
assert math.isclose(results[3]['value'], expected)
assert results[4]['reason'] == 'PEI temperature coefficient unknown'
report = {
    'source_commit': '66bae26af9970c3142b72d25031c844b5461708f',
    'scope': 'Exact published _number/evaluate excerpt; synthetic input; no full repository run',
    'expected_pore_ratio_by_implemented_formula': expected,
    'observed': results,
    'conclusion': 'Pore-ratio evaluation is unnecessarily gated by gas RH, partial pressure and PEI isotherm temperature; this does NOT establish empirical validity of the pore formula.'
}
Path(__file__).with_name('probe_results.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
