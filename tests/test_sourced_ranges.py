"""Offline lineage and numerical checks for T014; never fetch/open holdout data."""
import copy
import hashlib
import json
import math
from pathlib import Path

import pytest
import yaml

from pet2mof.model.config import load_config
from pet2mof.provenance.extraction import read_extraction


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/sourced_ranges.yaml"
EVIDENCE = ROOT / "data/extraction/T014"
FORBIDDEN = {"S2", "S102", "S103", "S113", "S117"}
PARAMETERS = {
    "tau_over_t", "Q_W", "gamma", "kappa", "V_p0", "alpha_in", "W_max",
    "h_max", "Q_phys", "Q_d", "f3", "water_volume_transfer",
}


def quantities(node):
    if isinstance(node, dict):
        if "value" in node or "range" in node:
            yield node
        else:
            for child in node.values():
                yield from quantities(child)
    elif isinstance(node, list):
        for child in node:
            yield from quantities(child)


def evidence(eid):
    return json.loads((EVIDENCE / f"{eid}.json").read_text())


def values(eid, key):
    row = evidence(eid)["quantities"][key]
    return row.get("value", row.get("range"))


def test_existing_loader_and_complete_parameter_coverage():
    loaded = load_config(CONFIG)
    assert set(loaded["target_knowledge"]) == PARAMETERS
    assert all(v is None for v in loaded["target_knowledge"].values())
    assert set(loaded["scenario"]["screen_bounds"]) | {"tau_over_t"} == PARAMETERS
    assert loaded["literature_ranges"]["Q_phys"] == [22900, 24300]
    assert loaded["literature_ranges"]["f3"] == [.24, .32]
    raw = yaml.safe_load(CONFIG.read_text())
    assert all(row["type"] == "assumption_range" for row in quantities(raw["scenario"]))
    assert all(row["type"] == "unknown" for row in quantities(raw["target_knowledge"]))
    assert all(row["transfer_class"] == "analog" for row in quantities(raw["literature_ranges"]))


