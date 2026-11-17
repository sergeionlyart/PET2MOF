from pathlib import Path
import json,numpy as np
from PIL import Image
P=Path(__file__).resolve().parent
out={}
for name,xvals,yvals in [('S105-Fig8A',[.2,.4,.6,.8,1],[1,2,3,4,5,6,7]),('S105-Fig8B',[.2,.4,.6,.8,1],[1,2,3]),('S105-Fig8C',[.2,.4,.6,.8,1],[1,2]),('S105-Fig9',[.2,.4,.6,.8,1],[.1,.2,.3]),('S106-Fig4',[.2,.4,.6,.8],[100,200,300,400,500])]:
 j=json.loads((P/f'{name}.project.json').read_text());a=np.asarray(Image.open(P/f'{name}.png'));m=a[:,:,:3].max(2)<90
 (x0,_),(x1,xv)=j['calibration']['x'];(y0,_),(y1,yv)=j['calibration']['y'];rr=[]
 axis_x=165 if name.startswith('S106') else x0
 frame_y=996 if name.startswith('S106') else y0
 for v in xvals:
  pred=x0+(x1-x0)*v/xv;lo=round(pred)-8;hi=round(pred)+9
  scores=m[round(frame_y)-18:round(frame_y)-5,lo:hi].sum(0);hits=np.where(scores>=.9*max(scores))[0];px=float(lo+hits.mean());val=(px-x0)/(x1-x0)*xv
  rr.append(dict(axis='x',printed_value=v,pixel=px,residual=val-v))
 for v in yvals:
  pred=y0+(y1-y0)*v/yv;lo=round(pred)-8;hi=round(pred)+9
  scores=m[lo:hi,round(axis_x)+5:round(axis_x)+18].sum(1);hits=np.where(scores>=.9*max(scores))[0];px=float(lo+hits.mean());val=(y0-px)/(y0-y1)*yv
  rr.append(dict(axis='y',printed_value=v,pixel=px,residual=val-v))
 out[name]=rr
 print(name,'max tick residual',max(abs(r['residual']) for r in rr if r['axis']=='x'),max(abs(r['residual']) for r in rr if r['axis']=='y'))
(P/'calibration_tick_checks.json').write_text(json.dumps(out,indent=2))
