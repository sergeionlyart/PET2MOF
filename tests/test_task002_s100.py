"""Numerical contracts for S100; synthetic recovery is not empirical evidence."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize._numdiff import approx_derivative

from pet2mof.task002 import s100 as s

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/task002/PET2MOF_Task002_DataPack_v1.0"
spec = importlib.util.spec_from_file_location("s100_model", ROOT / "scripts/task002/s100_model.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture(scope="module")
def curves():
    return s.load_curves(PACK)


@pytest.fixture(scope="module")
def nominal(curves):
    return {c.sample: s.fit_isotherm(c) for c in curves}


def synthetic_curve(model="Langmuir"):
    p = np.linspace(.06, .95, 20)
    q = s.langmuir(p, 4., 3.) if model == "Langmuir" else s.toth(p, 4., 3., .7)
    fit = np.ones(len(p), bool)
    fit[8:11] = False
    return s.Curve("synthetic", tuple(map(str, range(len(p)))), p, q, fit)


def test_fixed_split_and_loader_never_opens_quarantine(monkeypatch):
    real = s.read_csv
    opened = []
    def read(path):
        opened.append(path.relative_to(PACK).as_posix())
        return real(path)
    monkeypatch.setattr(s, "read_csv", read)
    data = s.load_curves(PACK)
    assert opened == ["data/benchmark/S100_dry_isotherms.csv", "metadata/S100_internal_split.csv"]
    assert sum(np.count_nonzero(c.fit) for c in data) == 39
    assert sum(np.count_nonzero(~c.fit) for c in data) == 9
    assert all(np.all(c.fit == ~((c.p >= .33) & (c.p <= .46))) for c in data)


def test_loader_rejects_role_change_even_when_counts_match(monkeypatch):
    real = s.read_csv
    def read(path):
        rows = real(path)
        if path.name == "S100_internal_split.csv":
            rows[0]["role"], rows[3]["role"] = rows[3]["role"], rows[0]["role"]
        return rows
    monkeypatch.setattr(s, "read_csv", read)
    with pytest.raises(ValueError, match="split changed"):
        s.load_curves(PACK)


def test_independent_reference_all_fields_and_shapes(curves):
    residuals, shapes = s.baseline(curves)
    for rows, name, keys in ((residuals, "S100_internal_baseline_residuals.csv", ("point_id",)),
                              (shapes, "S100_nominal_shapes.csv", ("sample_label", "p_bar"))):
        comparison = runner.compare_reference(rows, s.read_csv(PACK / "reference" / name), keys)
        assert comparison["passed"], comparison
    assert s.metrics([r["residual"] for r in residuals])["mae"] == pytest.approx(s.EXPECTED_MAE, abs=1e-10)
    assert len(shapes) == 15
    assert all(r["q_over_q_at_0_85"] == 1 and r["fraction_difference_to_0_85"] == 0
               for r in shapes if r["p_bar"] == .85)


@pytest.mark.parametrize("target", [.059, .951, np.nan, np.inf])
def test_no_extrapolation_interpolation_and_model(target):
    c = synthetic_curve()
    fit = s.fit_isotherm(c)
    with pytest.raises(ValueError):
        s.interpolate(c.p, c.q, target)
    with pytest.raises(ValueError):
        fit.predict(target)


def test_interpolation_hand_arithmetic_and_duplicate_support():
    assert s.interpolate([1., 3., 7.], [2., 6., 8.], [1., 2., 5., 7.]).tolist() == [2., 4., 7., 8.]
    with pytest.raises(ValueError):
        s.interpolate([1, 1, 3], [1, 2, 3], 2)


@pytest.mark.parametrize("model,parameters", [("Langmuir", [4., 3.]), ("Toth", [4., 3., .7])])
def test_recover_synthetic_parameters_and_jacobians(model, parameters):
    c = synthetic_curve(model)
    result = s.fit_isotherm(c, model)
    assert result.success
    assert result.parameters == pytest.approx(parameters, rel=1e-5)
    assert max(abs(result.predict(c.p) - c.q)) < 1e-7
    if model == "Langmuir":
        numerical = approx_derivative(lambda x: s.langmuir(c.p, *x), np.array(parameters))
        analytic = s.langmuir_jacobian(c.p, *parameters)
    else:
        numerical = approx_derivative(lambda x: s.toth(c.p, *np.exp(x)), np.log(parameters))
        analytic = s.toth_log_jacobian(c.p, np.log(parameters))
        assert s.toth(c.p, 4, 3, 1) == pytest.approx(s.langmuir(c.p, 4, 3))
    assert analytic == pytest.approx(numerical, rel=1e-6, abs=1e-8)


def test_check_values_cannot_change_fit_parameters_or_stability(curves, nominal):
    for c in curves:
        altered = c.q.copy()
        altered[~c.fit] += 1000
        changed = s.fit_isotherm(s.Curve(c.sample, c.ids, c.p, altered, c.fit))
        assert changed.parameters.tolist() == nominal[c.sample].parameters.tolist()
        assert changed.diagnostics == nominal[c.sample].diagnostics


def test_jacobian_standard_errors_against_hand_diagonal_case():
    jac = np.array([[1., 0.], [0., 2.], [1., 0.], [0., 2.]])
    # SSE=4, df=2 => variance=2, J'J=diag(2,8), SE=(1,.5).
    d = s.parameter_diagnostics([2., 4.], jac, np.ones(4), 2)
    assert d["standard_errors"] == pytest.approx([1., .5])
    assert d["relative_standard_errors"] == pytest.approx([.5, .125])
    assert not d["relative_se_gt_50pct"]  # strict >50%, not >=
    assert not d["qs_gt_3maxq"]
    assert s.parameter_diagnostics([6.001, 4.], jac, np.ones(4), 2)["qs_gt_3maxq"]
    singular = s.parameter_diagnostics([2., 4.], np.ones((4, 2)), np.ones(4), 2)
    assert singular["standard_errors"] == [None, None]
    assert singular["unstable"]


@pytest.mark.parametrize("residuals,trigger,changes", [
    ([1] * 7, False, 0), ([1] * 8, True, 0),
    ([1, 1, -1, -1, -1, 1, 1, 1], True, 2),
    ([1, -1, 1, -1, 1, -1, 1, -1], False, 7),
    ([1, 0, -1, 0, 1, 0, 1, 0], True, 2)])
def test_toth_trigger_exact_boundaries(residuals, trigger, changes):
    assert s.systematic_deficiency(residuals) == dict(n_fit=len(residuals), sign_changes=changes, triggered=trigger)


@pytest.mark.parametrize("base,model,unstable,selected", [
    (.03, .02, False, "piecewise_linear"), (.03, .03, False, "piecewise_linear"),
    (.03, .04, False, "piecewise_linear"), (.2, .1, False, "Langmuir"),
    (.2, .1, True, "piecewise_linear"), (.105, .1, False, "Langmuir"),
    (.2, .105, False, "Langmuir")])
def test_preregistered_selection(base, model, unstable, selected):
    assert s.select_model(base, model, unstable=unstable)["selected"] == selected


def test_sensitivity_uniform_shift_refits_and_support(curves, nominal):
    residuals, per_sample, pooled = runner.compare_models(curves, nominal)
    rows = runner.sensitivity(curves, nominal, per_sample, pooled)
    assert len(rows) == 25
    for r in rows:
        assert r["piecewise_linear_delta_check_mae"] == pytest.approx(0, abs=1e-14)
        if r["scenario"] == "nominal":
            assert r["delta_q_s"] == r["delta_b"] == r["Langmuir_delta_check_mae"] == 0
    assert any(abs(r["delta_q_s"]) > .01 for r in rows if r["scenario"] == "p_minus")
    # A uniform pressure shift preserves the split identities, not a new block.
    c = curves[0].shifted(dp=-s.P_HALF)
    assert c.p[0] > 0
    assert s.fit_isotherm(c).predict(c.p[~c.fit]).size == np.count_nonzero(~c.fit)


def test_nonconverged_toth_retains_failed_attempts(monkeypatch):
    import scipy.optimize
    real = scipy.optimize.least_squares
    def stop_early(*args, **kwargs):
        kwargs["max_nfev"] = 1
        return real(*args, **kwargs)
    monkeypatch.setattr(s, "least_squares", stop_early)
    result = s.fit_isotherm(synthetic_curve("Toth"), "Toth")
    assert not result.success
    assert result.diagnostics["optimizer_failed"]
    assert len(result.attempts) == 9
    assert all(not a["success"] and a["nfev"] == 1 for a in result.attempts)


def test_end_to_end_outputs_toth_guard_and_deterministic_png(tmp_path, curves, nominal):
    before = {p.relative_to(PACK): p.read_bytes() for p in PACK.rglob("*") if p.is_file()}
    decision = runner.generate(tmp_path, "synthetic-test-not-accounted")
    assert decision["selection"]["selected"] == "piecewise_linear"
    assert decision["pooled"]["piecewise_linear"]["n"] == 9
    assert not decision["toth"]["per_sample"]["UiO-66"]["toth_attempted"]
    assert sum(v["toth_attempted"] for v in decision["toth"]["per_sample"].values()) == 4
    attempts = json.loads((tmp_path / "optimizer_attempts.json").read_text())
    assert set(attempts["Toth"]) == {c.sample for c in curves if len(c.p[c.fit]) >= 8}
    described = s.read_csv(tmp_path / "descriptive_all48.csv")
    assert sum(int(r["n_fit"]) for r in described) == 48
    assert {r["purpose"] for r in described} == {"описание, не проверка"}
    for name in ("langmuir_fit.csv", "check_residuals.csv", "sensitivity.csv", "descriptive_all48.csv", "toth_fit.csv"):
        rows = s.read_csv(tmp_path / name)
        assert all(r["run_id"] == "synthetic-test-not-accounted" and r["extraction_id"] and r["source_file"] for r in rows)
    pngs = {name: (tmp_path / name).read_bytes() for name in ("curves.png", "residuals.png")}
    residuals, _, _ = runner.compare_models(curves, nominal)
    runner.plot_results(curves, nominal, residuals, tmp_path, "synthetic-test-not-accounted")
    assert all((tmp_path / name).read_bytes() == data for name, data in pngs.items())
    assert {p.relative_to(PACK): p.read_bytes() for p in PACK.rglob("*") if p.is_file()} == before
