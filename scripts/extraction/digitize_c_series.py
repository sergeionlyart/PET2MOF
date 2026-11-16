#!/usr/bin/env python3
"""Offline T011 marker extraction from native embedded images (no curve sampling).

Run with UV_CACHE_DIR=$PWD/.uv-cache uv run --locked --no-sync python
scripts/extraction/digitize_c_series.py. Originals and overlays remain private.
Pixel coordinates below calibrate axes/ROIs, never supply uptake measurements.
"""
import csv
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pymupdf
import scipy
import yaml
import PIL
from PIL import Image, ImageDraw
from scipy import ndimage, signal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pet2mof.extraction.digitize import AxisCalibration, validate_project

DIG = ROOT / "data/extraction/digitization"
PRIVATE = ROOT / "private/renders"
RECORDS = ROOT / "data/extraction/records"
MATERIALS = ["UiO-66", "UiO-66-NH2", "UiO-66/GO", "UiO-66-NH2/GO"]
# Template windows contain a single printed symbol, not assigned isotherm values.
TEMPLATES = {
    "S105-Fig8A": [(344,113,372,140), (342,203,373,234), (339,308,376,340), (339,409,376,442)],
    "S105-Fig8B": [(377,133,405,160), (375,223,407,254), (373,327,409,359), (373,429,409,461)],
    "S105-Fig8C": [(332,191,359,218), (330,273,361,304), (327,375,364,407), (327,469,364,501)],
    "S105-Fig9": [(495,258,525,287), (494,357,527,390), (491,480,530,513), (491,590,530,624)],
    "S106-Fig4": [(323,496,345,515), (447,357,466,375), (757,186,774,202)],
}
# Native PDF image coordinates, top-left origin. Each rectangle removes only a legend.
PANELS = [
    dict(id="S105-Fig8A", page=8, image=0, crop=(0, 0, 2068, 1660),
         x=(232.5, 0, 1968.5, 1.2), y=(1353, 0, 60, 8), T=273, gas="CO2",
         legend=(280, 80, 1000, 610), colors=["black", "red", "green", "blue"],
         markers=["square", "circle", "triangle_up", "triangle_down"]),
    dict(id="S105-Fig8B", page=8, image=0, crop=(0, 1660, 2068, 3372),
         x=(246.5, 0, 1981.5, 1.2), y=(1355, 0, 206, 4), T=298, gas="CO2",
         legend=(300, 20, 1100, 525), colors=["black", "red", "blue", "teal"],
         markers=["square", "circle", "triangle_up", "triangle_down"]),
    dict(id="S105-Fig8C", page=9, image=0, crop=(0, 0, 2013, 1707),
         x=(197, 0, 1932.5, 1.2), y=(1353, 0, 59, 3), T=318, gas="CO2",
         legend=(250, 100, 1000, 620), colors=["black", "red", "blue", "teal"],
         markers=["square", "circle", "triangle_up", "triangle_down"]),
    dict(id="S105-Fig9", page=11, image=0, crop=(0, 0, 2212, 1652),
         x=(304, 0, 2122, 1.2), y=(1408, 0, 55, .4), T=298, gas="N2",
         legend=(440, 190, 1260, 650), colors=["black", "red", "blue", "teal"],
         markers=["square", "circle", "triangle_up", "triangle_down"]),
    dict(id="S106-Fig4", page=5, image=1, crop=(0, 0, 1029, 787),
         x=(193.5, 0, 1007.5, 1), y=(668.5, 0, 24.5, 600), T=293, gas="H2O",
         legend=(710, 55, 990, 240), colors=["lavender", "pink", "purple"],
         markers=["triangle_up", "circle", "square"],
         materials=["UiO-66_100", "UiO-66_160", "UiO-66_220"]),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_yaml(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True))


