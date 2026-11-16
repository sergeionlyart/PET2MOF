#!/usr/bin/env python3
"""Offline, page-specific extraction and rendering for the T006 pilot."""
import hashlib
import json
import sys
import subprocess
import time
from pathlib import Path

import pymupdf
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pet2mof.ocr.cache import RawCache, cache_key
from pet2mof.ocr.local import extract_local

ROOT = Path(__file__).resolve().parents[2]
SELECTION = {
    "S100": ("data/raw/pdf/S100_SI.pdf", [2, 3, 4, 5, 7, 9]),
    "S106": ("data/raw/pdf/S106.pdf", [3, 4, 5, 6, 7]),
    "S105": ("data/raw/pdf/S105_T006.pdf", [8, 9]),
    "S113": ("data/raw/pdf/S113_T006.pdf", [6, 7, 9]),
    "S103": ("data/raw/pdf/S103_T006.pdf", [2, 3]),
    "S102": ("data/raw/pdf/S102_SI_T006.pdf", [5]),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    registry = {s["source_id"]: s for s in yaml.safe_load((ROOT / "sources/registry.yaml").read_text())}
    renders = ROOT / "private/renders"
    renders.mkdir(parents=True, exist_ok=True)
    manifest = []
    engines = []
    tsv_records = []
    for sid, (filename, numbers) in SELECTION.items():
        path = ROOT / filename
        digest = sha(path)
        doc = pymupdf.open(path)
        for n in numbers:
            started = time.monotonic()
            page = doc[n - 1]
            rid = f"T006-{sid}-p{n:02d}"
            image = renders / f"{sid}_p{n:02d}.png"
            page.get_pixmap(dpi=200).save(image)
            result = extract_local(path, [n], method="pymupdf")
            key = cache_key(path, [n], engine="pymupdf", version=result["version"],
                            params=result["params"], input_sha256=digest)
            cache = RawCache(ROOT)
            try:
                raw = cache.write_once(key, result)
            except FileExistsError:
                raw = cache.path(key)
            (renders / f"{sid}_p{n:02d}.txt").write_text(result["pages"][0]["text"])
            printed = f"S{n}" if sid in {"S100", "S102"} else str(n - 1 if sid == "S106" else n)
            manifest.append(dict(extraction_id=rid, source_id=sid, input=filename,
                                 input_sha256=digest, pdf_page=n, printed_page=printed,
                                 doi=registry[sid]["doi"], role=registry[sid]["role_candidate"],
                                 render=str(image.relative_to(ROOT)), render_sha256=sha(image),
                                 dpi=200, page_size_pt=list(page.rect)[2:],
                                 image_size_px=[page.get_pixmap(dpi=200).width, page.get_pixmap(dpi=200).height],
                                 raw_response_ref=str(raw.relative_to(ROOT)),
                                 quality=result["pages"][0]["quality"],
                                 text_chars=len(result["pages"][0]["text"]),
                                 elapsed_s=round(time.monotonic() - started, 4)))
            methods=["pdftotext"]
            if (sid,n) in {("S100",7),("S106",6),("S113",9)}:
                methods.append("tesseract")
            for method in methods:
                start=time.monotonic()
                auxiliary=extract_local(path,[n],method=method,workdir=renders)
                aux_key=cache_key(path,[n],engine=method,version=auxiliary["version"],params=auxiliary["params"],input_sha256=digest)
                try:
                    aux_raw=cache.write_once(aux_key,auxiliary)
                except FileExistsError:
                    aux_raw=cache.path(aux_key)
                (renders/f"{sid}_p{n:02d}.{method}.txt").write_text(auxiliary["pages"][0]["text"])
                engines.append(dict(extraction_id=rid,engine=method,version=auxiliary["version"],
                                    raw_response_ref=str(aux_raw.relative_to(ROOT)),elapsed_s=round(time.monotonic()-start,4)))
                if method=="tesseract":
                    image300=renders/f"{sid}_p{n:02d}_300.png"
                    page.get_pixmap(dpi=300).save(image300)
                    start=time.monotonic()
                    run=subprocess.run(["tesseract",str(image300),"stdout","-l","eng","--dpi","300","tsv"],check=True,capture_output=True)
                    tsv_digest=hashlib.sha256(run.stdout).hexdigest()
                    raw_tsv=ROOT/"private/ocr_cache/raw"/(tsv_digest+".tsv")
                    if not raw_tsv.exists():
                        with raw_tsv.open("xb") as stream:stream.write(run.stdout)
                    tsv_records.append(dict(extraction_id=rid,input_render=str(image300.relative_to(ROOT)),
                                            render_sha256=sha(image300),engine="tesseract-tsv",
                                            raw_response_ref=str(raw_tsv.relative_to(ROOT)),elapsed_s=round(time.monotonic()-start,4)))
    target = ROOT / "data/extraction/benchmark/pages.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    target.with_name("engines.json").write_text(json.dumps(engines,indent=2)+"\n")
    target.with_name("tesseract_regions.json").write_text(json.dumps(tsv_records,indent=2)+"\n")
    print(f"Rendered and extracted {len(manifest)} pages; PyMuPDF {pymupdf.VersionBind}")


if __name__ == "__main__":
    main()
