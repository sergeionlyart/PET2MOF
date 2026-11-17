#!/usr/bin/env python3
"""T019 offline extraction. Never imports/runs a predictive model.

UV_CACHE_DIR=$PWD/.uv-cache uv run --locked --no-sync python scripts/extraction/extract_holdout_v1.py
Inputs: lawful downloads listed in data/extraction/digitization/T019-work/access.json.
Source PDFs, native images and overlays stay ignored. Pixels are measured by image
segmentation/template correlation, never entered as response values. Conservative
shape gates retain only identifiable symbols; rejected candidates remain reviewable.
"""
import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pymupdf
import scipy
from scipy import ndimage as nd, signal
from PIL import Image, ImageDraw
import yaml

ROOT = Path(__file__).resolve().parents[2]
DIG = ROOT / 'data/extraction/digitization'
REC = ROOT / 'data/extraction/records'
PRIV = ROOT / 'private/T019'
OUT = ROOT / 'holdout/v1'
COND = 'series point_id source_id extraction_id material gas observable unit basis T_K p_total_bar p_partial_bar y_CO2_dry RH_fraction w_PEI w_reading Mw_PEI notes'.split()
OBS = 'series point_id source_id extraction_id q u_exp u_dig u_p u_T u_a dq_dp dq_dT dq_da scale observable comparable inputs_known'.split()
CONDITIONS, OBSERVATIONS, SUMMARY = [], [], []
METADATA = DIG / 'T019b-build-metadata.json'
DOIS = {'S113':'10.3390/membranes10070154','S103':'10.1038/s42004-022-00742-z','S102':'10.1021/acs.langmuir.1c01149','S2':'10.1021/acsomega.8b02319','S117':'10.1039/d1fd00017a'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).relative_to(ROOT))


def dump(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n')


def csvout(p, rows, fields):
    with Path(p).open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields, lineterminator='\n');w.writeheader();w.writerows(rows)


def add(series, point, source, eid, q='', u_dig='', u_p='', scale='', comparable=True, known=True, **condition):
    keys=dict(series=series,point_id=point,source_id=source,extraction_id=eid)
    CONDITIONS.append(dict.fromkeys(COND,'') | keys | condition)
    OBSERVATIONS.append(dict.fromkeys(OBS,'') | keys | dict(q=q,u_dig=u_dig,u_p=u_p,
      u_a=0 if condition.get('RH_fraction')==0 else '',scale=scale,observable=condition['observable'],comparable=str(comparable).lower(),inputs_known=str(known).lower()))


def passport(eid, source, input_path, page, locator, derived, kind, region=None, conversions=None, error=None, params=None):
    access=json.loads((DIG/'T019-work/access.json').read_text())
    matches=[a for a in access if a.get('sha256')==sha(input_path)]
    url=matches[0]['url'] if matches else 'https://doi.org/'+DOIS[source]
    record=dict(extraction_id=eid,source_id=source,doi=DOIS[source],url=url,input_sha256=sha(input_path),pdf_page=page,
      api_page_map=({'1':page} if page is not None else {}),figure_or_table=locator,region=region,
      tool='T019 offline structured XML / image marker extraction',tool_version=f'PyMuPDF {pymupdf.__version__}; scipy {scipy.__version__}',
      params=dict(script='scripts/extraction/extract_holdout_v1.py',script_sha256=sha(__file__),**(params or {})),
      date=json.loads(METADATA.read_text())['extraction_started_utc'],raw_response_ref=rel(input_path),unit_conversions=conversions or [],
      derived_sha256=sha(derived),status='provisional',reviewer=None,
      corrections=[dict(task='T019b-holdout-fix',report='reviews/T019b_holdout_fix.md',independent_review_pending='T019v2')],error_estimate=error,
      data_kind=kind,sensitivity_only=True)
    (REC/(eid+'.yaml')).write_text(yaml.safe_dump(record,sort_keys=False,allow_unicode=True))


def prepare(source,page):
    path=ROOT/f'data/raw/pdf/{source}_T019.pdf'
    d=pymupdf.open(path);p=d[page-1]
    p.get_pixmap(matrix=pymupdf.Matrix(2,2)).save(PRIV/f'{source}_page{page}.png')
    (PRIV/f'{source}_text.txt').write_text('\n'.join(x.get_text() for x in d))
    ims=[]
    for i,info in enumerate(p.get_images()):
        obj=d.extract_image(info[0]);f=PRIV/f'{source}_native{i}.{obj["ext"]}';f.write_bytes(obj['image']);ims.append(f)
    return path,ims


def axis(p1,v1,p2,v2):
    return dict(pixel_1=p1,value_1=v1,pixel_2=p2,value_2=v2,scale='linear')


def transform(a,p):
    return a['value_1']+(p-a['pixel_1'])*(a['value_2']-a['value_1'])/(a['pixel_2']-a['pixel_1'])


def uncertainty(a,p,bound):
    """Independent rectangular readout and calibration limits -> standard u (k=1)."""
    t=(p-a['pixel_1'])/(a['pixel_2']-a['pixel_1'])
    slope=abs((a['value_2']-a['value_1'])/(a['pixel_2']-a['pixel_1']))
    return slope*math.sqrt((bound**2+(1-t)**2+t*t)/3)


