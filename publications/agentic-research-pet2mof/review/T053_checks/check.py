import csv, json, re, subprocess, hashlib, tempfile
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
R=Path.cwd(); P=R/'publications/agentic-research-pet2mof'; out={}
def run(args):
 p=subprocess.run(args,capture_output=True,text=True); return {'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def rows(p):
 with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
required='index.html article.ru.md article.metadata.json assets prompts evidence/chronology.csv evidence/claims.csv evidence/prompts_manifest.csv evidence/assets_manifest.csv evidence/source_versions.json evidence/repo_cleanup.md evidence/site_integration.md review/editorial_review.md review/html_check.md review/screenshots README_RU.md'.split()
out['package']={p:(P/p).exists() for p in required}
shas={'66bae26af9970c3142b72d25031c844b5461708f','1558433614619e04102989d6b6f1479c50f364ce','70685dc686ce22505b303a60920980a02772f019'}
class Parser(HTMLParser):
 def __init__(self): super().__init__(); self.ids=[]; self.links=[]; self.resources=[]; self.css=[]; self.instyle=False
 def handle_starttag(self,t,attrs):
  a=dict(attrs); self.ids += [a['id']] if 'id' in a else []
  for k in ('href','src'):
   if k in a:self.links.append((t,k,a[k],self.getpos()[0])); self.resources += [(t,k,a[k],self.getpos()[0])] if t in ('script','link','img') and urlsplit(a[k]).scheme in ('http','https') else []
  if 'style' in a:self.css.append(a['style'])
  if t=='style':self.instyle=True
 def handle_endtag(self,t):
  if t=='style':self.instyle=False
 def handle_data(self,d):
  if self.instyle:self.css.append(d)
h=(P/'index.html').read_text(); md=(P/'article.ru.md').read_text(); page=Parser();page.feed(h)
gh=re.compile(r'https://github\.com/sergeionlyart/PET2MOF/(?:blob|tree)/[^\s)\]"<>]+')
links=[]
for name,s in [('article.ru.md',md),('index.html',h)]:
 for m in gh.finditer(s):
  u=m.group().rstrip('.,'); parts=urlsplit(u).path.split('/',5); sha=parts[4]; path=unquote(parts[5]); x=run(['git','cat-file','-e',sha+':'+path]);links.append({'file':name,'line':s.count('\n',0,m.start())+1,'url':u,'allowed':sha in shas,'exists':x['exit']==0})
issues=[]
for tag,k,u,line in page.links:
 p=urlsplit(u)
 if u.startswith('#') and unquote(u[1:]) not in page.ids:issues.append([line,u,'missing anchor'])
 elif not p.scheme and not p.netloc and not u.startswith('#') and not (P/unquote(p.path)).exists():issues.append([line,u,'missing local'])
md_links=re.sub(r'```[^\n]*\n.*?\n```', lambda m: re.sub(r'[^\n]', ' ', m.group()), md, flags=re.S)
for m in re.finditer(r'(?<!!)\[[^\]]*\]\((#[^\s)]+|[^\s):]+)\)',md_links):
 u=m.group(1); line=md.count('\n',0,m.start())+1
 if u.startswith('#') and unquote(u[1:]) not in page.ids:issues.append(['md',line,u,'missing anchor'])
 elif not u.startswith('#') and not (P/unquote(urlsplit(u).path)).exists():issues.append(['md',line,u,'missing local'])
out['links']={'github_count':len(links),'github_failures':[x for x in links if not x['allowed'] or not x['exists']],'github':links,'local_or_anchor_failures':issues,'external_resources':page.resources,'css_external':re.findall(r'(?:url\(\s*[\"\']?\s*(?:https?:)?//[^)]*|@import\s+[^;]+)', '\n'.join(page.css),re.I)}
claims=[]
for row in rows(P/'evidence/claims.csv'):
 paths=[]
 for raw in row['source_path'].split(';'):
  path=raw.strip().split(' §')[0].split(' (')[0].split(' #')[0].strip().rstrip('/')
  if path.startswith(('git ','run ')) or path in ('—',''): paths.append({'raw':raw,'kind':'nonpath'});continue
  p=run(['git','cat-file','-e',row['commit']+':'+path]);paths.append({'path':path,'exists':p['exit']==0})
 claims.append({'id':row['claim_id'],'claim':row['claim'],'commit':row['commit'],'paths':paths,'status':'not_checkable_mechanically','reason':'Составное утверждение требует смысловой проверки или вычисления; наличие файла не подтверждает его содержание.'})
checks={
 'C10':('reports/final_report.md',['31 запись; полных сравнений 0, условных 0, `not_testable` 31']),
 'C14':('reports/task002/A/nominal.csv',['S2-BASE,2.67','S2-C72,3.26,22.097','S2-C96,3.15,17.977']),
 'C19':('reports/task003/final_report.md',['BET 874.6 (PET) против 873.9']),
}
for c in claims:
 if c['id'] in checks:
  path,terms=checks[c['id']]; blob=run(['git','show',c['commit']+':'+path])['stdout']; lines=blob.splitlines(); hits=[next((i for i,line in enumerate(lines,1) if term in line),None) for term in terms]; c['evidence']={'path':path,'terms':terms,'lines':hits}; c['status']='confirmed' if all(hits) else 'not_checkable_mechanically'; c['reason']='Дословное совпадение значений в указанном источнике' if all(hits) else 'Не все части найдены дословно'
out['claims']=claims
fig=[]
for row in rows(P/'evidence/assets_manifest.csv'):
 num=row['figure_no']; pattern=r'!\[([^\]]+)\]\(([^)]+)\)\n\*(Рис\. '+re.escape(num)+r'\..*?)\*';m=re.search(pattern,md)
 fig.append({'id':row['asset_id'],'exists':(P/row['file']).is_file(),'article_line':md.count('\n',0,m.start())+1 if m else None,'alt':m.group(1) if m else None,'caption':m.group(3) if m else None,'manifest_caption':row['caption_ru'],'sources':row['data_sources']})
out['figures']=fig
prompts=rows(P/'evidence/prompts_manifest.csv'); block=md.split('## Промпты, которые двигали работу',1)[1].split('\n## ',1)[0]; entries=[]
for m in re.finditer(r'### (P\d+)\.[^\n]*\n.*?```text\n(.*?)\n```',block,re.S):
 id,quote=m.group(1),m.group(2);row=next(x for x in prompts if x['prompt_id']==id);src=run(['git','show',row['commit']+':'+row['source_path']]); entries.append({'id':id,'article_line':md.count('\n',0,md.index(m.group(0)))+1,'manifest':quote in row['excerpt_1'] or quote in row['excerpt_2'],'source':quote in src['stdout'],'source_exit':src['exit']})
out['prompts']=entries
out['excerpt_command']=run(['python3.12','-I',str(P/'evidence/check_excerpts.py')]);out['check_command']=run(['python3.12','-I',str(P/'tools/check.py')])
with tempfile.TemporaryDirectory() as d:
 target=Path(d)/'index.html'; out['build_command']=run(['python3.12','-I',str(P/'tools/build.py'),'--output',str(target)]);out['build_hash']={'original':hashlib.sha256((P/'index.html').read_bytes()).hexdigest(),'built':hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None}
out['scientific_diff']=run(['git','diff','--stat','70685dc686ce22505b303a60920980a02772f019','--','reports','data','runs','src','scripts','configs','results','holdout','Makefile','pyproject.toml','uv.lock'])
(P/'review/T053_checks/results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
