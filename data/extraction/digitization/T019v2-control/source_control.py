"""Independent source-only template localisation; no extraction inputs."""
from pathlib import Path
import numpy as np,cv2,csv,json,hashlib,datetime
from PIL import Image
D=Path(__file__).parent
P=[];R=[]
def extract(name,file,color,seeds,shape,cal,search=5):
 im=np.array(Image.open(D/file).convert('RGB'));r,g,b=im.transpose(2,0,1).astype(float)
 if color=='orange':m=(r>210)&(g>70)&(g<210)&(b<100)
 elif color=='teal':m=(g>65)&(g>r+10)&(g>b*.85)&(b>40)&(r<160)
 elif color=='magenta':m=(r>100)&(r>g*1.5+20)&(b>30)&(b<170)&(g<100)
 elif color=='black':m=(r<80)&(g<80)&(b<80)
 elif color=='green':m=(g>100)&(g>r*1.06)&(g>b*1.3)
 elif color=='violet':m=(b>170)&(r>80)&(r<200)&(g<90)
 n=21;tpl=np.zeros((n,n),np.uint8);c=n//2
 if shape=='disc':cv2.circle(tpl,(c,c),6,1,-1)
 if shape=='ring':cv2.circle(tpl,(c,c),6,1,2)
 if shape=='square':cv2.rectangle(tpl,(c-5,c-5),(c+5,c+5),1,2)
 if shape=='filled_square':cv2.rectangle(tpl,(c-5,c-5),(c+5,c+5),1,-1)
 if shape=='small_square':cv2.rectangle(tpl,(c-2,c-2),(c+2,c+2),1,-1)
 if shape=='small_disc':cv2.circle(tpl,(c,c),3,1,-1)
 if shape=='diamond':cv2.polylines(tpl,[np.array([[c,c-7],[c+4,c],[c,c+7],[c-4,c]])],True,1,1)
 if shape in ['triangle','open_triangle']:
  pts=np.array([[c,c-7],[c+7,c+6],[c-7,c+6]])
  if shape=='triangle':cv2.fillPoly(tpl,[pts],1)
  else:cv2.polylines(tpl,[pts],True,1,2)
 # Match only inner 17x17 for large shapes; small shapes smaller support
 half=8 if shape not in ['small_square','small_disc'] else 4
 tpl=tpl[c-half:c+half+1,c-half:c+half+1].astype(np.float32)
 out=[]
 for j,(x,y) in enumerate(seeds):
  crop=m[y-half-search:y+half+search+1,x-half-search:x+half+search+1].astype(np.float32)
  corr=cv2.matchTemplate(crop,tpl,cv2.TM_CCOEFF_NORMED)
  _,score,_,loc=cv2.minMaxLoc(corr)
  px=x-search+loc[0];py=y-search+loc[1]
  (a,bv),(c0,d),(e,f),(g0,h)=cal
  sx=(d-bv)/(c0-a);sy=(h-f)/(g0-e)
  row=dict(series=name,control_id=f'{name}-{j+1:02}',px=px,py=py,x=bv+(px-a)*sx,y=f+(py-e)*sy,score=score,u_x=abs(sx)*3/np.sqrt(3),u_y=abs(sy)*3/np.sqrt(3))
  out.append(row);R.append(row)
 vis=im.copy()
 for pt in out:cv2.circle(vis,(pt['px'],pt['py']),10,(0,0,255),1)
 Image.fromarray(vis).save(D/(name+'-accepted.png'))
 P.append(dict(series=name,image=file,image_sha256=hashlib.sha256((D/file).read_bytes()).hexdigest(),shape=shape,color=color,seeds=seeds,search=search,calibration=cal,linear=True,readout_bound_px=3,uncertainty='uniform bound / sqrt(3), k=1; calibration/readout only; no 3% floor',points=out))