def color_mask(a, color):
    r, g, b = a.astype(float).transpose(2, 0, 1)
    return {
        "black": (r < 65) & (g < 65) & (b < 65),
        "red": (r > 190) & (g < 90) & (b < 90),
        "green": (g > 180) & (r < 90) & (b < 90),
        "blue": (b > 180) & (r < 90) & (g < 90),
        "teal": (g > 65) & (b > 65) & (r < 65) & (abs(g-b) < 45),
        "lavender": (b > 200) & (r > 95) & (r < 180) & (g > 95) & (g < 180),
        "pink": (r > 200) & (b > 210) & (g > 105) & (g < 200),
        "purple": (r < 125) & (g < 65) & (b > 90) & (b < 210),
    }[color]


def bound(axis, pixel, readout):
    t = (pixel - axis.pixel_1) / (axis.pixel_2 - axis.pixel_1)
    slope = abs((axis.value_2-axis.value_1)/(axis.pixel_2-axis.pixel_1))
    # 2 px endpoint error, plus marker readout bound (not a standard deviation).
    return slope * (readout + 2 * abs(1-t) + 2 * abs(t))


def calibration_checks(a, panel, x_axis, y_axis):
    """Interior tick checks from dark-pixel runs; endpoints are not QA points."""
    row, col, x_values, y_values = {
        "S105-Fig8A": (1340, 242, [.2,.4,.6,.8,1], [1,2,3,4,5,6,7]),
        "S105-Fig8B": (1344, 255, [.2,.4,.6,.8,1], [.5,1,1.5,2,2.5,3,3.5]),
        "S105-Fig8C": (1340, 205, [.2,.4,.6,.8,1], [.5,1,1.5,2,2.5]),
        "S105-Fig9": (1393, 315, [.2,.4,.6,.8,1], [.05,.1,.15,.2,.25,.3,.35]),
        "S106-Fig4": (680, 118, [.2,.4,.6,.8], [100,200,300,400,500]),
    }[panel["id"]]
    result = {}
    dark = a.max(2) < 65
    for name, axis, scan, values in [("x",x_axis,dark[row],x_values), ("y",y_axis,dark[:,col],y_values)]:
        indices = np.flatnonzero(scan)
        groups = np.split(indices, np.flatnonzero(np.diff(indices)>1)+1)
        ticks = [float(g.mean()) for g in groups if len(g)]
        checks = []
        for value in values:
            expected = axis.pixel_1 + (value-axis.value_1)*(axis.pixel_2-axis.pixel_1)/(axis.value_2-axis.value_1)
            pixel = min(ticks, key=lambda p:abs(p-expected))
            residual = axis.transform(pixel)-value
            if abs(pixel-expected)>3:
                raise ValueError(f"tick not found: {panel['id']} {name}={value}")
            checks.append(dict(value=value, pixel=pixel, residual_data=residual))
        result[name] = checks
    result["scan_row"] = row
    result["scan_column"] = col
    result["method"] = "dark-pixel run centers at independent interior ticks; <=3 px residual required"
    return result


