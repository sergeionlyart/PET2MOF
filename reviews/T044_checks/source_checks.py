"""Check primary-source cells, archive hashes and make source-table renderings.

Uses the supplied JATS/DOCX directly (not the lead's reports).
Renders are reconstructed source tables, not claims of original DOCX pagination.
"""
import csv
import hashlib
import html
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
sources = [ROOT/'data/raw/html/S2.xml', ROOT/'data/raw/html/S100_SI.text.txt',
    ROOT/'data/raw/task003/si_S1385894723040809_mmc1.docx',
    ROOT/'data/raw/task003/si_S0926337326013524_mmc1.docx',
    OUT/'source_downloads/HP20.xml', OUT/'source_downloads/stoichiometry.xml', OUT/'source_downloads/S100_SI.pdf']
checks=[]
tables=[]


def verify(name,a,b):
    checks.append(dict(name=name,actual=a,expected=b,passed=abs(float(a)-float(b))<1e-9))


def load(path):
    return list(csv.DictReader(path.open()))


def docx_tables(path):
    with zipfile.ZipFile(path) as z:
        r=ET.fromstring(z.read('word/document.xml'))
    return [[[''.join(t.text or '' for t in c.findall('.//w:t',NS)) for c in row.findall('w:tc',NS)]
             for row in table.findall('w:tr',NS)] for table in r.findall('.//w:tbl',NS)]


s2 = ET.parse(sources[0]).getroot()
raws2=[]
for tid in ('tbl1','tbl2'):
    el=s2.find(f'.//table-wrap[@id="{tid}"]')
    rows=[[''.join(c.itertext()) for c in tr] for tr in el.findall('.//tbody/tr')]
    raws2.append(rows)
    header = (['sample','PEI feed / MOF %','PEI / total feed %','W %','N %','PEI_exp %','BET','Vp','Dp']
              if tid=='tbl1' else ['sample','dry q','moist q','alpha','q_mix','q_0.15bar','Qdes'])
    tables.append((f'S2 {tid}: source JATS cells; concise column headings', [header]+rows))
pack=ROOT/'data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary'
mat=load(pack/'S2_materials.csv')
dry={r['sample_id']:r['q_CO2_dry_mmol_g'] for r in load(pack/'S2_dry_CO2.csv')}
for source,row in zip(raws2[0],mat):
    for i,col in [(1,'PEI_feed_pct_of_initial_MOF'),(2,'PEI_feed_pct_of_total_feed'),
                  (3,'mass_gain_pct_of_initial_MOF'),(4,'N_elemental_wt_pct'),(5,'PEI_content_author_calculated_wt_pct')]:
        verify('S2 '+row['sample_id']+' '+col,source[i],row[col])
for source,sample in zip(raws2[1],['S2-BASE','S2-C48','S2-C72','S2-N72','S2-C96','S2-I96']):
    verify('S2 dry '+sample,source[1],dry[sample])

s3=docx_tables(sources[2]);s6=docx_tables(sources[3])
src3=load(ROOT/'data/task003/extracted/SRC03_tables.csv')
src6=load(ROOT/'data/task003/extracted/SRC06_tables.csv')


def cell(rows,label,quantity,locator):
    found=[r for r in rows if r['sample_label']==label and r['quantity']==quantity and r['locator']==locator]
    assert len(found)==1,(label,quantity,locator)
    return found[0]['value']


for row in s6[0][1:4]:
    for i,quantity in [(1,'PET mass'),(2,'BDC yield')]:
        verify('SRC06 S1 '+row[0]+' '+quantity,row[i].split()[0],cell(src6,row[0],quantity,'Table S1'))
for row in s6[1][1:]:
    verify('SRC06 S2 '+row[0],row[4].strip('%'),cell(src6,row[0],'MOF conversion','Table S2'))
for row in s6[2][1:]:
    verify('SRC06 S3 '+row[0],row[3],cell(src6,row[0],'BDC-NH2 fraction by NMR','Table S3'))
for row in s6[3][1:]:
    verify('SRC06 S4 '+row[0],row[3],cell(src6,row[0],'x','Table 4'))
quantities=['BET area','Langmuir area','t-plot micropore area','t-plot micropore volume',
            'cumulative BJH adsorption volume','total pore volume','HK pore size']
for row in s3[2][2:]:
    for x,quantity in zip(row[1:],quantities):
        verify('SRC03 S2 '+row[0]+' '+quantity,x,cell(src3,row[0],quantity,'Table S2'))
for i in range(4): tables.append((f'SRC06 original DOCX table {i+1}',s6[i]))
tables.append(('SRC03 original DOCX Table S2 (headings normalized from merged cells)',
               [['sample','BET area','Langmuir','micropore area','micropore V','BJH V','total V','HK size']]+s3[2][2:]))

parsed=[]
for p in sources[4:6]:
    r=ET.parse(p).getroot()
    parsed.append(dict(file=str(p.relative_to(ROOT)),title=''.join(r.find('.//article-title').itertext()),
                       dois=[e.text for e in r.findall('.//article-id[@pub-id-type="doi"]')]))

# Source-derived arithmetic, not measurements of new specimens.
arithmetic=dict(SRC03_linkers_per_Zr6=(39.75/164)/(40.72/123)*6,
    SRC06_f50=1.13/(1.13+.96), SRC06_f75=1.38/(1.38+.34),
    SRC06_BDC_recovery_mass_ratios=[1.77/2.11,1.66/2.05,1.64/1.97],
    S2_primary_fraction_conditional=12.8/32.9, lower_ceiling_conditional=.5*12.8/32.9,
    HP20_apparent_eta=4.35/(.5*1000/43.069))

render_html='''<html><body><p>Primary-source table cells, independently extracted by T044.
Not original DOCX page layout. See source hashes in source_checks.json.</p>'''
for title,rows in tables:
    render_html+='<h2>'+html.escape(title)+'</h2><table border="1">'
    for row in rows:
        render_html+='<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>'
    render_html+='</table>'
render_html+='</body></html>'
(OUT/'rendered/source_tables.html').write_text(render_html)
import pymupdf
story=pymupdf.Story(html=render_html,user_css='body {font-size:9pt} td {padding:3pt} h2 {font-size:12pt}')
writer=pymupdf.DocumentWriter(str(OUT/'rendered/source_tables.pdf'))
more=1
while more:
    page=pymupdf.Rect(0,0,842,595);dev=writer.begin_page(page)
    more,_=story.place(page+ (30,30,-30,-30))
    story.draw(dev);writer.end_page()
writer.close()
with pymupdf.open(OUT/'rendered/source_tables.pdf') as doc:
    for i,page in enumerate(doc):
        page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(OUT/f'rendered/source_tables_{i+1}.png')

result=dict(checks=checks,failures=sum(not x['passed'] for x in checks),arithmetic=arithmetic,
    source_xml_identity=parsed,sources=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sources],
    render_limitation='Original DOCX to PDF conversion failed (LibreOffice exit 1); tables rendered from original XML cells, not original pagination.')
(OUT/'source_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(checks=len(checks),failures=result['failures'],arithmetic=arithmetic),indent=2))
raise SystemExit(bool(result['failures']))
