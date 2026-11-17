#!/usr/bin/env python3
"""Blind V scaffold. No V observations/parameters are embedded in this module.

Accepted independent files under holdout/: observations.csv and predictions.csv.
observations: series,point_id,source_id,extraction_id,q,u_exp,u_dig,u_p,u_T,u_a,
              dq_dp,dq_dT,dq_da,scale,observable,comparable,inputs_known.
predictions: series,point_id,model,q_pred,u_num,prediction_low,prediction_high.
All uncertainties are standard uncertainties in matching units. Unknown stays
blank -> conditional comparison, never zero experimental error. Inputs such as
S2 retained loading must have been supplied by the independent reviewer under
D-11, without refitting frozen parameters. Predictions must precede V disclosure.
For water-step position/porosity/ratios, use separate comparable series and units.
Correlated uncertainty and rank-pair covariance require reviewer-provided joint
intervals; this scaffold deliberately does not manufacture rank significance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from pet2mof.calibration.metrics import metrics


def validate(root, directory='holdout/v1', *, output='reports/T013/validation.json'):
    root=Path(root).resolve()
    directory=(root/directory).resolve()
    directory.relative_to(root/'holdout')
    paths=[directory/'observations.csv',directory/'predictions.csv',directory/'freeze.json']
    if not all(p.is_file() for p in paths):
        raise FileNotFoundError('V data unavailable: expected observations.csv, predictions.csv and freeze.json under holdout/v1; no validation performed')
    tag=subprocess.run(['git','rev-parse','prereg-v1^{commit}'],cwd=root,capture_output=True,text=True,check=True).stdout.strip()
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True).stdout.strip()
    if tag!=head:
        raise ValueError('validation requires exact frozen prereg-v1 HEAD')
    freeze=json.loads(paths[2].read_text())
    if freeze['commit_sha']!=tag or not freeze.get('reviewer') or not freeze.get('predictions_precede_disclosure'):
        raise ValueError('independent freeze/disclosure declaration missing')
    for file in paths[:2]:
        if hashlib.sha256(file.read_bytes()).hexdigest()!=freeze[file.name+'_sha256']:
            raise ValueError('frozen holdout input hash mismatch')
    obs,pred=pd.read_csv(paths[0]),pd.read_csv(paths[1])
    keys=['series','point_id']
    if obs.duplicated(keys).any() or pred.duplicated(keys+['model']).any():
        raise ValueError('duplicate V identities')
    reports=[]
    for name,f in obs.groupby('series',sort=False):
        if not f.comparable.eq(True).all() or not f.inputs_known.eq(True).all():
            reports.append(dict(series=name,status='not_testable',reason='incomparable observable or unknown mandatory inputs'))
            continue
        for model in ('M1','B1'):
            merged=f.merge(pred[pred.model==model],on=keys,validate='one_to_one',how='left')
            if merged.q_pred.isna().any():
                reports.append(dict(series=name,model=model,status='not_testable',reason='frozen predictions missing'));continue
            if any(merged[k].isna().any() for k in ('u_dig','u_p','u_T','u_a','dq_dp','dq_dT','dq_da','u_num')):
                reports.append(dict(series=name,model=model,status='not_testable',reason='observation/numerical uncertainty budget incomplete'));continue
            known=not merged.u_exp.isna().any()
            if not known:
                # Sensitivity scenario only, as protocol section 4.2; scale required.
                if merged.scale.isna().any():
                    reports.append(dict(series=name,model=model,status='conditional_comparison',reason='experimental error and source scale unknown'));continue
                exp=.03*merged.scale/np.sqrt(3)
            else:exp=merged.u_exp
            u=np.sqrt(exp**2+merged.u_dig**2+(merged.dq_dp*merged.u_p)**2+
                      (merged.dq_dT*merged.u_T)**2+(merged.dq_da*merged.u_a)**2)
            if (merged.u_num > .05*u.min()).any():
                reports.append(dict(series=name,model=model,status='not_testable',reason='numerical uncertainty exceeds protocol budget'));continue
            report=metrics(merged.q,merged.q_pred,u,u_num=float(merged.u_num.max()),experimental_known=known,
                           scale=None if merged.scale.isna().any() else float(merged.scale.iloc[0]))
            report.update(series=name,model=model,source_ids=sorted(f.source_id.unique()),extraction_ids=sorted(f.extraction_id.unique()))
            if (merged.q_pred<0).any():report.update(status='fail',reason='negative predicted loading')
            if merged.prediction_low.notna().all() and merged.prediction_high.notna().all():
                report.update(prediction_coverage=float(((merged.q>=merged.prediction_low)&(merged.q<=merged.prediction_high)).mean()),
                              prediction_mean_width=float((merged.prediction_high-merged.prediction_low).mean()))
            reports.append(report)
    result=dict(commit_sha=head,series=reports,rank_comparison='requires independent joint pair intervals; not inferred from adjacent points',
                S2_attribution='bare-host failure -> carrier; porosity trend failure -> placement; capacity failure after both pass -> chemistry',
                water_split='reviewer uses accepted D-14 split; do not count calibrated S106 as independent V')
    path=root/output;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',default='holdout/v1')
    args=parser.parse_args()
    try:validate(Path(__file__).resolve().parents[1],args.directory)
    except (ValueError,FileNotFoundError,subprocess.CalledProcessError) as exc:
        parser.exit(2,str(exc)+'\n')
