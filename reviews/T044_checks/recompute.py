"""Independent TASK003 arithmetic. Standard library only; no production imports.

Run from repository root: python3 reviews/T044_checks/recompute.py
All numbers are deterministic checks/scenarios, not new measurements.
"""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACK = ROOT / 'data/task002/PET2MOF_Task002_DataPack_v1.0/data'
N = 307.4 / 14.007
errors = []
counts = {}
maxdiff = {}


def read(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))


def check(group, actual, expected, context='', tol=1e-9):
    counts[group] = counts.get(group, 0) + 1
    if isinstance(expected, (float, int)) and not isinstance(expected, bool):
        delta = abs(float(actual) - expected)
        maxdiff[group] = max(maxdiff.get(group, 0), delta)
        ok = delta <= tol
    else:
        ok = actual == expected
    if not ok:
        errors.append(dict(group=group, context=context, actual=actual, expected=expected))


def eta(q, q0, h, w, phi):
    return (q - h * phi * q0) / (w * N)


def interval(q, q0, h, w, ceiling):
    if not w:
        p = q / (h * q0)
        return (p, p) if 0 <= p <= 1 else None
    lo = max(0., (q - w * N * ceiling) / (h * q0))
    hi = min(1., q / (h * q0))
    return (lo, hi) if lo <= hi else None


def threshold(G, h, phi, g):
    a = h * phi
    if g == a:
        return math.inf if G >= a else 0.
    return max(0., (G - a) / (g - a))


def interp(points, p):
    points = sorted(points)
    assert points[0][0] <= p <= points[-1][0]
    for (x0,y0),(x1,y1) in zip(points,points[1:]):
        if x0 <= p <= x1:
            return y0 + (p-x0) * (y1-y0)/(x1-x0)
    raise AssertionError('unsupported pressure')


materials = read(PACK / 'primary/S2_materials.csv')
dry = {r['sample_id']: float(r['q_CO2_dry_mmol_g']) for r in read(PACK/'primary/S2_dry_CO2.csv')}
recs = {}
formula = []
third_readings = []
for r in materials:
    sample = r['sample_id']
    W = float(r['mass_gain_pct_of_initial_MOF'])/100
    nc = float(r['N_elemental_wt_pct'])/100
    w = float(r['PEI_content_author_calculated_wt_pct'])/100
    h = 1/(1+W)
    s = 1-h-w
    calc = ((1+W)*nc-.05)/(.3074*(1+W))
    corners = [((1+W+dW)*(nc+dN)-(.05+dN0))/(.3074*(1+W+dW))
               for dW,dN,dN0 in itertools.product((-.005,.005),(-.0005,.0005),(-.0005,.0005)) if W+dW>=0]
    if sample == 'S2-BASE': corners = [0.]
    check('formula_rounding_overlap', max(w-.0005,min(corners)) <= min(w+.0005,max(corners)), True, sample)
    formula.append(dict(sample=sample, w_table=w, w_recomputed=calc,
                        delta_percentage_points=100*(calc-w), rounding_low=min(corners), rounding_high=max(corners),
                        residual_per_g_host=s/h, ga_feed=.6007*.5/.78 if sample not in ('S2-BASE','S2-I96') else 0,
                        nitrogen_reconstruction=h*.05+w*.3074))
    for branch, hh, ww, ss in [('s-I',h,w,s),('s-V',h/(h+w),w/(h+w),0.)]:
        recs[sample,branch,'composite_after_outgassing'] = dict(q=dry[sample],q0=dry['S2-BASE'],h=hh,w=ww,s=ss)
    if w:
        # Alternative mass basis: reported q referred to mass before removal of s.
        hh, ww = h/(h+w), w/(h+w)
        qdry = dry[sample]/(h+w)
        # Another conditional reading: W is not a usable dry-mass increment, N is dry,
        # and the activated specimen has only host and PEI. Do not assert this is true.
        wbinary = (nc-.05)/(.3074-.05)
        third_readings.append(dict(sample=sample,
            dry_fraction_after_s_removal=h+w, q_if_reported_on_predegassing_mass=qdry,
            kstar_g110_if_predegassing_mass=qdry/dry['S2-BASE']/1.1,
            eta_phi1_if_predegassing_mass=eta(qdry,dry['S2-BASE'],hh,ww,1),
            binary_N_reading_w=wbinary,
            binary_N_reading_eta_phi1=eta(dry[sample],dry['S2-BASE'],1-wbinary,wbinary,1)))

