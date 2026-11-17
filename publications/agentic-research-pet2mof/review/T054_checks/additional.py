"""T054-only checks. Standard library; reads Git/public files; writes beside itself."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
PUB = ROOT / 'publications/agentic-research-pet2mof'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def rows(path):
    return list(csv.DictReader((ROOT / path).open(newline='')))

def stamp(value):
    return datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)

runs = rows('publications/agentic-research-pet2mof/evidence/agent_runs.csv')
stages = rows('publications/agentic-research-pet2mof/evidence/stage_stats.csv')
result = {'head': git('rev-parse', 'HEAD').decode().strip(), 'stages': {}}
for stage in stages:
    selected = [r for r in runs if r['stage'] == stage['stage']]
    events = sorted([(stamp(r['started_utc']), 1) for r in selected] +
                    [(stamp(r['finished_utc']), -1) for r in selected])
    n = maximum = 0
    for _, change in events:
        n += change
        maximum = max(maximum, n)
    duration = sum(int(r['duration_s']) for r in selected)
    assert len(selected) == int(stage['agent_runs'])
    assert maximum == int(stage['max_concurrent_runs'])
    assert duration == int(stage['agent_duration_sum_s'])
    assert all((stamp(r['finished_utc'])-stamp(r['started_utc'])).total_seconds()
               == int(r['duration_s']) for r in selected)
    result['stages'][stage['stage']] = {
        'runs': len(selected), 'max_concurrent': maximum, 'sum_seconds': duration,
        'calendar_seconds': int(stage['calendar_duration_s']),
        'calendar_hours': int(stage['calendar_duration_s'])/3600,
    }
result['working_runs'] = sum(r['stage'] != 'setup' for r in runs)
result['setup_runs'] = sum(r['stage'] == 'setup' for r in runs)
result['first_run_to_final_commit_hours'] = (
    datetime.fromisoformat(git('show','-s','--format=%cI','70685dc').decode().strip())
    - min(stamp(r['started_utc']) for r in runs)).total_seconds()/3600
result['git_dates'] = {s: git('show','-s','--format=%H %cI',s).decode().strip()
                       for s in ('009a8b9','66bae26','1558433','70685dc')}
registry = git('show','66bae26:sources/registry.yaml').decode()
result['registry_entries'] = len(re.findall(r'^- source_id:', registry, re.M))
paths = git('ls-tree','-r','--name-only','66bae26','data/raw/nist_isodb/isotherms/').decode().splitlines()
result['nist_files_historical'] = len(paths)
result['nist_files_local'] = len(list((ROOT/'data/raw/nist_isodb/isotherms').glob('*')))
result['nist_historical_local_bytes_equal'] = all(git('show','66bae26:'+p) == (ROOT/p).read_bytes() for p in paths)
agreement = json.loads((ROOT/'reports/task003/independent_agreement.json').read_text())
result['agreement'] = {k: agreement[k] for k in ('n_checks','n_failed','worst_abs_diff','not_compared')}
result['agreement']['observed_max'] = max(x['abs_diff'] for x in agreement['checks'])
result['bdc_per_zr6'] = (39.75/164)/(40.72/123)*6
result['bet_relative_difference_pct'] = (874.6/873.9-1)*100
result['png_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((PUB/'assets').glob('*.png'))}
result['png_changed_from_0_9'] = {
    p.name: git('show','task004-draft-0.9:'+str(p.relative_to(ROOT))) != p.read_bytes()
    for p in sorted((PUB/'assets').glob('*.png'))}
result['parallel_episode'] = [{k:r[k] for k in ('task_id','started_utc','finished_utc')}
    for r in runs if r['task_id'].startswith(('T006-','T008-','T013-'))]
(OUT/'additional.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k: result[k] for k in ('working_runs','setup_runs','registry_entries','nist_files_historical','agreement')},indent=2))
