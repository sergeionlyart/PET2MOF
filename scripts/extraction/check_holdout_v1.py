#!/usr/bin/env python3
"""T019 local artifact checks; not independent source verification or model validation."""
import csv
import hashlib
import json
import math
from pathlib import Path

import jsonschema
import numpy as np
import yaml
from PIL import Image
from scipy import ndimage as nd
from pet2mof.extraction.digitize import validate_project

ROOT=Path(__file__).resolve().parents[2]
DIG=ROOT/'data/extraction/digitization'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
cond_fields='series point_id source_id extraction_id material gas observable unit basis T_K p_total_bar p_partial_bar y_CO2_dry RH_fraction w_PEI w_reading Mw_PEI notes'.split()
obs_fields='series point_id source_id extraction_id q u_exp u_dig u_p u_T u_a dq_dp dq_dT dq_da scale observable comparable inputs_known'.split()
C=list(csv.DictReader((ROOT/'holdout/v1/conditions.csv').open()))
O=list(csv.DictReader((ROOT/'holdout/v1/observations.csv').open()))
assert list(C[0])==cond_fields and list(O[0])==obs_fields
assert len(C)==len(O) and len({(r['series'],r['point_id']) for r in C})==len(C)
for c,o in zip(C,O):
    assert all(c[k]==o[k] for k in ['series','point_id','source_id','extraction_id','observable'])
    assert (ROOT/f'data/extraction/records/{c["extraction_id"]}.yaml').exists()
    assert c['unit'] in ['mmol/g','1'] and c['basis'] in ['dry_sorbent','dry_MOF','unknown']
    assert o['comparable'] in ['true','false'] and o['inputs_known'] in ['true','false']
    assert all(o[k]=='' for k in ['u_exp','u_T','dq_dp','dq_dT','dq_da'])
    assert o['u_a']==('0' if c['RH_fraction']=='0' else '')
    for k in ['q','u_dig','u_p','scale']:
        if o[k]!='':assert math.isfinite(float(o[k]))
    if 'moist' in c['series'] or c['source_id']=='S117':assert o['q']=='' and o['comparable']=='false'
    if c['source_id']=='S102':assert c['RH_fraction']=='' and c['T_K']=='' and o['inputs_known']=='false'
    if c['source_id'] in ['S103','S113']:
        assert c['RH_fraction']=='' and o['inputs_known']=='false'
        assert 'RH' in c['notes']
    if c['series']=='S103-Fig2a-UiO66_160-adsorption':
        assert o['comparable']=='false' and 'endpoint only' in c['notes']
    if c['series']=='S2-Table2-corrected-secondary':
        assert o['comparable']=='true' and o['inputs_known']=='false'
        assert c['RH_fraction']==''
        assert math.isclose(float(c['p_partial_bar']),float(c['p_total_bar'])*float(c['y_CO2_dry']))
    if c['RH_fraction']=='0':
        assert c['source_id']=='S2' and c['series'] in ['S2-Table2-dry','S2-Table2-dry-ratio']
    if c['source_id']=='S2':assert o['scale']=='' and o['u_dig']=='' and c['w_reading']=='retained'
    assert o['q']!='' or o['comparable']=='false'

schema=json.loads((ROOT/'data/extraction/schema/extraction.schema.json').read_text())
record_checks=[]
for p in sorted((ROOT/'data/extraction/records').glob('T019-*.yaml')):
    r=yaml.safe_load(p.read_text());errors=list(jsonschema.Draft202012Validator(schema).iter_errors(r))
    assert not errors,[e.message for e in errors]
    assert r['status']=='provisional' and r['reviewer'] is None and r['sensitivity_only'] is True
    assert sha(ROOT/r['raw_response_ref'])==r['input_sha256']
    assert r['params']['script_sha256']==sha(ROOT/'scripts/extraction/extract_holdout_v1.py')
    assert r['params']['holdout_exports']=={name:sha(ROOT/'holdout/v1'/name) for name in ['conditions.csv','observations.csv']}
    assert r['corrections'][0]['independent_review_pending']=='T019v2'
    record_checks.append(dict(file=str(p.relative_to(ROOT)),schema_valid=True,issues=[]))

