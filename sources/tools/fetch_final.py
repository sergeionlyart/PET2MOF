import sys,csv,concurrent.futures
sys.path.insert(0,'sources/tools')
from fetch_audit import fetch
jobs=[
('S113','https://api.crossref.org/works/10.3390%2Fmembranes10070154','sources/metadata/S113.crossref.json'),
('S114','https://api.crossref.org/works/10.1039%2FC5TA05997F','sources/metadata/S114.crossref.json'),
('S115','https://api.crossref.org/works/10.1016%2Fj.cej.2023.145349','sources/metadata/S115.crossref.json'),
('S113_XML','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7407110/fullTextXML','data/raw/html/S113.xml'),
('S108_PDF','https://files.core.ac.uk/download/pdf/96620597.pdf','data/raw/pdf/S108.pdf'),
('S3_HTML','https://pubs.rsc.org/en/content/articlehtml/2025/su/d5su00463b','data/raw/html/S3.html'),
('S104_PDF','https://pubs.rsc.org/en/content/articlepdf/2024/ta/d4ta06814a','data/raw/pdf/S104.pdf'),
('S110_HTML','https://www.mdpi.com/1996-1073/15/3/1075/xml','data/raw/html/S110.xml'),
('S107_PDF','https://pubs.rsc.org/en/content/getauthorversionpdf/C4CC04945D','data/raw/pdf/S107.pdf')]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as e: rows=list(e.map(fetch,jobs))
with open('sources/downloads_manifest.csv','a') as f:
 w=csv.DictWriter(f,fieldnames=['source_id','url','accessed','path','sha256','bytes','status']);w.writerows(rows)
for r in rows: print(r['source_id'],r['status'],r.get('bytes'))
