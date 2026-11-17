#!/usr/bin/env python3
"""Independent T019v raster measurements. Does not import/run T019 extraction code.
Run from repository root with .venv/bin/python.
Raw copyrighted images and overlays stay under ignored private/T019v/.
"""
from pathlib import Path
import csv, hashlib, json, math, xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

OUT=Path('data/extraction/digitization/T019v-control')
RAW=Path('private/T019v')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def writecsv(path, rows):
    if not rows:return
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def runs(a):
    labels,n=ndi.label(a)
    return [(s[0].start+s[0].stop-1)/2 for s in ndi.find_objects(labels)]
def axis(im,orient,line,lo,hi,values):
    dark=np.max(im,2)<180
    scan=dark[line,lo:hi] if orient=='x' else dark[lo:hi,line]
    centers=[x+lo for x in runs(scan)]
    if len(centers)!=len(values):raise ValueError((orient,line,centers,values))
    b,a=np.polyfit(centers,values,1)
    residual=np.array(values)-(a+b*np.array(centers))
    return dict(pixel_centers=centers,tick_values=values,intercept=a,slope=b,max_residual=float(abs(residual).max()),scale='linear')
def maskcolor(im,color):
    r,g,b=[im[:,:,i].astype(float) for i in range(3)]
    return {'black':(r<100)&(g<100)&(b<100),
        'orange':(r>190)&(g>65)&(g<215)&(b<100),
        'teal':(r<110)&(g>70)&(b>65)&(g>r+25),
        'red':(r>120)&(g<95)&(b>30)&(b<170)&(r>g+70),
        'green':(g>r*1.04)&(g>b*1.15)&(g>80)&(r>85),
        'purple':(r>80)&(r<210)&(g<95)&(b>160)}[color]
def kernel(shape,filled=True):
    yy,xx=np.mgrid[-10:11,-10:11];r2=xx*xx+yy*yy
    if shape=='circle':
        fg=r2<=5.1**2 if filled else (r2>=4.8**2)&(r2<=6.2**2)
        bg=(r2>7.6**2)&(r2<9**2)
        if not filled:bg|=r2<3.5**2
    elif shape=='square':
        rr=np.maximum(abs(xx),abs(yy))
        fg=rr<=3 if filled else (((yy==-5)|(yy==-4))&(abs(xx)<=5))|((abs(xx)>=4)&(abs(xx)<=5)&(yy>=-3)&(yy<=1))
        bg=(rr>=7)&(rr<=8)
        if not filled:bg|=rr<=2
    elif shape=='triangle':
        # Native triangle has apex 7 px above and base 5 px below centre.
        outer=(yy>=-7)&(yy<=5)&(abs(xx)<=(yy+7)*.60)
        inner=(yy>=-3)&(yy<=2)&(abs(xx)<=(yy+3)*.55)
        fg=outer if filled else outer&~inner
        bg=~ndi.binary_dilation(outer,iterations=2)&(r2<9**2)
        if not filled:bg|=inner
    elif shape=='diamond':
        rr=abs(xx)/5+abs(yy)/8
        fg=(rr>=.68)&(rr<=1.05);bg=(rr<.38)|((rr>1.4)&(rr<1.7))
    return fg,bg

def detect(im,color,shape,filled,roi,threshold=.68):
    mask=maskcolor(im,color);fg,bg=kernel(shape,filled)
    score=ndi.correlate(mask.astype(float),fg.astype(float)/fg.sum(),mode='constant')-.35*ndi.correlate(mask.astype(float),bg.astype(float)/bg.sum(),mode='constant')
    if not filled and shape in ['circle','square','triangle']:
        yy,xx=np.mgrid[-10:11,-10:11]; core=(xx*xx+yy*yy<=2.5**2)
        score[ndi.correlate(mask.astype(float),core.astype(float)/core.sum())>.18]=-1
    x0,y0,x1,y1=roi
    allowed=np.zeros(score.shape,bool);allowed[y0:y1,x0:x1]=1
    peaks=(score==ndi.maximum_filter(score,size=9))&(score>=threshold)&allowed
    labels,n=ndi.label(peaks);pts=[]
    for s in ndi.find_objects(labels):
        yy,xx=np.where(peaks[s]);vals=score[s][yy,xx];weight=vals/vals.sum()
        x=float((xx*weight).sum()+s[1].start);y=float((yy*weight).sum()+s[0].start)
        pts.append((x,y,float(vals.max())))
    # Tie plateaus can split: retain strongest within 9 px.
    kept=[]
    for p in sorted(pts,key=lambda p:-p[2]):
        if all(math.dist(p[:2],k[:2])>9 for k in kept):kept.append(p)
    return sorted(kept)

