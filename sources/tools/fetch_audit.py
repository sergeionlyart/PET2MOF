"""Fetch public source files with curl TLS verification; preserve bytes and hashes."""
import csv,hashlib,json,subprocess,concurrent.futures
from pathlib import Path
DATE='2026-11-16'
DOIS={'S2':'10.1021/acsomega.8b02319','S3':'10.1039/D5SU00463B','S100':'10.1021/acs.iecr.5b03517','S101':'10.1016/j.ces.2019.03.053','S102':'10.1021/acs.langmuir.1c01149','S103':'10.1038/s42004-022-00742-z','S104':'10.1039/D4TA06814A','S105':'10.3390/ma11040589','S106':'10.1016/j.micromeso.2021.111555','S107':'10.1039/C4CC04945D','S108':'10.1016/j.cej.2014.04.063','S109':'10.1016/j.jcou.2017.03.008','S110':'10.3390/en15031075','S111':'10.1021/acsanm.5c05631','S112':'10.2139/ssrn.5123041'}
URLS={
'S2':('https://pmc.ncbi.nlm.nih.gov/articles/PMC6648867/','html'),
'S3':('https://pubs.rsc.org/en/content/articlehtml/2026/su/d5su00463b','html'),
'S103':('https://pmc.ncbi.nlm.nih.gov/articles/PMC9814431/','html'),
'S104':('https://pubs.rsc.org/en/content/articlehtml/2025/ta/d4ta06814a','html'),
'S105':('https://pmc.ncbi.nlm.nih.gov/articles/PMC5951473/','html'),
'S106':('https://pure.tue.nl/ws/portalfiles/portal/193896004/1_s2.0_S1387181121006818_main_1_.pdf','pdf'),
'S110':('https://www.mdpi.com/1996-1073/15/3/1075','html'),
'S100_SI':('https://pstorage-acs-6854636.s3.amazonaws.com/3743113/ie5b03517_si_001.pdf','pdf')}
def fetch(t):
 sid,url,path=t
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 r=subprocess.run(['curl','-L','--fail','--max-time','50','-sS',url,'-o',str(p)],capture_output=True)
 if r.returncode: return {'source_id':sid,'url':url,'status':f'curl_exit_{r.returncode}'}
 b=p.read_bytes()
 if 'crossref' in str(p):
  try:
   m=json.loads(b)['message']; print(sid,m['DOI'],m.get('title'),m.get('published'),flush=True)
  except Exception: return {'source_id':sid,'url':url,'status':'invalid_json'}
 return {'source_id':sid,'url':url,'accessed':DATE,'path':path,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'status':'downloaded_unvalidated'}
if __name__=='__main__':
 tasks=[(sid,'https://api.crossref.org/works/'+doi,f'sources/metadata/{sid}.crossref.json') for sid,doi in DOIS.items()]
 tasks += [(sid,url,f'data/raw/{typ}/{sid}.{typ}') for sid,(url,typ) in URLS.items()]
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as e: rows=list(e.map(fetch,tasks))
 with open('sources/downloads_manifest.csv','w') as f:
  w=csv.DictWriter(f,fieldnames=['source_id','url','accessed','path','sha256','bytes','status']);w.writeheader();w.writerows(rows)
 for r in rows: print(r['source_id'],r['status'],r.get('bytes'))