f='S103_T019.pdf-image0.png';cal=[(141,0),(688,1),(550,0),(13,90)]
# Marker locations are source-view ROIs only, measured by the template tool.
# source orange filled branch, choose well-separated high-pressure markers
extract('S103-100-ads',f,'orange',[(346,337),(387,311),(428,278),(469,253),(510,228),(551,205),(592,181),(633,158),(686,121)],'disc',cal,6)
extract('S103-100-des',f,'orange',[(332,332),(373,300),(414,272),(455,245),(496,220),(537,196),(578,173),(619,152),(674,127)],'ring',cal,6)
extract('S103-160-ads',f,'teal',[(686,228)],'filled_square',cal,3)
extract('S103-160-des',f,'teal',[(332,380),(373,359),(414,340),(455,321),(496,303),(537,280),(578,265),(619,250),(674,233)],'square',cal,6)
extract('S103-220-ads',f,'magenta',[(346,400),(387,377),(428,351),(469,333),(510,310),(551,291),(592,276),(633,261),(686,246)],'triangle',cal,6)
extract('S103-220-des',f,'magenta',[(332,391),(373,370),(414,350),(455,330),(496,313),(537,297),(578,280),(619,264),(674,250)],'open_triangle',cal,6)
f='S113_T019.pdf-image0.png'
extract('S113-a',f,'black',[(120,231),(154,213),(183,198),(215,183),(254,164),(287,151),(330,130),(382,106)],'small_square',[(62,0),(386,1),(265,0),(14,1.6)],4)
extract('S113-b',f,'black',[(515,255),(547,247),(578,237),(605,227),(645,209),(668,198),(712,181),(755,160),(815,135)],'small_square',[(483,0),(802,1),(264,0),(16,.16)],4)
for i,seeds,cal in [
 (0,[(284,357),(485,262),(566,220),(643,198),(750,127)],[(114,0),(752,8),(442,0),(26,.2)]),
 (1,[(235,374),(345,321),(470,250),(602,166),(726,98)],[(114,0),(752,8),(442,0),(26,.2)]),
 (2,[(245,369),(382,320),(524,253),(650,189),(751,148)],[(111,0),(736,8),(433,0),(25,.2)])]:
 extract(f'S102-{chr(97+i)}',f'S102_T019.pdf-image{i}.png','green',seeds,'diamond',cal,5)
# Distance-transform separates filled CO2 discs from thin connecting lines/open N2 rings.
for name,img,box,cal in [
 ('S117-S37A',2,(170,205,325,435),[(104,0),(628,125),(448,0),(31,1.6)]),
 ('S117-S37B',2,(790,195,910,435),[(740,0),(1262,100),(448,0),(31,1.6)]),
 ('S117-S38A',1,(190,205,365,435),[(98,0),(622,125),(448,0),(31,1.6)]),
 ('S117-S38B',1,(790,190,920,435),[(731,0),(1256,125),(448,0),(31,1.6)])]:
 im=np.array(Image.open(D/f'S117_SI_T019.pdf-image{img}.png').convert('RGB'));r,g,b=im.transpose(2,0,1).astype(float)
 m=((b>170)&(r>80)&(r<200)&(g<90)).astype('uint8')
 dist=cv2.distanceTransform(m,cv2.DIST_L2,5)
 x0,y0,x1,y1=box;keep=np.zeros_like(m);keep[y0:y1,x0:x1]=1
 n,l,stats,cent=cv2.connectedComponentsWithStats(((dist>2.15)&(keep>0)).astype('uint8'))
 seeds=[tuple(map(round,c)) for st,c in zip(stats[1:],cent[1:]) if st[4]>=1]
 seeds.sort()
 extract(name,f'S117_SI_T019.pdf-image{img}.png','violet',seeds,'small_disc',cal,2)
(D/'source-projects.json').write_text(json.dumps(P,indent=2))
with (D/'source-controls.csv').open('w') as h:
 w=csv.DictWriter(h,fieldnames=list(R[0]));w.writeheader();w.writerows(R)
print({p['series']:len(p['points']) for p in P})
