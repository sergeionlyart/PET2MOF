#!/usr/bin/env python3
"""Extract compact coloured markers, excluding thin red DSL curves. Offline."""
import csv
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pymupdf
import yaml
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pet2mof.extraction.digitize import AxisCalibration, validate_project

ID = "T006-S100-FigS5"
CROP = (380, 1120, 1310, 1840)  # pixels in the 200 dpi page; retains all axis labels
X = AxisCalibration(152, 0, 667, 100)
Y = AxisCalibration(601, 0, 105, 3.5)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def components(mask):
    """8-connected components; no scipy/OpenCV/ML dependencies."""
    visited = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    for yy, xx in zip(*np.nonzero(mask)):
        if visited[yy, xx]:
            continue
        stack, pixels = [(int(xx), int(yy))], []
        visited[yy, xx] = True
        while stack:
            x, y = stack.pop()
            pixels.append((x, y))
            for ny in range(max(0, y - 1), min(height, y + 2)):
                for nx in range(max(0, x - 1), min(width, x + 2)):
                    if mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
        yield pixels


def bound(axis, pixel):
    t = (pixel - axis.pixel_1) / (axis.pixel_2 - axis.pixel_1)
    slope = (axis.value_2 - axis.value_1) / (axis.pixel_2 - axis.pixel_1)
    return abs(slope) * (2 + abs(1 - t) + abs(t))


def tick_centres(indices):
    runs=[]
    for value in indices:
        if not runs or value>runs[-1][-1]+1:
            runs.append([int(value)])
        else:
            runs[-1].append(int(value))
    return [sum(run)/len(run) for run in runs]


