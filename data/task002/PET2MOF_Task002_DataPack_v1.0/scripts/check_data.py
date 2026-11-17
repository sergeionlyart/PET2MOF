#!/usr/bin/env python3
"""Offline integrity/data-contract checks. No scientific validation is implied."""
from __future__ import annotations
import csv
import hashlib
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def load(rel: str) -> list[dict[str,str]]:
    with (ROOT / rel).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))
def run() -> dict:
    checks=[]
    def check(name: str, ok: bool) -> None:
        checks.append({'check':name,'passed':bool(ok)})
    mats=load('data/primary/S2_materials.csv');dry=load('data/primary/S2_dry_CO2.csv')
    sec=load('data/primary/S2_secondary_properties.csv');curve=load('data/benchmark/S100_dry_isotherms.csv')
    excluded=load('data/quarantine/S100_excluded_points.csv')
    check('S2_materials_6_unique',len(mats)==6 and len({r['sample_id'] for r in mats})==6)
    check('S2_dry_exactly_one_per_sample',len(dry)==6 and {r['sample_id'] for r in mats}=={r['sample_id'] for r in dry})
    check('S2_secondary_grain_30_unique',len(sec)==30 and len({(r['sample_id'],r['metric']) for r in sec})==30)
    check('S2_missing_heat_preserved',sum(r['value']=='' for r in sec)==3 and all(r['metric']=='Qdes_DSC' for r in sec if r['value']==''))
    check('S2_positive_dry_capacity',all(math.isfinite(float(r['q_CO2_dry_mmol_g'])) and float(r['q_CO2_dry_mmol_g'])>0 for r in dry))
    check('S2_pressure_discrepancy_retained',all(float(r['pressure_lower_bar'])==1 and float(r['pressure_upper_bar'])==1.01325 for r in dry))
    check('S2_PE I_not_feed_label'.replace('PE I','PEI'),next(r for r in mats if r['sample_id']=='S2-C96')['PEI_content_author_calculated_wt_pct']=='22.4')
    check('S2_no_false_PET_provenance',all(r['PET_derived']=='not_reported' for r in mats))
    check('S2_wet_segregated',all(r['allowed_use']=='context_only_not_fit_or_CO2_only_validation' for r in sec if r['metric']=='q_moist_reported'))
    check('S100_48_points_5_series',len(curve)==48 and len({r['sample_label'] for r in curve})==5)
    check('S100_2_provisional_quarantined',len(excluded)==2 and all(r['legacy_status']=='provisional' for r in excluded))
    check('S100_unique_point_ids',len({r['point_id'] for r in curve})==48)
    check('S100_unknown_mass_not_filled',all(r['mass_basis']=='unresolved_reported_gram' for r in curve))
    check('S100_error_not_missing_in_benchmark',all(r['q_digitization_halfwidth'] and r['p_digitization_halfwidth_bar'] for r in curve))
    check('S100_gas_and_temperature',all(r['gas']=='CO2' and r['T_K']=='298' for r in curve))
    for m in sorted({r['sample_label'] for r in curve}):
        rows=sorted([r for r in curve if r['sample_label']==m],key=lambda r:float(r['p_bar']))
        p=[float(r['p_bar']) for r in rows];q=[float(r['q_mmol_per_g_reported']) for r in rows]
        check('S100_monotone_'+m,all(b>a for a,b in zip(p,p[1:])) and all(b>=a for a,b in zip(q,q[1:])))
        check('S100_probe_interior_'+m,min(p)+0.042<0.15 and max(p)-0.042>0.85)
    for entry in json.loads((ROOT/'metadata/legacy_sources.json').read_text()):
        b=(ROOT/entry['path']).read_bytes();sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        check('Git_blob_'+Path(entry['path']).stem,sha==entry['git_blob_sha1'])
    split=load('metadata/S100_internal_split.csv')
    check('split_exact_coverage',len(split)==48 and {r['point_id'] for r in split}=={r['point_id'] for r in curve})
    check('split_no_false_external',all(r['independent_external']=='False' for r in split))
    check('no_GitHub_Actions',not (ROOT/'.github/workflows').exists())
    check('no_env_or_keys',not (ROOT/'.env').exists() and not any(p.suffix in {'.pem','.key','.p12'} for p in ROOT.rglob('*')))
    ref={r['sample_id']:float(r['dry_table2']) for r in load('metadata/S2_transcription_crosscheck.csv')}
    check('S2_transcription_crosscheck',all(float(r['q_CO2_dry_mmol_g'])==ref[r['sample_id']] for r in dry))
    manifest=ROOT/'metadata/SHA256SUMS.txt'
    if manifest.exists():
        hashes=[]
        for line in manifest.read_text().splitlines():
            expected,rel=line.split('  ',1);p=ROOT/rel
            hashes.append(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==expected)
        check('distributed_manifest_integrity',all(hashes))
    return {'scope':'file integrity, schema, units and explicit exclusions; NOT validation of physical model',
            'counts':{'S2_samples':len(mats),'S2_dry_observations':len(dry),'S2_secondary_records':len(sec),'S100_benchmark_points':len(curve),'S100_quarantined_points':len(excluded)},
            'passed':sum(c['passed'] for c in checks),'total':len(checks),'checks':checks}
if __name__=='__main__':
    report=run();(ROOT/'checks').mkdir(exist_ok=True)
    (ROOT/'checks/data_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['passed']==report['total'] else 1)
