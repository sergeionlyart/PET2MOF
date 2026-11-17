"""Offline contract checks for C data; never open holdout files or primary PDFs."""
import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

from pet2mof.extraction.digitize import AxisCalibration, read_project
from pet2mof.extraction.c_series_review import review_status
from pet2mof.provenance.extraction import validate_extraction

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_c_series", ROOT/"scripts/extraction/build_c_series.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
spec = importlib.util.spec_from_file_location("digitize_c_series", ROOT/"scripts/extraction/digitize_c_series.py")
digitizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(digitizer)
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
                assert (r["extraction_id"] == "T006-S100-FigS5" and r["source_id"] == "S100") or r["extraction_id"].startswith("T011-")
        assert pressures == sorted(pressures)
    baseline = json.loads((ROOT/"data/extraction/digitization/T011b/baseline.json").read_text())
    expected_verified = 48 + 806
    assert counts["verified"] == expected_verified
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
        expected_status = "verified" if all(s["status"] == "verified" for s in project["series"]) else "provisional"
        assert passport["status"] == project["status"] == expected_status
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


def test_t011v_status_requires_review_and_byte_identical_coordinates():
    baseline = json.loads((ROOT/"data/extraction/digitization/T011b/baseline.json").read_text())
    manifest = json.loads((OUT/"manifest.json").read_text())
    reviewed = {}
    for line in (ROOT/baseline["review_ref"]).read_text().splitlines():
        c = [v.strip() for v in line.strip("|").split("|")]
        if len(c) == 10 and c[0].startswith("T011-"):
            reviewed[c[0].removeprefix("T011-")+"|"+c[1]] = c[8]
    assert len(reviewed) == 19 and list(reviewed.values()).count("verified") == 12
    for figure in builder.FIGURES:
        eid = "T011-"+figure
        data = rows(ROOT/f"data/extraction/digitization/{eid}.csv")
        project = read_project(ROOT/f"data/extraction/digitization/{eid}.digitization.yaml")
        passport = yaml.safe_load((ROOT/f"data/extraction/records/{eid}.yaml").read_text())
        for s in project["series"]:
            sub = [r for r in data if r["series"] == s["name"]]
            quality = review_status(ROOT, figure, s["name"], sub)
            prior_verified = reviewed[figure+"|"+s["name"]] == "verified"
            assert quality["status"] == "verified"
            assert {r["status"] for r in sub} == {quality["status"]}
            for item in [s, passport["params"]["series"][s["name"]]]:
                assert all(item[k] == v for k,v in quality.items())
            assert quality["reviewer"] == ("T011v" if prior_verified else "T011v2")
            assert quality["review_ref"] == ("reviews/T011v_c_series_verification.md" if prior_verified else "reviews/T011v2_reverification.md")
            assert quality["pending_review"] is None
            assert quality["coordinates_byte_identical"] == prior_verified
            changed = [dict(r) for r in sub]
            changed[0]["pixel_x"] = str(float(changed[0]["pixel_x"]) + .01)
            assert review_status(ROOT, figure, s["name"], changed)["status"] == "provisional"
            sid = f"C-{figure}-{builder.slug(s['name'])}-{project['gas']}-{project['T_K']}K"
            assert manifest["series"][sid]["status"] == quality["status"]
            assert {r["status"] for r in rows(OUT/(sid+".csv"))} == {quality["status"]}


