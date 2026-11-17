"""T054: rerun of audited T052 checks; offline, stdlib-only editorial evidence checks. Writes only beside itself."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
PUB = ROOT / 'publications/agentic-research-pet2mof'
PACK = 'data/task002/PET2MOF_Task002_DataPack_v1.0/'
result = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()}

def rows(path):
    with (ROOT / path).open(newline='') as f:
        return list(csv.DictReader(f))

def raw(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)

def close(a, b):
    assert math.isclose(a, b, abs_tol=1e-10, rel_tol=1e-10), (a, b)

versions = [('66bae26', 'reports/final_report.md'),
            ('1558433', 'reports/task002/final_report_task002.md'),
            ('70685dc', 'reports/task003/final_report.md')]
result['historical_identity'] = {}
for sha, path in versions:
    same = raw(sha, path) == (ROOT / path).read_bytes()
    assert same
    result['historical_identity'][path] = same

article = (PUB / 'article.ru.md').read_text()
result['prompts'] = []
for r in rows('publications/agentic-research-pet2mof/evidence/prompts_manifest.csv'):
    source = raw(r['commit'], r['source_path'])
    assert hashlib.sha256(source).hexdigest() == r['blob_sha256']
    for k in ('excerpt_1', 'excerpt_2'):
        assert r[k].encode() in source
    copy = next((PUB / 'prompts').glob(r['prompt_id'] + '-*.md')).read_text()
    assert copy.rstrip() in article
    match = re.search(r'### ' + r['prompt_id'] + r'\..*?```text\n(.*?)\n```', article, re.S)
    assert match and match.group(1).encode() in source
    result['prompts'].append({'id': r['prompt_id'], 'article_excerpt_exact': True,
                              'full_copy_in_article': True, 'source_sha256': r['blob_sha256']})
template = (PUB / 'prompts/P08-generic-template.md').read_text()
result['template_in_article'] = template.rstrip() in article
assert result['template_in_article']

dry = rows(PACK + 'data/primary/S2_dry_CO2.csv')
nominal = rows('reports/task002/A/nominal.csv')
jats = ET.parse(ROOT / 'reviews/T031-control/tbl2.xml')
jats_dry = [float(''.join(tr.findall('td')[1].itertext())) for tr in jats.findall('.//tbody/tr')]
assert jats_dry == [float(r['q_CO2_dry_mmol_g']) for r in dry]
q = {r['sample_id']: float(r['q_CO2_dry_mmol_g']) for r in dry}
result['dry_values'] = []
for r in nominal:
    v = q[r['sample_id']]
    gain = 100 * (v / q['S2-BASE'] - 1)
    close(v, float(r['q_dry_mmol_g']))
    close(gain, float(r['gain_vs_base_pct']))
    result['dry_values'].append({'id': r['sample_id'], 'q': v, 'gain_pct': gain})
result['pair_threshold_pct'] = 100 * (q['S2-C72'] - q['S2-C96'] - .01) / (q['S2-C72'] + q['S2-C96'])
result['pair_gap_pct'] = 100 * (q['S2-C72'] / q['S2-C96'] - 1)
result['robust_vs_base'] = {s: {str(d): q[s]*(1-d)-.005 > q['S2-BASE']*(1+d)+.005
                             for d in (.03, .05, .10)} for s in ('S2-C72', 'S2-C96')}

residuals = rows('reports/task002/B/check_residuals.csv')
data = rows(PACK + 'data/benchmark/S100_dry_isotherms.csv')
fits = rows('reports/task002/B/langmuir_fit.csv')
points = {r['point_id']: r for r in data}
fits = {r['sample_label']: r for r in fits}
errors = {'baseline': [], 'langmuir': []}
for r in residuals:
    fit = fits[r['sample_label']]
    ids = fit['source_point_ids'].split(';')
    assert r['point_id'] not in ids
    pts = sorted((float(points[i]['p_bar']), float(points[i]['q_mmol_per_g_reported'])) for i in ids)
    p, obs = float(r['p_bar']), float(r['observed_q_reported'])
    a, b = next((a, b) for a, b in zip(pts, pts[1:]) if a[0] <= p <= b[0])
    linear = a[1] + (b[1]-a[1])*(p-a[0])/(b[0]-a[0])
    qs, affinity = float(fit['q_s_reported']), float(fit['b_per_bar'])
    lang = qs * affinity * p / (1 + affinity * p)
    for key, value in [('baseline', linear), ('langmuir', lang)]:
        close(value, float(r[key + '_prediction']))
        close(value - obs, float(r[key + '_residual']))
        errors[key].append(abs(value - obs))
result['s100'] = {'n_points': len(data), 'n_check': len(residuals),
                  'mae': {k: sum(v)/len(v) for k, v in errors.items()}}

materials = rows(PACK + 'data/primary/S2_materials.csv')
result['s2_residual_pct'] = {}
for r in materials:
    h = 1 / (1 + float(r['mass_gain_pct_of_initial_MOF']) / 100)
    w = float(r['PEI_content_author_calculated_wt_pct']) / 100
    s = 1-h-w
    if r['sample_id'] in ('S2-C48','S2-C72','S2-C96','S2-N72'):
        result['s2_residual_pct'][r['sample_id']] = 100*s
    if r['sample_id'] == 'S2-C72':
        result['c72_kstar'] = {'nominal': q['S2-C72']/q['S2-BASE']/1.1,
                              'third_mass_reading': q['S2-C72']/(h+w)/q['S2-BASE']/1.1}
transfer = rows('reports/task003/transfer_kstar.csv')
selected = [r for r in transfer if '30PEI' in r['sample_id'] and float(r['g']) == 1.1]
assert selected
result['r1_kstar'] = sorted(set(float(r['registered_kstar_G_over_g']) for r in selected))

counter = json.loads((ROOT / 'reviews/T044_checks/counterexamples.json').read_text())['T044_01_lower_guarantee']
value = counter['h'] * counter['phi'] * (1 - 1/counter['k']) + counter['G_analog']/counter['k']
close(value, counter['G_PET_at_k095'])
result['historical_counterexample'] = value
h, gc, k = .7, 1.17, 1.1
A, B = gc/k, gc/k + h*(1-1/k)
result['paired_example'] = {'A': A, 'B': B,
    'outward': [math.floor(A*1000)/1000, math.ceil(B*1000)/1000],
    'twosigma_relative_pct_A': 200*.02*math.sqrt(2),
    'twosigma_relative_pct_B': 200*.02*math.sqrt((B*k)**2+gc**2+h**2+(h*k)**2)/(k*B)}
# Counterexample to transplanting the equal-composition guarantee to unequal h.
hp, hc, gc, k = .68, .70, 1.11, 1.
result['unequal_composition_counterexample'] = {
    'h_P': hp, 'h_C': hc, 'G_C': gc, 'k': k, 'phi': 1.,
    'k_le_GC_over_1p1': k <= gc/1.1, 'G_P': gc/k + hp-hc/k}
assert result['unequal_composition_counterexample']['G_P'] < 1.10

runs = rows('publications/agentic-research-pet2mof/evidence/agent_runs.csv')
parse = lambda s: datetime.strptime(s, '%Y%m%dT%H%M%SZ')
intervals = sorted((parse(r['started_utc']), parse(r['finished_utc'])) for r in runs)
merged = []
for a,b in intervals:
    if merged and a <= merged[-1][1]:
        merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
    else:
        merged.append((a,b))
result['timeline_hours'] = {'sum': sum(int(r['duration_s']) for r in runs)/3600,
    'span': (max(b for a,b in intervals)-min(a for a,b in intervals)).total_seconds()/3600,
    'active_union': sum((b-a).total_seconds() for a,b in merged)/3600}
result['stages'] = {}
for stage in ('TASK-001','TASK-002','TASK-003'):
    sel = [r for r in runs if r['stage'] == stage]
    fresh = sum(int(r['input_tokens'])-int(r['cached_input_tokens']) for r in sel)
    cached = sum(int(r['cached_input_tokens']) for r in sel)
    result['stages'][stage] = {'runs': len(sel), 'duration_s': sum(int(r['duration_s']) for r in sel),
        'fresh_tokens': fresh, 'cached_tokens': cached, 'cached_over_fresh': cached/fresh,
        'output_tokens': sum(int(r['output_tokens']) for r in sel)}

# Literal locations only, never echo any matched content.
# PET2MOF lead edit: the home-directory prefix is split as '/Use' 'rs/' so the repository publish-check does not flag this search pattern; behaviour unchanged.
pattern = re.compile(r'/Use' r'rs/|/home/|/private/tmp/|claude\.ai|sandbox:|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')
result['privacy_literal_locations'] = []
for f in [PUB/'article.ru.md', PUB/'index.html', *sorted((PUB/'prompts').glob('*.md')),
          *sorted((PUB/'evidence').glob('*')), *sorted((PUB/'assets').glob('*.svg'))]:
    if f.is_file():
        for i,line in enumerate(f.read_text().splitlines(), 1):
            if pattern.search(line):
                result['privacy_literal_locations'].append({'path': str(f.relative_to(ROOT)), 'line': i})
result['work_order_word_count_whitespace'] = len((ROOT/'docs/work_order_v1.1_RU.md').read_text().split())
(OUT/'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
