"""T011v2: pixel boundary geometry, no printed-template correlation.

Offline. Writes only this directory. The T011 CSV supplies search neighbourhoods
and comparison values, never measured centres. This is a non-blind recheck.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import subprocess

import cv2
import fitz
import numpy as np
from PIL import Image, ImageDraw
import yaml

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
PANELS = {
    'S105-Fig8A': {0: ('black', 'square'), 2: ('green', 'triangle')},
    'S105-Fig8C': {2: ('blue', 'triangle')},
    'S105-Fig9': {0: ('black', 'square'), 1: ('red', 'circle'), 2: ('blue', 'triangle')},
    'S106-Fig4': {1: ('pink', 'circle')},
}
# Independently selected broad legend/isolated-marker regions; not T011 templates.
REFERENCE = {
    ('S105-Fig8A',0):(337,105,380,150),
    ('S105-Fig8A',2):(330,300,385,348),
    ('S105-Fig8C',2):(320,365,370,415),
    ('S105-Fig9',0):(488,250,535,297),
    ('S105-Fig9',1):(485,348,535,400),
    ('S105-Fig9',2):(480,470,540,525),
    ('S106-Fig4',1):(446,354,467,378),
}

def sha(b): return hashlib.sha256(b).hexdigest()
def dump(path, obj): path.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n')

def mask(im, color, variant=0):
    r,g,b = im.astype(float).transpose(2,0,1)
    if color=='black': return (np.maximum(np.maximum(r,g),b)<(75+variant*15)) & (np.maximum(np.maximum(r,g),b)-np.minimum(np.minimum(r,g),b)<20)
    if color=='red': return (r>160)&(g<100+variant*15)&(b<100+variant*15)
    if color=='green': return (g>160)&(r<100+variant*15)&(b<100+variant*15)
    if color=='blue': return (b>160)&(r<100+variant*15)&(g<100+variant*15)
    return (r>180)&(b>200)&(g>80)&(g<215+variant*10)&(r-g>25)&(b-g>25)&(abs(r-b)<65)

def reference(im, box, color, shape):
    x0,y0,x1,y1=box
    m=mask(im[y0:y1,x0:x1],color)
    ys,xs=np.where(m)
    bbox=[int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0),int(ys.max()+y0)]
    return {'region':box,'ink_bbox_inclusive':bbox,'width':bbox[2]-bbox[0], 'height':bbox[3]-bbox[1]}

def external_edge(im,m):
    white=(im.min(axis=2)>235).astype('uint8')
    near=cv2.dilate(white,np.ones((3,3),np.uint8))>0
    edge=m&near
    edge[[0,-1],:]=False;edge[:,[0,-1]]=False
    return edge

def distances(points, centers, shape, width, height):
    d=points[None,:,:]-centers[:,None,:]
    if shape=='circle':
        return abs(np.linalg.norm(d,axis=2)-(width+height)/4)
    if shape=='square':
        verts=[(-width/2,-height/2),(width/2,-height/2),(width/2,height/2),(-width/2,height/2)]
    else:
        verts=[(0,-height/2),(width/2,height/2),(-width/2,height/2)]
    ds=[]
    for a,b in zip(verts,verts[1:]+verts[:1]):
        a=np.array(a);v=np.array(b)-a
        t=np.clip(((d-a)*v).sum(axis=2)/(v*v).sum(),0,1)
        ds.append(np.linalg.norm(d-a-t[:,:,None]*v,axis=2))
    return np.min(ds,axis=0)

def square_edges(im, ref, box, variant=0):
    """Directed, straight edges distinguish a square from a sloping fit line."""
    x0,y0,x1,y1=box;pad=4
    cut=im[y0-pad:y1+pad,x0-pad:x1+pad]
    m=mask(cut,'black',variant);white=cut.min(axis=2)>200
    runs=[];centers=[];bounds=[];edge_points=[]
    for axis in [0,1]:
        candidates=[]
        for sign in [-1,1]:
            hits={}
            for y in range(pad,len(m)-pad):
                for x in range(pad,m.shape[1]-pad):
                    if not m[y,x]:continue
                    dx=sign if axis==0 else 0;dy=sign if axis==1 else 0
                    if m[y+dy,x+dx]:continue
                    if not any(white[y+k*dy,x+k*dx] for k in [1,2,3]):continue
                    key=x if axis==0 else y;other=y if axis==0 else x
                    hits.setdefault(key,[]).append(other)
            for key,values in hits.items():
                values=sorted(values)
                pieces=np.split(values,np.where(np.diff(values)>1)[0]+1)
                longest=max(pieces,key=len);n=len(longest)
                if n<3:continue
                pos=key+(x0-pad if axis==0 else y0-pad)
                center=pos-sign*(ref['width'] if axis==0 else ref['height'])/2
                lo,hi=(x0,x1) if axis==0 else (y0,y1)
                if not lo+3<center<hi-3:continue
                entry={'axis':axis,'outside_direction':sign,'edge_coordinate':pos,
                       'center_estimate':center,'consecutive_pixels':n}
                runs.append(entry);candidates.append(entry)
                for other in longest:
                    point=[key,other] if axis==0 else [other,key]
                    edge_points.append([int(point[0]+x0-pad),int(point[1]+y0-pad)])
        if not candidates:return None
        scores=[sum(b['consecutive_pixels'] for b in candidates if abs(a['center_estimate']-b['center_estimate'])<=1.5) for a in candidates]
        mode=candidates[int(np.argmax(scores))]['center_estimate']
        chosen=[a for a in candidates if abs(a['center_estimate']-mode)<=1.5]
        val=float(np.average([a['center_estimate'] for a in chosen],weights=[a['consecutive_pixels'] for a in chosen]))
        centers.append(val);bounds.append([min(a['center_estimate'] for a in chosen)-1,max(a['center_estimate'] for a in chosen)+1])
    return {'center':centers,'edge_pixels':edge_points,'edge_count':len(edge_points),'directed_runs':runs,
            'rms_native_px':0.,'rms_note':'not applicable: directed edge estimator, not an RMS fit',
            'plausible_center_bounds':[bounds[0][0],bounds[1][0],bounds[0][1],bounds[1][1]],
            'visible_ink_pixels':int(m[pad:-pad,pad:-pad].sum()),'search_region':box,
            'method':'directed straight edge runs >=3 px; run-weighted modal centre; 1 px edge allowance'}

def fit(im,color,shape,ref,box,variant=0):
    if shape=='square':return square_edges(im,ref,box,variant)
    x0,y0,x1,y1=box;cut=im[y0:y1,x0:x1]
    m=mask(cut,color,variant);ed=external_edge(cut,m)
    yy,xx=np.where(ed);points=np.column_stack((xx+x0,yy+y0)).astype(float)
    iy,ix=np.where(m);ink=np.column_stack((ix+x0,iy+y0)).astype(float)
    if len(points)<3: return None
    # Crop is manually/search-window selected. Exhaustive half-pixel geometry fit.
    xx,yy=np.meshgrid(np.arange(x0+3,x1-3,.5),np.arange(y0+3,y1-3,.5))
    centers=np.column_stack((xx.ravel(),yy.ravel()))
    scores=[]
    for chunk in np.array_split(centers,max(1,len(centers)//1000)):
        d=distances(points,chunk,shape,ref['width'],ref['height'])
        # Robust against thin connecting lines and isolated compression speckles.
        # 80% retained; all edge samples and search range preserved for audit.
        k=max(3,int(.8*len(points)))
        score=np.mean(np.sort(d,axis=1)[:,:k]**2,axis=1)
        # Avoid reflecting a visible left/top edge to the opposite side: the
        # observed target ink must lie inside the candidate geometric symbol.
        if shape=='square':
            z=abs(ink[None,:,:]-chunk[:,None,:])-np.array([ref['width']/2,ref['height']/2])
            outside=np.maximum(z.max(axis=2),0)
            keep=max(3,int(.8*len(ink)))
            score+=np.mean(np.sort(outside,axis=1)[:,:keep]**2,axis=1)
        elif shape=='triangle':
            z=ink[None,:,:]-chunk[:,None,:]
            slope=2*ref['height']/ref['width']
            side=(-ref['height']/2+slope*abs(z[:,:,0])-z[:,:,1])/np.sqrt(1+slope*slope)
            outside=np.maximum(np.maximum(z[:,:,1]-ref['height']/2,side),0)
            keep=max(3,int(.8*len(ink)))
            score+=np.mean(np.sort(outside,axis=1)[:,:keep]**2,axis=1)
        scores.extend(score.tolist())
    scores=np.array(scores);best=int(scores.argmin());center=centers[best]
    # Not a confidence interval: translations at RMS <= best RMS + 0.75 native px.
    acceptable=centers[scores<=(np.sqrt(scores[best])+.75)**2]
    lo=acceptable.min(axis=0);hi=acceptable.max(axis=0)
    return {'center':center.tolist(),'edge_pixels':points.tolist(),'edge_count':len(points),
            'rms_native_px':float(np.sqrt(scores[best])),
            'plausible_center_bounds':[float(lo[0]),float(lo[1]),float(hi[0]),float(hi[1])],
            'visible_ink_pixels':int(m.sum()),'search_region':box}

def axis_calibration(im, name):
    dark=im.max(axis=2)<90
    # Find long frame edges directly in pixels, independently of T011 axis values.
    rows=np.sum(dark,axis=1);cols=np.sum(dark,axis=0)
    if name=='S106-Fig4':
        xregions=[(175,210),(990,1020)]; yregions=[(10,40),(655,680)];xmax=1.;ymax=600.
    elif name=='S105-Fig9':
        xregions=[(290,315),(2110,2135)];yregions=[(40,70),(1398,1418)];xmax=1.2;ymax=.4
    elif name=='S105-Fig8C':
        xregions=[(185,210),(1920,1945)];yregions=[(45,75),(1340,1365)];xmax=1.2;ymax=3.
    else:
        xregions=[(220,245),(1955,1980)];yregions=[(45,75),(1340,1365)];xmax=1.2;ymax=8.
    def center(v,ab):
        a,b=ab;ids=np.arange(a,b);w=v[a:b];return float(ids[w>=w.max()*.95].mean())
    xs=[center(cols,r) for r in xregions];ys=[center(rows,r) for r in yregions]
    ticks=None
    if name=='S106-Fig4':
        # Zero lies inside the frame, not on its left border. Use labelled .2/.8 ticks.
        ids=[]
        for a,b in [(348,363),(836,852)]:
            q=np.where(dark[680,a:b])[0]+a;ids.append(float(q.mean()))
        slope=(ids[1]-ids[0])/.6
        xs=[ids[0]-.2*slope,ids[0]+.8*slope]
        ticks={'row':680,'values':[.2,.8],'pixels':ids}
    return {'x':[xs[0],xs[1],0,xmax],'y':[ys[1],ys[0],0,ymax],
            'scale':'linear','method':'long dark frame runs; midpoint of >=95% peak support',
            'calibration_bound_native_px':1.5,'interior_ticks':ticks}

def convert(c,cal):
    ans=[]
    for val,key in zip(c,['x','y']):
        a,b,u,v=cal[key];ans.append(u+(val-a)*(v-u)/(b-a))
    return ans

def main():
    allrows=[];projects=[]
    for panel,targets in PANELS.items():
        path=ROOT/f'data/extraction/digitization/T011-{panel}.digitization.yaml'
        p=yaml.safe_load(path.read_text());im=np.array(Image.open(OUT/f'{panel}-native.png'))
        cal=axis_calibration(im,panel);print(panel,cal)
        data=list(csv.DictReader((ROOT/f'data/extraction/digitization/T011-{panel}.csv').open()))
        project={'extraction_id':'T011v2-'+panel,'source_extraction_id':p['extraction_id'],
                 'calibration':cal,'native_png_sha256':sha((OUT/f'{panel}-native.png').read_bytes()),'series':[]}
        for si,(color,shape) in targets.items():
            s=p['series'][si];ref=reference(im,REFERENCE[(panel,si)],color,shape)
            records=[r for r in data if r['series']==s['name']]
            rec={tuple(r['pixel']):r for r in s['recoveries']}
            res=[]
            for j,r in enumerate(records):
                cx=float(r['pixel_x']);cy=float(r['pixel_y']);recovery=rec.get((cx,cy))
                # One marker neighbourhood bounded halfway to adjacent marker x.
                h=ref['height']/2+5;w=ref['width']/2+5
                x0=max(cx-w,(cx+float(records[j-1]['pixel_x']))/2 if j else cx-w)
                x1=min(cx+w,(cx+float(records[j+1]['pixel_x']))/2 if j+1<len(records) else cx+w)
                box=[int(np.floor(x0)),int(np.floor(cy-h)),int(np.ceil(x1))+1,int(np.ceil(cy+h))+1]
                f=fit(im,color,shape,ref,box)
                if not f:
                    res.append({'index':j+1,'recovery_id':recovery['id'] if recovery else None,'fit':None});continue
                controls=[fit(im,color,shape,ref,box,v) for v in [-1,1]] if recovery else []
                x,y=convert(f['center'],cal);dx=abs(x-float(r['x']));dy=abs(y-float(r['y']))
                row={'extraction_id':'T011v2-'+panel,'series':s['name'],'series_row':j+1,
                     'recovery_id':recovery['id'] if recovery else '', 'control_pixel_x':f['center'][0],
                     'control_pixel_y':f['center'][1],'control_x':x,'control_y':y,'T011_x':r['x'],'T011_y':r['y'],
                     'abs_delta_x':dx,'abs_delta_y':dy,'T011_x_err':r['x_err'],'T011_y_err':r['y_err'],
                     'within_T011_error':dx<=float(r['x_err']) and dy<=float(r['y_err']),
                     'rms_native_px':f['rms_native_px']}
                allrows.append(row);res.append({'index':j+1,'recovery_id':row['recovery_id'], 'fit':f,'threshold_variants':controls})
            project['series'].append({'name':s['name'],'index':si,'color':color,'shape':shape,'reference':ref,'markers':res})
            print(s['name'],'n',len(res),'fit',sum(r['fit'] is not None for r in res),'reference',ref)
        dump(OUT/f'{panel}.project.json',project);projects.append(project)
    with (OUT/'geometric_comparison.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
    print('fits',len(allrows),'outside raw error',sum(not r['within_T011_error'] for r in allrows))

if __name__=='__main__': main()