def test_every_number_resolves_to_canonical_evidence_and_registered_source():
    registry = yaml.safe_load((ROOT / "sources/registry.yaml").read_text())
    ids = [row["source_id"] for row in registry]
    assert len(ids) == len(set(ids))
    sources = {row["source_id"]: row for row in registry}
    passports = {
        path.stem: read_extraction(path)
        for path in (ROOT / "data/extraction/records").glob("T014-*.yaml")
    }
    assert passports
    raw = yaml.safe_load(CONFIG.read_text())
    all_rows = list(quantities(raw))
    for eid, passport in passports.items():
        assert passport["status"] == "provisional"
        assert passport["reviewer"] is None
        assert passport["sensitivity_only"] is True
        assert passport["source_id"] not in FORBIDDEN
        path = ROOT / passport["params"]["output_ref"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == passport["derived_sha256"]
        packet = evidence(eid)
        assert packet["source_id"] == passport["source_id"]
        assert packet["doi"] == passport["doi"] == sources[passport["source_id"]]["doi"]
        # Run the production numeric guard over the evidence too (JSON is valid YAML).
        load_config(path)
        all_rows.extend(quantities(packet))
        for row in packet["quantities"].values():
            for operand in row.get("derived_from", []):
                origin, key = operand.split(":", 1) if ":" in operand else (eid, operand)
                assert key in evidence(origin)["quantities"]
    for row in all_rows:
        assert row["status"] == "provisional"
        assert row["source_id"] in sources and row["source_id"] not in FORBIDDEN
        assert row["extraction_id"] in passports
        path, pointer = row["evidence_ref"].split("#", 1)
        assert pointer.startswith("/quantities/")
        stored = json.loads((ROOT / path).read_text())["quantities"][pointer.removeprefix("/quantities/")]
        assert row == stored  # Editing a bound without its provenance must fail.
        assert row["source_id"] == passports[row["extraction_id"]]["source_id"]
        assert set(row["conditions"]) >= {"T", "RH", "material", "PEI_Mw", "method"}
        assert row["locator"] and row["limitations"] and row["evidence_kind"]
        if "range" in row:
            assert len(row["range"]) == 2 and row["range"][0] < row["range"][1]


def test_new_literature_dois_and_licenses_have_crossref_evidence():
    sources = {s["source_id"]: s for s in yaml.safe_load((ROOT / "sources/registry.yaml").read_text())}
    for sid in ("S119", "S121", "S124"):
        row = sources[sid]
        m = json.loads((ROOT / row["doi_evidence"]).read_text())["message"]
        assert row["doi_verified"] is True
        assert m["DOI"].lower() == row["doi"].lower()
        assert m["title"][0] == row["title"]
        assert m["container-title"][0] == row["journal"]
        assert m["published"]["date-parts"][0][0] == row["year"]
        assert row["license"] and row["evidence_urls"]
    assert "no CC" in sources["S119"]["license"]
    assert "CC BY-NC" in sources["S121"]["license"]
    assert sources["DESIGN-T014"]["doi"] is None


def test_input_and_render_hashes_without_requiring_private_articles_in_a_clone():
    manifest = json.loads((EVIDENCE / "inputs.json").read_text())
    inputs = {row["path"]: row for row in manifest["files"]}
    for path in (ROOT / "data/extraction/records").glob("T014-*.yaml"):
        passport = read_extraction(path)
        ref = passport["params"]["input_ref"]
        assert passport["input_sha256"] == inputs[ref]["sha256"]
        assert passport["url"] == inputs[ref]["url"]
        expected = {ref: passport["input_sha256"]}
        if passport["region"]:
            expected[passport["region"]["render"]] = passport["region"]["render_sha256"]
        for relpath, checksum in expected.items():
            assert not Path(relpath).is_absolute() and ".." not in Path(relpath).parts
            local = ROOT / relpath
            # Original copyrighted inputs are intentionally not distributed with Git.
            # When present, verify exact bytes; offline canonical lineage always runs.
            if local.exists():
                assert hashlib.sha256(local.read_bytes()).hexdigest() == checksum


def test_unit_conversions_extrema_and_conditional_kinetics():
    e = "T014-S105-Qphys"
    assert values(e, "Q_phys") == pytest.approx([x * 1000 for x in values(e, "reported_Qst")])
    e = "T014-S106-Qwater"
    heats = values(e, "zero_coverage_heats")
    assert values(e, "Q_water_simulation") == pytest.approx([min(heats) * 1000, max(heats) * 1000])
    e = "T014-S106-pores"
    volumes = values(e, "micropore_volumes")
    assert values(e, "V_p0_proxy") == [min(volumes), max(volumes)]
    e = "T014-S119-f3"
    fractions = values(e, "tertiary_percent")
    assert values(e, "f3") == [min(fractions) / 100, max(fractions) / 100]
    e = "T014-S116-desorption"
    taus = []
    for fraction, key in zip(values(e, "fractions"), ("t80_minutes", "t90_minutes"), strict=True):
        taus.extend(-t * 60 / math.log1p(-fraction) for t in values(e, key))
    assert values(e, "tau_equivalents") == pytest.approx(taus)
    assert values(e, "tau_CO2_des") == pytest.approx([min(taus), max(taus)])
    t_min, t_max = values("T014-DESIGN", "stage_time")
    assert values("T014-DESIGN", "tau_over_t_des_analog") == pytest.approx([min(taus) / t_max, max(taus) / t_min])
    heat_tau = values("T014-S124-kinetics", "tau_heat_max")
    assert values("T014-DESIGN", "tau_over_t_heat_analog") == pytest.approx([heat_tau / t_max, heat_tau / t_min])
    e = "T014-S124-heat"
    assert values(e, "Q_d_initial_proxy") == [x * 1000 for x in values(e, "initial_heat")]
    e = "T014-S124-pores"
    assert values(e, "specific_volume_ratio") == values(e, "V_loaded") / values(e, "V_parent")


def test_humidity_ratios_preserve_both_signs_and_material_identity():
    e = "T014-S121-humidity"
    ratios = []
    assert values(e, "RH") == [0, 20, 50, 80]
    for label in ("30", "40", "50"):
        dry, *wet = values(e, "q_" + label)
        expected = [v / dry for v in wet]
        assert values(e, "ratio_" + label) == pytest.approx(expected)
        ratios.extend(expected)
    assert min(ratios) < 1 < max(ratios)
    assert values(e, "wet_dry_ratio") == [min(ratios), max(ratios)]
    e = "T014-S110-humidity"
    b = values(e, "BPEI_humid") / values(e, "BPEI_dry")
    l = values(e, "LPEI_humid") / values(e, "LPEI_dry")
    assert values(e, "BPEI_wet_dry_ratio") == b
    assert values(e, "wet_dry_ratio_analog_envelope") == [min(b, l), max(b, l)]


def test_design_bounds_have_project_origin_and_structures_remain_separate():
    original = load_config(ROOT / "configs/scenarios.yaml")["scenario"]
    revision = load_config(ROOT / "configs/revision.yaml")
    result = load_config(CONFIG)
    for key, bounds in result["scenario"]["screen_bounds"].items():
        if key == "f3":
            assert bounds == [0, 1]
        elif key == "water_volume_transfer":
            assert bounds == revision["water_volume_transfer_bounds"]
        elif key == "W_max":
            assert bounds == [0, original["screen_bounds"][key][1]]
        else:
            assert bounds == original["screen_bounds"][key]
    assert result["scenario"]["tau_over_t"] == [min(original["tau_grid"]), max(original["tau_grid"])]
    assert result["structural_branches"]["v1.1-connectivity"]["kappa"] == revision["branches"]["v1.1-connectivity"]["kappa_bounds"]
    basis = json.loads((EVIDENCE / "design_basis.json").read_text())
    for item in basis["inputs"]:
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]


@pytest.mark.parametrize("change", ["missing_source", "bare_number", "two_value_fields", "nonfinite"])
def test_loader_rejects_untraceable_or_malformed_numbers(tmp_path, change):
    doc = copy.deepcopy(yaml.safe_load(CONFIG.read_text()))
    row = doc["scenario"]["tau_over_t"]
    if change == "missing_source":
        del row["source_id"]
    elif change == "bare_number":
        doc["untraced_bound"] = 12.0
    elif change == "two_value_fields":
        row["value"] = 1.0
    else:
        row["range"][1] = float("inf")
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(doc))
    with pytest.raises(ValueError):
        load_config(path)
