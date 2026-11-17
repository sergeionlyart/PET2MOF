#!/usr/bin/env python3
"""Deterministically normalize the explicit T011 C allowlist. Offline; no PDFs/OCR.

Unknown NIST errors are empty CSV cells, never zero. Status is a row property:
the two NIST-only S100 points do NOT inherit the verified status of SI Fig.S5.
The manifest distinguishes C candidates, GO context and sensitivity-only data.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import yaml
from pet2mof.extraction.c_series_review import review_status

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ["series_id", "source_id", "extraction_id", "material", "gas", "T_K",
          "p_bar", "q_mmol_g", "q_err_mmol_g", "p_err_bar", "data_kind", "status"]
FIGURES = ("S105-Fig8A", "S105-Fig8B", "S105-Fig8C", "S105-Fig9", "S106-Fig4")
NIST_PREFIXES = ("10.1021acs.inorgchem.5b00435", "10.1039C2cp23839j", "10.1021Ie202325p")
GASES = {"Carbon Dioxide":"CO2", "Nitrogen":"N2", "Water":"H2O"}
S100 = {"UiO-66":5, "10PEI@UiO-66":6, "20PEI@UiO-66":7, "30PEI@UiO-66":8, "40PEI@UiO-66":9}
STP_CM3_PER_MMOL = 22.414  # 273.15 K, 101.325 kPa; explicit project convention
PROTOCOL_SCALE_FRACTION = .03
IAPWS_URL = "https://iapws.org/public/documents/6dGkr/Supp-sat.pdf"


def water_psat_bar(T_K):
    """IAPWS SR1-86(1992), Eq.1, PDF p.3; pure-water saturation pressure.

    RH = p/p_sat at the nominal source temperature, ideal vapor convention.
    This is a unit conversion, not another measured pressure series.
    """
    if not math.isfinite(T_K) or not 273.16 <= T_K <= 647.096:
        raise ValueError("IAPWS liquid-vapor saturation temperature out of range")
    tau = 1-T_K/647.096
    coefficients = [-7.85951783,1.84408259,-11.7866497,22.6807411,-15.9618719,1.80122502]
    powers = [1,1.5,3,3.5,4,7.5]
    return 220.64*math.exp(647.096/T_K*sum(c*tau**p for c,p in zip(coefficients,powers)))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(value):
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def row(series_id, source_id, extraction_id, material, gas, T, p, q, qe, pe, kind, status):
    if source_id in {"S2", "S103", "S113"}:
        raise ValueError("holdout source in C input")
    for value in (T,p,q):
        if not math.isfinite(value) or value < 0:
            raise ValueError("invalid physical coordinate")
    for value in (qe,pe):
        if value != "" and (not math.isfinite(value) or value <= 0):
            raise ValueError("unknown error must be empty, known bound must be positive")
    return dict(zip(FIELDS,[series_id,source_id,extraction_id,material,gas,T,p,q,qe,pe,kind,status]))


def collect(root=ROOT):
    datasets = defaultdict(list)
    metadata = {}
    inputs = {}

    def remember(path):
        inputs[str(path.relative_to(root))] = sha(path)

    for relative in ["data/extraction/digitization/T011b/baseline.json",
                     "data/extraction/digitization/T011b/recovery_windows.json",
                     "src/pet2mof/extraction/c_series_review.py",
                     "reviews/T011v_c_series_verification.md",
                     "reviews/T011v2_reverification.md"]:
        remember(root/relative)
    for figure in FIGURES:
        eid = "T011-"+figure
        path = root / f"data/extraction/digitization/{eid}.csv"
        project_path = path.with_name(eid+".digitization.yaml")
        project = yaml.safe_load(project_path.read_text())
        record_path = root/f"data/extraction/records/{eid}.yaml"
        record = yaml.safe_load(record_path.read_text())
        remember(path); remember(project_path); remember(record_path)
        if sha(path) != record["derived_sha256"]:
            raise ValueError("digitization CSV hash disagrees with passport")
        water = figure.startswith("S106")
        expected_units = ("p/p0 = RH fraction", "cm3(STP)/g") if water else ("bar absolute", "mmol/g")
        if (project["x_unit"],project["y_unit"]) != expected_units:
            raise ValueError("unexpected digitization units")
        q_scale = project["protocol_scale_span_y"]
        p_scale = project["protocol_scale_span_x"]
        source_rows = read_csv(path)
        qualities = {}
        project_series = {s["name"]:s for s in project["series"]}
        for material, s in project_series.items():
            quality = review_status(root, figure, material, [r for r in source_rows if r["series"] == material])
            for item in [s, record["params"]["series"][material]]:
                if any(item[k] != quality[k] for k in quality):
                    raise ValueError("series status disagrees with exact-coordinate review authority")
                if not math.isfinite(item["usable_p_min_bar"]) or item["usable_p_min_bar"] < 0:
                    raise ValueError("invalid usable pressure lower bound")
            qualities[material] = quality
        for r in source_rows:
            source = "S106" if water else "S105"
            if r["source_id"] != source or r["extraction_id"] != eid:
                raise ValueError("source/extraction mismatch")
            quality = qualities[r["series"]]
            if r["status"] != quality["status"] or r["data_kind"] != "digitized_markers":
                raise ValueError("T011 row status disagrees with per-series review")
            T, x, y = float(r["T_K"]), float(r["x"]), float(r["y"])
            if T != project["T_K"] or r["gas"] != project["gas"]:
                raise ValueError("temperature/gas mismatch")
            pf = water_psat_bar(T) if water else 1
            qf = 1/STP_CM3_PER_MMOL if water else 1
            if water and (not 0<=x<=1 or float(r["RH_fraction"]) != x):
                raise ValueError("invalid relative humidity")
            sid = f"C-{figure}-{slug(r['series'])}-{r['gas']}-{T:g}K"
            qe = max(float(r["y_err"]), PROTOCOL_SCALE_FRACTION*q_scale)*qf
            pe = max(float(r["x_err"]), PROTOCOL_SCALE_FRACTION*p_scale)*pf
            usable_min = project_series[r["series"]]["usable_p_min_bar"]
            if not math.isclose(usable_min, record["params"]["series"][r["series"]]["usable_p_min_bar"], abs_tol=1e-14):
                raise ValueError("usable range differs between project and passport")
            datasets[sid].append(row(sid,source,eid,r["series"],r["gas"],T,x*pf,y*qf,qe,pe,
                                     "digitized_markers",quality["status"]))
            metadata[sid] = dict(role="context_GO" if "/GO" in r["series"] else "C_candidate",
                                 branch="adsorption", figure=figure, passport=str(record_path.relative_to(root)),
                                 status=quality["status"], reviewer=quality["reviewer"],
                                 review_ref=quality["review_ref"], pending_review=quality["pending_review"],
                                 usable_p_min_bar=usable_min,
                                 uncertainty="max(pixel worst-case bound, 3% displayed axis scale); experimental error unknown",
                                 p_conversion="p_bar=RH_fraction*p_sat(T); derived absolute water partial pressure" if water else "absolute bar, unchanged",
                                 q_conversion="q_mmol_g=q_cm3_STP_g/22.414" if water else "mmol/g, unchanged")

    # S100 conditions and verified status are established by D-15, superseding
    # old provisional fields in the unchanged T006 CSV/project.
    path = root/"data/extraction/digitization/T006-S100-FigS5.csv"
    remember(path)
    record_path = root/"data/extraction/records/T006-S100-FigS5.yaml"
    record = yaml.safe_load(record_path.read_text()); remember(record_path)
    if record["status"] != "verified" or sha(path) != record["derived_sha256"]:
        raise ValueError("S100 must retain its accepted verified coordinates")
    own = read_csv(path)
    missing = []
    for material, number in S100.items():
        sid = f"C-S100-FigS5-{slug(material)}-CO2-298K"
        sub = [r for r in own if r["series"] == material]
        for r in sub:
            datasets[sid].append(row(sid,"S100","T006-S100-FigS5",material,"CO2",298,
                                     float(r["x_display_kPa"])/100,float(r["uptake_mmol_g"]),
                                     max(float(r["uptake_bound_mmol_g"])+.017,.03*3.5),
                                     max((float(r["x_bound_kPa"])+.20)/100,.03*1.4),
                                     "digitized_markers","verified"))
        npath = root/f"data/raw/nist_isodb/isotherms/10.1021acs.iecr.5b03517.Isotherm{number}.json"
        j = json.loads(npath.read_text()); remember(npath)
        if (j["pressureUnits"],j["adsorptionUnits"],j["temperature"]) != ("bar","mmol/g",298):
            raise ValueError("S100 NIST units/temperature changed")
        used = set()
        for r in sub:
            index = min(range(len(j["isotherm_data"])), key=lambda i:
                        (j["isotherm_data"][i]["pressure"]*100-float(r["x_display_kPa"]))**2 +
                        ((j["isotherm_data"][i]["species_data"][0]["adsorption"]-float(r["uptake_mmol_g"]))/ .05)**2)
            if index in used:
                raise ValueError("ambiguous S100 nearest-neighbor mapping")
            point = j["isotherm_data"][index]
            if abs(point["pressure"]*100-float(r["x_display_kPa"])) > float(r["x_bound_kPa"]) or abs(point["species_data"][0]["adsorption"]-float(r["uptake_mmol_g"])) > float(r["uptake_bound_mmol_g"]):
                raise ValueError("S100 cross-match no longer within accepted bounds")
            used.add(index)
        for index, point in enumerate(j["isotherm_data"]):
            if index not in used:
                datasets[sid].append(row(sid,"S100","T002-"+npath.stem,material,"CO2",298,
                                         point["pressure"],point["species_data"][0]["adsorption"],"","",
                                         "digitized_markers","provisional"))
                missing.append(dict(series_id=sid, raw_file=str(npath.relative_to(root)), raw_point_index=index))
        metadata[sid] = dict(role="C", conditions_authority="docs/decisions.md D-15", branch="adsorption",
                             passport="data/extraction/records/T006-S100-FigS5.yaml",
                             NIST_passport="data/extraction/T002-nist-isodb.yaml",
                             uncertainty="max(T006 bound + inter-operator difference, 3% full axis); NIST-only error unknown",
                             PEI_loading="nominal sample label; not measured retained mass fraction; Mw unknown")
    if len(missing) != 2:
        raise ValueError("D-15 expects exactly two NIST-only points")

    # Closed-article NIST copies remain sensitivity only. Never merge paired
    # RSC records: experimental versus simulated origin is unknown in the JSON.
    for prefix in NIST_PREFIXES:
        for npath in sorted((root/"data/raw/nist_isodb/isotherms").glob(prefix+".*.json")):
            j = json.loads(npath.read_text())
            if j["adsorbent"]["name"] not in {"UiO-66","UiO-66-NH2"}:
                continue
            gas = GASES[j["adsorbates"][0]["name"]]
            if prefix != "10.1021Ie202325p" and gas not in {"CO2","N2"}:
                continue
            if len(j["adsorbates"]) != 1 or j["pressureUnits"] != "bar" or j["adsorptionUnits"] != "mmol/g":
                raise ValueError("unsupported NIST composition/units")
            remember(npath)
            material, T = j["adsorbent"]["name"], j["temperature"]
            sid = "SENS-NIST-"+slug(npath.stem)
            source = "NIST-"+prefix
            kind = "digitized_markers" if j["category"] == "exp" else "nist_category_unknown"
            for point in j["isotherm_data"]:
                datasets[sid].append(row(sid,source,"T002-"+npath.stem,material,gas,T,
                                         point["pressure"],point["species_data"][0]["adsorption"],"","",kind,"provisional"))
            metadata[sid] = dict(role="sensitivity_only", raw_file=str(npath.relative_to(root)),
                                 raw_sha256=sha(npath), DOI=j["DOI"], figure=j["articleSource"],
                                 NIST_category=j["category"] or "unknown", uncertainty="unknown; empty cells are not zero",
                                 passport="data/extraction/T002-nist-isodb.yaml",
                                 empirical_fit_allowed=False if kind=="nist_category_unknown" else "only marked sensitivity")
    return datasets, dict(schema_version=1, fields=FIELDS, units=dict(p_bar="absolute bar (gas partial pressure)",
                        q_mmol_g="mmol per g dry adsorbent", T_K="K", RH="fraction in S106 digitization CSV"),
                        water_conversion=dict(STP_cm3_per_mmol=STP_CM3_PER_MMOL, STP_T_K=273.15,
                                              STP_P_kPa=101.325, psat_source=IAPWS_URL,
                                              psat_293K_bar=water_psat_bar(293),
                                              temperature_uncertainty="unknown; nominal T used"),
                        protocol_error_floor_fraction=PROTOCOL_SCALE_FRACTION,
                        S100_NIST_only_points=missing, inputs=dict(sorted(inputs.items())),
                        series=metadata)


def build(root=ROOT, output=None):
    root = Path(root)
    output = Path(output) if output else root/"data/processed/c_series"
    datasets, manifest = collect(root)
    output.mkdir(parents=True, exist_ok=True)
    expected = {sid+".csv" for sid in datasets}
    stale = {p.name for p in output.glob("*.csv")}-expected
    if stale:
        raise ValueError(f"unrecognized CSVs in output (not deleted): {sorted(stale)}")
    for sid, rows in sorted(datasets.items()):
        rows.sort(key=lambda r:(r["p_bar"],r["q_mmol_g"],r["extraction_id"]))
        path = output/(sid+".csv")
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            for r in rows:
                writer.writerow({k:format(v,".12g") if isinstance(v,float) else v for k,v in r.items()})
        manifest["series"][sid].update(rows=len(rows), csv_sha256=sha(path))
    manifest["builder_sha256"] = sha(Path(__file__))
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = build(output=args.output)
    print(f"{len(manifest['series'])} series, {sum(s['rows'] for s in manifest['series'].values())} points")
