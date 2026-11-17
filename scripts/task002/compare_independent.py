#!/usr/bin/env python3
"""Compare Part A (T030, closed form, floats) with the independent recompute (T033, exact fractions,
vertex enumeration, bisection). Writes reports/task002/A/independent_agreement.json."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOL = 1e-10  # metadata/analysis_contract.json numerical_check_abs_tol


def main(argv):
    run_id = argv[argv.index('--run-id') + 1] if '--run-id' in argv else 'debug-unregistered'
    ind = json.loads((ROOT / 'reviews/T033-control/recompute.json').read_text(encoding='utf-8'))
    a_dir = ROOT / 'reports/task002/A'
    pairs = {(r['sample_a'], r['sample_b']): r for r in csv.DictReader((a_dir / 'pairwise.csv').open(encoding='utf-8'))}
    nominal = {r['sample_id']: r for r in csv.DictReader((a_dir / 'nominal.csv').open(encoding='utf-8'))}
    rows, worst, flag_mismatch = [], 0.0, 0
    for key, c in sorted(ind['comparisons'].items()):
        a, b = key.split('/')
        r = pairs[(a, b)]
        diffs = {'ratio': abs(float(c['ratio']['decimal']) - float(r['q_ratio']))}
        for d in ('0.03', '0.05', '0.10'):
            s = c['scenarios'][d] if d in c['scenarios'] else c['scenarios'][str(float(d))]
            diffs[f'low_{d}'] = abs(float(s['ratio_min']['decimal']) - float(r[f'ratio_low_d_{d}']))
            diffs[f'high_{d}'] = abs(float(s['ratio_max']['decimal']) - float(r[f'ratio_high_d_{d}']))
            flag_mismatch += s['a_above_b'] != (r[f'robust_A_gt_B_d_{d}'] == 'True')
        m = max(diffs.values())
        worst = max(worst, m)
        rows.append({'pair': key, 'max_abs_diff': m})
    for sid, s in sorted(ind['samples'].items()):
        r = nominal[sid]
        m = max(abs(float(s['gain_percent']['decimal']) - float(r['gain_vs_base_pct'])),
                abs(float(s['inventory_kg']['decimal']) - float(r['adsorbent_kg_per_kg_CO2_equilibrium_proxy'])))
        worst = max(worst, m)
        rows.append({'sample': sid, 'max_abs_diff_gain_pct_or_inventory_kg': m})
    out = {'run_id': run_id, 'methods': {'T030': 'closed form, IEEE floats (src/pet2mof/task002/screening.py)',
                                         'T033': 'exact fractions, interval vertex enumeration, bisection thresholds'},
           'tolerance': TOL, 'worst_abs_diff': worst, 'robustness_flag_mismatches': flag_mismatch,
           'passed': worst <= TOL and flag_mismatch == 0, 'rows': rows,
           'scope': 'arithmetic agreement of two independent implementations; not validation of measurements'}
    (a_dir / 'independent_agreement.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('worst_abs_diff', 'robustness_flag_mismatches', 'passed')}))
    return 0 if out['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