def finish(eid,source,page,input_path,image_path,xa,ya,series,scale,factor=1,pressure_factor=1,params=None,excluded=None):
    im=Image.open(image_path).convert('RGB');draw=ImageDraw.Draw(im)
    rows=[]; project_series=[]
    for s in series:
        points=sorted(s['points'],key=lambda p:(p[0],p[1]));pr=[]
        for i,p in enumerate(points,1):
            x,y=p[:2];pid=f'{i:03d}';readout=p[3] if len(p)>3 else s.get('readout',2)
            xp=transform(xa,x);yp=transform(ya,y)
            uq=uncertainty(ya,y,readout)*factor;up=uncertainty(xa,x,readout)*pressure_factor
            row=dict(series=s['name'],point_id=pid,pixel_x=x,pixel_y=y,x_source=xp,y_source=yp,q=yp*factor,u_dig=uq,u_p=up,score=p[2] if len(p)>2 else '',readout_bound_px=readout)
            rows.append(row);pr.append([float(x),float(y)])
            draw.ellipse((x-4,y-4,x+4,y+4),outline=s.get('overlay','lime'),width=1)
            c=s['condition'].copy()
            if source=='S102':
                # Pressure label lacks total/partial definition for the binary experiment.
                c['notes']+=f'; displayed pressure={xp:.8g} kPa; water loading is not RH'
                up=''
            else:
                c['p_total_bar']=xp*pressure_factor;c['p_partial_bar']=xp*pressure_factor
            add(s['name'],pid,source,eid,q=yp*factor,u_dig=uq,u_p=up,scale=scale*factor,comparable=s.get('comparable',True),known=s.get('known',True),**c)
        bounds=[p[3] if len(p)>3 else s.get('readout',2) for p in points]
        project_series.append(dict(name=s['name'],data_kind='digitized_markers',sigma_pixel=max(bounds,default=s.get('readout',2))/math.sqrt(3),pixels=pr,
          sigma_pixel_policy='conservative series maximum; exact per-point rectangular readout bounds below; CSV u_dig also includes calibration',
          per_point_readout_bound_px=bounds,
          condition=s['condition'],comparable=s.get('comparable',True),inputs_known=s.get('known',True)))
        SUMMARY.append(dict(series=s['name'],points=len(pr),comparable=s.get('comparable',True)))
    path=DIG/(eid+'.csv');csvout(path,rows,'series point_id pixel_x pixel_y x_source y_source q u_dig u_p score readout_bound_px'.split())
    overlay=PRIV/(eid+'-overlay.png');im.save(overlay)
    project=dict(image_sha256=sha(image_path),image_path=rel(image_path),pdf_sha256=sha(input_path),pdf_page=page,
      native_image_size=list(im.size),pixel_origin='top-left',x_axis=xa,y_axis=ya,code_version=sha(__file__),
      series=project_series,overlay=rel(overlay),overlay_sha256=sha(overlay),export=rel(path),export_sha256=sha(path),
      params=params or {},excluded=excluded or [],
      uncertainty=dict(type='standard (k=1)',formula='abs(slope)*sqrt((readout_bound_px^2 + (1-t)^2 + t^2)/3)',
        t='(pixel-pixel_1)/(pixel_2-pixel_1)',calibration_endpoint_bound_px=1,
        distribution='independent rectangular bounds; calibration common to all points (correlated across rows)',
        scope='digitization only; experimental uncertainty unknown; not 3% of full scale'),
      scale_source_units=scale)
    (DIG/(eid+'.digitization.yaml')).write_text(yaml.safe_dump(project,sort_keys=False,allow_unicode=True))
    passport(eid,source,input_path,page,eid.split(source+'-')[-1],path,'digitized_markers',
      region=dict(image=rel(image_path),image_sha256=sha(image_path),overlay=rel(overlay)),
      conversions=[dict(from_unit='source ordinate',to_unit='mmol/g',factor=factor),dict(from_unit='source pressure',to_unit='bar',factor=pressure_factor)],
      error=project['uncertainty'],params=dict(project=rel(DIG/(eid+'.digitization.yaml')),provisional_until='T019v2'))


