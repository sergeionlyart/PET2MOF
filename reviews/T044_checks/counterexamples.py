"""Numerical witnesses for T044 findings; no production imports."""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
rows = list(csv.DictReader((ROOT/'data/task002/PET2MOF_Task002_DataPack_v1.0/data/benchmark/S100_dry_isotherms.csv').open()))


def points(name):
    return sorted((float(r['p_bar']),float(r['q_mmol_per_g_reported'])) for r in rows if r['sample_label']==name)


def at(xy,p):
    for (a,u),(b,v) in zip(xy,xy[1:]):
        if a <= p <= b:
            return u+(v-u)*(p-a)/(b-a)
    raise AssertionError('No interpolation support')


n = 307.4/14.007
q0 = at(points('UiO-66'),.896)
q30 = at(points('30PEI@UiO-66'),.896)
# An explicit supported coordinate realization, all coordinates within the published boxes.
worst30 = [(p+.042,q-.105) for p,q in points('30PEI@UiO-66')]
worst0 = [(p,q+.105) for p,q in points('UiO-66')]
worst0[-1] = (.896,worst0[-1][1])
qa,qb = at(worst30,.896)*.7,at(worst0,.896)
G = qa/qb
critical = dict(q_composite=qa,q_host=qb,G_analog=G,phi=1.,h=.7,w=.3,k=.95,
    eta=(qa-.7*qb)/(.3*n),G_PET_at_k095=.7+(G-.7)/.95,
    wrong_threshold_G_over_g=G/1.1,correct_all_phi_threshold=(G-.7)/(.4),
    supported_coordinates_30PEI=worst30,supported_coordinates_host=worst0)
assert 0 < critical['eta'] < .3747 and critical['G_PET_at_k095'] < 1.1

nominal_G=q30/q0
upper = dict(branch='30PEI w-C/b-C',phi=1.,k=1.6,eta=(q30-.7*q0)/(.3*n),
             kstar_all=nominal_G/1.1,kcrit_phi1=(nominal_G-.7)/.4,
             G_PET=.7+(nominal_G-.7)/1.6)
assert upper['G_PET']>1.1 and upper['eta']<.3747

# Even at k=1 and unchanged PEI contribution, phi need not transfer.
Gm=.7*nominal_G
phi_example=dict(branch='30PEI w-C/b-M',k=1.,phi_analog=1.,phi_PET=.5,
                 eta=(.7*q30-.7*q0)/(.3*n),G_PET=.7*.5+(Gm-.7),G_analog=Gm)
assert phi_example['G_PET']<1.1 and phi_example['eta']>0

# k measured against another commercial batch C is k_true / a, a=q_C/q_S100.
denominator=dict(q_new_commercial_over_S100=1.5,k_measured=.95,k_true=.95*1.5,
                 branch='30PEI w-C/b-M',phi=1.,G_PET=.7+(Gm-.7)/(.95*1.5))

# General source-only checks of uncertainty arithmetic; no invented probability law for ignorance.
precision=dict(relative_u_ratio_if_independent_q_2pct=math.sqrt(2)*.02,
               separation_k095_vs106_sigma=(1.06-.95)/(.03*1.06),
               G_lower_2sigma_at117=1.17*(1-2*.03),
               G_upper_2sigma_at103=1.03*(1+2*.03))

out=dict(T044_01_lower_guarantee=critical,T044_02_upper_no_gain=upper,
         T044_03_phi_transfer=phi_example,T044_04_denominator=denominator,precision=precision)
(OUT/'counterexamples.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='T044_01_lower_guarantee'},indent=2))
print('lower guarantee:',critical['G_PET_at_k095'],'correct threshold:',critical['correct_all_phi_threshold'])
