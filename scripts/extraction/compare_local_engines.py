#!/usr/bin/env python3
"""Compare the same annotated fields, using region-specific local outputs."""
import csv
import hashlib
import io
import json
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/extraction/benchmark"


def outcome(field, text):
    if field["category"]=="relationships":
        return None,"omission"
    expected=field["expected"]
    pattern=re.escape(expected)
    if field["category"]=="numbers":
        pattern=r"(?<![\d.])"+pattern+r"(?!\d)(?!\.\d)"
    match=re.search(pattern,text)
    if match:
        return match.group(),"correct"
    alt=field["lossy_alternative"]
    if alt and alt in text:
        return alt,"mismatch"
    return None,"omission"


def main():
    fields=json.loads((DATA/"reference_fields.json").read_text())
    pages={p["extraction_id"]:p for p in json.loads((DATA/"pages.json").read_text())}
    tsv={p["extraction_id"]:p for p in json.loads((DATA/"tesseract_regions.json").read_text())}
    results=[]
    region_cache={}
    durations=defaultdict(float)
    for field in fields:
        eid=field["extraction_id"]
        page=pages[eid]
        a,b,c,d=field["region_norm"]
        width,height=page["page_size_pt"]
        key=(eid,tuple(field["region_norm"]))
        if key not in region_cache:
            start=time.monotonic()
            run=subprocess.run(["pdftotext","-layout","-f",str(page["pdf_page"]),"-l",str(page["pdf_page"]),
                                "-r","72","-x",str(int(a*width)),"-y",str(int(b*height)),
                                "-W",str(int((c-a)*width)),"-H",str(int((d-b)*height)),
                                str(ROOT/page["input"]),"-"],check=True,capture_output=True,text=True)
            region_cache[key]=run.stdout
            durations['pdftotext']+=time.monotonic()-start
        texts={"pdftotext":region_cache[key]}
        if eid in tsv:
            words=list(csv.DictReader(io.StringIO((ROOT/tsv[eid]['raw_response_ref']).read_text()),delimiter="\t"))
            lines=defaultdict(list)
            for word in words:
                if not word['text'].strip():continue
                x=(int(word['left'])+int(word['width'])/2)/(width*300/72)
                y=(int(word['top'])+int(word['height'])/2)/(height*300/72)
                if a<=x<=c and b<=y<=d:
                    lines[(word['block_num'],word['par_num'],word['line_num'])].append(word['text'])
            texts['tesseract']="\n".join(" ".join(line) for line in lines.values())
        for engine,text in texts.items():
            candidate,status=outcome(field,text)
            results.append(dict(field_id=field['field_id'],extraction_id=eid,category=field['category'],
                                expected=field['expected'],engine=engine,candidate=candidate,result=status,region_text=text))
    (DATA/'engine_field_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n")
    summary={}
    for engine in ['pdftotext','tesseract']:
        summary[engine]={}
        for category in ['numbers','units','symbols','relationships']:
            counts=Counter(r['result'] for r in results if r['engine']==engine and r['category']==category)
            summary[engine][category]=dict(total=sum(counts.values()),**{k:counts[k] for k in ['correct','omission','mismatch']})
    summary['region_pdftotext_elapsed_s']=round(durations['pdftotext'],4)
    (DATA/'engine_summary.json').write_text(json.dumps(summary,indent=2)+"\n")
    # Immutable outputs for the region extraction as well as the full-page raw outputs.
    import sys
    sys.path.insert(0,str(ROOT/'src'))
    from pet2mof.ocr.cache import RawCache
    payload=json.dumps(results,ensure_ascii=False).encode()
    cache=RawCache(ROOT)
    try:cache.write_once(hashlib.sha256(payload).hexdigest(),results)
    except FileExistsError:pass
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
