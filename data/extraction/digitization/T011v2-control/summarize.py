"""Produce control summaries and explicit low-visibility uncertainty evidence."""
from pathlib import Path
import csv
import json
import collections
import numpy as np
from PIL import Image, ImageDraw
import yaml
from geometric_check import PANELS, dump, fit, mask

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]

def main():
    rows=list(csv.DictReader((OUT/'geometric_comparison.csv').open()))
    groups=collections.defaultdict(list)
    for r in rows:groups[(r['extraction_id'],r['series'])].append(r)
    summary=[]
    ps=.02317544979505042;vol=22.414
    for (eid,name),rs in groups.items():
        water='S106' in eid;xp=ps if water else 1.;yq=1/vol if water else 1.
        summary.append({'extraction_id':eid,'series':name,'n_control':len(rs),
                        'n_restored':sum(bool(r['recovery_id']) for r in rs),
                        'max_abs_delta_p_bar':max(float(r['abs_delta_x'])*xp for r in rs),
                        'max_abs_delta_q_mmol_g':max(float(r['abs_delta_y'])*yq for r in rs),
                        'median_abs_delta_p_bar':float(np.median([float(r['abs_delta_x'])*xp for r in rs])),
                        'median_abs_delta_q_mmol_g':float(np.median([float(r['abs_delta_y'])*yq for r in rs])),
                        'source_p_error_bar':float(rs[0]['T011_x_err'])*xp,
                        'source_q_error_mmol_g':float(rs[0]['T011_y_err'])*yq,
                        'outside_source_error':sum(r['within_T011_error']!='True' for r in rs)})
    dump(OUT/'comparison_summary.json',summary)
    with (OUT/'comparison_summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    sensitivity=[];low=[]
    for panel in PANELS:
        pr=json.loads((OUT/f'{panel}.project.json').read_text())
        src=yaml.safe_load((ROOT/f'data/extraction/digitization/T011-{panel}.digitization.yaml').read_text())
        im=np.array(Image.open(OUT/f'{panel}-native.png'))
        for s in pr['series']:
            sr=src['series'][s['index']];recs={r['id']:r for r in sr['recoveries']}
            for r in s['markers']:
                if not r['recovery_id']:continue
                rec=recs[r['recovery_id']];f=r['fit'];variants=[]
                if panel=='S106-Fig4' and r['index']<=7:
                    for delta in [-1.,1.]:
                        ref=dict(s['reference']);ref['width']+=2*delta;ref['height']+=2*delta
                        g=fit(im,s['color'],s['shape'],ref,f['search_region'])
                        variants.append({'radius_delta':delta,'fit':g})
                    sensitivity.append({'id':r['recovery_id'],'variants':variants})
                fraction=rec['visible_support_pixels']/rec['template_ink_pixels']
                if fraction>=.25:continue
                fs=[f]+[v for v in r['threshold_variants'] if v]+[v['fit'] for v in variants]
                boxes=np.array([g['plausible_center_bounds'] for g in fs]);lo=boxes[:,:2].min(axis=0);hi=boxes[:,2:].max(axis=0)
                proposed=np.array(rec['pixel']);deviation=np.maximum(abs(proposed-lo),abs(hi-proposed))
                # Shape variation for circles is explicitly sampled above. For
                # squares add 0.5 px to account for half-width/height variation.
                allowance=0.5 if s['shape']=='square' else 0.
                total=deviation+1.5+allowance
                low.append({'recovery_id':rec['id'],'series_row':r['index'],'shape':s['shape'],
                            'T011b_visible_fraction':fraction,'control_center':f['center'],
                            'T011_center':rec['pixel'],'union_center_bounds':list(lo)+list(hi),
                            'calibration_allowance_px':1.5,'extra_shape_allowance_px':allowance,
                            'required_total_bound_x_px':float(total[0]),'required_total_bound_y_px':float(total[1]),
                            'T011_total_bound_px':rec['readout_bound_px']+2,
                            'within_total_T011_bound':bool(np.all(total<=rec['readout_bound_px']+2+1e-9)),
                            'source_identity':'own black orthogonal edges' if s['shape']=='square' else 'own pink upper arc over purple square',
                            'directed_runs':f.get('directed_runs'),
                            'edge_count':f['edge_count']})
                x0,y0,x1,y1=f['search_region'];cut=Image.fromarray(im[y0:y1,x0:x1]).resize(((x1-x0)*6,(y1-y0)*6),Image.Resampling.NEAREST)
                draw=ImageDraw.Draw(cut)
                for x,y in f['edge_pixels']:
                    u=(x-x0)*6+3;v=(y-y0)*6+3;draw.ellipse((u-1,v-1,u+1,v+1),fill='#007500')
                x,y=f['center'];u=(x-x0)*6+3;v=(y-y0)*6+3
                draw.line((u-6,v,u+6,v),fill='#ff7f00',width=2);draw.line((u,v-6,u,v+6),fill='#ff7f00',width=2)
                cut.save(OUT/f'{rec["id"]}-edge-evidence.png')
    dump(OUT/'circle_radius_sensitivity.json',{'reference_radius':8.75,'radius_variation_px':1,'variations':sensitivity})
    dump(OUT/'low_visibility_checks.json',{'definition':'T011b visible_support_pixels/template_ink_pixels < 25%; not independently re-estimated area fraction',
                                        'method':'union of threshold/radius geometry envelopes, plus calibration and shape allowance; diagnostic bounds, not statistical confidence intervals',
                                        'points':low})
    assert len(rows)==302
    assert len(low)==9
    assert all(r['within_T011_error']=='True' for r in rows)
    print('302 controls, 32 restored; 9 low-visibility points; low-visibility envelope check:',[r['within_total_T011_bound'] for r in low])

if __name__=='__main__':main()