def main():
    private = ROOT / "private/renders"
    private.mkdir(parents=True, exist_ok=True)
    source = ROOT / "data/raw/pdf/S100_SI.pdf"
    with pymupdf.open(source) as doc:
        pix = doc[6].get_pixmap(dpi=200)
        page = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    picture = page.crop(CROP)
    image_path = private / "S100_FigS5.png"
    picture.save(image_path)
    a = np.asarray(picture).astype(int)
    dark=a.max(axis=2)<100
    x_checks=tick_centres(np.flatnonzero(dark[609,:] & (np.arange(a.shape[1])>=150)))
    y_checks=tick_centres(np.flatnonzero(dark[:,142] & (np.arange(a.shape[0])>=100) & (np.arange(a.shape[0])<=605)))
    assert len(x_checks)==8 and len(y_checks)==8
    calibration_checks=dict(
        x=[dict(pixel=p,value=v,residual_data=X.transform(p)-v) for p,v in zip(x_checks,range(0,141,20))],
        y=[dict(pixel=p,value=v,residual_data=Y.transform(p)-v) for p,v in zip(y_checks,[3.5,3,2.5,2,1.5,1,.5,0])],
        method="dark-pixel runs along x-axis row 609 and y-axis column 142; matches major ticks",
        max_residual_x_data=max(abs(X.transform(p)-v) for p,v in zip(x_checks,range(0,141,20))),
        max_residual_y_data=max(abs(Y.transform(p)-v) for p,v in zip(y_checks,[3.5,3,2.5,2,1.5,1,.5,0])))
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    masks = {
        "UiO-66": (r < 70) & (g < 70) & (b < 70),
        "10PEI@UiO-66": (r > 190) & (g < 85) & (b < 85),
        "20PEI@UiO-66": (b > 170) & (r < 90) & (g < 90),
        "30PEI@UiO-66": (r > 170) & (b > 170) & (g < 100),
        "40PEI@UiO-66": (g > 65) & (g > r * 1.7) & (g > b * 1.7) & (r < 100) & (b < 100),
    }
    overlay = picture.copy()
    draw = ImageDraw.Draw(overlay)
    series, rows, audit = [], [], []
    for name, mask in masks.items():
        # ROI removes legend/text and axes; origin is shared/occluded and excluded.
        roi = np.zeros(mask.shape, dtype=bool)
        roi[95:588, 168:682] = True
        mask &= roi
        # Close 1 px interruptions where the red fit crosses a coloured symbol,
        # then erode to remove thin curves. This is binary segmentation, not
        # scientific-image enhancement; the original image is always retained.
        binary = Image.fromarray(mask.astype("uint8") * 255)
        binary = binary.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
        eroded = np.asarray(binary.filter(ImageFilter.MinFilter(3))) > 0
        pixels = []
        for component in components(eroded):
            xs, ys = zip(*component)
            width, height = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            accepted = 3 <= width <= 18 and 3 <= height <= 18 and len(component) >= 10
            if name == "UiO-66":
                accepted &= min(width, height) / max(width, height) >= 0.7 and len(component) / (width * height) > 0.75
            # Bounding-box centre is invariant to triangle direction (unlike centroid).
            x, y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            audit.append(dict(series=name, bbox=[min(xs), min(ys), max(xs), max(ys)],
                              core_pixels=len(component), accepted=bool(accepted)))
            if accepted:
                pixels.append([x, y])
        pixels.sort()
        for x, y in pixels:
            draw.ellipse((x-10, y-10, x+10, y+10), outline="orange", width=2)
            draw.line((x-5, y, x+5, y), fill="black", width=1)
            rows.append(dict(extraction_id=ID, source_id="S100", pdf_page=7,
                             figure="S5", series=name, data_kind="digitized_markers",
                             pixel_x=x, pixel_y=y, x_display_kPa=X.transform(x),
                             uptake_mmol_g=Y.transform(y),
                             x_bound_kPa=bound(X, x), uptake_bound_mmol_g=bound(Y, y),
                             status="provisional"))
        series.append(dict(name=name, data_kind="digitized_markers", sigma_pixel=2,
                           pixels=pixels, marker={"UiO-66":"square", "10PEI@UiO-66":"circle",
                           "20PEI@UiO-66":"triangle_up", "30PEI@UiO-66":"triangle_down",
                           "40PEI@UiO-66":"diamond"}[name]))
    target = ROOT / "data/extraction/digitization"
    target.mkdir(parents=True, exist_ok=True)
    code_version = "sha256:" + sha(__file__)
    project = dict(image_sha256=sha(image_path), code_version=code_version,
                   x_axis=asdict(X), y_axis=asdict(Y), series=series,
                   extraction_id=ID, source_pdf_sha256=sha(source), pdf_page=7,
                   figure="S5", dpi=200, crop_page_pixels=list(CROP),
                   image_ref="private/renders/S100_FigS5.png",
                   x_label_verbatim="P/P₀ (kPa)", y_label_verbatim="CO₂ Adsorbed amounts (mmol/g)",
                   axis_issue="P/P0 is a ratio but label says kPa; preserve displayed scale; physical pressure interpretation provisional",
                   temperature_K="unknown in Fig. S5 caption; 298 K in Fig. S4 is not transferred",
                   RH="unknown", PEI_loading_basis="unknown; retain sample labels",
                   excluded=["Shared origin: markers occlude each other", "Thin red DSL fitted curves",
                             "No error bars visible; no experimental uncertainty inferred"],
                   calibration_error_px_bound=1, readout_error_px_bound=2,
                   calibration_checks=calibration_checks,
                   error_method="absolute linear worst-case sum; see frozen protocol",
                   algorithm=dict(color_masks="see versioned script", closing_square_px=3, erosion_square_px=3,
                                  component_connectivity=8, roi=[168,95,682,588]),
                   status="provisional", sensitivity_only=True)
    validate_project(project)
    (target / f"{ID}.digitization.yaml").write_text(yaml.safe_dump(project, sort_keys=False, allow_unicode=True))
    with (target / f"{ID}.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (private / f"{ID}_components.json").write_text(json.dumps(audit, indent=2))
    overlay.save(private / "overlay_S100_FigS5.png")
    print(json.dumps({s["name"]:len(s["pixels"]) for s in series}))


if __name__ == "__main__":
    main()
