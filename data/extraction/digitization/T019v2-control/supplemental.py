"""Post-disclosure source geometry audit. Not counted as strict blind evidence."""
from pathlib import Path
from PIL import Image,ImageDraw
import cv2,numpy as np,csv,json,math
D=Path(__file__).parent;out=[];summary=[]
for fig,index,color in [('S37',2,'blue'),('S38',1,'green')]:
 im=np.array(Image.open(D/f'S117_SI_T019.pdf-image{index}.png').convert('RGB'));r,g,b=im.transpose(2,0,1).astype(float)
 mask=((b>150)&(r<75)&(g<100)) if color=='blue' else ((g>65)&(r<80)&(b<80))
 dist=cv2.distanceTransform(mask.astype('uint8'),cv2.DIST_L2,5)
 for panel,box in [('A',(180,210,520,435)),('B',(800,195,1055,435))]:
  x0,y0,x1,y1=box;keep=np.zeros_like(mask);keep[y0:y1,x0:x1]=1
  n,lab,stats,cent=cv2.connectedComponentsWithStats(((dist>2.15)&keep).astype('uint8'))
  pts=[dict(px=float(c[0]),py=float(c[1])) for st,c in zip(stats[1:],cent[1:]) if st[4]>=1];pts.sort(key=lambda p:p['px'])
  # current export read only AFTER all source centres calculated for this panel
  export=list(csv.DictReader((D.parent/f'T019-S117-Fig{fig}{panel}.csv').open()));exp=[e for e in export if e['series']==f'{fig}{panel}-dry-CO2'];used=set();ms=[]
  for p in pts:
   e=min(exp,key=lambda e:math.hypot(float(e['pixel_x'])-p['px'],float(e['pixel_y'])-p['py']));pd=math.hypot(float(e['pixel_x'])-p['px'],float(e['pixel_y'])-p['py'])
   if pd<=5 and e['point_id'] not in used:
    used.add(e['point_id']);ms.append(p|dict(point_id=e['point_id'],distance_px=pd))
  overlay=Image.fromarray(im);draw=ImageDraw.Draw(overlay)
  for p in pts:draw.ellipse((p['px']-8,p['py']-8,p['px']+8,p['py']+8),outline='orange')
  overlay.save(D/f'{fig}{panel}-dry-supplemental.png');out.append(dict(series=f'{fig}{panel}-dry-CO2',phase='post-disclosure, not blind',image=f'S117_SI_T019.pdf-image{index}.png',method='colour-mask distance transform >2.15 px, component centroids',source_points=pts,matches=ms))
  summary.append(dict(series=f'{fig}{panel}-dry-CO2',controls=len(pts),matches=len(ms),quota_met=len(ms)>=8,blind=False))
# extra lower-pressure triangle geometry, deliberately kept separate from frozen controls
im=np.array(Image.open(D/'S103_T019.pdf-image0.png').convert('RGB'));r,g,b=im.transpose(2,0,1).astype(float)
m=((r>100)&(r>g*1.5+20)&(b>30)&(b<170)&(g<100)).astype('float32')
tpl=np.zeros((19,19),np.uint8);cv2.fillPoly(tpl,[np.array([[9,2],[16,15],[2,15]])],1)
corr=cv2.matchTemplate(m[350:540,155:360],tpl.astype('float32'),cv2.TM_CCOEFF_NORMED);pts=[]
for k in range(12):
 _,score,_,pos=cv2.minMaxLoc(corr)
 if score<.72:break
 x,y=pos;pts.append(dict(px=x+155+9,py=y+350+9,score=score));cv2.rectangle(corr,(max(0,x-10),max(0,y-10)),(x+10,y+10),-1,-1)
pts.sort(key=lambda p:p['px']);out.append(dict(series='S103-220-ads-supplemental',phase='post-disclosure, not blind',method='synthetic filled-triangle template, full source-only ROI',source_points=pts))
(D/'supplemental-controls.json').write_text(json.dumps(out,indent=2));(D/'supplemental-summary.json').write_text(json.dumps(summary,indent=2));print(summary);print('extra_triangle_controls',len(pts))