def extract(panel):
    source_id = panel["id"].split("-")[0]
    source = ROOT / ("data/raw/pdf/S105_T011.pdf" if source_id == "S105" else "data/raw/pdf/S106.pdf")
    with pymupdf.open(source) as doc:
        page = doc[panel["page"]-1]
        ref = page.get_images()[panel["image"]][0]
        image = doc.extract_image(ref)
        native = PRIVATE / f"T011-{panel['id']}-native.{image['ext']}"
        native.write_bytes(image["image"])
        picture = Image.open(native).convert("RGB").crop(panel["crop"])
    image_path = PRIVATE / f"T011-{panel['id']}.png"
    picture.save(image_path)
    x_axis, y_axis = AxisCalibration(*panel["x"]), AxisCalibration(*panel["y"])
    a = np.array(picture)
    water = source_id == "S106"
    # Match the actual printed glyph. This tolerates a dark fit crossing a colored
    # symbol without confusing the fit with a marker or splitting the symbol.
    readout = 4 if water else 7
    series, rows, audit = [], [], []
    overlay = picture.copy()
    draw = ImageDraw.Draw(overlay)
    for material, color, marker, template_box in zip(panel.get("materials", MATERIALS), panel["colors"], panel["markers"], TEMPLATES[panel["id"]]):
        mask = color_mask(a, color)
        roi = np.zeros(mask.shape, bool)
        left, right = sorted([x_axis.pixel_1, x_axis.pixel_2])
        top, bottom = sorted([y_axis.pixel_1, y_axis.pixel_2])
        # S106 axis extends above 600; retain its entire frame interior.
        if water:
            top = 4
        roi[int(top)+4:int(bottom)-2, int(left)+4:int(right)-4] = True
        if water:
            # Labels are inside the frame; remove only each label's own color.
            l,t,r,b = dict(lavender=(775,65,990,103), pink=(710,120,970,158),
                          purple=(775,205,990,241))[color]
        else:
            l, t, r, b = panel["legend"]
        roi[t:b, l:r] = False
        tl,tt,tr,tb = template_box
        template = mask[tt:tb,tl:tr].astype(float)
        if template.sum() < 100:
            raise ValueError(f"empty symbol template: {panel['id']} {material}")
        response = signal.fftconvolve(mask.astype(float), template[::-1,::-1], mode="same")/template.sum()
        height, width = template.shape
        threshold = .44 if water and color == "pink" else .58
        peaks = (response >= threshold) & (response >= ndimage.maximum_filter(response, size=(height, width))-1e-8) & roi
        labels, count = ndimage.label(peaks)
        pixels = []
        for label, sl in enumerate(ndimage.find_objects(labels), 1):
            yy, xx = sl
            iy, ix = np.nonzero(labels[sl] == label)
            # Convolution 'same' anchor is floor(n/2); restore bbox midpoint.
            px = float(xx.start+ix.mean()-(.5 if width%2==0 else 0))
            py = float(yy.start+iy.mean()-(.5 if height%2==0 else 0))
            score = float(response[sl][labels[sl] == label].max())
            accepted = True
            # Exclude the crowded origin: no coordinates invented for occlusions.
            accepted &= x_axis.transform(px) > (.025 if water else .015)
            audit.append(dict(series=material, pixel_x=px, pixel_y=py,
                              template_match_fraction=score, accepted=bool(accepted)))
            if accepted:
                pixels.append([float(px), float(py)])
        pixels.sort()
        for px, py in pixels:
            draw.ellipse((px-12, py-12, px+12, py+12), outline="orange", width=2)
            draw.line((px-4, py, px+4, py), fill="black", width=1)
            rows.append(dict(extraction_id="T011-"+panel["id"], source_id=source_id,
                             series=material, gas=panel["gas"], T_K=panel["T"],
                             pixel_x=px, pixel_y=py, x=x_axis.transform(px),
                             y=y_axis.transform(py), x_err=bound(x_axis, px, readout),
                             y_err=bound(y_axis, py, readout),
                             branch="adsorption", data_kind="digitized_markers", status="provisional"))
            if water:
                rows[-1].update(RH_fraction=x_axis.transform(px), RH_percent=100*x_axis.transform(px))
        series.append(dict(name=material, data_kind="digitized_markers", sigma_pixel=readout,
                           pixels=pixels, marker=marker, color=color, branch="adsorption",
                           template_box_native_pixels=list(template_box), match_threshold=threshold))
    extraction_id = "T011-"+panel["id"]
    project = dict(extraction_id=extraction_id, image_sha256=sha(image_path),
                   image_ref=str(image_path.relative_to(ROOT)), code_version="sha256:"+sha(__file__),
                   source_pdf_sha256=sha(source), pdf_page=panel["page"],
                   source_image_index=panel["image"], native_image_sha256=sha(native),
                   crop_native_pixels=list(panel["crop"]), x_axis=asdict(x_axis), y_axis=asdict(y_axis),
                   x_unit="p/p0 = RH fraction" if water else "bar absolute",
                   y_unit="cm3(STP)/g" if water else "mmol/g",
                   protocol_scale_span_x=1 if water else 1.2,
                   protocol_scale_span_y=4.5 if panel["id"]=="S105-Fig8B" else abs(y_axis.value_2-y_axis.value_1),
                   T_K=panel["T"], gas=panel["gas"], series=series,
                   versions=dict(numpy=np.__version__, scipy=scipy.__version__,
                                 pillow=PIL.__version__, pymupdf=pymupdf.__version__),
                   calibration_checks=calibration_checks(a, panel, x_axis, y_axis),
                   algorithm=dict(method="color mask; correlate printed-symbol template; local response maxima; bbox midpoint anchor",
                                  legend_exclusion=list(panel["legend"]) if not water else "per-color label rectangles in script",
                                  shared_origin_excluded=True, no_curve_sampling=True),
                   error_estimate=dict(readout_bound_px=readout, calibration_endpoint_bound_px=2,
                                       method="linear worst-case sum; no experimental uncertainty inferred"),
                   status="provisional", reviewer=None)
    validate_project(project)
    write_yaml(DIG / f"{extraction_id}.digitization.yaml", project)
    csv_path = DIG / f"{extraction_id}.csv"
    with csv_path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    overlay_path = PRIVATE / f"{extraction_id}-overlay.png"
    overlay.save(overlay_path)
    (PRIVATE / f"{extraction_id}-components.json").write_text(json.dumps(audit, indent=2))
    limitations = (["Fig.4 contains adsorption isotherms only; no separate desorption branch identified.",
                    "Static volumetric water measurements at 293 K: vacuum activation 1 h at 60 C then 2 h at 150 C, ramp 2 C/min (PDF pp.3-4).",
                    "Samples _100/_160/_220 differ in synthesis temperature and defect content, not adsorption temperature.",
                    "Crowded low-RH markers unresolved by segmentation are not imputed."] if water else
                   ["Activation conflict: section 2.3 ambient-temperature vacuum 12 h vs section 3.4 vacuum 393 K 12 h.",
                    "N2 section 3.5 gives 0-1 bar while Fig.9 absolute-pressure axis extends to 1.2 bar; retain plotted coordinates.",
                    "GO composites kept distinct from unmodified carriers; no transfer of uptake normalization.",
                    "Langmuir lines excluded; Table 3 is a separate author_fit.",
                    "Unresolved or partially occluded markers omitted, especially in crowded low-pressure regions; not imputed."])
    record = dict(extraction_id=extraction_id, source_id=source_id,
                  doi="10.1016/j.micromeso.2021.111555" if water else "10.3390/ma11040589",
                  url="https://doi.org/10.1016/j.micromeso.2021.111555" if water else "https://www.mdpi.com/1996-1944/11/4/589",
                  input_sha256=sha(source), pdf_page=panel["page"], api_page_map={"1":panel["page"]},
                  figure_or_table=panel["id"].split("-",1)[1],
                  region=dict(image_ref=str(image_path.relative_to(ROOT)), image_sha256=sha(image_path),
                              crop_native_pixels=list(panel["crop"])),
                  tool="scripts/extraction/digitize_c_series.py; NumPy/SciPy/Pillow; AxisCalibration",
                  tool_version="sha256:"+sha(__file__),
                  params=dict(project=f"data/extraction/digitization/{extraction_id}.digitization.yaml",
                              overlay=str(overlay_path.relative_to(ROOT)), overlay_sha256=sha(overlay_path),
                              limitations=limitations, T_K=panel["T"], gas=panel["gas"],
                              mass_basis="dry adsorbent; each material's own mass",
                              RH="p/p0 in selected water figure" if water else "unknown; no humidification specified, not measured RH=0",
                              license="CC BY 4.0", units=project["y_unit"],
                              branch="adsorption; no desorption series identified in selected figure"),
                  date=datetime.now(timezone.utc).isoformat(), raw_response_ref=str(native.relative_to(ROOT)),
                  unit_conversions=([dict(from_unit="cm3(STP)/g", to_unit="mmol/g", factor=1/22.414,
                                          STP_T_K=273.15, STP_P_kPa=101.325),
                                     dict(from_unit="p/p0", to_unit="RH fraction", factor=1),
                                     dict(from_unit="RH fraction", to_unit="absolute bar",
                                          formula="p_bar=RH_fraction*p_sat(293 K)",
                                          method="IAPWS SR1-86(1992) Eq.1; build_c_series.water_psat_bar",
                                          source="https://iapws.org/public/documents/6dGkr/Supp-sat.pdf",
                                          pdf_page=3, temperature_uncertainty="unknown")] if water else []),
                  derived_sha256=sha(csv_path), status="provisional", reviewer=None,
                  corrections=[], error_estimate=project["error_estimate"],
                  data_kind="digitized_markers", sensitivity_only=True)
    write_yaml(RECORDS / f"{extraction_id}.yaml", record)
    print(extraction_id, {s["name"]:len(s["pixels"]) for s in series})