def main():
    projects=[];rows=[]
    im=np.array(Image.open(RAW/'S113_T019-p9-im0.jpeg').convert('RGB'))
    # Calibration from multiple interior ticks rather than T019 endpoint mapping.
    for panel,roi,xline,xlo,xhi,xvals,yline,ylo,yhi,yvals in [
      ('a',(90,90,403,250),270,100,350,[.2,.4,.6,.8],58,40,230,[1.2,.8,.4]),
      ('b',(530,120,819,263),268,520,780,[.2,.4,.6,.8],480,50,230,[.12,.08,.04])]:
        xax=axis(im,'x',xline,xlo,xhi,xvals);yax=axis(im,'y',yline,ylo,yhi,yvals)
        # 3x3 black square core; independent local maxima, not erosion components.
        yy,xx=np.mgrid[-4:5,-4:5];fg=(abs(xx)<=1)&(abs(yy)<=1);bg=(abs(xx)>=4)|(abs(yy)>=4)
        m=maskcolor(im,'black');sc=ndi.correlate(m.astype(float),fg.astype(float)/fg.sum())-.45*ndi.correlate(m.astype(float),bg.astype(float)/bg.sum())
        x0,y0,x1,y1=roi;allowed=np.zeros(sc.shape,bool);allowed[y0:y1,x0:x1]=1
        pk=(sc==ndi.maximum_filter(sc,size=7))&(sc>.78)&allowed
        labs,n=ndi.label(pk);pts=[]
        for s in ndi.find_objects(labs):
            ys,xs=np.where(pk[s]);pts.append((float(xs.mean()+s[1].start),float(ys.mean()+s[0].start),float(sc[s][ys,xs].max())))
        # Merge split equal-score plateaus of the same tiny square.
        groups=[]
        for pt in sorted(pts):
            if groups and math.dist(pt[:2],groups[-1][-1][:2])<6:groups[-1].append(pt)
            else:groups.append([pt])
        pts=[tuple(np.mean(g,axis=0)) for g in groups]
        name=f'S113-Fig5{panel}-UiO66';projects.append(dict(series=name,image='private/T019v/S113_T019-p9-im0.jpeg',method='local black square core contrast',x_axis=xax,y_axis=yax,pixels=pts,readout_bound_px=1.5))
    im=np.array(Image.open(RAW/'S103_T019-p3-im0.png').convert('RGB'))
    xax=axis(im,'x',18,230,610,[.2,.4,.6,.8]);yax=axis(im,'y',90,40,515,[80,70,60,50,40,30,20,10])
    for sample,color,shape in [('100','orange','circle'),('160','teal','square'),('220','red','triangle')]:
      for branch,filled in [('adsorption',True),('desorption',False)]:
        pts=detect(im,color,shape,filled,(355,130,545,420),.62 if shape!='triangle' else .58)
        # For hollow teal squares, a covered solid square can mimic the upper
        # outline. Within each x-column retain the upper hollow marker only.
        if sample=='160' and not filled:
            groups=[]
            for pt in pts:
                if groups and pt[0]-groups[-1][-1][0]<6:groups[-1].append(pt)
                else:groups.append([pt])
            pts=[min(g,key=lambda z:z[1]) for g in groups]
        name=f'S103-Fig2a-UiO66_{sample}-{branch}'
        projects.append(dict(series=name,image='private/T019v/S103_T019-p3-im0.png',method='analytic native symbol stencil; colour foreground/background contrast',color=color,shape=shape,filled=filled,roi=[355,130,545,420],threshold=.62 if shape!='triangle' else .58,x_axis=xax,y_axis=yax,pixels=pts,readout_bound_px=2,unit_factor=1000/(8.31446261815324*273.15/101.325*1000),occlusion_note='No centre inferred from smooth curve. Teal filled markers obscured by triangles may be unresolvable.'))
    # Three panels: all individually resolvable experimental green diamonds.
    for panel,idx in [('a',0),('b',1),('c',2)]:
      p=RAW/f'S102_T019-p5-im{idx}.jpeg';im=np.array(Image.open(p).convert('RGB'))
      # Native image c has slightly different axis geometry.
      if panel!='c':
       xax=axis(im,'x',446,240,610,[2,4,6]);yax=axis(im,'y',110,100,360,[.15,.10,.05])
      else:
       xax=axis(im,'x',436,240,610,[2,4,6]);yax=axis(im,'y',108,100,360,[.15,.10,.05])
      pts=detect(im,'green','diamond',False,(120,60,770,438),.49)
      projects.append(dict(series=f'S102-FigS6{panel}-binary',image=str(p),method='analytic diamond stencil; green outline contrast',x_axis=xax,y_axis=yax,pixels=pts,readout_bound_px=2,pressure_factor=.01,pressure_semantics='displayed kPa only; total/partial not asserted'))
    for fig,idx in [('S37',2),('S38',1)]:
      p=RAW/f'S117_SI_T019-p25-im{idx}.png';im=np.array(Image.open(p).convert('RGB'))
      m=maskcolor(im,'purple');distance=ndi.distance_transform_edt(m)
      for panel,roi,xscan,xlo,xhi,xvals,yscan in [
          ('A',(125,65,420,430),458,180,570,[25,50,75,100],100),
          ('B',(760,65,1030,430),458,830,1150,[25,50,75],735)]:
        # S38 native image is 12 px narrower; choose calibrations by tick scans.
        if fig=='S38':
          if panel=='A':roi=(120,65,420,430);xscan=458;xlo=180;xhi=570;yscan=95
          else:roi=(750,65,1030,430);xscan=458;xlo=830;xhi=1200;xvals=[25,50,75,100];yscan=730
        xax=axis(im,'x',xscan,xlo,xhi,xvals)
        yax=axis(im,'y',yscan,65,420,[1.4,1.2,1,.8,.6,.4,.2])
        allowed=np.zeros(m.shape,bool);x0,y0,x1,y1=roi;allowed[y0:y1,x0:x1]=1
        peaks=(distance==ndi.maximum_filter(distance,size=7))&(distance>=1.8)&allowed
        labels,n=ndi.label(peaks);pts=[]
        for sl in ndi.find_objects(labels):
          ys,xs=np.where(peaks[sl]);pts.append((float(xs.mean()+sl[1].start),float(ys.mean()+sl[0].start),float(distance[sl][ys,xs].max())))
        projects.append(dict(series=f'S117-Fig{fig}{panel}-wet-breakthrough-control',reference_series=f'{fig}{panel}-wet-CO2',image=str(p),method='purple filled circle: Euclidean distance-to-background local maxima; excludes thin line and hollow N2 markers',x_axis=xax,y_axis=yax,pixels=sorted(pts),readout_bound_px=2,observable='outlet_ratio_CO2',unit='1',x_unit='min/cm3 as printed; not equilibrium pressure',not_capacity=True))
    for pr in projects:
      name=pr['series'];im=Image.open(pr['image']).convert('RGB');draw=ImageDraw.Draw(im)
      for j,(x,y,score) in enumerate(pr['pixels'],1):
        draw.rectangle((x-9,y-9,x+9,y+9),outline='cyan',width=1);draw.text((x+7,y+6),str(j),fill='cyan')
        a=pr['x_axis'];b=pr['y_axis'];factor=pr.get('unit_factor',1)
        rows.append(dict(series=name,control_id=f'{j:03}',pixel_x=x,pixel_y=y,score=score,display_pressure=a['intercept']+a['slope']*x,control_q=(b['intercept']+b['slope']*y)*factor,control_u_dig=abs(b['slope']*factor)*math.sqrt((pr['readout_bound_px']**2+1)/3)))
      dest=RAW/(name+'-control-overlay.png');im.save(dest);pr.update(overlay=str(dest),overlay_sha256=sha(dest),image_sha256=sha(pr['image']))
    (OUT/'control_snapshot.json').write_text(json.dumps({'script_sha256':sha(__file__),'stage':'independent source-only control; before comparison with T019 exports','method_note':'Parameters chosen from primary images, without T019 extraction implementation. T019 project metadata were seen for locating sources; this is independence of measurement method, not full blinding to exports.'},indent=2)+'\n')
    (OUT/'projects.json').write_text(json.dumps(projects,indent=2)+'\n');writecsv(OUT/'controls.csv',rows)
    print(json.dumps({p['series']:len(p['pixels']) for p in projects},indent=2))

if __name__=='__main__':main()
