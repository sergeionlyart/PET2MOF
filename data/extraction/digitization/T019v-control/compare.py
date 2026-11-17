#!/usr/bin/env python3
"""Compare frozen independent controls; never writes any T019 file or holdout."""
from pathlib import Path
import collections,csv,hashlib,json,math,xml.etree.ElementTree as E
OUT=Path('data/extraction/digitization/T019v-control')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open()))
def write(p,rows):
 with Path(p).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
c=read('holdout/v1/conditions.csv');o=read('holdout/v1/observations.csv');cm={(x['series'],x['point_id']):x for x in c};om={(x['series'],x['point_id']):x for x in o}
issues=[]
for label,rows in [('conditions',c),('observations',o)]:
 keys=[(r['series'],r['point_id']) for r in rows]
 if len(keys)!=len(set(keys)):issues.append(label+' duplicate keys')
if cm.keys()!=om.keys():issues.append('unpaired keys')
for key,x in cm.items():
 for field in ['source_id','extraction_id','observable']:
  if x[field]!=om[key][field]:issues.append(str(key)+' metadata mismatch '+field)
 if not Path('data/extraction/records/'+x['extraction_id']+'.yaml').exists():issues.append(str(key)+' missing passport')
 if x['source_id'] in ['S102','S117'] and om[key]['inputs_known']!='false':issues.append(str(key)+' falsely known')
 if 'moist' in x['series'] and (x['RH_fraction']!='' or om[key]['comparable']!='false' or om[key]['q']!=''):issues.append(str(key)+' moist quantitative')
expected_c='series point_id source_id extraction_id material gas observable unit basis T_K p_total_bar p_partial_bar y_CO2_dry RH_fraction w_PEI w_reading Mw_PEI notes'.split()
expected_o='series point_id source_id extraction_id q u_exp u_dig u_p u_T u_a dq_dp dq_dT dq_da scale observable comparable inputs_known'.split()
if list(c[0])!=expected_c or list(o[0])!=expected_o:issues.append('column mismatch')
# Independently parse each complete source table. JATS row order differs between tables.
r=E.parse('private/T019v/S2.xml').getroot();tables={}
for tid in ['tbl1','tbl2']:
 t=r.find(f'.//table-wrap[@id="{tid}"]');rows=[]
 for tr in t.findall('.//tbody/tr'):
  rows.append([''.join(td.itertext()).strip() for td in tr.findall('td')])
 tables[tid]=rows