def test_usable_pressure_ranges_and_individual_recovery_coverage():
    requests = json.loads((ROOT/"data/extraction/digitization/T011b/recovery_windows.json").read_text())["windows"]
    wanted = {r["id"] for r in requests}
    recovered = set()
    for figure in builder.FIGURES:
        eid = "T011-"+figure
        project = read_project(ROOT/f"data/extraction/digitization/{eid}.digitization.yaml")
        passport = yaml.safe_load((ROOT/f"data/extraction/records/{eid}.yaml").read_text())
        x = AxisCalibration(**project["x_axis"])
        pf = builder.water_psat_bar(project["T_K"]) if figure.startswith("S106") else 1
        for s in project["series"]:
            minimum = min(x.transform(px)*pf for px,py in s["pixels"])
            assert s["usable_p_min_bar"] == pytest.approx(minimum)
            assert passport["params"]["series"][s["name"]]["usable_p_min_bar"] == minimum
            for recovery in s["recoveries"]:
                assert recovery["action"] == "recovered"
                assert recovery["visible_support_pixels"] >= 10
                assert recovery["readout_bound_px"] >= s["sigma_pixel"]
                assert "source color mask" in recovery["method"]
                assert recovery["pixel"] in s["pixels"]
                recovered.add(recovery["id"])
    assert recovered == wanted
    assert sum(r["defect"] == "T011v-D02" for r in requests) == 2
    assert len({(r["figure"],r["series_index"]) for r in requests if r["defect"] == "T011v-D03"}) == 7


def test_each_printed_symbol_is_counted_once():
    # Check actual 2-D source-ink support, not just unique IDs or pressure gaps.
    from PIL import Image
    import numpy as np
    for figure in builder.FIGURES:
        project = read_project(ROOT/f"data/extraction/digitization/T011-{figure}.digitization.yaml")
        a = np.array(Image.open(ROOT/project["image_ref"]).convert("RGB"))
        for s in project["series"]:
            ids = [v["symbol_id"] for v in s["symbols"]]
            assert len(ids) == len(set(ids)) == len(s["pixels"])
            assert [v["pixel"] for v in s["symbols"]] == s["pixels"]
            mask = digitizer.color_mask(a, s["color"])
            l,t,r,b = s["template_box_native_pixels"]
            template = mask[t:b,l:r]
            supports = [digitizer.symbol_support(mask,template,p) for p in s["pixels"]]
            for i, support in enumerate(supports):
                for other in supports[:i]:
                    assert len(support & other)/min(len(support),len(other)) <= .75
    water = read_project(ROOT/"data/extraction/digitization/T011-S106-Fig4.digitization.yaml")
    removed = next(s for s in water["series"] if s["name"] == "UiO-66_160")["duplicate_detections_removed"]
    assert len(removed) == 1
    assert removed[0]["shared_ink_fraction"] > .75


def test_symbol_dedup_keeps_real_markers_with_same_pressure():
    import numpy as np
    mask = np.zeros((50,50),bool)
    mask[10:19,10:19] = True
    mask[30:39,10:19] = True
    template = np.ones((9,9),bool)
    candidates = [dict(pixel=p,score=s) for p,s in [([14.,14.],1),([15.,15.],.9),([14.,34.],1)]]
    kept, rejected = digitizer.deduplicate_symbols(candidates,mask,template)
    assert [v["pixel"] for v in kept] == [[14.,14.],[14.,34.]]
    assert len(rejected) == 1


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


def test_t011c_nonstatus_bytes_preserved():
    """Compare non-status bytes, including EOLs, to pre-T011c HEAD 623ebd62778e."""
    import hashlib
    expected = json.loads((ROOT/"tests/fixtures/t011c_nonstatus_sha256.json").read_text())
    paths = set(OUT.glob("*.csv")) | {ROOT/f"data/extraction/digitization/T011-{f}.csv" for f in builder.FIGURES}
    assert {str(p.relative_to(ROOT)) for p in paths} == set(expected)
    for path in paths:
        lines = path.read_bytes().splitlines(keepends=True)
        index = lines[0].rstrip(b"\r\n").split(b",").index(b"status")
        stripped = []
        for line in lines:
            assert b'"' not in line
            body = line.rstrip(b"\r\n")
            ending = line[len(body):]
            fields = body.split(b",")
            fields.pop(index)
            stripped.append(b",".join(fields) + ending)
        assert hashlib.sha256(b"".join(stripped)).hexdigest() == expected[str(path.relative_to(ROOT))]
