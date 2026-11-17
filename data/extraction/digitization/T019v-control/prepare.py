#!/usr/bin/env python3
"""Prepare independent native images and page renders from local primary PDFs.
Optional --fetch-s2 requests the public Europe PMC JATS endpoint (no credentials).
"""
import argparse,hashlib,json,urllib.request
from pathlib import Path
import fitz
OUT=Path('data/extraction/digitization/T019v-control');RAW=Path('private/T019v')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 assert fitz.VersionBind=='1.27.2.3','Use PyMuPDF 1.27.2.3 for byte-identical native PNG serialization; fail before writing.'
 parser=argparse.ArgumentParser();parser.add_argument('--fetch-s2',action='store_true');args=parser.parse_args();RAW.mkdir(parents=True,exist_ok=True)
 expected=json.loads((OUT/'source_images.json').read_text());hashes={x['pdf']:x['pdf_sha256'] for x in expected}
 actual=[]
 for name,pages in [('S113_T019',[9]),('S103_T019',[3]),('S102_T019',[5]),('S117_SI_T019',[25])]:
  p=Path('data/raw/pdf')/(name+'.pdf');assert sha(p)==hashes[str(p)],str(p)+' primary PDF hash mismatch'
  d=fitz.open(p)
  (RAW/(name+'.txt')).write_text('\n'.join(f'\nPAGE {i+1}\n'+x.get_text() for i,x in enumerate(d)))
  for page in d:
   for n,img in enumerate(page.get_images(full=True)):
    pix=d.extract_image(img[0]);w,h=pix['width'],pix['height']
    if w>700 and h>250:
     dest=RAW/f'{name}-p{page.number+1}-im{n}.{pix["ext"]}';dest.write_bytes(pix['image'])
     actual.append({'pdf':str(p),'pdf_sha256':sha(p),'page':page.number+1,'image':str(dest),'size':[w,h],'sha256':sha(dest)})
  for page in pages:d[page-1].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(RAW/f'{name}-page{page}.png')
 assert actual==expected,'native-image manifest changed'
 xml=RAW/'S2.xml';expected_xml='0abfc9634b9a3192be44894af38d20eb9aa4875cf602f38e4f39b19c36fcd574'
 if args.fetch_s2:
  content=urllib.request.urlopen('https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6648867/fullTextXML',timeout=45).read()
  assert hashlib.sha256(content).hexdigest()==expected_xml,'primary JATS changed; do not overwrite frozen source'
  xml.write_bytes(content)
 if xml.exists():assert sha(xml)==expected_xml
 print('Primary PDF hashes, extracted native images and source-page renders verified.')
if __name__=='__main__':main()
