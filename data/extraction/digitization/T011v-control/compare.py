from pathlib import Path
import csv,json,hashlib,statistics,math
from collections import defaultdict,Counter
from PIL import Image,ImageDraw
import yaml
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def read(p):return list(csv.DictReader(p.open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
freeze=json.loads((OUT/'blind_freeze.json').read_text());assert sha(OUT/'blind_controls.csv')==freeze['controls_sha256']
controls=read(OUT/'blind_controls.csv');groups=defaultdict(list)
for r in controls:groups[(r['extraction_id'].replace('T011v-',''),r['series'])].append(r)
comparisons=[];summary=[]
for (panel,mat),cc in groups.items():
 path=ROOT/f'data/extraction/digitization/T011-{panel}.csv'; raw=[r for r in read(path) if r['series']==mat]
 pr=yaml.safe_load(path.with_suffix('.digitization.yaml').read_text())
 checks=[]
 for r in cc:
  idx,s=min(enumerate(raw),key=lambda z:abs(float(z[1]['x'])-float(r['p_native'])))
  item=dict(panel=panel,series=mat,check_id=r['check_id'],control_x=float(r['p_native']),control_q=float(r['q_native']),T011_row_in_series=idx+1,T011_x=float(s['x']),T011_q=float(s['y']),dp=abs(float(s['x'])-float(r['p_native'])),dq=abs(float(s['y'])-float(r['q_native'])),T011_x_err=float(s['x_err']),T011_y_err=float(s['y_err']),processed_p_bound=max(float(s['x_err']),.03*pr['protocol_scale_span_x']),processed_q_bound=max(float(s['y_err']),.03*pr['protocol_scale_span_y']))
  checks.append(item);comparisons.append(item)
 st=dict(panel=panel,series=mat,n_check=len(cc),n_T011=len(raw),max_dq=max(x['dq'] for x in checks),median_dq=statistics.median(x['dq'] for x in checks),max_dp=max(x['dp'] for x in checks),median_dp=statistics.median(x['dp'] for x in checks),raw_q_bound=checks[0]['T011_y_err'],raw_p_bound=checks[0]['T011_x_err'],n_over_raw=sum(x['dq']>x['T011_y_err'] or x['dp']>x['T011_x_err'] for x in checks),n_over_processed=sum(x['dq']>x['processed_q_bound'] or x['dp']>x['processed_p_bound'] for x in checks))
 summary.append(st)
 print(panel,mat,'n=',len(raw),'dq max/median',round(st['max_dq'],6),round(st['median_dq'],6),'dp',round(st['max_dp'],6),'over raw/proc',st['n_over_raw'],st['n_over_processed'])
for fn,rows in [('comparison_points.csv',comparisons),('comparison_summary.csv',summary)]:
 with (OUT/fn).open('w') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
for panel in sorted({p for p,m in groups}):
 project=json.loads((OUT/f'{panel}.project.json').read_text());cal=project['calibration'];(x0,v0),(x1,v1)=cal['x'];(y0,w0),(y1,w1)=cal['y']
 im=Image.open(OUT/f'{panel}.png').convert('RGB');dr=ImageDraw.Draw(im)
 for mat in project['series']:
  raw=[r for r in read(ROOT/f'data/extraction/digitization/T011-{panel}.csv') if r['series']==mat]
  for i,r in enumerate(raw):
   px=x0+float(r['x'])/v1*(x1-x0);py=y0+float(r['y'])/w1*(y1-y0)
   dr.ellipse((px-14,py-14,px+14,py+14),outline='orange',width=2);dr.text((px+6,py+12),str(i+1),fill='black')
 im.save(OUT/f'{panel}-T011-overlay.png')
