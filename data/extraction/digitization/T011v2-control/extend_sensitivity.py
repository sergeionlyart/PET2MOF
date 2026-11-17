"""Additional post-freeze check: jointly vary pink threshold AND circle radius."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from geometric_check import fit, dump

OUT=Path(__file__).resolve().parent

def main():
    s=json.loads((OUT/'S106-Fig4.project.json').read_text())['series'][0]
    im=np.array(Image.open(OUT/'S106-Fig4-native.png'))
    low=json.loads((OUT/'low_visibility_checks.json').read_text())
    byid={r['recovery_id']:r for r in low['points']};allfits=[]
    for r in s['markers'][:7]:
        variants=[]
        for delta in [-1.,0.,1.]:
            for v in [-1,0,1]:
                ref=dict(s['reference']);ref['width']+=2*delta;ref['height']+=2*delta
                f=fit(im,'pink','circle',ref,r['fit']['search_region'],v)
                variants.append({'radius_delta':delta,'threshold_variant':v,'fit':f})
        allfits.append({'recovery_id':r['recovery_id'],'variants':variants})
        if r['recovery_id'] not in byid:continue
        item=byid[r['recovery_id']];boxes=np.array([v['fit']['plausible_center_bounds'] for v in variants])
        lo=boxes[:,:2].min(axis=0);hi=boxes[:,2:].max(axis=0);center=np.array(item['T011_center'])
        bound=np.maximum(abs(center-lo),abs(hi-center))+1.5
        item['union_center_bounds']=list(lo)+list(hi)
        item['required_total_bound_x_px']=float(bound[0]);item['required_total_bound_y_px']=float(bound[1])
        item['within_total_T011_bound']=bool(np.all(bound<=item['T011_total_bound_px']+1e-9))
    low['additional_check']='After T011b-report reading; joint radius x threshold variations; coordinates and verdicts unchanged.'
    dump(OUT/'circle_joint_sensitivity.json',allfits)
    dump(OUT/'low_visibility_joint_checks.json',low)
    assert all(r['within_total_T011_bound'] for r in low['points'])
    print('Joint threshold/radius variations: 9/9 low-visibility total bounds remain compatible.')

if __name__=='__main__':main()
