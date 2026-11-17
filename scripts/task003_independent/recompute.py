#!/usr/bin/env python3
"""Independent TASK-003 sensitivity recomputation; no task003 code imports."""
import csv
import json
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/task002/PET2MOF_Task002_DataPack_v1.0/data'
OUT = ROOT / 'reports/task003/independent'

def read(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

rows = []
def emit(quantity, case, branch, value):
    value = F(value)
    rows.append(dict(quantity=quantity, case=case, branch=branch,
                     value_exact=f'{value.numerator}/{value.denominator}', value_float=float(value)))

materials = {r['sample_id']: r for r in read(DATA / 'primary/S2_materials.csv')}
dry = {r['sample_id']: F(r['q_CO2_dry_mmol_g']) for r in read(DATA / 'primary/S2_dry_CO2.csv')}
methods = read(ROOT / 'data/task003/extracted/S100_methods.csv')
assert all(any(r['quantity'] == q and r['value'] == 'unknown' for r in methods)
           for q in ('PEI molecular weight', 'PEI type', 'PEI loading mass basis'))
base_n = F(materials['S2-BASE']['N_elemental_wt_pct'])
s2 = {}
for name in ('C48', 'C72', 'C96', 'N72', 'I96'):
    case = 'S2-' + name
    m = materials[case]
    W = F(m['mass_gain_pct_of_initial_MOF']) / 100
    h = 1 / (1 + W)
    w = F(m['PEI_content_author_calculated_wt_pct']) / 100
    # Nitrogen mass in composite = N_BASE*h + N_PEI*w.
    reproduced = (F(m['N_elemental_wt_pct']) - base_n*h) / F('30.74')
    emit('PEI_exp_recomputed', case, 'N_W', reproduced)
    emit('PEI_exp_author', case, 'table', w)
    emit('PEI_exp_difference', case, 'N_W_minus_table', reproduced-w)
    for branch, values in {'s-I': (h, w, 1-h-w),
                           's-V': (h/(h+w), w/(h+w), F(0))}.items():
        assert sum(values) == 1 and min(values) >= 0
        s2[case, branch] = values
        for key, v in zip(('h', 'w', 's'), values): emit(key, case, branch, v)
        emit('sum', case, branch, sum(values))

series = defaultdict(list)
for r in read(DATA / 'benchmark/S100_dry_isotherms.csv'):
    series[r['sample_label']].append((F(r['p_bar']), F(r['q_mmol_per_g_reported']), r['point_id']))
q = {}
brackets = {}
p = F('0.896')
for name, points in sorted(series.items()):
    points.sort()
    pairs = [(a, b) for a, b in zip(points, points[1:]) if a[0] <= p <= b[0]]
    assert len(pairs) == 1
    a, b = pairs[0]
    q[name] = a[1] + (p-a[0]) * (b[1]-a[1]) / (b[0]-a[0])
    brackets[name] = [a[2], b[2]]
    emit('q_interpolated_mmol_g', 'S100-'+name, 'reported_basis', q[name])
host = q['UiO-66']
s100 = {}
for label in (10, 20, 30, 40):
    name = f'{label}PEI@UiO-66'
    case = 'S100-'+name
    for wb in ('w-C', 'w-F'):
        w = F(label,100) if wb == 'w-C' else F(label,100+label)
        for bb in ('b-C', 'b-M'):
            branch = wb+';'+bb
            qc = q[name] if bb == 'b-C' else q[name]*(1-w)
            s100[case,branch] = (1-w,w,qc)
            for key,v in (('w',w),('h',1-w),('s',0),('sum',1),('q_comp_mmol_g',qc),('G',qc/host)):
                emit(key,case,branch,v)

def line(case, branch, h, w, qc, qhost):
    for nlabel, n in (('30.74',F('21.95')), ('32.52',F('23.22'))):
        for phi in (0,1):
            eta = (qc-h*phi*qhost)/(w*n)
            emit('eta_line',case,branch+f';N={nlabel};phi={phi}',eta)
for case in ('S2-C72','S2-I96'):
    for branch in ('s-I','s-V'):
        h,w,_=s2[case,branch]
        line(case,branch,h,w,dry[case],dry['S2-BASE'])
for (case,branch),(h,w,qc) in s100.items():
    if case.startswith(('S100-30','S100-40')): line(case,branch,h,w,qc,host)

TOL=F(1,10**12)
def bisect(lo,hi,predicate):
    assert predicate(lo) and not predicate(hi)
    while hi-lo > TOL:
        mid=(lo+hi)/2
        if predicate(mid): lo=mid
        else: hi=mid
    return lo,hi

def boundary1(case,branch,h,G):
    # For fixed k, the affine expression attains its minimum at an endpoint.
    def ok(k):
        return min(h*phi*(1-1/k)+G/k for phi in (0,1)) >= F('1.10')
    lo=F(1,2**10)
    assert ok(lo)
    hi=F(1)
    while ok(hi): hi*=2
    a,b=bisect(lo,hi,ok)
    emit('k_max_lower',case,branch,a); emit('k_max_upper',case,branch,b)
for branch in ('s-I','s-V'):
    boundary1('S2-C72',branch,s2['S2-C72',branch][0],dry['S2-C72']/dry['S2-BASE'])
for (case,branch),(h,w,qc) in s100.items():
    if case.startswith('S100-30'): boundary1(case,branch,h,qc/host)

# Solve over the real line by bracketing first; retain roots outside physical [0,1].
for hname,qhost in (('S2-BASE',dry['S2-BASE']),('S100-UiO-66',host)):
    for nlabel,n in (('30.74',F('21.95')),('32.52',F('23.22'))):
        for eta in (F('0.20'),F('0.30')):
            def below(phi): return F('0.8')*phi*qhost+F('0.2')*n*eta <= F('1.10')*qhost
            lo,hi=F(-1),F(1)
            while not below(lo): lo*=2
            while below(hi): hi*=2
            a,b=bisect(lo,hi,below)
            branch=f'N={nlabel};eta={float(eta):.2f}'
            emit('phi_crit_lower',hname,branch,a);emit('phi_crit_upper',hname,branch,b)

OUT.mkdir(parents=True,exist_ok=True)
with (OUT/'recompute.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=['quantity','case','branch','value_exact','value_float'])
    writer.writeheader();writer.writerows(rows)
metadata = {'task':'T043-task003-independent-recompute', 'status':'provisional conditional sensitivity analysis; not a validated prediction',
 'pressure_bar':'0.896', 'interpolation_brackets_point_ids':brackets,
 'n_N_mmol_g':{'30.74':'21.95','32.52':'23.22'},
 'extraction_ids':{'S2':'T001-S2-02; T001-S2-03; T001-S2-04; T001-S2-05; T001-S2-06; T001-S2-07', 'S100':'T006-S100-FigS5', 'S100_methods':'T040-S100-methods'},
 'inputs':['data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary/S2_materials.csv','data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary/S2_dry_CO2.csv','data/task002/PET2MOF_Task002_DataPack_v1.0/data/benchmark/S100_dry_isotherms.csv','data/task003/extracted/S100_methods.csv'],
 'bisection':'lower and upper rational brackets width <= 1e-12; lower satisfies inequality', 'rows':rows}
(OUT/'recompute.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(rows)} rows; all mass balances exact; bisection widths <= {float(TOL):g}')
