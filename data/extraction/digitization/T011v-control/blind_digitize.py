"""Independent raster control. Reads only source PDFs, never T011 artifacts."""
from pathlib import Path
import fitz, json, hashlib, csv
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PANELS={
 'S105-Fig8A':('S105_T011.pdf',8,(173,277,423,477)),
 'S105-Fig8B':('S105_T011.pdf',8,(173,479,423,683)),
 'S105-Fig8C':('S105_T011.pdf',9,(176,87,420,293)),
 'S105-Fig9':('S105_T011.pdf',11,(164,343,431,542)),
 'S106-Fig4':('S106.pdf',5,(308,55,556,245)),
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def render():
 for name,(file,page,clip) in PANELS.items():
  pdf=ROOT/'data/raw/pdf'/file
  d=fitz.open(pdf); pix=d[page-1].get_pixmap(matrix=fitz.Matrix(6,6),clip=fitz.Rect(clip),alpha=False)
  pix.save(OUT/f'{name}.png')
if __name__=='__main__':render()
# Tick locations independently read from the rendered source; refined by dark-pixel projections.
AXES={
'S105-Fig8A':(171,1422,979,48,1.2,8),
'S105-Fig8B':(181,1431,964,136,1.2,4),
'S105-Fig8C':(147,1397,980,48,1.2,3),
'S105-Fig9':(224,1535,1017,41,1.2,.4),
'S106-Fig4':(282,1456,965,37,1,600),
}
COLORS={'black':(0,0,0),'red':(255,0,0),'blue':(0,0,255),'green':(0,255,0),'teal':(0,128,128),
'purple':(75,0,130),'pink':(235,163,250),'lavender':(141,147,255)}
MATERIALS=['UiO-66','UiO-66-NH2','UiO-66/GO','UiO-66-NH2/GO']

def extract():
 rows=[]; projects={}
 for name,(file,page,clip) in PANELS.items():
  im=Image.open(OUT/f'{name}.png').convert('RGB'); a=np.asarray(im).astype(float)
  x0,x1,y0,y1,xmax,ymax=AXES[name]
  # Four calibration readings, linear axes. Use vertical frame for S105 x; S106 x=0 tick.
  black=(a.max(2)<90)
  def peakx(x,ylo,yhi):
   counts=black[ylo:yhi,x-4:x+5].sum(0); sel=np.where(counts>=counts.max()*.85)[0];return float(x-4+sel.mean())
  def peaky(y,xlo,xhi):
   counts=black[y-4:y+5,xlo:xhi].sum(1);sel=np.where(counts>=counts.max()*.85)[0];return float(y-4+sel.mean())
  if name.startswith('S105'):
   x0=peakx(x0,100,int(y0)-30);x1=peakx(x1,100,int(y0)-30)
   y0=peaky(y0,int(x0)+50,int(x1)-20)
   y1=peaky(y1,int(x0)+2,int(x0)+40) if name.endswith('8B') else peaky(y1,int(x0)+30,int(x1)-30)
   keys=['black','red','green' if name.endswith('8A') else 'blue','blue' if name.endswith('8A') else 'teal']
   mats=MATERIALS
  else:
   x0=peakx(x0,980,995);x1=peakx(x1,100,900)
   y0=peaky(y0,166,188);y1=peaky(y1,166,188)
   keys=['lavender','pink','purple'];mats=['UiO-66_100','UiO-66_160','UiO-66_220']
  drawing=ImageDraw.Draw(im)
  project={'extraction_id':'T011v-'+name,'source_pdf':str(Path('data/raw/pdf')/file),'source_sha256':sha(ROOT/'data/raw/pdf'/file),'page_1based':page,'clip_pdf_points':clip,'render_scale':6,'image':name+'.png','image_sha256':sha(OUT/f'{name}.png'),'software':{'PyMuPDF':fitz.VersionBind},'calibration':{'x':[[x0,0],[x1,xmax]],'y':[[y0,0],[y1,ymax]],'scale':'linear','reading':'dark-pixel projection around visually identified ticks/frame'},'series':{}}
  for key,mat in zip(keys,mats):
   if key=='black': mask=black.copy()
   elif key=='red': mask=(a[:,:,0]>180)&(a[:,:,1]<90)&(a[:,:,2]<90)
   elif key=='green': mask=(a[:,:,1]>160)&(a[:,:,0]<100)&(a[:,:,2]<100)
   elif key=='blue': mask=(a[:,:,2]>170)&(a[:,:,0]<100)&(a[:,:,1]<100)
   elif key=='teal': mask=(a[:,:,0]<80)&(a[:,:,1]>70)&(a[:,:,1]<190)&(a[:,:,2]>70)&(a[:,:,2]<190)
   elif key=='purple': mask=(a[:,:,0]<130)&(a[:,:,1]<80)&(a[:,:,2]>90)&(a[:,:,2]<190)
   elif key=='pink': mask=(a[:,:,0]>190)&(a[:,:,1]>110)&(a[:,:,1]<205)&(a[:,:,2]>220)
   else:mask=(a[:,:,0]>90)&(a[:,:,0]<180)&(a[:,:,1]>95)&(a[:,:,1]<190)&(a[:,:,2]>220)
   yy,xx=np.indices(mask.shape)
   mask &= (xx>x0+10)&(xx<x1-25)&(yy<y0-5)&(yy>10)
   if name.startswith('S105'): mask &= ~((xx<880)&(yy<460))
   else:
    mask &= ~((xx>1090)&(yy>95)&(yy<180))
    mask &= ~((xx>1000)&(yy>178)&(yy<235))
    mask &= ~((xx>1100)&(yy>290)&(yy<345))
   # Remove fit lines while retaining finite-area filled symbols; no line sampling.
   cleaned=ndi.binary_opening(mask,structure=np.ones((5 if key!='black' else 7,)*2))
   lab,n=ndi.label(cleaned)
   candidates=[]
   for s in ndi.find_objects(lab):
    if s is None:continue
    ys,xs=s; w=xs.stop-xs.start;h=ys.stop-ys.start
    if 8<=w<=40 and 6<=h<=40:
     candidates.append([xs.start,ys.start,xs.stop-1,ys.stop-1])
   # A dark fitted line can bisect a colored marker: merge its two surviving pieces.
   candidates.sort(key=lambda b:(b[0]+b[2])/2)
   merged=[]
   for b in candidates:
    if merged and abs((b[0]+b[2]-merged[-1][0]-merged[-1][2])/2)<9 and abs((b[1]+b[3]-merged[-1][1]-merged[-1][3])/2)<20:
     c=merged[-1]; merged[-1]=[min(b[0],c[0]),min(b[1],c[1]),max(b[2],c[2]),max(b[3],c[3])]
    else:merged.append(b)
   pts=[]
   for b in merged:
    px=(b[0]+b[2])/2;py=(b[1]+b[3])/2
    # Opening clips triangular tips. Restore 2 px toward tip, using known marker orientation.
    shape='square' if key in ['black','purple'] else 'circle' if key in ['red','pink'] else 'triangle_up' if (key in ['green','lavender'] or key=='blue' and not name.endswith('8A')) else 'triangle_down'
    if shape=='triangle_up':py-=2
    if shape=='triangle_down':py+=2
    x=(px-x0)/(x1-x0)*xmax;q=(y0-py)/(y0-y1)*ymax
    pts.append({'pixel_x':px,'pixel_y':py,'p_native':x,'q_native':q,'bbox_after_opening':b})
   # Explicit source-only extra windows for partly overlapped initial pink circle and terminal triangle.
   windows=[]
   if name=='S106-Fig4' and key=='pink': windows=[(442,881,470,911,'upper_circle_arc')]
   if name=='S106-Fig4' and key=='lavender': windows=[(1320,20,1355,65,'triangle')]
   for lx,ty,rx,by,method in windows:
    sy,sx=np.where(mask[ty:by,lx:rx]); px=(sx.min()+sx.max())/2+lx
    py=sy.min()+ty+13 if method=='upper_circle_arc' else (sy.min()+sy.max())/2+ty
    pts.append({'pixel_x':float(px),'pixel_y':float(py),'p_native':(px-x0)/(x1-x0)*xmax,'q_native':(y0-py)/(y0-y1)*ymax,'local_window':[lx,ty,rx,by],'method':method,'radius_px':13 if method=='upper_circle_arc' else None})
   pts.sort(key=lambda p:p['p_native'])
   # Fixed 12-point range-spanning subset chosen before opening T011 data.
   pts=[p for p in pts if p['p_native'] >= (.06 if name=='S105-Fig8C' and key=='teal' else .035)]
   ids=np.unique(np.rint(np.linspace(0,len(pts)-1,min(12,len(pts)))).astype(int))
   controls=[pts[i] for i in ids]
   for j,p in enumerate(controls):
    drawing.ellipse((p['pixel_x']-16,p['pixel_y']-16,p['pixel_x']+16,p['pixel_y']+16),outline='orange',width=2)
    drawing.text((p['pixel_x']+9,p['pixel_y']+10),str(j+1),fill='black')
    rows.append({'extraction_id':'T011v-'+name,'series':mat,'check_id':j+1,'pixel_x':p['pixel_x'],'pixel_y':p['pixel_y'],'p_native':p['p_native'],'q_native':p['q_native']})
   project['series'][mat]={'color':key,'marker':shape,'n_candidates':len(pts),'candidates':pts,'controls':controls}
   print(name,mat,len(pts),len(controls),[(round(p['p_native'],3),round(p['q_native'],3)) for p in controls])
  project['control_uncertainty']={'pixel_center_bound':4,'axis_anchor_bound_px':1,'p_native_conservative':5*xmax/(x1-x0),'q_native_conservative':5*ymax/(y0-y1),'meaning':'raster localization bound, not experimental uncertainty; occluded marks excluded from blind sample'}
  (OUT/f'{name}.project.json').write_text(json.dumps(project,indent=2))
  im.save(OUT/f'{name}-controls.png');projects[name]=project
 with (OUT/'blind_controls.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (OUT/'blind_freeze.json').write_text(json.dumps({'phase':'blind; no T011 CSV/project/script/report read','controls_sha256':sha(OUT/'blind_controls.csv'),'n_series':19,'n_controls':len(rows),'projects':{k:sha(OUT/f'{k}.project.json') for k in projects}},indent=2))
if __name__=='__main__':extract()
