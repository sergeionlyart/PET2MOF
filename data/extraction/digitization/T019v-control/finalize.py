#!/usr/bin/env python3
"""Check immutable inputs and create control-operation passports and run evidence."""
from pathlib import Path
import collections,csv,datetime,hashlib,json,subprocess,math
import jsonschema,numpy,PIL,scipy,yaml
OUT=Path('data/extraction/digitization/T019v-control')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 src=json.loads((OUT/'source_images.json').read_text());images={x['image']:x for x in src}
 projects=json.loads((OUT/'projects.json').read_text());schema=json.loads(Path('data/extraction/schema/extraction.schema.json').read_text())
 dates=datetime.datetime.now(datetime.timezone.utc).isoformat();passport_paths=[]
 for pr in projects:
  for key,hkey in [('image','image_sha256'),('overlay','overlay_sha256')]:assert sha(pr[key])==pr[hkey],pr[key]
  s=images[pr['image']];assert sha(s['pdf'])==s['pdf_sha256']
  sid=pr['series'].split('-')[0]
  doi,url={'S113':('10.3390/membranes10070154','https://mdpi-res.com/d_attachment/membranes/membranes-10-00154/article_deploy/membranes-10-00154.pdf'),'S103':('10.1038/s42004-022-00742-z','https://www.nature.com/articles/s42004-022-00742-z.pdf'),'S102':('10.1021/acs.langmuir.1c01149','https://ndownloader.figshare.com/files/30440111'),'S117':('10.1039/d1fd00017a','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8517963/supplementaryFiles')}[sid]
  e='T019v-'+pr['series'].split('-',1)[1]
  record=dict(extraction_id=e,source_id=sid,doi=doi,url=url,input_sha256=s['pdf_sha256'],pdf_page=s['page'],api_page_map={'1':s['page']},figure_or_table=pr['series'],region={'image':pr['image'],'image_sha256':pr['image_sha256'],'overlay':pr['overlay'],'overlay_sha256':pr['overlay_sha256']},tool='independent T019v raster control; control.py',tool_version=f'source image extraction PyMuPDF 1.27.2.3; numpy {numpy.__version__}; scipy {scipy.__version__}; Pillow {PIL.__version__}',params={'script_sha256':sha(OUT/'control.py'),'project':'data/extraction/digitization/T019v-control/projects.json','series_selector':pr['series'],'method':pr['method'],'x_axis':pr['x_axis'],'y_axis':pr['y_axis'],'comparison_rule':'abscissa-only nearest unique same-series marker within 4 native pixels','scope':'source check; not model validation','uncertainty_role':'control readout and calibration; not independent experiment'},date=dates,raw_response_ref=s['pdf'],unit_conversions=[{'ordinate_factor':pr.get('unit_factor',1),'abscissa':pr.get('x_unit','native displayed pressure; S102 not total/partial assigned')}],derived_sha256=sha(OUT/'controls.csv'),status='provisional',reviewer=None,corrections=[{'reason':'Own initial method/compare errors preserved and corrected; see method_corrections.json'}],error_estimate={'type':'standard k=1, conservative readout estimate','formula':'abs(y_slope * unit_factor) * sqrt((readout_bound_px**2 + 1)/3)','readout_bound_px':pr['readout_bound_px'],'experimental_uncertainty':'unknown','calibration_shared':True},data_kind='digitized_markers',sensitivity_only=True)
  jsonschema.Draft202012Validator(schema).validate(record)
  p=OUT/'passports'/(e+'.yaml');p.write_text(yaml.safe_dump(record,sort_keys=False,allow_unicode=True));passport_paths.append(str(p))
 protected=json.loads((OUT/'protected_hashes.json').read_text())
 for p,h in protected.items():assert sha(p)==h,'changed protected input: '+p
 frozen=json.loads((OUT/'blind_checkpoint.json').read_text())['frozen_artifacts']
 for p,h in frozen.items():assert sha(OUT/p)==h,'changed source-control checkpoint: '+p
 check=json.loads((OUT/'schema_checks.json').read_text());summary=json.loads((OUT/'comparison_summary.json').read_text())
 assert not check['schema_and_join_issues'] and check['S2_values_exact'] and check['S2_retained_w_all_match'] and check['S2_Mw_all_match']
 assert all(x['within_2_combined_u']==x['matched'] for x in summary)
 known=[]
 for p in sorted(Path('data/extraction/records').glob('T019-*.yaml')):
  errors=list(jsonschema.Draft202012Validator(schema).iter_errors(yaml.safe_load(p.read_text())))
  if errors:known.append({'file':str(p),'errors':[{'path':list(e.path),'message':e.message} for e in errors]})
 assert len(known)==4 and all(all(x['path']==['pdf_page'] for x in p['errors']) for p in known)
 head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head=='8a81f3d1766d0f4dd27dcfa13d69152efd9bd7d8'
 report=Path('reviews/T019v_holdout_verification.md').read_text()
 obs=list(csv.DictReader(open('holdout/v1/observations.csv')))
 conditions=list(csv.DictReader(open('holdout/v1/conditions.csv')))
 cm={(r['series'],r['point_id']):r for r in conditions}
 for r in obs:
  c=cm[(r['series'],r['point_id'])]
  assert c['basis'] in ['dry_sorbent','dry_MOF','unknown'] and c['unit'] in ['mmol/g','1']
  assert c['material'] in ['UiO-66','UiO-66-NH2','PEI@UiO-66-NH2']
  assert c['gas'] in ['CO2','N2','H2O','CO2+H2O']
  for k in ['u_exp','u_T','u_a','dq_dp','dq_dT','dq_da']:assert r[k]==''
  sid=r['source_id']
  if sid in ['S113','S103','S102']:
   expected_scale=({'S113':.16 if 'Fig5b' in r['series'] else 1.6,'S103':95/22.414,'S102':.2})[sid]
   assert math.isclose(float(r['scale']),expected_scale,rel_tol=1e-12) and float(r['u_dig'])>0
  else:assert r['scale']=='' and r['u_dig']==''
  if sid in ['S102','S117']:assert r['comparable']=='false' and r['inputs_known']=='false'
  if sid=='S102':assert all(c[k]=='' for k in ['T_K','p_total_bar','p_partial_bar','RH_fraction'])
  if 'desorption' in r['series']:assert r['comparable']=='false'
  if 'moist' in r['series'] or sid=='S117':assert r['q']==''
 data_lines=[l for l in report.splitlines() if l.startswith('| S')]
 assert len(data_lines)==20
 verdicts=collections.Counter(line.split('|')[4].strip() for line in data_lines)
 assert dict(verdicts)=={'verified':5,'исправить':7,'not_testable':7,'excluded':1},verdicts
 checks=dict(head=head,checks=[{'command':'UV_CACHE_DIR=$PWD/.uv-cache uv sync --frozen','exit_code':0},{'command':'UV_CACHE_DIR=$PWD/.uv-cache .venv/bin/python data/extraction/digitization/T019v-control/prepare.py (initial incompatible PyMuPDF 1.28.2)','exit_code':1,'reason':'Native PNG byte encoding differed; initial failure preserved; restored with source engine 1.27.2.3'},{'command':'UV_CACHE_DIR=$PWD/.uv-cache python3 data/extraction/digitization/T019v-control/prepare.py','exit_code':0},{'command':'UV_CACHE_DIR=$PWD/.uv-cache .venv/bin/python data/extraction/digitization/T019v-control/control.py','exit_code':0},{'command':'UV_CACHE_DIR=$PWD/.uv-cache .venv/bin/python data/extraction/digitization/T019v-control/compare.py','exit_code':0},{'command':'make test-ocr','exit_code':0,'passed':81},{'command':'UV_CACHE_DIR=$PWD/.uv-cache .venv/bin/python data/extraction/digitization/T019v-control/finalize.py','exit_code':0}],control_passports_valid=len(passport_paths),known_T019_schema_failures=known,protected_file_hashes_unchanged=len(protected),blind_checkpoint_hashes_unchanged=len(frozen),conditions_rows=check['conditions_rows'],observations_rows=len(obs),matched_graph_controls=sum(x['matched'] for x in summary),table_comparisons=check['S2_numeric_checks'],control_quotas_unmet=[x['series'] for x in summary if not x['quota_met']],verdicts=dict(verdicts),not_run=['model predictions','validate.py','CI','make publish-check','commit','push'])
 (OUT/'checks.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({k:v for k,v in checks.items() if k not in ['checks','known_T019_schema_failures']},indent=2,ensure_ascii=False))
if __name__=='__main__':main()
