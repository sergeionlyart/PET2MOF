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
import json
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from pet2mof.calibration.metrics import metrics
from pet2mof.calibration.final import sha256
from pet2mof.calibration.freeze import require_freeze
from pet2mof.calibration.prediction import MODEL_LABELS


def validate(root, directory='holdout/v1', *, output='reports/validation/validation.json'):
    root=Path(root).resolve()
    directory=(root/directory).resolve()
    directory.relative_to(root/'holdout')
    paths=[directory/name for name in ('observations.csv', 'conditions.csv', 'predictions.csv',
                                      'model_derivatives.csv', 'prediction_metadata.json', 'freeze.json')]
    if not all(p.is_file() for p in paths):
        raise FileNotFoundError('V data unavailable: complete prediction package, conditions.csv, observations.csv and freeze.json required; no validation performed')
    head = require_freeze(root)
    freeze=json.loads((directory/'freeze.json').read_text())
    if freeze.get('commit_sha')!=head or not freeze.get('reviewer') or freeze.get('predictions_precede_disclosure') is not True:
        raise ValueError('independent freeze/disclosure declaration missing')
    # Authenticate the whole package before parsing observations or computing any
    # comparison. Metadata must also bind the original conditions and parameters.
    for file in paths[:-1]:
        if sha256(file)!=freeze.get(file.name+'_sha256'):
            raise ValueError('frozen holdout input hash mismatch')
    metadata=json.loads((directory/'prediction_metadata.json').read_text())
    if metadata.get('status')!='frozen_prediction' or metadata.get('commit_sha')!=head:
        raise ValueError('synthetic or unfrozen prediction metadata')
    internal_hashes = {'conditions_sha256': directory/'conditions.csv',
                       'parameters_sha256': root/'configs/frozen_parameters.yaml',
                       'prediction_sha256': directory/'predictions.csv',
                       'derivatives_sha256': directory/'model_derivatives.csv'}
    for field, file in internal_hashes.items():
        if metadata.get(field) != sha256(file):
            raise ValueError('prediction metadata hash mismatch: '+field)
    pred=pd.read_csv(directory/'predictions.csv')
    if pred.empty or 'run_status' not in pred or not pred.run_status.eq('frozen_prediction').all():
        raise ValueError('predictions require run_status=frozen_prediction')
    derivatives=pd.read_csv(directory/'model_derivatives.csv')
    keys=['series','point_id']
    if pred.duplicated(keys+['model']).any():
        raise ValueError('duplicate V identities')
    if derivatives.duplicated(keys+['model']).any():
        raise ValueError('duplicate derivative identity')
    expected=set(map(tuple,pred[keys+['model']].to_numpy()))
    if set(map(tuple,derivatives[keys+['model']].to_numpy()))!=expected:
        raise ValueError('derivative/prediction identities differ')
    obs=pd.read_csv(directory/'observations.csv')
    if obs.duplicated(keys).any():
        raise ValueError('duplicate V identities')
    models=sorted(pred.model.dropna().unique())
    if not models:
        raise ValueError('no frozen model labels')
    if any('/' in m for m in models):
        models=sorted(set(models) | set(MODEL_LABELS))
    reports=[]
    for name,f in obs.groupby('series',sort=False):
        if not f.comparable.eq(True).all() or not f.inputs_known.eq(True).all():
            reports.append(dict(series=name,status='not_testable',reason='incomparable observable or unknown mandatory inputs'))
            continue
        for model in models:
            merged=f.merge(pred[pred.model==model],on=keys,validate='one_to_one',how='left')
            # Sidecar is produced without observations; its model-specific
            # derivatives replace the common observation placeholders.
            side=derivatives[derivatives.model==model].drop(columns=['model'])
            merged=merged.drop(columns=[c for c in ('dq_dp','dq_dT','dq_da','u_num','u_num_x','u_num_y') if c in merged])
            merged=merged.merge(side,on=keys,validate='one_to_one',how='left')
            if merged.q_pred.isna().any():
                reasons = sorted(set(merged.get('reason', pd.Series(dtype=str)).dropna()))
                reports.append(dict(series=name,model=model,status='not_testable',reason='frozen predictions missing',
                                    prediction_reasons=reasons));continue
            conditional_reasons = []
            # D-18: dry a is identically zero, even when source u_a is blank.
            # Keep dq_da blank in the immutable sidecar; zero only its contribution.
            dry = merged.get('dry_series', pd.Series(False, index=merged.index)).eq(True)
            merged.loc[dry, ['u_a', 'dq_da']] = 0.
            matching_T = merged.get('temperature_matches_calibration', pd.Series(False, index=merged.index)).eq(True)
            excluded_T = merged.u_T.isna() & matching_T
            if excluded_T.any():
                conditional_reasons.append('T-uncertainty excluded')
                # Computational zero represents an excluded term, not an estimate
                # of u_T. The report explicitly records every excluded point.
                merged.loc[excluded_T, ['u_T', 'dq_dT']] = 0.
            for derivative,uncertainty in (('dq_dp','u_p'),('dq_dT','u_T'),('dq_da','u_a')):
                merged.loc[merged[derivative].isna() & merged[uncertainty].eq(0),derivative]=0.
            if any(merged[k].isna().any() for k in ('u_dig','u_p','u_T','u_a','dq_dp','dq_dT','dq_da','u_num')):
                reports.append(dict(series=name,model=model,status='not_testable',reason='observation/numerical uncertainty budget incomplete'));continue
            uncertainties = merged[['u_exp','u_dig','u_p','u_T','u_a','u_num']]
            if (uncertainties < 0).any().any() or np.isinf(uncertainties.to_numpy()).any():
                reports.append(dict(series=name,model=model,status='not_testable',reason='invalid standard uncertainty'));continue
            known=not merged.u_exp.isna().any()
            if not known:
                # Sensitivity scenario only, as protocol section 4.2; scale required.
                missing_exp = merged.u_exp.isna()
                if not (merged.loc[missing_exp, 'scale'] > 0).all():
                    reports.append(dict(series=name,model=model,status='not_testable',reason='experimental error and source scale unknown'));continue
                exp=merged.u_exp.fillna(.03*merged.scale/np.sqrt(3))
                conditional_reasons.append('experimental uncertainty unknown; 3% source-scale scenario')
            else:exp=merged.u_exp
            u=np.sqrt(exp**2+merged.u_dig**2+(merged.dq_dp*merged.u_p)**2+
                      (merged.dq_dT*merged.u_T)**2+(merged.dq_da*merged.u_a)**2)
            if (merged.u_num > .05*u.min()).any():
                reports.append(dict(series=name,model=model,status='not_testable',reason='numerical uncertainty exceeds protocol budget'));continue
            full_budget = not conditional_reasons
            report=metrics(merged.q,merged.q_pred,u,u_num=float(merged.u_num.max()),experimental_known=full_budget,
                           scale=None if merged.scale.isna().any() else float(merged.scale.iloc[0]))
            report.update(series=name,model=model,source_ids=sorted(f.source_id.unique()),extraction_ids=sorted(f.extraction_id.unique()))
            report.update(comparison_kind='full' if full_budget else 'conditional',
                          conditional_reasons=conditional_reasons,
                          excluded_T_points=merged.loc[excluded_T, 'point_id'].tolist(),
                          dry_activity_points=merged.loc[dry, 'point_id'].tolist())
            if (merged.q_pred<0).any():
                report.update(status='fail' if full_budget else 'conditional_comparison',
                              within_conditional_tolerances=False,reason='negative predicted loading')
            if merged.prediction_low.notna().all() and merged.prediction_high.notna().all():
                report.update(prediction_coverage=float(((merged.q>=merged.prediction_low)&(merged.q<=merged.prediction_high)).mean()),
                              prediction_mean_width=float((merged.prediction_high-merged.prediction_low).mean()))
            reports.append(report)
    result=dict(commit_sha=head,series=reports,rank_comparison='requires independent joint pair intervals; not inferred from adjacent points',
                S2_attribution='bare-host failure -> carrier; porosity trend failure -> placement; capacity failure after both pass -> chemistry',
                water_split='reviewer uses accepted D-14 split; do not count calibrated S106 as independent V')
    result['comparison_groups'] = {
        'full': [r for r in reports if r.get('comparison_kind') == 'full'],
        'conditional': [r for r in reports if r.get('comparison_kind') == 'conditional'],
        'not_testable': [r for r in reports if r['status'] == 'not_testable']}
    result['full_verdict_available'] = bool(reports) and all(r.get('comparison_kind') == 'full' for r in reports)
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
