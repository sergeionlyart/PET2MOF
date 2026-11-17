"""Independent exact-byte projections and normalized-data checks, C sources only."""
from pathlib import Path
import csv
import hashlib
import io
import json
import subprocess
import yaml
from geometric_check import PANELS, dump, sha

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
BASE='447364e'

def gitbytes(path):
    return subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
def rows(b): return list(csv.DictReader(io.StringIO(b.decode())))
def filtered_bytes(b,series=None):
    lines=b.splitlines(keepends=True)
    return b''.join(l for l in lines[1:] if series is None or next(csv.reader([l.decode()]))[2]==series)
def no_status(b,index):
    # These files have no quoted/embedded-comma fields. Preserve literal fields
    # and original EOL; water has two RH columns AFTER status.
    assert b'"' not in b
    out=[]
    for line in b.splitlines(keepends=True):
        body=line.rstrip(b'\r\n');eol=line[len(body):];fields=body.split(b',')
        out.append(b','.join(fields[:index]+fields[index+1:])+eol)
    return b''.join(out)

def main():
    manifest=json.loads((ROOT/'data/processed/c_series/manifest.json').read_text())
    ps=manifest['water_conversion']['psat_293K_bar'];vol=manifest['water_conversion']['STP_cm3_per_mmol']
    preservation=[];normal=[];ranges=[];hashes={}
    for path in sorted((ROOT/'data/extraction/digitization').glob('T011-*.digitization.yaml')):
        d=yaml.safe_load(path.read_text());rawpath=path.with_name(path.name.replace('.digitization.yaml','.csv'))
        raw=rawpath.read_bytes();old=gitbytes(rawpath);rr=rows(raw)
        hashes[str(path.relative_to(ROOT))]=sha(path.read_bytes());hashes[str(rawpath.relative_to(ROOT))]=sha(raw)
        for s in d['series']:
            r=[v for v in rr if v['series']==s['name']]
            matches=[]
            for sid,meta in manifest['series'].items():
                if sid.startswith('C-'+d['extraction_id'][5:]+'-'):
                    f=ROOT/f'data/processed/c_series/{sid}.csv';b=f.read_bytes();nr=rows(b)
                    if nr[0]['material']==s['name']:matches.append((sid,meta,f,b,nr))
            assert len(matches)==1,(path,s['name'],len(matches))
            sid,meta,f,b,nr=matches[0];assert len(r)==len(nr)
            assert sha(b)==meta['csv_sha256'];hashes[str(f.relative_to(ROOT))]=sha(b)
            xp=ps if d['gas']=='H2O' else 1.;yq=1/vol if d['gas']=='H2O' else 1.
            errors=[]
            for a,z in zip(r,nr):
                expect={'p_bar':float(a['x'])*xp,'q_mmol_g':float(a['y'])*yq,
                        'p_err_bar':max(float(a['x_err']),.03*d['protocol_scale_span_x'])*xp,
                        'q_err_mmol_g':max(float(a['y_err']),.03*d['protocol_scale_span_y'])*yq}
                for k,v in expect.items():
                    delta=abs(float(z[k])-v);assert delta<=max(1e-10,abs(v)*1e-10),(sid,k,delta)
                for k in ['gas','T_K','status','data_kind']:assert a[k]==z[k]
                assert float(a['pixel_x'])==s['pixels'][len(errors)][0]
                assert float(a['pixel_y'])==s['pixels'][len(errors)][1]
                errors.append({k:abs(float(z[k])-v) for k,v in expect.items()})
            pmin=min(float(a['x'])*xp for a in r)
            assert abs(s['usable_p_min_bar']-pmin)<1e-12
            assert abs(meta['usable_p_min_bar']-pmin)<1e-12
            ranges.append({'series_id':sid,'n':len(r),'project_usable_p_min_bar':s['usable_p_min_bar'],
                           'manifest_usable_p_min_bar':meta['usable_p_min_bar'],'observed_min_p_bar':pmin,
                           'origin_coverage':s['origin_coverage']})
            normal.append({'series_id':sid,'rows':len(r),'max_rounding_residual':max(max(e.values()) for e in errors),
                           'sha256_matches_manifest':True,'x_multiplier':xp,'y_multiplier':yq})
            if s.get('status')=='verified':
                a=filtered_bytes(old,s['name']);bb=filtered_bytes(raw,s['name']);ob=gitbytes(f)
                oldrows=rows(ob)
                changed=sorted({k for x,y in zip(oldrows,nr) for k in x if x[k]!=y[k]})
                # T011b also changed raw CSV EOL from CRLF to LF. Check this
                # separately; do not describe whole-file bytes as unchanged.
                an=no_status(a,13).replace(b'\r\n',b'\n');bn=no_status(bb,13).replace(b'\r\n',b'\n')
                on=no_status(ob,11).replace(b'\r\n',b'\n');nn=no_status(b,11).replace(b'\r\n',b'\n')
                assert an==bn
                assert on==nn
                assert changed==['status']
                preservation.append({'series_id':sid,'rows':len(r),'changed_fields':changed,
                    'raw_series_exact_byte_equal':a==bb,'normalized_file_exact_byte_equal':ob==b,
                    'all_nonstatus_field_bytes_equal':True,
                    'raw_baseline_CRLF_count':a.count(b'\r\n'),'raw_current_CRLF_count':bb.count(b'\r\n'),
                    'normalized_baseline_CRLF_count':ob.count(b'\r\n'),'normalized_current_CRLF_count':b.count(b'\r\n'),
                    'raw_baseline_sha256':sha(a),'raw_current_sha256':sha(bb),
                    'normalized_baseline_sha256':sha(ob),'normalized_current_sha256':sha(b),
                    'raw_nonstatus_LF_sha256':sha(an),'normalized_nonstatus_LF_sha256':sha(on)})
    assert len(preservation)==12;assert len(ranges)==19
    dump(OUT/'preservation_checks.json',{'baseline_commit':subprocess.check_output(['git','rev-parse',BASE],cwd=ROOT,text=True).strip(),
                                       'literal_byte_check':False,'numerical_and_nonstatus_byte_check':True,'series':preservation})
    dump(OUT/'normalization_checks.json',{'series':normal,'checked_rows':sum(s['rows'] for s in normal)})
    dump(OUT/'usable_ranges.json',ranges);dump(OUT/'input_hashes.json',hashes)
    print('Preservation: 12/12 non-status field bytes unchanged; raw full bytes differ in status AND CRLF->LF.')
    print('Normalization and usable_p_min_bar:',len(normal),'series',sum(s['rows'] for s in normal),'rows: PASS')

if __name__=='__main__':main()
