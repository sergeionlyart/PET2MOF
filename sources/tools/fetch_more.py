import sys,csv,concurrent.futures,json
sys.path.insert(0,'sources/tools')
from fetch_audit import fetch
jobs=[
('S100','https://api.crossref.org/works/10.1021%2Facs.iecr.5b03517','sources/metadata/S100.crossref.json'),
('S102','https://api.crossref.org/works/10.1021%2Facs.langmuir.1c01149','sources/metadata/S102.crossref.json'),
('S109','https://api.crossref.org/works/10.1016%2Fj.jcou.2017.03.008','sources/metadata/S109.crossref.json'),
('S111','https://api.crossref.org/works/10.1021%2Facsanm.5c05631','sources/metadata/S111.crossref.json'),
('S2_XML','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6648867/fullTextXML','data/raw/html/S2.xml'),
('S103_XML','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9814431/fullTextXML','data/raw/html/S103.xml'),
('S105_XML','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5951473/fullTextXML','data/raw/html/S105.xml'),
('S3_PDF','https://pubs.rsc.org/en/content/articlepdf/2025/su/d5su00463b','data/raw/pdf/S3.pdf'),
('S108_PDF','https://nottingham-repository.worktribe.com/OutputFile/733547','data/raw/pdf/S108.pdf'),
('S110_HTML','https://www.mdpi.com/1996-1073/15/3/1075/htm','data/raw/html/S110.html')]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as e: rows=list(e.map(fetch,jobs))
with open('sources/downloads_manifest.csv','a') as f:
 w=csv.DictWriter(f,fieldnames=['source_id','url','accessed','path','sha256','bytes','status']);w.writerows(rows)
for r in rows: print(r['source_id'],r['status'],r.get('bytes'))