def s113():
    path,ims=prepare('S113',9);im=Image.open(ims[0]).convert('RGB');a=np.array(im);m=a.max(2)<100
    roi=np.zeros(m.shape,bool);roi[20:264,65:402]=1;roi[20:262,486:818]=1;roi[40:121,65:185]=0;roi[37:117,486:608]=0
    e=nd.binary_erosion(m&roi,structure=np.ones((2,2)));lab,n=nd.label(e);pts=[]
    for i,z in enumerate(nd.find_objects(lab),1):
        yy,xx=z;area=int((lab[z]==i).sum())
        if area<3 or xx.stop-xx.start>8 or yy.stop-yy.start>8:continue
        pts.append([(xx.start+xx.stop-1)/2-.5,(yy.start+yy.stop-1)/2-.5,area])
    # Two partially overprinted squares: locate by translated native square shape.
    # Windows only localize image regions; no uptake/pressure is supplied.
    recovery=[]
    for box in [(90,237,103,251),(505,247,521,263)]:
        l,t,r,b=box;fits=[]
        for y in range(t+3,b-2):
            for x in range(l+3,r-2):
                crop=a[y-2:y+3,x-2:x+3];black=crop.max(2)<100
                colored=(crop.max(2)-crop.min(2)>40)&(crop.min(2)<200)
                score=int(black.sum())-int((~black&~colored).sum())
                fits.append((score,x,y,int(black.sum())))
        best=max(f[0] for f in fits);ties=[f for f in fits if f[0]==best]
        x=float(np.mean([f[1] for f in ties]));y=float(np.mean([f[2] for f in ties]))
        accepted=best>=10
        recovery.append(dict(window=list(box),best_score=best,optimal_centers=[[f[1],f[2]] for f in ties],pixel=[x,y],accepted=accepted,
          reason='requires >=10 net black pixels; a connecting-line fragment behind colored squares is insufficient'))
        if accepted:pts.append([x,y,best])
    for panel,gas,xa,ya,scale in [('a','CO2',axis(61.5,0,386,1),axis(266,0,13.5,1.6),1.6),('b','N2',axis(483,0,802.5,1),axis(264,0,15,.16),.16)]:
        ps=[p for p in pts if (p[0]<450)==(panel=='a')]
        condition=dict(material='UiO-66',gas=gas,observable='q_'+gas,unit='mmol/g',basis='dry_sorbent',T_K=308.15,RH_fraction='',w_PEI=0,
          y_CO2_dry=1 if gas=='CO2' else 0,notes='Powder; Fig.5'+panel+'; activation 120 C for 1 day (section 2.4.1); gas RH not established by activation; not_testable: unknown RH; frame-clipped endpoint retained with 2 px readout bound'+('; D-18: N2 temperature outside calibration without T coefficient' if gas=='N2' else ''))
        finish('T019-S113-Fig5'+panel,'S113',9,path,ims[0],xa,ya,[dict(name='S113-Fig5'+panel+'-UiO66',points=ps,condition=condition,known=False)],scale,
          params=dict(method='black-mask 2x2 erosion, compact components; partial square translation fit',recovery=recovery),
          excluded=[dict(region='CO2 near origin, x pixels <90' if panel=='a' else 'origin and first overprinted N2 symbol (native x 505:521)' ,reason='overprinted symbols; cannot assign distinct black UiO-66 centers; no invented zero'),dict(region='other materials',reason='outside requested UiO-66 powder series')])