# Check interior tick locations on independent pixel scan lines. These are not
# re-reads of calibration endpoints. Threshold 180 includes grey/antialiased ink.
tick_specs={
 'T019-S113-Fig5a':dict(x=(269,[.2,.4,.6,.8]),y=(58,[.4,.8,1.2])),
 'T019-S113-Fig5b':dict(x=(267,[.2,.4,.6,.8]),y=(479,[.04,.08,.12])),
 'T019-S103-Fig2a':dict(x=(17,[.2,.4,.6,.8]),y=(90,[10,20,30,40,50,60,70,80])),
 'T019-S102-FigS6a':dict(x=(445,[2,4,6]),y=(110,[.05,.1,.15])),
 'T019-S102-FigS6b':dict(x=(445,[2,4,6]),y=(110,[.05,.1,.15])),
 'T019-S102-FigS6c':dict(x=(435,[2,4,6]),y=(108,[.05,.1,.15])),
 'T019-S117-FigS37A':dict(x=(460,[25,50,75,100]),y=(100,[.2,.4,.6,.8,1,1.2,1.4])),
 'T019-S117-FigS37B':dict(x=(460,[25,50,75]),y=(734,[.2,.4,.6,.8,1,1.2,1.4])),
 'T019-S117-FigS38A':dict(x=(460,[25,50,75,100]),y=(95,[.2,.4,.6,.8,1,1.2,1.4])),
 'T019-S117-FigS38B':dict(x=(460,[25,50,75,100]),y=(729,[.2,.4,.6,.8,1,1.2,1.4])),
}
projects=[];ticks=[]
for p in sorted(DIG.glob('T019-*.digitization.yaml')):
    pr=yaml.safe_load(p.read_text());validate_project(pr)
    assert sha(ROOT/pr['image_path'])==pr['image_sha256']
    assert sha(ROOT/pr['overlay'])==pr['overlay_sha256']
    assert sha(ROOT/pr['export'])==pr['export_sha256']
    assert pr['code_version']==sha(ROOT/'scripts/extraction/extract_holdout_v1.py')
    passport=yaml.safe_load((ROOT/'data/extraction/records'/p.name.replace('.digitization.yaml','.yaml')).read_text())
    assert passport['derived_sha256']==pr['export_sha256']
    # Compare holdout values with the source-coordinate export and recompute
    # image uncertainty. A protocol floor or loss of the partial-marker bound
    # must fail even if both CSVs still have syntactically valid numbers.
    if 'S117' not in p.name:
        export=list(csv.DictReader((ROOT/pr['export']).open()))
        for e in export:
            o=next(o for o in O if (o['series'],o['point_id'])==(e['series'],e['point_id']))
            factor=1/22.414 if 'S103' in p.name else 1
            y=pr['y_axis'];t=(float(e['pixel_y'])-y['pixel_1'])/(y['pixel_2']-y['pixel_1'])
            slope=abs((y['value_2']-y['value_1'])/(y['pixel_2']-y['pixel_1']))
            expected=slope*math.sqrt((float(e['readout_bound_px'])**2+(1-t)**2+t*t)/3)*factor
            assert math.isclose(float(o['u_dig']),expected,rel_tol=1e-12)
            assert float(o['q'])==float(e['q'])
            s=next(s for s in pr['series'] if s['name']==e['series'])
            assert s['per_point_readout_bound_px'][int(e['point_id'])-1]==float(e['readout_bound_px'])
    a=np.array(Image.open(ROOT/pr['image_path']).convert('RGB'));dark=a.max(2)<180
    for ax,(line,values) in tick_specs[p.name.replace('.digitization.yaml','')].items():
        scan=dark[line,:] if ax=='x' else dark[:,line];labs,n=nd.label(scan)
        centers=[(z[0].start+z[0].stop-1)/2 for z in nd.find_objects(labs) if z[0].stop-z[0].start<=7]
        axis=pr[ax+'_axis'];slope=(axis['value_2']-axis['value_1'])/(axis['pixel_2']-axis['pixel_1'])
        for value in values:
            expected=axis['pixel_1']+(value-axis['value_1'])/slope
            actual=min(centers,key=lambda c:abs(c-expected)) if centers else None
            residual=actual-expected if actual is not None else None
            ticks.append(dict(project=p.name,axis=ax,scan_line=line,tick_value=value,measured_pixel=actual,residual_px=residual,pass_bound_1px=residual is not None and abs(residual)<=1.01))
    projects.append(dict(file=p.name,series_points={s['name']:len(s['pixels']) for s in pr['series']}))

