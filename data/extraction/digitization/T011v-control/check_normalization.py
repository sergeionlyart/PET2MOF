"""Read-only independent arithmetic/schema audit; no holdout inputs are opened."""
from pathlib import Path
import csv,json,math,hashlib,collections
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
D=ROOT/'data/processed/c_series';M=json.loads((D/'manifest.json').read_text())
def read(p):return list(csv.DictReader(p.open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=2e-10,abs_tol=1e-11),(a,b)
# Independent transcription from official IAPWS SR1-86, page 3, Eq. 1.
t=293.;tc=647.096;tau=1-t/tc
lnratio=tc/t*(-7.85951783*tau+1.84408259*tau**1.5-11.7866497*tau**3+22.6807411*tau**3.5-15.9618719*tau**4+1.80122502*tau**7.5)
psat=22.064*10*math.exp(lnratio)
close(psat,M['water_conversion']['psat_293K_bar'])
R=8.31446261815324
ideal_cm3_per_mmol=R*273.15/101325*1000
close(M['water_conversion']['STP_cm3_per_mmol'],22.414)
roles=collections.Counter();sources=collections.Counter();kinds=collections.Counter();statuses=collections.Counter();normalization=collections.Counter();hashes=0;rebuild=0
fields=['series_id','source_id','extraction_id','material','gas','T_K','p_bar','q_mmol_g','q_err_mmol_g','p_err_bar','data_kind','status']
assert M['fields']==fields
for rel,h in M['inputs'].items():
 assert not any('/'+v in rel for v in ['S2.','S2-','S103','S113'])
 assert sha(ROOT/rel)==h;hashes+=1
for sid,meta in M['series'].items():
 p=D/(sid+'.csv');rows=read(p);roles[meta['role']]+=1
 assert len(rows)==meta['rows'];assert sha(p)==meta['csv_sha256']
 assert p.read_bytes()==(ROOT/'tmp/T011v-rebuild'/p.name).read_bytes();rebuild+=1
 assert list(rows[0])==fields
 for r in rows:
  assert r['series_id']==sid and r['source_id'] not in {'S2','S103','S113'}
  assert r['extraction_id']!='T011-S105-Table3';assert r['data_kind']!='author_fit'
  sources[r['source_id']]+=1;kinds[r['data_kind']]+=1;statuses[r['status']]+=1
  assert all(math.isfinite(float(r[k])) and float(r[k])>=0 for k in ['T_K','p_bar','q_mmol_g'])
  for k in ['p_err_bar','q_err_mmol_g']:assert r[k]=='' or float(r[k])>0
  if r['source_id'] in ['S105','S106']:
   orig=read(ROOT/f"data/extraction/digitization/{r['extraction_id']}.csv")
   orig=[x for x in orig if x['series']==r['material']]
   pf=psat if r['source_id']=='S106' else 1;qf=1/22.414 if r['source_id']=='S106' else 1
   o=min(orig,key=lambda x:abs(float(x['x'])*pf-float(r['p_bar'])))
   close(r['p_bar'],float(o['x'])*pf);close(r['q_mmol_g'],float(o['y'])*qf)
   close(r['T_K'],o['T_K']);assert r['gas']==o['gas'];assert r['status']=='provisional'
   assert meta['role']==('context_GO' if '/GO' in r['material'] else 'C_candidate')
   if pf!=1:close(o['x'],o['RH_fraction']);close(float(o['x'])*100,o['RH_percent'])
   normalization[r['source_id']]+=1
  elif r['source_id']=='S100':
   assert meta['role']=='C'
   if r['extraction_id']=='T006-S100-FigS5':
    orig=[x for x in read(ROOT/'data/extraction/digitization/T006-S100-FigS5.csv') if x['series']==r['material']]
    o=min(orig,key=lambda x:abs(float(x['x_display_kPa'])/100-float(r['p_bar'])))
    close(r['p_bar'],float(o['x_display_kPa'])/100);close(r['q_mmol_g'],o['uptake_mmol_g']);assert r['status']=='verified';normalization['S100']+=1
   else:assert r['status']=='provisional' and r['p_err_bar']==r['q_err_mmol_g']=='';normalization['S100_NIST_only']+=1
  else:
   assert meta['role']=='sensitivity_only' and r['status']=='provisional'
   assert r['q_err_mmol_g']==r['p_err_bar']==''
assert (D/'manifest.json').read_bytes()==(ROOT/'tmp/T011v-rebuild/manifest.json').read_bytes()
# Visual transcription of all 36 printed numbers of Table 3 on PDF page 10.
expected={'UiO-66':[(11.78,.45,.999),(15.49,.17,.999),(4.42,.45,.999)],'UiO-66-NH2':[(12.63,.45,.999),(8.28,.45,.999),(3.82,.71,.998)],'UiO-66/GO':[(10.83,1.26,.997),(6.03,1.20,.997),(3.37,1.22,.997)],'UiO-66-NH2/GO':[(10.92,1.39,.996),(6.38,1.41,.996),(4.39,1.06,.998)]}
table=read(ROOT/'data/extraction/digitization/T011-S105-Table3.csv')
assert len(table)==12
for r in table:
 for k,v in zip(['Q_m_display','b_display','R_squared'],expected[r['material']][[273,298,318].index(int(r['T_K']))]):close(r[k],v)
 assert r['data_kind']=='author_fit'
result=dict(psat_293K_bar=psat,ideal_STP_cm3_per_mmol=ideal_cm3_per_mmol,STP_rounding_relative_error=22.414/ideal_cm3_per_mmol-1,roles=dict(roles),sources=dict(sources),kinds=dict(kinds),statuses=dict(statuses),independently_checked_conversion_rows=dict(normalization),input_hashes_verified=hashes,rebuilt_csv_identical=rebuild,manifest_identical=True,table3_numbers_verified=36,no_holdout_rows=True,no_author_fit_in_measurements=True)
(OUT/'normalization_checks.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