points = read(PACK/'benchmark/S100_dry_isotherms.csv')
curves = {}
for name in sorted({r['sample_label'] for r in points}):
    xy = [(float(r['p_bar']),float(r['q_mmol_per_g_reported'])) for r in points if r['sample_label']==name]
    curves[name] = interp(xy,.896)
for sample,q in curves.items():
    x = 0. if sample=='UiO-66' else float(sample.split('PEI')[0])/100
    for branch,w in [('w-C',x),('w-F',x/(1+x))]:
        for basis in ('b-C','b-M'):
            recs[sample,branch,basis] = dict(q=q*(1-w) if basis=='b-M' else q,q0=curves['UiO-66'],h=1-w,w=w,s=0.)


def record(row):
    return recs[row['sample_id'],row['composition_branch'],row['mass_basis_branch']]


for row in read(ROOT/'reports/task003/material_balance.csv'):
    r = record(row)
    for col,k in [('h_g_mof_g_composite','h'),('w_g_pei_g_composite','w'),('s_g_residue_g_composite','s')]:
        check('mass_fractions',float(row[col]),r[k],row['sample_id'])
    check('mass_sum',r['h']+r['w']+r['s'],1.)
    check('mass_nonnegative',min(r[k] for k in ('h','w','s'))>=0,True)
    check('PEI_N_only',float(row['n_pei_mmol_g_composite']),r['w']*N)
    f,L = float(row['nh2_linker_mole_fraction']),float(row['unique_linkers_per_zr6'])
    node = 6*91.224 + 8*15.999 + 4*1.008
    mw = node + L*(164.116*(1-f)+179.131*f)
    mol = 1000*r['h']*L/mw
    pet = row['route']!='analog'
    check('PET_inventory',float(row['pet_fragment_mass_fraction']),mol*(1-f)*164.116/1000 if pet else 0.)
    check('PET_inventory',float(row['pet_linker_mole_fraction']),1-f if pet else 0.)
    check('linker_N',float(row['nitrogen_linker_mmol_g_composite']),mol*f)

for row in read(ROOT/'reports/task003/analog_lines.csv'):
    r=record(row); h,w,q,q0=(r[k] for k in ('h','w','q','q0'))
    iv=interval(q,q0,h,w,float(row['eta_ceiling']))
    for col,j in [('admissible_phi_low',0),('admissible_phi_high',1)]:
        if iv is None: check('analog_interval',row[col],'')
        else: check('analog_interval',float(row[col]),iv[j])
    if w:
        for phi,col in [(0,'eta_phi0'),(1,'eta_phi1')]: check('analog_eta',float(row[col]),eta(q,q0,h,w,phi))

for row in read(ROOT/'reports/task003/design_window.csv'):
    h,w,s,phi,g = (float(row[k]) for k in ('h','w','s','phi','g'))
    check('grid_mass',h+w+s,1.)
    if not w:
        check('w_zero',row['eta_min_mol_co2_mol_n'],'')
        check('w_zero',row['host_only_meets_target'],str(h*phi>=g))
        continue
    check('grid_normalized',float(row['eta_min_normalized']),(g-h*phi)/w)
    if not row['q_host_mmol_g_mof']:
        check('PET_unknown',row['class_nominal'],'unknown')
        continue
    q0=float(row['q_host_mmol_g_mof'])
    e=(g-h*phi)*q0/(w*N)
    check('grid_eta',float(row['eta_min_mol_co2_mol_n']),e)
    cls='A' if e<=0 else 'B' if e<=.3747 else 'C' if e<=.5 else 'D'
    check('grid_class',row['class_nominal'],cls)
    check('closed_form',float(row['phi_crit_lit']),(g-w*N*.3747/q0)/h)
    if phi==0: check('phi_zero',float(row['eta_min_mol_co2_mol_n']),g*q0/(w*N))