s103=yaml.safe_load((DIG/'T019-S103-Fig2a.digitization.yaml').read_text())
for group in s103['params']['partial_recovery']:
    name='S103-Fig2a-UiO66_'+group['series']
    series=next(s for s in s103['series'] if s['name']==name)
    for recovery in group['recovered']:
        index=series['pixels'].index(recovery['pixel'])
        assert series['per_point_readout_bound_px'][index]==3
        assert not any(e.get('series')==group['series'] and math.dist(e['pixel'],recovery['pixel'])<8 for e in s103['excluded'])

# Verify S2 joins and all derived ratios against structured source transcription.
tables=json.loads((DIG/'T019-S2-tables.json').read_text())['rows'];parent=next(r for r in tables if r['sample']=='UiO-66-NH2')
for t in tables:
    for suffix,value in [('Table2-dry',t['dry_q_mmol_g']),('Table2-dry-ratio',t['dry_q_mmol_g']/parent['dry_q_mmol_g']),('Table1-Vp-ratio',t['Vp_cm3_g']/parent['Vp_cm3_g']),('Table2-corrected-secondary',t['corrected_q_mmol_g'])]:
        row=next(r for r in O if r['series']=='S2-'+suffix and r['point_id']==t['sample']);assert math.isclose(float(row['q']),value,rel_tol=1e-12)
        c=next(r for r in C if r['series']==row['series'] and r['point_id']==t['sample']);assert float(c['w_PEI'])==t['retained_PEI_percent']/100

statuses=json.loads((DIG/'T019b-series-status.json').read_text())
assert {r['series'] for r in statuses}=={r['series'] for r in C}
for status in statuses:
    rows=[o for o in O if o['series']==status['series']]
    assert len(rows)==status['points']
    assert all((o['comparable']=='true')==status['comparable'] and (o['inputs_known']=='true')==status['inputs_known'] for o in rows)
    assert status['verification_status']=='provisional' and status['reviewer_pending']=='T019v2'
    assert status['reason'] and not status['complete_isotherm_claim'] and not status['independent_eight_point_check_claim']
    if status['status']=='excluded':assert not status['comparable']
    if status['status']=='not_testable':assert not status['inputs_known']

result=dict(holdout_rows=len(C),numeric_observations=sum(r['q']!='' for r in O),placeholder_observations=sum(r['q']=='' for r in O),
 conditions_schema='exact columns; no observed uptake values',join='unique and complete',record_checks=record_checks,projects=projects,
 calibration_tick_checks=ticks,calibration_pass=all(t['pass_bound_1px'] for t in ticks),
 schema_contract='unpaginated JATS requires explicit format, locator, pagination and empty PDF mapping',
 scientific_verification='pending T019v2; successful checks do not confer verified status or resolve source limitations',
 conditions_sha256=sha(ROOT/'holdout/v1/conditions.csv'),observations_sha256=sha(ROOT/'holdout/v1/observations.csv'))
(DIG/'T019-work/validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['record_checks','projects','calibration_tick_checks']},indent=2))
if not result['calibration_pass']:
    print(json.dumps([t for t in ticks if not t['pass_bound_1px']],indent=2));raise SystemExit(1)
