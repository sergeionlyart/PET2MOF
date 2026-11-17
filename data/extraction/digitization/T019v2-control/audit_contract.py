"""Read-only independent checks; outputs restricted to T019v2-control."""
from pathlib import Path
import csv,json,hashlib,math,yaml,copy,collections
from jsonschema import Draft202012Validator
from PIL import Image,ImageDraw
import fitz,numpy as np
D=Path(__file__).parent;ROOT=D.parents[3];DIG=D.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
C=list(csv.DictReader((ROOT/'holdout/v1/conditions.csv').open()));O=list(csv.DictReader((ROOT/'holdout/v1/observations.csv').open()))
cf='series point_id source_id extraction_id material gas observable unit basis T_K p_total_bar p_partial_bar y_CO2_dry RH_fraction w_PEI w_reading Mw_PEI notes'.split()
of='series point_id source_id extraction_id q u_exp u_dig u_p u_T u_a dq_dp dq_dT dq_da scale observable comparable inputs_known'.split()
assert list(C[0])==cf and list(O[0])==of
key=lambda r:(r['series'],r['point_id']);cm={key(r):r for r in C};om={key(r):r for r in O}
assert len(cm)==len(C)==len(om)==len(O) and cm.keys()==om.keys()
assert not any(k in cf for k in ['q','u_exp','u_dig','scale'])
for k,c in cm.items():
 o=om[k];assert all(c[f]==o[f] for f in ['source_id','extraction_id','observable'])
 for f in of[4:14]:
  if o[f]:assert math.isfinite(float(o[f]))
 assert o['u_exp']==o['u_T']==o['dq_dp']==o['dq_dT']==o['dq_da']==''
 assert o['u_a']==('0' if c['RH_fraction']=='0' else '')
 if c['RH_fraction']=='0':assert c['series'] in ['S2-Table2-dry','S2-Table2-dry-ratio']
 if c['source_id'] in ['S103','S113','S102']:assert c['RH_fraction']=='' and o['inputs_known']=='false'
 if c['source_id']=='S102':assert c['T_K']=='' and c['basis']=='unknown' and c['p_total_bar']==c['p_partial_bar']==''
 if c['series']=='S2-Table2-corrected-secondary':
  assert o['comparable']=='true' and o['inputs_known']=='false' and c['RH_fraction']==''
  assert math.isclose(float(c['p_partial_bar']),float(c['p_total_bar'])*float(c['y_CO2_dry']))
 if c['source_id']=='S117' or 'moist' in c['series']:assert o['q']=='' and o['comparable']=='false'
 if c['series']=='S103-Fig2a-UiO66_160-adsorption':assert o['comparable']=='false' and 'endpoint' in c['notes']
schema=json.loads((ROOT/'data/extraction/schema/extraction.schema.json').read_text());validator=Draft202012Validator(schema);records=[]
for p in sorted((ROOT/'data/extraction/records').glob('T019-*.yaml')):
 r=yaml.safe_load(p.read_text());assert not list(validator.iter_errors(r))
 assert r['status']=='provisional' and r['reviewer'] is None
 assert r['params']['script_sha256']==sha(ROOT/'scripts/extraction/extract_holdout_v1.py')
 assert r['params']['holdout_exports']=={name:sha(ROOT/'holdout/v1'/name) for name in ['conditions.csv','observations.csv']}
 raw=ROOT/r['raw_response_ref']
 records.append(dict(file=p.name,schema_valid=True,raw_reference_exists=raw.exists(),input_hash_matches=sha(raw)==r['input_sha256'] if raw.exists() else None))
base=yaml.safe_load((ROOT/'data/extraction/records/T019-S2-Table1.yaml').read_text());negative={}
for field in ['source_format','source_locator','pagination']:
 r=copy.deepcopy(base);del r['params'][field];negative['missing_'+field]=bool(list(validator.iter_errors(r)))
for field,val in [('source_format','PDF'),('pagination','paginated'),('source_locator','')]:
 r=copy.deepcopy(base);r['params'][field]=val;negative['invalid_'+field]=bool(list(validator.iter_errors(r)))
