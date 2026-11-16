"""Offline contract checks for C data; never open holdout files or primary PDFs."""
import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

from pet2mof.extraction.digitize import AxisCalibration, read_project
from pet2mof.provenance.extraction import validate_extraction

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_c_series", ROOT/"scripts/extraction/build_c_series.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
OUT = ROOT/"data/processed/c_series"


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def test_rebuild_is_deterministic_and_matches_committed_artifacts(tmp_path):
    # This exercises production inputs, serialization, input hashes, and manifest.
    builder.build(output=tmp_path)
    before = {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    builder.build(output=tmp_path)
    assert before == {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    assert before == {p.name:p.read_bytes() for p in OUT.iterdir() if p.suffix in {".json",".csv"}}


def test_csv_schema_source_allowlist_status_and_unknown_errors():
    manifest = json.loads((OUT/"manifest.json").read_text())
    assert len(manifest["series"]) == 58
    counts = Counter()
    allowed = {"S100","S105","S106"} | {"NIST-"+p for p in builder.NIST_PREFIXES}
    for sid, meta in manifest["series"].items():
        path = OUT/(sid+".csv")
        with path.open() as stream:
            assert next(csv.reader(stream)) == builder.FIELDS
        data = rows(path)
        assert len(data) == meta["rows"] and builder.sha(path) == meta["csv_sha256"]
        pressures = []
        for r in data:
            assert r["series_id"] == sid
            assert r["source_id"] in allowed
            assert r["source_id"] not in {"S2","S103","S113"}
            assert r["gas"] in {"CO2","N2","H2O"}
            assert 273 <= float(r["T_K"]) <= 323
            assert float(r["q_mmol_g"]) >= 0
            assert float(r["p_bar"]) >= 0
            pressures.append(float(r["p_bar"]))
            assert r["status"] in {"verified","provisional"}
            counts[r["status"]] += 1
            if r["extraction_id"].startswith("T002-"):
                assert r["q_err_mmol_g"] == r["p_err_bar"] == ""
                assert r["status"] == "provisional"
            else:
                assert float(r["q_err_mmol_g"]) > 0
                assert float(r["p_err_bar"]) > 0
            if r["status"] == "verified":
                assert r["extraction_id"] == "T006-S100-FigS5" and r["source_id"] == "S100"
        assert pressures == sorted(pressures)
    assert counts == {"verified":48,"provisional":2084}
    # Inputs are explicit. No searching/opening holdout content is needed for QA.
    assert all("S103" not in p and "S113" not in p for p in manifest["inputs"])
    assert not any(r["data_kind"]=="author_fit" for p in OUT.glob("*.csv") for r in rows(p))


def test_water_stp_rh_and_absolute_pressure_conversion():
    # Independent numerical reference: IAPWS Eq.1 at 293 K (not 293.15 K).
    assert builder.water_psat_bar(293) == pytest.approx(.02317544979505, rel=1e-10)
    assert builder.water_psat_bar(373.15) == pytest.approx(1.01417994, rel=1e-7)
    assert 22.414/builder.STP_CM3_PER_MMOL == 1
    for r in rows(ROOT/"data/extraction/digitization/T011-S106-Fig4.csv"):
        sid = f"C-S106-Fig4-{builder.slug(r['series'])}-H2O-293K"
        candidates = rows(OUT/(sid+".csv"))
        p = float(r["x"])*.02317544979505
        target = min(candidates,key=lambda v:abs(float(v["p_bar"])-p))
        assert float(target["p_bar"]) == pytest.approx(p, rel=1e-10)
        assert float(target["q_mmol_g"]) == pytest.approx(float(r["y"])/22.414, rel=1e-10)
        assert float(r["RH_percent"]) == pytest.approx(100*float(r["x"]))
        assert 0 <= float(target["p_bar"]) <= .02317545
        assert float(target["q_err_mmol_g"]) == pytest.approx(18/22.414)


def test_s100_preserves_verified_coordinates_and_only_two_nist_supplements():
    own = rows(ROOT/"data/extraction/digitization/T006-S100-FigS5.csv")
    all_s100 = [r for p in OUT.glob("C-S100*.csv") for r in rows(p)]
    assert len(all_s100) == 50
    for r in own:
        candidates = [v for v in all_s100 if v["material"] == r["series"] and v["status"] == "verified"]
        target = min(candidates,key=lambda v:abs(float(v["p_bar"])-float(r["x_display_kPa"])/100))
        assert float(target["p_bar"])*100 == pytest.approx(float(r["x_display_kPa"]))
        assert float(target["q_mmol_g"]) == pytest.approx(float(r["uptake_mmol_g"]))
    missing = [r for r in all_s100 if r["status"] == "provisional"]
    assert {r["material"] for r in missing} == {"UiO-66","20PEI@UiO-66"}
    for r in missing:
        path = ROOT/"data/raw/nist_isodb/isotherms"/(r["extraction_id"].removeprefix("T002-")+".json")
        j = json.loads(path.read_text())
        assert any(float(r["p_bar"]) == p["pressure"] and float(r["q_mmol_g"]) == p["species_data"][0]["adsorption"] for p in j["isotherm_data"])


def test_all_figure_series_projects_calibration_and_passports():
    for figure in builder.FIGURES:
        eid = "T011-"+figure
        path = ROOT/f"data/extraction/digitization/{eid}.csv"
        project = read_project(path.with_name(eid+".digitization.yaml"))
        passport = yaml.safe_load((ROOT/f"data/extraction/records/{eid}.yaml").read_text())
        validate_extraction(passport)
        assert builder.sha(path) == passport["derived_sha256"]
        assert passport["status"] == project["status"] == "provisional"
        assert len(project["series"]) == (3 if figure.startswith("S106") else 4)
        x, y = AxisCalibration(**project["x_axis"]), AxisCalibration(**project["y_axis"])
        data = rows(path)
        for s in project["series"]:
            sub = [r for r in data if r["series"] == s["name"]]
            assert len(sub) == len(s["pixels"]) > 20
            for r,(px,py) in zip(sub,s["pixels"]):
                assert float(r["x"]) == x.transform(px)
                assert float(r["y"]) == y.transform(py)
        # Independent tick residuals must fit the stored endpoint error budget.
        for key, axis in [("x",x),("y",y)]:
            slope=abs((axis.value_2-axis.value_1)/(axis.pixel_2-axis.pixel_1))
            assert all(abs(c["residual_data"]) <= 2*slope for c in project["calibration_checks"][key])
    record = yaml.safe_load((ROOT/"data/extraction/records/T011-S105-Table3.yaml").read_text())
    validate_extraction(record)
    assert record["data_kind"] == "author_fit"
    table = rows(ROOT/"data/extraction/digitization/T011-S105-Table3.csv")
    assert len(table)==12 and {r["data_kind"] for r in table}=={"author_fit"}


def test_closed_nist_categories_stay_sensitivity_and_distinct():
    manifest = json.loads((OUT/"manifest.json").read_text())
    rsc = [sid for sid in manifest["series"] if "C2cp23839j" in sid]
    assert len(rsc) == 24
    for sid in rsc:
        meta = manifest["series"][sid]
        assert meta["role"] == "sensitivity_only" and meta["NIST_category"] == "unknown"
        assert meta["empirical_fit_allowed"] is False
        assert {r["data_kind"] for r in rows(OUT/(sid+".csv"))} == {"nist_category_unknown"}


def test_builder_rejects_invalid_physical_rows_and_unrecognized_outputs(tmp_path):
    args = ["s","S105","e","UiO-66","CO2",298,1,2,.1,.1,"digitized_markers","provisional"]
    for index,value in [(1,"S103"),(6,float("nan")),(7,-1),(8,0),(9,float("inf"))]:
        bad=args.copy();bad[index]=value
        with pytest.raises(ValueError):
            builder.row(*bad)
    stale=tmp_path/"unexpected.csv";stale.write_text("retain me")
    with pytest.raises(ValueError,match="unrecognized CSV"):
        builder.build(output=tmp_path)
    assert stale.read_text()=="retain me"
