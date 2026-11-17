"""Offline rereview evidence; no production imports, no new measured data.

Run from repository root with uv run --locked --no-sync --offline python .../check.py.
Writes only alongside this script. Replays T044 arithmetic against current CSVs,
then independently checks interval algebra and uncertainty from four raw uptakes.
"""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
old = ROOT / 'reviews/T044_checks/recompute.py'
# The old script derives ROOT and OUT only from __file__. Keep its formulas intact,
# redirecting its output into this review's permitted directory.
try:
    exec(compile(old.read_text(), str(old.relative_to(ROOT)), 'exec'),
         {'__file__': str(OUT / 'replay_T044.py'), '__name__': '__main__'})
except SystemExit as exc:
    if exc.code:
        raise

checks = 0


def require(condition):
    global checks
    checks += 1
    assert condition


def rows(name):
    with (ROOT / 'reports/task003' / name).open() as stream:
        return list(csv.DictReader(stream))


def interval(G, h, k):
    # h=0 handled by continuous extension; q(C0), q(P0)>0 required.
    top = min(1., G / h) if h else 1.
    endpoints = (G / k, h * top + (G - h * top) / k)
    return sorted(endpoints)


for G, h, k in itertools.product((0., .2, .7, 1.048297073419, 1.17, 1.67),
                                  (0., .3, .7, 1.), (.1, .5, .95, 1., 1.1, 1.6, 3.)):
    top = min(1., G/h) if h else 1.
    lo, hi = interval(G, h, k)
    for j in range(101):
        phi = top*j/100
        peiq = G-h*phi
        predicted = h*phi+peiq/k
        require(peiq >= -1e-12)
        require(lo-1e-12 <= predicted <= hi+1e-12)
    if 1 <= k <= G/1.1:
        require(lo >= 1.1-1e-12)
    if k == 1:
        require(abs(lo-G) < 1e-12 and abs(hi-G) < 1e-12)


def residual_and_u(a, b, c, d, h, endpoint, e=.02, uh=0.):
    """a=C0,b=P0,c=C1,d=P1; independent raw q, fixed h unless uh>0.

    Endpoint 0: c/b; endpoint 1: h+(c-h*a)/b (G_C>=h).
    R=G_P-endpoint; linear covariance propagation, not a power calculation.
    """
    if endpoint == 0:
        residual = (d-c)/b
        gradients = (0., -residual/b, -1/b, 1/b)
        gh = 0.
    else:
        residual = (d-c-h*(b-a))/b
        gradients = (h/b, -(residual+h)/b, -1/b, 1/b)
        gh = -(1-a/b)
    sigma = math.sqrt(sum((g*e*x)**2 for g,x in zip(gradients,(a,b,c,d)))+(gh*uh)**2)
    return residual, sigma


uncertainty = []
for k, fraction in ((1.1, 0.), (.05, 0.), (.05, -.11)):
    a, b, c, h = 1., k, 1.17, .7
    for endpoint in (0, 1):
        bound = c/b if endpoint == 0 else h+(c-h*a)/b
        d = b*bound*(1+fraction)
        r, u = residual_and_u(a,b,c,d,h,endpoint)
        uncertainty.append(dict(k=k,G_C=c,h=h,endpoint=endpoint,
            bound=bound,G_P=d/b,fraction_below_bound=-fraction,
            residual=r,u_residual=u,u_relative_to_bound=u/bound,
            two_sigma_relative_to_bound=2*u/bound,z=abs(r)/u))
        # Confirm analytic propagation with finite differences on raw uptakes.
        xs = [a,b,c,d]
        numeric = []
        for i, x in enumerate(xs):
            dx = 1e-6*x
            plus, minus = xs.copy(), xs.copy()
            plus[i] += dx
            minus[i] -= dx
            rp = residual_and_u(*plus,h,endpoint)[0]
            rm = residual_and_u(*minus,h,endpoint)[0]
            numeric.append((rp-rm)/(2*dx))
        numeric_u = math.sqrt(sum((g*.02*x)**2 for g,x in zip(numeric,xs)))
        require(math.isclose(u,numeric_u,rel_tol=1e-8))
