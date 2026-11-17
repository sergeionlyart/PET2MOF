from pathlib import Path
import csv,json,math,hashlib,yaml,collections
D=Path(__file__).parent;root=D.parents[3]
controls=list(csv.DictReader((D/'source-controls.csv').open()))
mapseries={
 'S113-a':('T019-S113-Fig5a','S113-Fig5a-UiO66',1),
 'S113-b':('T019-S113-Fig5b','S113-Fig5b-UiO66',1),
 **{f'S103-{s}-{b}':('T019-S103-Fig2a',f'S103-Fig2a-UiO66_{s}-'+{'ads':'adsorption','des':'desorption'}[b],1/22.414) for s in ['100','160','220'] for b in ['ads','des']},
 **{f'S102-{a}':(f'T019-S102-FigS6{a}',f'S102-FigS6{a}-binary',1) for a in 'abc'},
 **{f'S117-{s}':(f'T019-S117-Fig{s}',f'{s}-wet-CO2',1) for s in ['S37A','S37B','S38A','S38B']}}
res=[];summ=[]
for alias,(file,series,factor) in mapseries.items():
 cs=[c for c in controls if c['series']==alias];ex=[e for e in csv.DictReader((D.parent/(file+'.csv')).open()) if e['series']==series];used=set();local=[]
 for c in cs:
  c={k:float(v) if k not in ['series','control_id'] else v for k,v in c.items()}
  e=min(ex,key=lambda e:math.hypot(float(e['pixel_x'])-c['px'],float(e['pixel_y'])-c['py']))
  pd=math.hypot(float(e['pixel_x'])-c['px'],float(e['pixel_y'])-c['py'])
  matched=pd<=6 and e['point_id'] not in used
  if matched:used.add(e['point_id'])
  ykey='outlet_ratio_CO2' if file.startswith('T019-S117') else 'q'
  delta=c['y']*factor-float(e[ykey]);u=math.hypot(c['u_y']*factor,float(e['u_dig']))
  r=dict(control_id=c['control_id'],series=series,point_id=e['point_id'],matched=matched,pixel_distance=pd,control_px=c['px'],control_py=c['py'],export_px=e['pixel_x'],export_py=e['pixel_y'],control_q=c['y']*factor,export_q=e[ykey],delta=delta,u_control=c['u_y']*factor,u_dig=float(e['u_dig']),z=delta/u,within_u_dig=abs(delta)<=float(e['u_dig']),within_2_combined=abs(delta)<=2*u)
  res.append(r);local.append(r)
 summ.append(dict(series=series,export_rows=len(ex),source_controls=len(cs),matched=len(used),quota_met=len(used)>=8,within_u_dig=sum(r['within_u_dig'] for r in local if r['matched']),within_2_combined=sum(r['within_2_combined'] for r in local if r['matched']),unmatched=[r['control_id'] for r in local if not r['matched']],outside_2_combined=[r['control_id'] for r in local if r['matched'] and not r['within_2_combined']]))
with (D/'comparison.csv').open('w') as h:
 w=csv.DictWriter(h,fieldnames=list(res[0]));w.writeheader();w.writerows(res)
(D/'comparison-summary.json').write_text(json.dumps(summ,indent=2));print(json.dumps(summ,indent=2))