r=copy.deepcopy(base);r['api_page_map']={'1':1};negative['fake_pdf_mapping']=bool(list(validator.iter_errors(r)));assert all(negative.values())
# Recompute every coordinate, source unit conversion and uncertainty, independently.
projects=[]
for p in sorted(DIG.glob('T019-*.digitization.yaml')):
 pr=yaml.safe_load(p.read_text());export=DIG/Path(pr['export']).name;assert sha(export)==pr['export_sha256']
 assert pr['code_version']==sha(ROOT/'scripts/extraction/extract_holdout_v1.py')
 x,y=pr['x_axis'],pr['y_axis'];sx=(x['value_2']-x['value_1'])/(x['pixel_2']-x['pixel_1']);sy=(y['value_2']-y['value_1'])/(y['pixel_2']-y['pixel_1'])
 tab=list(csv.DictReader(export.open()));factor=1/22.414 if 'S103' in p.name else 1
 for e in tab:
  px,py=float(e['pixel_x']),float(e['pixel_y']);vx=x['value_1']+(px-x['pixel_1'])*sx;vy=y['value_1']+(py-y['pixel_1'])*sy
  isbreak='S117' in p.name;assert math.isclose(vx,float(e['time_normalized_min_cm3' if isbreak else 'x_source']),abs_tol=1e-12)
  assert math.isclose(vy*factor,float(e['outlet_ratio_CO2' if isbreak else 'q']),abs_tol=1e-12)
  bound=2 if isbreak else float(e['readout_bound_px'])
  for axis,pix,ds,col,fac in [(x,px,sx,'u_time_normalized' if isbreak else 'u_p',.01 if 'S102' in p.name else 1),(y,py,sy,'u_dig',factor)]:
   t=(pix-axis['pixel_1'])/(axis['pixel_2']-axis['pixel_1']);u=abs(ds)*math.sqrt((bound*bound+(1-t)**2+t*t)/3)*fac
   assert math.isclose(u,float(e[col]),rel_tol=1e-12)
  if not isbreak:
   o=om[key(e)];assert e['q']==o['q'] and e['u_dig']==o['u_dig']
   assert o['u_p']==('' if 'S102' in p.name else e['u_p'])
 # Compare raw embedded image bytes/hash or decoded pixels with supplied image hash
 pdffile={'S113':'S113_T019.pdf','S103':'S103_T019.pdf','S102':'S102_T019.pdf','S117':'S117_SI_T019.pdf'}[next(s for s in ['S113','S103','S102','S117'] if s in p.name)]
 pdf=ROOT/'data/raw/pdf'/pdffile;assert sha(pdf)==pr['pdf_sha256'];doc=fitz.open(pdf);ims=doc[pr['pdf_page']-1].get_images();matches=[]
 for im in ims:
  b=doc.extract_image(im[0])['image'];matches.append(hashlib.sha256(b).hexdigest()==pr['image_sha256'])
 projects.append(dict(file=p.name,rows=len(tab),coordinates_conversion_uncertainty='pass',embedded_raw_hash_recovered=any(matches),private_image_available=(ROOT/pr['image_path']).exists(),export_sha256=sha(export)))
 # Independent overlay of supplied coordinates, no source-control fitting
 native=D/({'S113':'S113_T019.pdf-image0.png','S103':'S103_T019.pdf-image0.png','S102':f'S102_T019.pdf-image{"abc".index(p.name.split(".digitization")[0][-1])}.png' if 'S102' in p.name else '', 'S117':f'S117_SI_T019.pdf-image{2 if "S37" in p.name else 1}.png'}[next(s for s in ['S113','S103','S102','S117'] if s in p.name)])
 im=Image.open(native).convert('RGB');dr=ImageDraw.Draw(im)
 for e in tab:
  px,py=float(e['pixel_x']),float(e['pixel_y']);dr.ellipse((px-5,py-5,px+5,py+5),outline='blue');dr.text((px+4,py),e['point_id'],fill='black')
 im.save(D/(p.name+'.export-overlay.png'))
# S2: all rows independently parsed before exposure, normalise names only.
tables=json.loads((D/'S2-source-tables.json').read_text());norm=lambda x:x.replace(' ','')
t1={norm(r[0]):r for r in tables[0]['rows'][1:]};t2={norm(r[0]):r for r in tables[1]['rows'][2:]}
parent=t2['UiO-66-NH2'];tchecks=[]
for k,row in t2.items():
 a=t1[k];sample=k
 for suffix,val in [('Table2-dry',float(row[1])),('Table2-dry-ratio',float(row[1])/float(parent[1])),('Table2-corrected-secondary',float(row[5])),('Table1-Vp-ratio',float(a[7])/float(t1['UiO-66-NH2'][7]))]:
  o=om[('S2-'+suffix,sample)];c=cm[key(o)]
  assert math.isclose(float(o['q']),val,rel_tol=1e-12)
  assert float(c['w_PEI'])==float(a[5])/100 and c['w_reading']=='retained' and c['basis']=='dry_sorbent'
  assert c['Mw_PEI']==('' if k=='UiO-66-NH2' else '600')
  assert o['u_dig']==o['u_exp']==o['scale']==''
  tchecks.append(dict(series=o['series'],sample=sample,expected=val,match=True))
(D/'S2-comparison.json').write_text(json.dumps(tchecks,indent=2))
result=dict(head='23a87312d9ff9881f6fa4477e04013bc912b424b',rows=len(C),numeric_rows=sum(bool(o['q']) for o in O),series=len({c['series'] for c in C}),schema_columns_joins_flags='pass',D18='pass: RH/u_a only source-dry pure S2, u_T/u_exp blank; all digitization budgets recomputed without 3% floor',records=records,schema_negative_cases=negative,projects=projects,S2_comparisons=len(tchecks),protected_inputs={str(p.relative_to(ROOT)):sha(p) for p in list((ROOT/'holdout/v1').glob('*.csv'))+list((ROOT/'data/extraction/records').glob('T019-*.yaml'))+list(DIG.glob('T019-*.csv'))+list(DIG.glob('T019-*.digitization.yaml'))})
(D/'contract-checks.json').write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items() if k not in ['records','projects','protected_inputs']})
