"""Lead comparison of the counted TASK-003 run (T042 code) with the independent exact recompute (T043).

T043 used the rounded n_N printed in the plan (21.95 / 23.22 mmol N/g); T042 uses 30.74/32.52 wt% / 14.007. η is
therefore compared through the n_N-free product η·n_N = (q_comp − h·φ·q_host)/w, and k*/φ_crit are compared only
where they do not depend on n_N (k* = G/g) or are reported with the n_N difference explained.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/task003'


def rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    a = ap.parse_args(argv)
    ind = rows(OUT / 'independent/recompute.csv')
    lines = rows(OUT / 'analog_lines.csv')
    kst = rows(OUT / 'transfer_kstar.csv')

    def line(case, branch):
        sid = case.replace('S100-', '') if case.startswith('S100-') else case
        if case.startswith('S100-'):
            wb, bb = branch.split(';')[:2]
            cand = [r for r in lines if r['sample_id'] == sid and r['composition_branch'] == wb
                    and r['mass_basis_branch'] == bb]
        else:
            cand = [r for r in lines if r['sample_id'] == sid and r['composition_branch'] == branch]
        if not cand:
            raise KeyError((case, branch))
        return cand[0]

    checks = []

    def add(kind, case, branch, ind_v, main_v, tol, note=''):
        d = abs(ind_v - main_v)
        checks.append(dict(kind=kind, case=case, branch=branch, independent=ind_v, main=main_v, abs_diff=d,
                           tol=tol, ok=d <= tol, note=note))

    nN_ind = {'30.74': 21.95, '32.52': 23.22}
    for r in ind:
        q, case, br, v = r['quantity'], r['case'], r['branch'], float(r['value_float'])
        if q in ('h', 'w', 's'):
            add(q, case, br, v, float(line(case, br)[q]), 1e-12)
        elif q == 'G':
            add('G', case, br, v, float(line(case, br)['gain_analog']), 1e-12)
        elif q == 'eta_line' and 'N=30.74' in br:
            parts = dict(p.split('=') for p in br.split(';') if '=' in p)
            base = ';'.join(p for p in br.split(';') if '=' not in p)
            L = line(case, base)
            m = float(L['eta_phi0'] if parts['phi'] == '0' else L['eta_phi1']) * float(L['n_n_mmol_g_pei'])
            add('eta_times_nN', case, br, v * nN_ind['30.74'], m, 1e-9,
                'compared as eta*n_N (independent n_N 21.95 rounded; main 21.946)')
        elif q == 'k_max_lower':
            sid = case.replace('S100-', '')
            if case.startswith('S100-'):
                wb, bb = br.split(';')[:2]
                cand = [k for k in kst if k['sample_id'] == sid and k['composition_branch'] == wb
                        and k['mass_basis_branch'] == bb and abs(float(k['g']) - 1.1) < 1e-12]
            else:
                cand = [k for k in kst if k['sample_id'] == sid and k['composition_branch'] == br
                        and abs(float(k['g']) - 1.1) < 1e-12]
            add('kstar_g1.10', case, br, v, float(cand[0]['registered_kstar_G_over_g']), 1e-11,
                'independent: bisection lower end, width <= 1e-12')
    worst = max(c['abs_diff'] for c in checks)
    res = dict(run_id=a.run_id, n_checks=len(checks), n_failed=sum(not c['ok'] for c in checks),
               worst_abs_diff=worst, not_compared=[
                   'phi_crit (independent used rounded n_N 21.95/23.22; differences ~1e-4 explained by n_N only)',
                   'eta lines at N=32.52 (same algebra as 30.74; n_N convention differs)'],
               checks=checks)
    (OUT / 'independent_agreement.json').write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')
    print(f"checks={res['n_checks']} failed={res['n_failed']} worst={worst:.3e}")
    return 1 if res['n_failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