require(uncertainty[-1]['z'] < 2)

analog = rows('analog_lines.csv')
windows = rows('route_windows.csv')
uncertain = rows('uncertainty_vertices.csv')
selected = {
    's100_40': [r for r in analog if r['sample_id']=='40PEI@UiO-66' and r['eta_ceiling']=='0.5'],
    's2_N72_window': [r for r in windows if r['sample_id']=='S2-N72' and r['composition_branch']=='s-I' and r['eta_ceiling']=='0.5'],
    's100_30_envelope': [r for r in uncertain if r['sample_id']=='30PEI@UiO-66' and r['g']=='1.1' and r['metric']=='kstar_all_positive'],
}
third = []
for r in analog:
    if r['sample_id'] not in ('S2-C72','S2-C96','S2-N72') or r['composition_branch']!='s-I' or r['eta_ceiling']!='0.5':
        continue
    h,w,q,q0,n = (float(r[key]) for key in ('h','w','q_composite_mmol_g','q_host_mmol_g_mof','n_n_mmol_g_pei'))
    t = h+w
    eta = (q-h*q0)/(w*n)
    require(math.isclose(eta,(q/t-(h/t)*q0)/((w/t)*n),abs_tol=1e-12))
    third.append(dict(sample=r['sample_id'],t=t,q_dry=q/t,kstar=q/t/q0/1.1,
                      eta_phi1=eta,B_at_phi1=eta<=.3747))

G,h = 1.17,.7
examples = {
    'quoted_interval': interval(G,h,1.1),
    'reverse_order_k09': interval(G,h,.9),
    'G_less_than_h': interval(.2,.7,.5),
    'excluded_G_P': dict(G_C=G,h=h,k=1.1,G_P=1.3,interval=interval(G,h,1.1)),
    'same_GC_k_different_phi': dict(G_C=G,h=h,k=1.1,
        phi0_G_P=G/1.1,phi1_G_P=h+(G-h)/1.1),
    'GC_below_110_but_GP_above': dict(G_C=1.05,h=h,k=.8,interval=interval(1.05,h,.8)),
    'composition_tolerance': dict(G_C=G,k=1.,w_C=.30,w_P=.30,s_C=0.,s_P=.02,
        h_C=.70,h_P=.68,phi=1.,J_over_qC0=.47,nominal_interval=interval(G,.68,1.),
        actual_G_P=.68+.47,displacement=-.02),
    'near_threshold': dict(G_P=1.11,u_G_P=1.11*math.sqrt(2)*.02,
        lower_2sigma=1.11*(1-2*math.sqrt(2)*.02)),
}
require(examples['same_GC_k_different_phi']['phi0_G_P']<1.1<examples['same_GC_k_different_phi']['phi1_G_P'])
require(min(examples['GC_below_110_but_GP_above']['interval'])>1.1)

sources = [ROOT/'AGENTS.md', ROOT/'tasks/T044r-task003-rereview.md', ROOT/'README.md',old,
           ROOT/'reviews/T044_review.md', *sorted((ROOT/'reports/task003').glob('*.csv')),
           *[ROOT/'reports/task003'/name for name in ('final_report.md','decision_brief.md','next_experiment.md')],
           *sorted((ROOT/'data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary').glob('S2*.csv')),
           ROOT/'data/task002/PET2MOF_Task002_DataPack_v1.0/data/benchmark/S100_dry_isotherms.csv']
result = dict(review_id='T044r',head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    evidence_class='deterministic review checks and hypothetical counterexamples; not measurements',
    extraction_id='T044r-algebra-csv-check',checks=checks,failures=0,
    nominal_ratio_u=math.sqrt(2)*.02,naive_three_independent_ratios_u=math.sqrt(6)*.02,
    uncertainty=uncertainty,examples=examples,third_S2_readings=third,selected_csv_rows=selected,
    input_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
(OUT/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(review_id='T044r',checks=checks,failures=0,examples=examples,
                     uncertainty=uncertainty,third_S2_readings=third),ensure_ascii=False,indent=2))
