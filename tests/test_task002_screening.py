"""Synthetic arithmetic and open-reference reproduction, not empirical validation."""

import importlib.util
import itertools
import json
import math
from pathlib import Path
import shutil
from fractions import Fraction

import pytest

from pet2mof.task002 import screening as s

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/task002/PET2MOF_Task002_DataPack_v1.0"


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/task002/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


screen = script("screen_s2")
intake = script("accept_pack")


@pytest.fixture
def inputs():
    dry = screen.load(PACK / "data/primary/S2_dry_CO2.csv")
    mats = screen.load(PACK / "data/primary/S2_materials.csv")
    secondary = screen.load(PACK / "data/primary/S2_secondary_properties.csv")
    return ({r["sample_id"]: float(r["q_CO2_dry_mmol_g"]) for r in dry},
            {r["sample_id"]: float(r["PEI_content_author_calculated_wt_pct"]) for r in mats}, secondary)


def test_synthetic_interval_vertices_and_inverse_inventory():
    # Exact rational endpoints and exhaustive interval vertices provide an
    # independent arithmetic oracle for a synthetic case, not T033 sign-off.
    qa, qb, d, rounding = Fraction(4), Fraction(2), Fraction(1, 10), Fraction(1, 200)
    a = (qa * (1 - d) - rounding, qa * (1 + d) + rounding)
    b = (qb * (1 - d) - rounding, qb * (1 + d) + rounding)
    corners = [x / y for x, y in itertools.product(a, b)]
    assert s.capacity_bounds(float(qa), float(d)) == pytest.approx(tuple(map(float, a)))
    assert s.ratio_bounds(float(qa), float(qb), float(d)) == pytest.approx((float(min(corners)), float(max(corners))))
    lo, hi = s.capacity_bounds(float(qa), float(d))
    assert s.inventory(hi) < s.inventory(float(qa)) < s.inventory(lo)
    assert s.inventory(4) * (4 * 44.01 / 1000) == pytest.approx(1)
    rows = s.independent_stress({s.CONTROL: 2, "test": 4}, [0.1])
    row = next(r for r in rows if r["sample_id"] == "test")
    assert row["gain_low_pct"] == pytest.approx(100 * (float(min(corners)) - 1))
    assert row["gain_high_pct"] == pytest.approx(100 * (float(max(corners)) - 1))
    assert row["inventory_low_kg_per_kg_CO2"] == pytest.approx(s.inventory(hi))
    assert row["inventory_high_kg_per_kg_CO2"] == pytest.approx(s.inventory(lo))
    assert row["robustly_above_base"]
    base = next(r for r in rows if r["sample_id"] == s.CONTROL)
    assert base["gain_low_pct"] == base["gain_high_pct"] == 0
    assert not base["robustly_above_base"]


def test_synthetic_strict_threshold_and_negative_direction():
    expected = float((Fraction(4) - 2 - Fraction(1, 100)) / 6)
    threshold = s.strict_threshold(4, 2)
    assert threshold == pytest.approx(expected)
    assert s.strict_threshold(4, 2, 0) == pytest.approx(1 / 3)
    for offset, robust in ((-1e-6, True), (1e-6, False)):
        lo, _ = s.capacity_bounds(4, threshold + offset)
        _, hi = s.capacity_bounds(2, threshold + offset)
        assert (lo > hi) is robust
    # Binary-exact equality: touching intervals do not establish A>B.
    assert s.capacity_bounds(3, 0.5, 0)[0] == s.capacity_bounds(1, 0.5, 0)[1]
    assert not (s.capacity_bounds(3, 0.5, 0)[0] > s.capacity_bounds(1, 0.5, 0)[1])
    assert s.strict_threshold(2, 4) < 0
    assert s.strict_threshold(2, 2) < 0


def test_common_factor_preserves_all_ratios_ranks_and_inverse_mass():
    qs = {s.CONTROL: 2.0, "high": 4.0, "tie": 4.0, "low": 1.0}
    rows = s.common_factor(qs)
    assert len(rows) == len(qs) * 6
    for row in rows:
        assert row["ratio_to_base_scaled"] == pytest.approx(row["ratio_to_base_nominal"], abs=1e-14)
        assert row["gain_scaled_pct"] == pytest.approx(row["gain_nominal_pct"], abs=1e-12)
        assert row["max_abs_all_pair_ratio_delta"] < 1e-14
        assert row["rank_scaled"] == row["rank_nominal"]
        assert row["inventory_scaled_kg_per_kg_CO2"] == pytest.approx(row["inventory_expected_1_over_k"])


@pytest.mark.parametrize("q,d,r", [(0, .1, .005), (math.nan, .1, .005), (2, -1, .005),
                                     (2, 1, .005), (2, .1, -.005), (.001, .1, .005)])
def test_invalid_interval_inputs_fail(q, d, r):
    with pytest.raises(ValueError):
        s.capacity_bounds(q, d, r)