def s103():
    path,ims=prepare('S103',3);im=Image.open(ims[0]).convert('RGB');a=np.array(im).astype(float);r,g,b=a.transpose(2,0,1)
    masks={'orange':(r>220)&(g>100)&(g<200)&(b<90),'teal':(r<100)&(g>80)&(g<160)&(b>70)&(b<160),'red':(r>120)&(g<70)&(b>25)&(b<130)}
    colors={'orange':'100','teal':'160','red':'220'}
    templates={'orange':(522,455,538,470),'teal':(523,489,536,503),'red':(520,520,540,537)}
    def domain(c):
        c[:80]=0;c[:,:150]=0;c[:,695:]=0;c[540:]=0;c[445:545,470:735]=0;return c
    def peaks(score,candidate,distance=10):
        ys,xs=np.where(domain(candidate));pts=[]
        for y,x in sorted(zip(ys,xs),key=lambda z:-score[z]):
            if any((x-p[0])**2+(y-p[1])**2<distance**2 for p in pts):continue
            pts.append([int(x),int(y),float(score[y,x])])
        return sorted(pts)
    series=[];excluded=[];open_scores={};open_points={};recoveries=[]
    Y,X=np.mgrid[-9:10,-10:11];d=np.hypot(X,Y);sq=np.maximum(abs(X),abs(Y));tri=(Y>=-7)&(Y<=5)&(abs(X)<=(Y+7)*.69)
    shapes={'orange':((d>=5)&(d<=7),d<4.5),'teal':((sq>=4)&(sq<=6),sq<3.5),'red':(tri&~nd.binary_erosion(tri,structure=np.ones((3,3))),nd.binary_erosion(tri,iterations=3))}
    for color,m in masks.items():
        t,inside=shapes[color]
        hit=signal.fftconvolve(m.astype(float),t[::-1,::-1],mode='same')/t.sum()
        fill=signal.fftconvolve(m.astype(float),inside[::-1,::-1],mode='same')/inside.sum()
        score=hit-.7*fill
        open_scores[color]=score
        threshold=.75 if color=='red' else .47
        cand=(score>=nd.maximum_filter(score,size=(9,9))-1e-6)&(score>threshold)&(fill<.25)
        open_points[color]=peaks(score,cand,9)
    # Teal hollow squares are partly covered by the red triangle series. Search
    # windows are determined from visible red outlines, not from any data values.
    # Require a native horizontal top edge and an empty square center.
    teal=[];teal_windows=[];m=masks['teal'];score=open_scores['teal']
    for x,y,_ in open_points['red']:
        l,r0=max(150,x-4),min(695,x+5);t,b0=max(80,y-21),y-2
        local=score[t:b0,l:r0];iy,ix=np.unravel_index(np.argmax(local),local.shape);px,py=int(l+ix),int(t+iy)
        # score uses both the outline and the white center; avoid weak fragments
        sc=float(score[py,px]);accepted=sc>=.38 and not (px in (l,r0-1) or py in (t,b0-1))
        teal_windows.append(dict(window=[l,t,r0,b0],pixel=[px,py],score=sc,accepted=accepted))
        if accepted:teal.append([px,py,sc])
    open_points['teal']=teal
    for color,m in masks.items():
        x0,y0,x1,y1=templates[color];t=m[y0:y1,x0:x1];yy,xx=np.where(t);t=t[yy.min():yy.max()+1,xx.min():xx.max()+1]
        # No occlusion reconstruction: full native legend shape must match.
        hit=signal.fftconvolve(m.astype(float),t[::-1,::-1],mode='same')
        score=(2*hit-t.sum())/t.sum();center=nd.uniform_filter(m.astype(float),size=3)>.7
        cand=(score>=nd.maximum_filter(score,size=(9,9))-1e-6)&(score>.35)&center
        candidates=peaks(score,cand)
        filled=[p for p in candidates if p[2]>=.8]
        excluded.extend(dict(series=colors[color]+'-adsorption',pixel=p[:2],score=p[2],reason='native filled-symbol agreement <0.8; partial overprint, no reconstruction') for p in candidates if p[2]<.8)
        # fftconvolve same has a half-pixel offset for even templates. Preserve
        # the geometric bbox center in the original image, not the array index.
        filled=[[p[0]-.5 if t.shape[1]%2==0 else p[0],p[1]-.5 if t.shape[0]%2==0 else p[1],p[2]] for p in filled]
        if color in ('orange','red'):
            # T019b: independently match the visible lower silhouette of the
            # native legend symbol. No reviewer coordinates, neighboring data,
            # fitted isotherm, or desorption branch determines these centers.
            shape=np.pad(t,3);region=np.zeros(shape.shape,bool)
            region[3+t.shape[0]//2:3+t.shape[0]+2,:]=True
            weights=np.zeros(shape.shape)
            weights[region&shape]=1/(region&shape).sum()
            weights[region&~shape]=-1/(region&~shape).sum()
            partial_score=signal.fftconvolve(m.astype(float),weights[::-1,::-1],mode='same')
            cand=(partial_score>=nd.maximum_filter(partial_score,size=9)-1e-8)&(partial_score>.65)
            cand[:,:165]=False
            partial=peaks(partial_score,cand)
            recovered=[]
            for x,y,sc in partial:
                x-=.5 if t.shape[1]%2==0 else 0
                y-=.5 if t.shape[0]%2==0 else 0
                if any(math.hypot(x-p[0],y-p[1])<8 for p in filled):continue
                filled.append([x,y,sc,3]);recovered.append(dict(pixel=[x,y],score=sc,readout_bound_px=3))
            recoveries.append(dict(series=colors[color]+'-adsorption',template_window=templates[color],
              template_shape=list(t.shape),method='lower-half filled silhouette plus negative exterior weights',
              padding_px=3,threshold=.65,minimum_separation_px=10,duplicate_radius_px=8,
              visible_source_review='accepted lower contours checked on native source overlay in T019b',
              recovered=recovered,coverage='partial; no claim of a complete isotherm'))
            # The full-template gate rejected some subsequently recovered
            # contours; do not label their final coordinates as excluded.
            excluded=[e for e in excluded if not (e.get('series')==colors[color]+'-adsorption'
              and any(math.hypot(e['pixel'][0]-p[0],e['pixel'][1]-p[1])<8 for p in filled))]
        for branch,ps in [('adsorption',filled),('desorption',open_points[color])]:
            restriction=('excluded: desorption branch outside adsorption comparison' if branch=='desorption' else
              'excluded: endpoint only; not a complete isotherm test; independent eight-point quota not met' if color=='teal' else
              'partial identifiable-marker subset only; not a complete isotherm; not_testable: unknown RH')
            c=dict(material='UiO-66',gas='CO2',observable='q_CO2',unit='mmol/g',basis='dry_sorbent',T_K=300.15,RH_fraction='',w_PEI=0,y_CO2_dry=1,
              notes=f'UiO-66_{colors[color]}; {branch}; {restriction}; Methods p.7: activation vacuum 100 C 8 h does not establish gas RH; STP conversion follows docs/methodology.md (273.15 K, 101.325 kPa); S103/S106 potential common synthesis lineage')
            series.append(dict(name=f'S103-Fig2a-UiO66_{colors[color]}-{branch}',points=ps,condition=c,readout=2,
              comparable=branch=='adsorption' and color!='teal',known=False,overlay='lime' if branch=='adsorption' else 'cyan'))
    excluded.extend([dict(region='native x <150 px / low pressure cluster',reason='overprinted symbols; cannot resolve individual series; no zero inserted'),dict(region='unresolved filled teal squares and remaining partial orange/red contours',reason='only identifiable full or lower-silhouette matches retained; incompleteness is not absence of measurements; no full-isotherm claim')])
    # Source drawing spans -5 to 90 cm3(STP)/g. The lower -5 boundary is inferred
    # from the 0 and 90 tick positions and plot frame, documented for review.
    finish('T019-S103-Fig2a','S103',3,path,ims[0],axis(140.5,0,687.5,1),axis(550.5,0,12.5,90),series,95,
      factor=1/22.414,params=dict(method='native-legend filled templates; geometric hollow templates; source-color masks',
      filled_agreement_min=.8,partial_recovery=recoveries,legend_windows=templates,teal_open_search=teal_windows,STP_convention='273.15 K / 101.325 kPa; 22.414 cm3/mmol',
      scale_range_source=[-5,90],scale_note='negative lower frame extension inferred from evenly spaced ticks; axis values checked on source page'),excluded=excluded)


def s102():
    path,ims=prepare('S102',5)
    for i,water in enumerate([2.05,3.03,4.10]):
        im=Image.open(ims[i]).convert('RGB');a=np.array(im).astype(float);r,g,b=a.transpose(2,0,1)
        m=(g>110)&(r>80)&(b<190)&(g>r*1.02)&(g-b>20)
        Y,X=np.mgrid[-11:12,-8:9];d=abs(X)/4.5+abs(Y)/8;t=(d>.75)&(d<1.2)
        score=signal.fftconvolve(m.astype(float),t[::-1,::-1],mode='same')/t.sum()
        cand=(score>=nd.maximum_filter(score,size=(15,15))-1e-6)&(score>.45)
        cand[:150,:410]=0;cand[:40]=0;cand[:,:130]=0;cand[:,810:]=0;cand[435:]=0
        ys,xs=np.where(cand);pts=[]
        for y,x in sorted(zip(ys,xs),key=lambda z:-score[z]):
            if any((x-p[0])**2+(y-p[1])**2<15**2 for p in pts):continue
            pts.append([int(x),int(y),float(score[y,x])])
        xa=axis(114,0,751.5,8) if i<2 else axis(112,0,736,8)
        ya=axis(441.5,0,25,.20) if i<2 else axis(432,0,25,.20)
        c=dict(material='UiO-66-NH2',gas='CO2+H2O',observable='q_CO2',unit='mmol/g',basis='unknown',w_PEI=0,
          notes=f'Fig.S6{chr(97+i)}; preadsorbed H2O={water} mol/kg (experimental input); not_testable: T/RH/basis and total-versus-partial pressure definition unknown; identifiable-marker subset below independent eight-point quota')
        finish(f'T019-S102-FigS6{chr(97+i)}','S102',5,path,ims[i],xa,ya,[dict(name=f'S102-FigS6{chr(97+i)}-binary',points=pts,condition=c,known=False,comparable=False)],.20,
          pressure_factor=.01,params=dict(method='green diamond outline correlation, threshold 0.45',water_loading_mol_kg=water,
            display_pressure_note='stored in source-coordinate CSV/condition notes; not silently assigned to p_partial or p_total'),
          excluded=[dict(region='origin cluster',reason='overprinted markers cannot be individually assigned'),dict(region='red circles / dark triangles / lines',reason='dry control / IAST / guides; not binary experimental markers')])


def s2():
    path=PRIV/'S2_xml.download';root=ET.parse(path).getroot();tables={}
    for table in root.findall('.//table-wrap'):
        if table.get('id') not in ['tbl1','tbl2']:continue
        tables[table.get('id')]=[[''.join(c.itertext()).strip() for c in list(row)] for row in table.findall('.//tbody/tr')]
    # Header rows are in thead. Join by printed sample names, never by row number:
    # Table 2 orders PEI72 before PEIC96 whereas Table 1 does the opposite.
    t1={r[0]:r for r in tables['tbl1'] if len(r)==9 and r[0]!='adsorbent'}
    t2={r[0]:r for r in tables['tbl2'] if len(r)==7 and r[0] in t1}
    assert len(t1)==len(t2)==6,(t1,t2)
    source_rows=[];qual=[]
    for sample,r in t1.items():
        z=t2[sample];w=float(r[5])/100;vp=float(r[7]);qd=float(z[1]);qc=float(z[5])
        source_rows.append(dict(sample=sample,retained_PEI_percent=float(r[5]),Vp_cm3_g=vp,dry_q_mmol_g=qd,corrected_q_mmol_g=qc,w_PEI=w,q_dry_ratio_to_w0=qd/float(t2['UiO-66-NH2'][1]),Vp_ratio_to_w0=vp/float(t1['UiO-66-NH2'][7])))
        c=dict(material='UiO-66-NH2' if w==0 else 'PEI@UiO-66-NH2',gas='CO2',observable='q_CO2',unit='mmol/g',basis='dry_sorbent',T_K=298.15,p_total_bar=1,p_partial_bar=1,y_CO2_dry=1,RH_fraction=0,w_PEI=w,w_reading='retained',Mw_PEI=600 if w else '',
          notes=f'{sample}; PEI_exp from Table1 nitrogen analysis; retained/Mw/basis known; dry pure CO2 established by section 2.4/Table2; D-11 nominal Table2 pressure 1 bar vs text 1 atm/atmospheric; source T=25 C (Table3 rounds to 298 K); not_testable: pressure ambiguity unresolved; original-layout visual check pending; pressure scenarios in T019b-S2-pressure-policy.json')
        add('S2-Table2-dry',sample,'S2','T019-S2-Table2-dry',q=qd,known=False,**c)
        cr=c|dict(observable='q_CO2_ratio_to_w0',unit='1',notes=c['notes']+'; ratio shares the same parent denominator across all samples')
        add('S2-Table2-dry-ratio',sample,'S2','T019-S2-Table2-dry',q=qd/float(t2['UiO-66-NH2'][1]),known=False,**cr)
        cc=c|dict(p_partial_bar=.15,y_CO2_dry=.15,RH_fraction='',
          notes=c['notes'].replace('dry pure CO2 established by section 2.4/Table2','mixed-feed RH not established by dry pure-CO2 experiment')+'; author-corrected CO2-only capacity, secondary per D-11; nominal composition matches Table2 pressure; reported flow ratio 10/(10+60) is a separate sensitivity scenario; not a direct CO2 measurement; secondary admission pending pressure and RH resolution')
        add('S2-Table2-corrected-secondary',sample,'S2','T019-S2-Table2-corrected',q=qc,comparable=True,known=False,**cc)
        v=c|dict(gas='N2',observable='Vp_ratio_to_w0',unit='1',T_K=77,p_total_bar='',p_partial_bar='',y_CO2_dry='',RH_fraction='',notes=f'{sample}; Table1 total pore volume from N2 desorption; 77 K; degassed 100 C 24 h; ratio shares parent denominator; PDF visual check pending')
        add('S2-Table1-Vp-ratio',sample,'S2','T019-S2-Table1',q=vp/float(t1['UiO-66-NH2'][7]),**v)
        cm=c|dict(RH_fraction='',p_partial_bar='',y_CO2_dry='',notes=f'{sample}; excluded: qualitative moist-CO2 record only; RH and water mass correction unknown; no numerical moist q exported')
        add('S2-Table2-moist-qualitative',sample,'S2','T019-S2-moist',comparable=False,known=False,**cm)
        moist=float(z[2]);qual.append(dict(sample=sample,direction_vs_dry='increase' if moist>qd else 'decrease' if moist<qd else 'equal',comparable=False,RH_fraction=None,extraction_id='T019-S2-moist'))
    derived=DIG/'T019-S2-tables.json'
    dump(derived,dict(rows=source_rows,join_key='printed sample name (not row order)',source='Europe PMC JATS tbl1/tbl2',status='provisional',visual_check='unavailable original PDF; no synthetic rendering presented as source',
      units=dict(PEI='retained mass % composite',Vp='cm3/g',q='mmol/g'),experimental_error='§2.2 reports <3% error without coverage/distribution; not a standard uncertainty; u_exp blank',
      pressure_discrepancy='1 bar table vs 1 atm/atmospheric text; 0.15 bar column vs 14.3 vol% flow',temperature='25 C = 298.15 K; D-11 uses rounded 298 K'))
    qp=DIG/'T019-S2-moist.json';dump(qp,qual)
    for eid,loc,kind,dv in [('T019-S2-Table1','tbl1; §2.1 PEI_exp; §4.1 Mw; §4.5 N2 characterization','measured_table',derived),('T019-S2-Table2-dry','tbl2 dry; §2.2 and §4.6','measured_table',derived),('T019-S2-Table2-corrected','tbl2 Cs,0.15bar; author correction, not raw mixture uptake','author_fit',derived),('T019-S2-moist','tbl2 moist; §2.4; qualitative only','text_value',qp)]:
        passport(eid,'S2',path,None,loc,dv,kind,conversions=[dict(from_unit='retained PEI mass percent',to_unit='mass fraction composite',factor=.01),dict(operation='q_dry/q_dry_parent and Vp/Vp_parent',reference_sample='UiO-66-NH2',shared_denominator=True)],error=dict(u_exp=None,source_error_bound='<3%, coverage undefined',u_dig=None,scale=None),
          params=dict(source_format='JATS_XML',source_locator=loc,pagination='unpaginated',
            visual_source_check='pending original PDF/publisher layout; T019b lawful retrieval unsuccessful',
            pressure_policy='data/extraction/digitization/T019b-S2-pressure-policy.json',
            data_kind_note='author_fit enum used for author algebraic correction, not a regression fit' if kind=='author_fit' else 'table values or reported text; ratios derived explicitly',
            standard_uncertainty='unknown; no assumed 3% standard deviation'))
    dump(DIG/'T019b-S2-pressure-policy.json',dict(
      authority='D-11 nominal pressures; D-18 no invented experimental uncertainty',
      source='S2 JATS tbl2 and sections 2.2/4.6; original visual layout unavailable',
      status='not_testable_pending_pressure_resolution',
      nominal=dict(p_total_bar=1,dry_p_CO2_bar=1,secondary_p_CO2_bar=.15,secondary_y_CO2_dry=.15),
      sensitivity_scenarios=[dict(name='text_standard_atmosphere_nominal_composition',p_total_bar=1.01325,dry_p_CO2_bar=1.01325,secondary_p_CO2_bar=1.01325*.15,secondary_y_CO2_dry=.15),
        dict(name='reported_flow_at_table_pressure',p_total_bar=1,secondary_p_CO2_bar=10/70,secondary_y_CO2_dry=10/70),
        dict(name='reported_flow_at_standard_atmosphere',p_total_bar=1.01325,secondary_p_CO2_bar=1.01325*10/70,secondary_y_CO2_dry=10/70)],
      interpretation='alternative source readings, not measurements or a probability distribution; atmospheric pressure was not measured in source; no u_p assigned',
      secondary_admission=dict(comparable=True,inputs_known=False,role='secondary only per D-11; never pooled with dry primary',
        acceptance='same preregistered metrics/tolerances; no new or relaxed tolerance chosen using V',
        pending='resolve pressure convention, mixed-feed RH and source visual verification before prereg; until then no quantitative admission'),
      model_run=False))
    SUMMARY.append(dict(series='S2 tables (five observable groups)',points=30,comparable='dry/ratios/corrected secondary provisional; capacity inputs unresolved; moist excluded'))


def madden():
    path=ROOT/'data/raw/pdf/S117_SI_T019.pdf';d=pymupdf.open(path);page=d[24]
    page.get_pixmap(matrix=pymupdf.Matrix(2,2)).save(PRIV/'S117_SI_page25.png')
    images=[]
    for i,info in enumerate(page.get_images()):
        obj=d.extract_image(info[0]);f=PRIV/f'S117_native{i}.{obj["ext"]}';f.write_bytes(obj['image']);images.append(f)
    for figure,index,material in [('S37',2,'UiO-66'),('S38',1,'UiO-66-NH2')]:
        image_path=images[index];im=Image.open(image_path).convert('RGB');a=np.array(im).astype(float);r,g,b=a.transpose(2,0,1)
        masks={'wet':(r>80)&(r<200)&(g<90)&(b>170),
          'dry':((g>70)&(r<80)&(b<80)) if index==1 else ((r<60)&(g<80)&(b>150))}
        allpoints={};omissions=[]
        for name,m in masks.items():
            roi=np.zeros(m.shape,bool)
            # retain baseline centers while excluding labels, axes and legends
            left=101 if index==1 else 107;right=736 if index==1 else 742
            roi[35:451,left:625]=1;roi[35:451,right:1250]=1
            roi[350:445,470:625]=0;roi[350:445,1100:1250]=0
            e=nd.binary_erosion(m&roi,structure=np.ones((3,3)));lab,n=nd.label(e);pts=[]
            for k,z in enumerate(nd.find_objects(lab),1):
                yy,xx=z;area=int((lab[z]==k).sum())
                if area<2:continue
                box=[xx.start,yy.start,xx.stop,yy.stop]
                if xx.stop-xx.start>9 or yy.stop-yy.start>9:
                    omissions.append(dict(condition=name,region=box,reason='overlapping adjacent filled markers form unresolved component'));continue
                pts.append([(xx.start+xx.stop-1)/2,(yy.start+yy.stop-1)/2,area])
            allpoints[name]=pts
        for panel,form in [('A','monolith'),('B','powder')]:
            eid=f'T019-S117-Fig{figure}{panel}'
            xzero=(101.5 if index==1 else 107.5) if panel=='A' else (735.5 if index==1 else 742.5)
            xend=(621.5 if index==1 else 627.5) if panel=='A' else (1255 if index==1 else 1261.5)
            xa=axis(xzero,0,xend,100 if figure=='S37' and panel=='B' else 125);ya=axis(448.5,0,30.5,1.6)
            rows=[];series=[];overlay=im.copy();draw=ImageDraw.Draw(overlay)
            for name,pts in allpoints.items():
                selected=sorted([p for p in pts if (p[0]<680)==(panel=='A')]);pixels=[]
                for j,(x,y,area) in enumerate(selected,1):
                    rows.append(dict(series=f'{figure}{panel}-{name}-CO2',point_id=f'{j:03d}',extraction_id=eid,pixel_x=x,pixel_y=y,
                      time_normalized_min_cm3=transform(xa,x),outlet_ratio_CO2=transform(ya,y),u_dig=uncertainty(ya,y,2),
                      u_time_normalized=uncertainty(xa,x,2),scale=1.6,RH_fraction=.74 if name=='wet' else 0,T_K=298))
                    pixels.append([x,y]);draw.ellipse((x-4,y-4,x+4,y+4),outline='orange',width=1)
                series.append(dict(name=f'{figure}{panel}-{name}-CO2',data_kind='digitized_markers',sigma_pixel=2/math.sqrt(3),pixels=pixels))
            output=DIG/(eid+'.csv');csvout(output,rows,'series point_id extraction_id pixel_x pixel_y time_normalized_min_cm3 outlet_ratio_CO2 u_dig u_time_normalized scale RH_fraction T_K'.split())
            op=PRIV/(eid+'-overlay.png');overlay.save(op)
            project=dict(image_sha256=sha(image_path),image_path=rel(image_path),pdf_sha256=sha(path),pdf_page=25,
              code_version=sha(__file__),x_axis=xa,y_axis=ya,x_unit='min/cm3 (as printed)',y_unit='C/C0',series=series,
              overlay=rel(op),overlay_sha256=sha(op),export=rel(output),export_sha256=sha(output),
              method='purple / blue / green masks; 3x3 erosion removes thin connecting lines and hollow N2 symbols; compact filled CO2 components only',
              exclusions=omissions+[dict(region='hollow N2 symbols',reason='not CO2 outlet observations; no nitrogen uptake inferred'),dict(region='shared near-zero symbols',reason='overprinted colors; no hidden zero values inserted')],
              uncertainty=dict(type='standard k=1',formula='abs(slope)*sqrt((2^2+(1-t)^2+t^2)/3)',calibration_endpoint_bound_px=1,readout_bound_px=2),
              not_equilibrium_uptake=True,holdout_mapping='no C/C0 observation is labeled as q_CO2; only a blank capacity placeholder is exported',
              capacity_unavailable='SI S5-S6 requires blank-reference area ARef; exact mass/volume and normalization for each trace are not provided')
            (DIG/(eid+'.digitization.yaml')).write_text(yaml.safe_dump(project,sort_keys=False,allow_unicode=True))
            passport(eid,'S117',path,25,f'Fig.{figure}{panel}; {form} {material}; breakthrough CO2, dry and 74% RH',output,'digitized_markers',
              region=dict(image=rel(image_path),image_sha256=sha(image_path)),params=dict(project=rel(DIG/(eid+'.digitization.yaml')),observable='outlet concentration C/C0, NOT adsorption capacity'),error=project['uncertainty'])
            add(f'S117-Fig{figure}{panel}-wet-capacity-unavailable','capacity','S117',eid,comparable=False,known=False,
              material=material,gas='CO2',observable='q_CO2',unit='mmol/g',basis='unknown',T_K=298,y_CO2_dry=.15,RH_fraction=.74,w_PEI=0,
              notes=f'{form}; SI p.S25; not_testable: source ordinate C/C0 vs time (min/cm3), not q; total flow 2 cm3/min; blank-reference integral and exact mass/volume unavailable; source marker CSV retained separately')
            SUMMARY.append(dict(series=f'S117-Fig{figure}{panel}-CO2-breakthrough',points=len(rows),comparable=False,outside_holdout_observable_schema=True))
    evidence=DIG/'T019-S117-access.json'
    dump(evidence,dict(source_id='S117',SI_available=True,pdf_sha256=sha(path),pdf_page=25,
      URL='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8517963/supplementaryFiles',archive_member='FD-231-D1FD00017A-s001.pdf',
      S36='HKUST-1, not UiO-66 or UiO-66-NH2; outside requested material scope',S37='UiO-66 monolith/powder',S38='UiO-66-NH2 monolith/powder',
      output_kind='CO2 breakthrough concentration markers, NOT mmol/g',quantitative_capacity_available=False,
      reason='C/C0 vs normalized time; blank reactor integral and exact sample normalization required by authors uptake method unavailable',
      T_K=298,RH_wet=.74,y_CO2_dry=.15,total_flow_cm3_min=2,pressure_bar=None))
    passport('T019-S117-access','S117',path,25,'SI Fig.S36-S38 and methods S5-S6; observable compatibility',evidence,'text_value',
      params=dict(SI_available=True,capacity_mapping_possible=False),error='No uptake uncertainty can be inferred from concentration digitization')


def main():
    CONDITIONS.clear();OBSERVATIONS.clear();SUMMARY.clear()
    for p in [DIG,REC,PRIV,OUT]:p.mkdir(parents=True,exist_ok=True)
    if not METADATA.exists():
        raise FileNotFoundError('Missing T019b-build-metadata.json: use the recorded extraction metadata, do not invent a replay date')
    s113();s103();s102();s2();madden()
    csvout(OUT/'conditions.csv',CONDITIONS,COND);csvout(OUT/'observations.csv',OBSERVATIONS,OBS)
    for record in REC.glob('T019-*.yaml'):
        r=yaml.safe_load(record.read_text())
        r['params']['holdout_exports']={name:sha(OUT/name) for name in ['conditions.csv','observations.csv']}
        record.write_text(yaml.safe_dump(r,sort_keys=False,allow_unicode=True))
    dump(DIG/'T019-work/summary.json',SUMMARY)
    statuses=[]
    for name in sorted({c['series'] for c in CONDITIONS}):
        pairs=[(c,o) for c,o in zip(CONDITIONS,OBSERVATIONS) if c['series']==name]
        c,o=pairs[0]
        status='excluded' if 'excluded:' in c['notes'] else 'not_testable' if 'not_testable:' in c['notes'] else 'pending_verification'
        reason=c['notes'].split('; ',1)[-1]
        statuses.append(dict(series=name,source_id=c['source_id'],extraction_id=c['extraction_id'],
          status=status,reason=reason,verification_status='provisional',reviewer_pending='T019v2',
          comparable=o['comparable']=='true',inputs_known=o['inputs_known']=='true',points=len(pairs),
          complete_isotherm_claim=False,independent_eight_point_check_claim=False))
    dump(DIG/'T019b-series-status.json',statuses)
    print('T019b holdout rebuilt; passports provisional pending T019v2; no model executed')


if __name__=='__main__':main()
