#!/usr/bin/env python3
"""Transparent baseline, not a new physical model and not blinded validation."""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from pathlib import Path
from check_data import load
ROOT = Path(__file__).resolve().parents[1]
def save(name: str, rows: list[dict]) -> None:
    (ROOT/'reference').mkdir(exist_ok=True)
    with (ROOT/'reference'/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def interp(points: list[tuple[float,float]], x: float) -> float:
    pts=sorted(points)
    if not pts or not pts[0][0]<=x<=pts[-1][0]:
        raise ValueError('Extrapolation is not allowed')
    for xx,yy in pts:
        if x==xx:return yy
    for (a,ya),(b,yb) in zip(pts,pts[1:]):
        if a<x<b:return ya+(yb-ya)*(x-a)/(b-a)
    raise ValueError('Invalid interpolation support')
def main() -> None:
    dry=load('data/primary/S2_dry_CO2.csv');mats={r['sample_id']:r for r in load('data/primary/S2_materials.csv')}
    qs={r['sample_id']:float(r['q_CO2_dry_mmol_g']) for r in dry};q0=qs['S2-BASE']
    metrics=[];pairs=[];intervals=[]
    for sid,q in qs.items():
        m=mats[sid];mass=1000/(44.01*q)
        metrics.append(dict(sample_id=sid,q_dry_mmol_g=q,gain_vs_base_pct=100*(q/q0-1),
            adsorbent_kg_per_kg_CO2_equilibrium_proxy=mass,
            retained_PEI_kg_in_equilibrium_inventory=mass*float(m['PEI_content_author_calculated_wt_pct'])/100,
            maximum_price_ratio_at_equal_single_loading_material_cost=q/q0,
            interpretation='dry_single_loading_proxy_NOT_cycle_or_process_cost'))
        for d in (0.03,0.05,0.10):
            lo=q*(1-d)-.005;hi=q*(1+d)+.005
            base_lo=q0*(1-d)-.005;base_hi=q0*(1+d)+.005
            intervals.append(dict(sample_id=sid,relative_halfwidth_design=d,q_low=lo,q_high=hi,
                gain_low_pct=100*(lo/base_hi-1) if sid!='S2-BASE' else 0.,
                gain_high_pct=100*(hi/base_lo-1) if sid!='S2-BASE' else 0.,
                robustly_above_base=(lo>base_hi) if sid!='S2-BASE' else False,
                interval_type='bounded_independent_stress_NOT_confidence_interval'))
    for a,qa in qs.items():
        for b,qb in qs.items():
            if a==b:continue
            pairs.append(dict(sample_a=a,sample_b=b,q_ratio=qa/qb,
                gain_pct=100*(qa/qb-1),
                max_common_relative_halfwidth_for_strict_A_gt_B=(qa-qb-0.01)/(qa+qb),
                negative_threshold_means_no_nominal_advantage=(qa-qb-0.01)<0,
                interpretation='independent_symmetric_bounds_plus_0.005_rounding_per_value_NOT_probability'))
    save('S2_nominal_metrics.csv',metrics);save('S2_stress_intervals.csv',intervals);save('S2_pairwise_thresholds.csv',pairs)
    rows=load('data/benchmark/S100_dry_isotherms.csv');split={r['point_id']:r['role'] for r in load('metadata/S100_internal_split.csv')}
    grouped=defaultdict(list)
    for r in rows:grouped[r['sample_label']].append(r)
    residuals=[];shapes=[]
    for sample,rr in sorted(grouped.items()):
        points=[(float(r['p_bar']),float(r['q_mmol_per_g_reported'])) for r in rr]
        train=[(float(r['p_bar']),float(r['q_mmol_per_g_reported'])) for r in rr if split[r['point_id']]=='fit']
        for r in rr:
            if split[r['point_id']]!='internal_interpolation_check':continue
            pred=interp(train,float(r['p_bar']));obs=float(r['q_mmol_per_g_reported'])
            residuals.append(dict(point_id=r['point_id'],sample_label=sample,p_bar=r['p_bar'],observed_q_reported=obs,predicted_q_reported=pred,residual=pred-obs,
                                 evidence='retrospective_internal_interpolation_check_NOT_external_validation'))
        q85=interp(points,.85)
        for p in (.15,.5,.85):
            q=interp(points,p)
            shapes.append(dict(sample_label=sample,p_bar=p,q_reported_basis=q,q_over_q_at_0_85=q/q85,
                               fraction_difference_to_0_85=1-q/q85,
                               interpretation='within_sample_adsorption_branch_shape_NOT_actual_desorption_or_cycle'))
    save('S100_internal_baseline_residuals.csv',residuals);save('S100_nominal_shapes.csv',shapes)
    summary={'S100_internal_points':len(residuals),'S100_internal_MAE_reported_units':sum(abs(r['residual']) for r in residuals)/len(residuals),
             'reference_is_not_blind':True,'reference_includes_no_physical_wet_model':True,
             'S2_top_nominal':'S2-C72','S2_C72_vs_C96_gain_pct':100*(qs['S2-C72']/qs['S2-C96']-1),
             'warning':'Prepared baseline is a numerical reference, not the executor final research or independent empirical validation.'}
    (ROOT/'reference/baseline_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