def test_unknown_secondary_and_candidate_selection_uses_only_q(inputs):
    qs, pei, secondary = inputs
    assert s.secondary_value("") == "unknown"
    assert s.secondary_value("  ") == "unknown"
    assert s.secondary_value("0") == 0  # Only an explicit reported zero is zero.
    missing = [r for r in secondary if r["metric"] == "Qdes_DSC" and not r["value"]]
    assert len(missing) == 3
    assert all(s.secondary_value(r["value"]) == "unknown" for r in missing)
    altered = [dict(r, value="99999") for r in secondary]
    normal = s.candidate_metrics(qs, s.nominal_metrics(qs, pei), secondary)
    changed = s.candidate_metrics(qs, s.nominal_metrics(qs, pei), altered)
    assert [r["sample_id"] for r in normal] == [r["sample_id"] for r in changed] == ["S2-C72", "S2-C96", s.CONTROL]
    assert normal[-1]["Qdes_DSC"] == "unknown"
    for row in normal[:2]:
        assert row["control_class_d_0.03"] == row["control_class_d_0.05"] == "устойчиво выше контроля при d"
        assert row["control_class_d_0.10"] == "преимущество над контролем не разрешено при d"
        for d in s.SCENARIOS:
            assert row[f"pair_class_d_{d:.2f}"] == "различие не разрешено при d"
        assert row["required_relative_halfwidth_strictly_below"] == pytest.approx(float(Fraction(10, 641)))
    assert normal[0]["nominal_class"] == "первый по номиналу"
    assert normal[0]["q_quantity_type"] == "measurement"
    assert normal[0]["retained_PEI_wt_pct_quantity_type"] == "author_calculated"
    assert normal[0]["derived_quantity_type"] == "our_derived"


def test_every_reference_record_and_field(inputs):
    qs, pei, _ = inputs
    tables = {"nominal.csv": s.nominal_metrics(qs, pei), "stress_independent.csv": s.independent_stress(qs),
              "pairwise.csv": s.pairwise_metrics(qs)}
    contract = json.loads((PACK / "metadata/analysis_contract.json").read_text())
    assert tuple(contract["q_stress_halfwidth_relative"]) == s.SCENARIOS
    assert contract["rounding_q_halfwidth_mmol_g"] == s.ROUNDING
    assert contract["M_CO2_g_mol"] == s.M_CO2
    for name, (reference, keys) in screen.REFERENCE_TABLES.items():
        result = screen.compare_reference(tables[name], screen.load(PACK / "reference" / reference), keys,
                                          contract["numerical_check_abs_tol"])
        assert result["passed"], result
    pairs = tables["pairwise.csv"]
    assert len(pairs) == 30
    assert len({(p["sample_a"], p["sample_b"]) for p in pairs}) == 30
    assert {p["highlighted_pair"] for p in pairs} == {"", "C72/C96", "C72/N72", "C96/I96"}
    for p in pairs:
        for d in s.SCENARIOS:
            lo, hi = s.ratio_bounds(qs[p["sample_a"]], qs[p["sample_b"]], d)
            assert p[f"ratio_low_d_{d:.2f}"] == lo
            assert p[f"ratio_high_d_{d:.2f}"] == hi
            assert p[f"robust_A_gt_B_d_{d:.2f}"] == (lo > 1)


def test_reference_comparison_rejects_changes_missing_duplicate_and_nonfinite():
    expected = [{"sample_id": "a", "q": "2", "flag": "True"}]
    def compare(actual):
        return screen.compare_reference(actual, expected, ("sample_id",), 1e-10)["passed"]
    assert compare([dict(expected[0], q=2 + 1e-11)])
    assert not compare([dict(expected[0], q=2 + 1e-9)])
    assert not compare([dict(expected[0], q="nan")])
    assert not compare([dict(expected[0], flag=False)])
    assert not compare([])
    assert not compare(expected * 2)


def test_intake_executes_in_copy_and_leaves_all_pack_bytes_unchanged():
    before = {p.relative_to(PACK): p.read_bytes() for p in PACK.rglob("*") if p.is_file()}
    report = intake.accept(PACK, "synthetic-test-not-accounted")
    assert report["status"] == "passed", report
    assert len(report["manifest"]) == 35
    assert {r["path"] for r in report["manifest_exceptions"]} == intake.EXCEPTIONS
    assert len(report["commands"]) == 3
    assert all(c["exit_code"] == 0 for c in report["commands"])
    assert len(report["legacy_blobs"]) == 5
    assert all(report["ast_functions"].values())
    after = {p.relative_to(PACK): p.read_bytes() for p in PACK.rglob("*") if p.is_file()}
    assert after == before


def test_intake_rejects_modified_input_before_execution(tmp_path):
    copied = tmp_path / "pack"
    shutil.copytree(PACK, copied)
    with (copied / "data/primary/S2_dry_CO2.csv").open("a") as file:
        file.write("\n")
    report = intake.accept(copied, "synthetic-test-not-accounted")
    assert report["status"] == "failed"
    assert report["commands"] == []
    assert not all(r["passed"] for r in report["manifest"])


def test_ast_comparison_ignores_layout_and_detects_logic_changes():
    source = "def _number(x):\n return float(x)\ndef evaluate(x):\n return x + 1\n"
    formatted = "# comment\ndef _number(x):\n    return float(x)\n\ndef evaluate(x):\n    return x+1\n"
    assert intake.function_asts(source) == intake.function_asts(formatted)
    assert intake.function_asts(source) != intake.function_asts(source.replace("+ 1", "+ 2"))
    with pytest.raises(ValueError):
        intake.function_asts("def evaluate(x): return x")