for row in read(ROOT/'reports/task003/transfer_kstar.csv'):
    r=record(row); q,q0,h,w=(r[k] for k in ('q','q0','h','w'))
    G=q/q0; g=float(row['g'])
    check('registered_kstar',float(row['registered_kstar_G_over_g']),G/g)
    full=min(threshold(G,h,p,g) for p in (0,1))
    check('full_kstar',float(row['kstar_all_phi_positive_k']),full)
    iv=interval(q,q0,h,w,float(row['eta_ceiling']))
    if iv:
        adm=min(threshold(G,h,p,g) for p in iv)
        if math.isinf(adm): check('admissible_kstar',row['kstar_admissible_unbounded'],'True')
        else: check('admissible_kstar',float(row['kstar_admissible']),adm)
    if row['phi']:
        phi=float(row['phi'])
        if w:
            peiq=q-h*phi*q0
            # Independently transfer the absolute PEI uptake; divide by PET q_host.
            for k,col in [(.8,'gain_pet_k08'),(1.5,'gain_pet_k15')]:
                direct=(h*phi*k*q0+peiq)/(k*q0)
                check('transfer_direct_balance',float(row[col]),direct)

windows=[]
for key,r in recs.items():
    if not r['w']: continue
    for ceiling in (.5,.195):
        iv=interval(r['q'],r['q0'],r['h'],r['w'],min(.3747,ceiling))
        windows.append(dict(sample=key[0],composition=key[1],basis=key[2],ceiling=ceiling,
                            B=bool(iv and r['q']/r['q0']>=1.1),
                            kstar=r['q']/r['q0']/1.1,phi_low=iv[0] if iv else None))
for row in read(ROOT/'reports/task003/route_windows.csv'):
    calc=next(x for x in windows if (x['sample'],x['composition'],x['basis'],x['ceiling'])==
              (row['sample_id'],row['composition_branch'],row['mass_basis_branch'],float(row['eta_ceiling'])))
    check('route_B',row['B_window_at_k1_g110'],str(calc['B']))

prov=json.loads((ROOT/'reports/task003/provenance.json').read_text())
hash_mismatches=[]
for group in ('inputs','implementation','outputs'):
    for x in prov[group]:
        p=ROOT/x['path']
        actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        if actual!=x['sha256']: hash_mismatches.append(dict(group=group,path=x['path'],actual=actual,recorded=x['sha256']))

result=dict(review_id='T044',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            methodology='independent standard-library formulas from primary table values; no production imports',
            counts=counts,max_abs_differences=maxdiff,failures=errors,
            n_N_mmol_g=N,s2_formula=formula,s100_q_at_0896=curves,
            third_S2_mass_readings=third_readings,route_B_windows=windows,
            hp20_eta_apparent=4.35/(.5*1000/43.069),hp20_eta_host_subtracted=(4.35-.5*.47)/(.5*1000/43.069),
            c72_kstar_rounding=[(3.26-.005)/(2.67+.005)/1.1,(3.26+.005)/(2.67-.005)/1.1],
            c72_kstar_3pct_scenario=[3.26*.97/(2.67*1.03)/1.1,3.26*1.03/(2.67*.97)/1.1],
            provenance_hash_mismatches=hash_mismatches)
(OUT/'recompute.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(checks=sum(counts.values()),failures=len(errors),max_abs_difference=max(maxdiff.values()),
                     provenance_hash_mismatches=hash_mismatches),ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