def author_table():
    """Table 3, visually checked on PDF p.10; no fitted curve turned into data."""
    values = [
        [(11.78,.45,.999),(15.49,.17,.999),(4.42,.45,.999)],
        [(12.63,.45,.999),(8.28,.45,.999),(3.82,.71,.998)],
        [(10.83,1.26,.997),(6.03,1.20,.997),(3.37,1.22,.997)],
        [(10.92,1.39,.996),(6.38,1.41,.996),(4.39,1.06,.998)],
    ]
    eid = "T011-S105-Table3"
    source = ROOT / "data/raw/pdf/S105_T011.pdf"
    render = PRIVATE / f"{eid}.png"
    raw = ROOT / f"private/ocr_cache/T011/{eid}.txt"
    with pymupdf.open(source) as doc:
        doc[9].get_pixmap(dpi=160).save(render)
        raw.write_text(doc[9].get_text())
    rows = [dict(extraction_id=eid, source_id="S105", material=m, T_K=T,
                 Q_m_display=qm, b_display=b, R_squared=r2,
                 units="table omits parameter units; Eq.1 with Fig.8 implies mmol/g and bar^-1",
                 data_kind="author_fit", status="provisional")
            for m, group in zip(MATERIALS, values)
            for T, (qm,b,r2) in zip([273,298,318], group)]
    output = DIG / f"{eid}.csv"
    with output.open("w") as stream:
        w=csv.DictWriter(stream, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    record = dict(extraction_id=eid, source_id="S105", doi="10.3390/ma11040589",
                  url="https://www.mdpi.com/1996-1944/11/4/589", input_sha256=sha(source),
                  pdf_page=10, api_page_map={"1":10}, figure_or_table="Table 3",
                  region=dict(render=str(render.relative_to(ROOT)), render_sha256=sha(render)),
                  tool="PyMuPDF text layer + visual table transcription; scripts/extraction/digitize_c_series.py",
                  tool_version="sha256:"+sha(__file__),
                  params=dict(parameter_units="not printed in Table 3; inference kept separate",
                              not_a_measurement=True, not_in_normalized_isotherms=True),
                  date=datetime.now(timezone.utc).isoformat(), raw_response_ref=str(raw.relative_to(ROOT)),
                  unit_conversions=[], derived_sha256=sha(output), status="provisional", reviewer=None,
                  corrections=[], error_estimate="Printed precision only; fit parameter uncertainty unknown",
                  data_kind="author_fit", sensitivity_only=True)
    write_yaml(RECORDS/f"{eid}.yaml", record)


def main():
    for path in [PRIVATE, DIG, RECORDS]:
        path.mkdir(parents=True, exist_ok=True)
    for panel in PANELS:
        extract(panel)
    author_table()


if __name__ == "__main__":
    main()
