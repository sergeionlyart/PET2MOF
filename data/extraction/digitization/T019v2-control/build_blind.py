"""Source-only marker template measurement. Never reads T019 exports."""
from pathlib import Path
import cv2, numpy as np, csv, json, hashlib, datetime
D=Path(__file__).parent
projects=[]; rows=[]
def measure(name,file,channel,box,template,cal,limit=12,threshold=.78,minsep=9):
 im=np.array(__import__('PIL.Image',fromlist=['Image']).open(D/file).convert('RGB'))
 r,g,b=im.transpose(2,0,1).astype(float)
 if channel=='orange':mask=(r>200)&(g>70)&(g<210)&(b<100)
 elif channel=='teal':mask=(g>65)&(g>r+10)&(g>b*.85)&(b>40)&(r<160)
 elif channel=='magenta':mask=(r>100)&(r>g*1.5+20)&(b>30)&(b<170)&(g<100)
 elif channel=='black':mask=(r<80)&(g<80)&(b<80)
 elif channel=='green':mask=(g>100)&(g>r*1.06)&(g>b*1.3)
 elif channel=='violet':mask=(b>170)&(r>80)&(r<200)&(g<90)
 mask=mask.astype('uint8')*255
 tx,ty,tw,th=template;templ=mask[ty:ty+th,tx:tx+tw]
 x0,y0,x1,y1=box;crop=mask[y0:y1,x0:x1]
 corr=cv2.matchTemplate(crop,templ,cv2.TM_CCOEFF_NORMED)
 candidates=[]
 while len(candidates)<limit:
  _,score,_,pos=cv2.minMaxLoc(corr)
  if score<threshold:break
  x,y=pos;px=x+x0+(tw-1)/2;py=y+y0+(th-1)/2
  candidates.append(dict(px=px,py=py,score=float(score)))
  cv2.rectangle(corr,(max(0,x-minsep),max(0,y-minsep)),(x+minsep,y+minsep),-1,-1)
 # no curve regression or use of T019 coordinates
 candidates.sort(key=lambda v:v['px'])
 a,c,d,e=cal # x pixel,value; y pixel,value provided as pairs
 sx=(c[1]-a[1])/(c[0]-a[0]);sy=(e[1]-d[1])/(e[0]-d[0])
 for n,p in enumerate(candidates):
  p.update(series=name,control_id=f'{name}-{n+1:02}',x=a[1]+(p['px']-a[0])*sx,y=d[1]+(p['py']-d[0])*sy,u_x=abs(sx)*1.5/3**.5,u_y=abs(sy)*1.5/3**.5)
  rows.append(p)
 vis=im.copy()
 for p in candidates:cv2.circle(vis,(round(p['px']),round(p['py'])),11,(0,0,255),1)
 __import__('PIL.Image',fromlist=['Image']).fromarray(vis).save(D/(name+'-overlay.png'))
 projects.append(dict(series=name,image=file,sha256=hashlib.sha256((D/file).read_bytes()).hexdigest(),channel=channel,box=box,template=template,calibration=cal,scales='linear',threshold=threshold,minsep=minsep,readout_bound_px=1.5,u_convention='uniform bound / sqrt(3), k=1; no experimental floor',points=candidates))
# source S103 panel a; y original cm3(STP)/g, unit conversion deferred
f='S103_T019.pdf-image0.png';cal=[(141,0),(688,1),(550,0),(13,90)]
measure('S103-100-ads',f,'orange',(220,95,705,500),(679,114,15,15),cal,12,.78,10)
measure('S103-100-des',f,'orange',(220,95,685,500),(667,119,15,15),cal,12,.78,10)
measure('S103-160-ads',f,'teal',(675,215,700,240),(679,221,14,14),cal,1,.9,10)
measure('S103-160-des',f,'teal',(280,200,685,450),(667,226,14,14),cal,12,.75,10)
measure('S103-220-ads',f,'magenta',(270,230,705,440),(678,237,17,17),cal,12,.73,10)
measure('S103-220-des',f,'magenta',(270,230,685,440),(665,241,17,17),cal,12,.73,10)
# S113 combined two-panel bitmap; actual squares, avoid legend and origin overlap
f='S113_T019.pdf-image0.png'
measure('S113-a',f,'black',(110,70,401,250),(283,147,9,9),[(62,0),(386,1),(265,0),(14,1.6)],12,.68,12)
measure('S113-b',f,'black',(505,90,819,263),(728,172,9,9),[(483,0),(802,1),(264,0),(16,.16)],12,.68,12)
# binary diamond controls; only distinct symbols, exclude legend
for i,templ,cal,box in [
 (0,(742,118,15,19),[(114,0),(752,8),(442,0),(26,.2)],(200,105,775,425)),
 (1,(719,88,15,20),[(114,0),(752,8),(442,0),(26,.2)],(200,75,775,425)),
 (2,(743,139,15,19),[(111,0),(736,8),(433,0),(25,.2)],(190,130,775,425))]:
 measure(f'S102-{chr(97+i)}',f'S102_T019.pdf-image{i}.png','green',box,templ,cal,15,.62,18)
# filled wet CO2 markers in S37 and S38, distinguish from open N2
for fig,img,panel,box,templ,cal in [
 ('S37',2,'A',(160,180,320,430),(236,340,11,11),[(104,0),(628,125),(448,0),(31,1.6)]),
 ('S37',2,'B',(810,180,910,430),(843,313,11,11),[(740,0),(1262,100),(448,0),(31,1.6)]),
 ('S38',1,'A',(190,190,410,430),(259,325,11,11),[(98,0),(622,125),(448,0),(31,1.6)]),
 ('S38',1,'B',(790,205,875,430),(819,341,11,11),[(731,0),(1256,125),(448,0),(31,1.6)])]:
 measure(f'S117-{fig}{panel}',f'S117_SI_T019.pdf-image{img}.png','violet',box,templ,cal,12,.63,10)
(D/'blind-projects.json').write_text(json.dumps(projects,indent=2))
with (D/'blind-controls.csv').open('w') as h:
 w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print({p['series']:len(p['points']) for p in projects})