(OUT/'S2-primary-tables.json').write_text(json.dumps({'source_url':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6648867/fullTextXML','source_sha256':sha('private/T019v/S2.xml'),'rows':tables,'visual_original_pdf':'unavailable; no synthetic rendering passed as original'},indent=2)+'\n')
t1={x[0]:x for x in tables['tbl1']};t2={x[0]:x for x in tables['tbl2']};parent='UiO-66-NH2'
s2=[]
for sample,x in t1.items():
 y=t2[sample]
 values={'S2-Table2-dry':float(y[1]),'S2-Table2-dry-ratio':float(y[1])/float(t2[parent][1]),'S2-Table2-corrected-secondary':float(y[5]),'S2-Table1-Vp-ratio':float(x[7])/float(t1[parent][7])}
 for series,q in values.items():
  key=(series,sample);a=om[key];b=cm[key]
  s2.append(dict(series=series,point_id=sample,control_q=q,T019_q=float(a['q']),delta=float(a['q'])-q,retained_w=float(x[5])/100,w_matches=math.isclose(float(b['w_PEI']),float(x[5])/100),Mw_matches=(b['Mw_PEI']=='600' if sample!=parent else b['Mw_PEI']==''),basis=b['basis'],inputs_known=a['inputs_known']))
write(OUT/'S2-comparison.csv',s2)
# Freeze project and control hashes before inspecting comparison residuals.
(OUT/'comparison_inputs.json').write_text(json.dumps({str(p):sha(p) for p in [OUT/'projects.json',OUT/'controls.csv',OUT/'control.py',Path('holdout/v1/conditions.csv'),Path('holdout/v1/observations.csv')]},indent=2)+'\n')
projects=json.loads((OUT/'projects.json').read_text());controls=read(OUT/'controls.csv');comp=[];summary=[]
for pr in projects:
 name=pr['series'];pool=[r for r in controls if r['series']==name]
 if name.startswith('S117'):
  fig=name.split('-')[1];source=read(f'data/extraction/digitization/T019-S117-{fig}.csv');source=[x for x in source if x['series']==pr['reference_series']];source_x='time_normalized_min_cm3';source_q='outlet_ratio_CO2'
 else:
  source=[dict(x,source_pressure=cm[(x['series'],x['point_id'])]['p_partial_bar']) for x in o if x['series']==name];source_x='source_pressure';source_q='q'
  if name.startswith('S102'):
   fig=name.split('-')[1];source=read(f'data/extraction/digitization/T019-S102-{fig}.csv');source_x='x_source';source_q='q'
 # Match by independently measured abscissa only, never uptake.
 used=set();matched=[]
 for a in pool:
  xp=float(a['display_pressure'])
  if not name.startswith(('S102','S117')):factor=1
  else:factor=1
  if not source:continue
  candidates=[(i,b) for i,b in enumerate(source) if i not in used and b.get(source_x,'')!='']
  if not candidates:continue
  i,b=min(candidates,key=lambda pair:abs(float(pair[1][source_x])-xp))
  # Four native pixels; S102 source pressure is kPa and Madden normalized time.
  tolerance=abs(pr['x_axis']['slope'])*4
  if abs(float(b[source_x])-xp)>tolerance:continue
  used.add(i);q=float(b[source_q]);delta=float(a['control_q'])-q;u=float(b['u_dig']);uc=float(a['control_u_dig']);combined=math.hypot(u,uc)
  row=dict(series=name,control_id=a['control_id'],point_id=b['point_id'],control_x=xp,T019_x=float(b[source_x]),control_q=float(a['control_q']),T019_q=q,delta=delta,abs_delta=abs(delta),T019_u_dig=u,control_u_dig=uc,abs_delta_over_u_dig=abs(delta)/u,abs_delta_over_combined_u=abs(delta)/combined,within_T019_u_dig=abs(delta)<=u,within_2_combined_u=abs(delta)<=2*combined)
  comp.append(row);matched.append(row)
 summary.append(dict(series=name,candidates=len(pool),matched=len(matched),export_rows=len(source),required_control_count=8,quota_met=len(matched)>=8,within_T019_u_dig=sum(x['within_T019_u_dig'] for x in matched),within_2_combined_u=sum(x['within_2_combined_u'] for x in matched),max_abs_delta_over_u_dig=max((x['abs_delta_over_u_dig'] for x in matched),default=None),max_abs_delta_over_combined_u=max((x['abs_delta_over_combined_u'] for x in matched),default=None)))
write(OUT/'comparison.csv',comp)
(OUT/'comparison_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
# Capture proof scope without modifying base evidence.
protected=[Path('holdout/v1/conditions.csv'),Path('holdout/v1/observations.csv')]+sorted(Path('data/extraction/digitization').glob('T019-*'))+sorted(Path('data/extraction/records').glob('T019-*'))
protected=[p for p in protected if p.is_file()]
(OUT/'protected_hashes.json').write_text(json.dumps({str(p):sha(p) for p in protected},indent=2)+'\n')
result=dict(conditions_rows=len(c),observations_rows=len(o),series=len(set(x['series'] for x in c)),numeric_observation_rows=sum(bool(x['q']) for x in o),placeholder_rows=sum(not bool(x['q']) for x in o),schema_and_join_issues=issues,conditions_observation_columns_present=sorted(set(c[0])&set(['q','u_exp','u_dig','scale'])),S2_numeric_checks=len(s2),S2_values_exact=all(abs(x['delta'])<1e-12 for x in s2),S2_retained_w_all_match=all(x['w_matches'] for x in s2),S2_Mw_all_match=all(x['Mw_matches'] for x in s2),control_matches=len(comp),source_XML_sha256=sha('private/T019v/S2.xml'))
(OUT/'schema_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));print(json.dumps(summary,indent=2))
