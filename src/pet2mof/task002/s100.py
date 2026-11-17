"""Independent S100 interpolation and separately fitted isotherms (reported units).

No reference implementation or quarantine input is used. All public predictions
are restricted to the pressure support supplied for the fit.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.special import expit

Q_HALF = 0.105
P_HALF = 0.042
EXPECTED_MAE = 0.028573177766352747
TOL = 1e-10
CHECK = "internal_interpolation_check"


@dataclass(frozen=True)
class Curve:
    sample: str
    ids: tuple[str, ...]
    p: np.ndarray
    q: np.ndarray
    fit: np.ndarray

    def shifted(self, dp=0.0, dq=0.0):
        return Curve(self.sample, self.ids, self.p + dp, self.q + dq, self.fit.copy())


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_curves(pack: Path) -> list[Curve]:
    rows = read_csv(pack / "data/benchmark/S100_dry_isotherms.csv")
    split = read_csv(pack / "metadata/S100_internal_split.csv")
    roles = {r["point_id"]: r["role"] for r in split}
    ids = [r["point_id"] for r in rows]
    if (len(rows) != 48 or len(set(ids)) != 48 or len(split) != 48
            or set(ids) != roles.keys() or set(roles.values()) != {"fit", CHECK}
            or sum(v == "fit" for v in roles.values()) != 39):
        raise ValueError("Expected the fixed 48-point S100 split (39 fit / 9 check)")
    for row in rows:
        if (row["legacy_status"] != "verified" or row["source_id"] != "S100"
                or float(row["T_K"]) != 298 or row["gas"] != "CO2"
                or float(row["q_digitization_halfwidth"]) != Q_HALF
                or float(row["p_digitization_halfwidth_bar"]) != P_HALF):
            raise ValueError("Unexpected S100 status, conditions or digitization halfwidth")
        expected = CHECK if .33 <= float(row["p_bar"]) <= .46 else "fit"
        if roles[row["point_id"]] != expected:
            raise ValueError("Fixed pressure-block split changed")
    curves = []
    for sample in sorted({r["sample_label"] for r in rows}):
        rr = sorted((r for r in rows if r["sample_label"] == sample), key=lambda r: float(r["p_bar"]))
        p = np.array([float(r["p_bar"]) for r in rr])
        q = np.array([float(r["q_mmol_per_g_reported"]) for r in rr])
        if not np.all(np.isfinite(p)) or not np.all(np.isfinite(q)) or np.any(p <= 0) or np.any(q <= 0) or np.any(np.diff(p) <= 0):
            raise ValueError("Invalid coordinates")
        curves.append(Curve(sample, tuple(r["point_id"] for r in rr), p, q,
                            np.array([roles[r["point_id"]] == "fit" for r in rr])))
    if len(curves) != 5:
        raise ValueError("Expected five separately fitted curves")
    return curves


def within_support(p, support):
    p, support = np.asarray(p, dtype=float), np.asarray(support, dtype=float)
    if (not np.all(np.isfinite(p)) or not np.all(np.isfinite(support))
            or support.size < 2 or np.any(np.diff(support) <= 0)
            or np.any(p < support[0]) or np.any(p > support[-1])):
        raise ValueError("Prediction outside ordered observed support is forbidden")
    return p


def interpolate(p, q, targets):
    targets = within_support(targets, p)
    q = np.asarray(q, dtype=float)
    if q.shape != np.asarray(p).shape or not np.all(np.isfinite(q)):
        raise ValueError("Invalid interpolation values")
    return np.interp(targets, p, q)


def baseline(curves):
    residuals, shapes = [], []
    for c in curves:
        check = np.flatnonzero(~c.fit)
        predicted = interpolate(c.p[c.fit], c.q[c.fit], c.p[check])
        for i, pred in zip(check, predicted):
            residuals.append(dict(point_id=c.ids[i], sample_label=c.sample, p_bar=float(c.p[i]),
                observed_q_reported=float(c.q[i]), predicted_q_reported=float(pred), residual=float(pred - c.q[i]),
                evidence="retrospective_internal_interpolation_check_NOT_external_validation"))
        q85 = float(interpolate(c.p, c.q, .85))
        for p in (.15, .50, .85):
            q = float(interpolate(c.p, c.q, p))
            shapes.append(dict(sample_label=c.sample, p_bar=p, q_reported_basis=q,
                q_over_q_at_0_85=q / q85, fraction_difference_to_0_85=1 - q / q85,
                interpretation="within_sample_adsorption_branch_shape_NOT_actual_desorption_or_cycle"))
    return residuals, shapes


def langmuir(p, qs, b):
    bp = b * np.asarray(p)
    return qs * bp / (1 + bp)


def langmuir_jacobian(p, qs, b):
    p = np.asarray(p)
    return np.column_stack((b * p / (1 + b * p), qs * p / (1 + b * p)**2))


def toth(p, qs, b, t):
    logbp = np.log(b * np.asarray(p))
    return np.exp(np.log(qs) + logbp - np.logaddexp(0.0, t * logbp) / t)


def toth_log_jacobian(p, log_parameters):
    """Jacobian in log(qs), log(b), log(t), used only for positive Toth fits."""
    qs, b, t = np.exp(log_parameters)
    z = np.log(b * np.asarray(p))
    a, sig = np.logaddexp(0., t * z), expit(t * z)
    return toth(p, qs, b, t)[:, None] * np.column_stack((
        np.ones(len(z)), 1 - sig, a / t - sig * z))


def systematic_deficiency(residuals):
    """Pressure-ordered fit residuals; exact zeros are omitted in sign counting."""
    r = np.asarray(residuals)
    if not np.all(np.isfinite(r)):
        raise ValueError("Nonfinite fit residuals")
    signs = np.sign(r[r != 0])
    changes = int(np.count_nonzero(np.diff(signs)))
    return dict(n_fit=len(r), sign_changes=changes, triggered=len(r) >= 8 and changes <= 2)


def parameter_diagnostics(parameters, jacobian, residuals, max_q):
    """Local unweighted OLS covariance s²(JᵀJ)⁻¹; not digitization uncertainty.

    SVD avoids squaring the condition number. Rank loss is reported as unknown
    standard errors, never as deceptively finite pseudoinverse errors.
    """
    parameters, jacobian, residuals = map(np.asarray, (parameters, jacobian, residuals))
    _, singular, vt = np.linalg.svd(jacobian, full_matrices=False)
    rank = int(np.count_nonzero(singular > np.finfo(float).eps * max(jacobian.shape) * singular[0]))
    dof = len(residuals) - len(parameters)
    full_rank = rank == len(parameters) and dof > 0
    if full_rank:
        covariance = (vt.T / singular**2) @ vt * float(residuals @ residuals) / dof
        se = np.sqrt(np.maximum(np.diag(covariance), 0))
        relative = se / parameters
        se_list, relative_list = se.tolist(), relative.tolist()
    else:
        covariance = None
        se_list = relative_list = [None] * len(parameters)
    relative_flag = not full_rank or any(v > .5 for v in relative_list[:2])
    capacity_flag = bool(parameters[0] > 3 * max_q)
    return dict(standard_errors=se_list, relative_standard_errors=relative_list,
        covariance=None if covariance is None else covariance.tolist(), jacobian_rank=rank,
        jacobian_condition=float(singular[0] / singular[-1]) if singular[-1] > 0 else None,
        degrees_of_freedom=dof, residual_variance=float(residuals @ residuals) / dof if dof > 0 else None,
        relative_se_gt_50pct=relative_flag, qs_gt_3maxq=capacity_flag,
        unstable=relative_flag or capacity_flag)


@dataclass
class Fit:
    model: str
    parameters: np.ndarray
    support: np.ndarray
    residuals: np.ndarray
    diagnostics: dict
    success: bool
    nfev: int
    optimality: float
    attempts: list[dict]

    def predict(self, p):
        p = within_support(p, self.support)
        function = langmuir if self.model == "Langmuir" else toth
        return function(p, *self.parameters)


def fit_isotherm(curve: Curve, model="Langmuir", *, all_points=False) -> Fit:
    if model not in {"Langmuir", "Toth"}:
        raise ValueError("Unsupported isotherm")
    mask = np.ones(len(curve.p), dtype=bool) if all_points else curve.fit
    p, q = curve.p[mask], curve.q[mask]
    if np.any(p <= 0) or np.any(q <= 0) or not np.all(np.isfinite(q)):
        raise ValueError("Positive finite coordinates required")
    function = langmuir if model == "Langmuir" else toth
    # Fixed starts, selected only by fit SSE, never by check-point errors.
    starts = [(2 * max(q), b / np.median(p)) for b in (.1, 1., 10.)]
    if model == "Toth":
        starts = [(*start, t) for start in starts for t in (.5, 1., 2.)]
    fits = []
    for start in starts:
        if model == "Langmuir":
            result = least_squares(lambda x: function(p, *x) - q, start,
                jac=lambda x: langmuir_jacobian(p, *x), bounds=(1e-12, np.inf),
                x_scale="jac", ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=10000)
        else:
            # Log coordinates preserve positivity over very large parameter
            # scales. Upper log limit 690 is a numerical overflow guard, not
            # a physical prior. Failed iterates remain diagnostic only.
            result = least_squares(lambda x: function(p, *np.exp(x)) - q, np.log(start),
                jac=lambda x: toth_log_jacobian(p, x), bounds=(np.log(1e-12), 690.),
                x_scale="jac", ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=10000)
            result.x = np.exp(result.x)
            result.jac = result.jac / result.x[None, :]
        fits.append(result)
    successful = [r for r in fits if r.success and np.isfinite(r.cost)]
    if not successful and model == "Langmuir":
        raise RuntimeError(f"{model} fit failed for {curve.sample}")
    result = min(successful or fits, key=lambda r: r.cost)
    # max(q) uses only the fitted subset, avoiding check leakage in diagnostics.
    diagnostics = parameter_diagnostics(result.x, result.jac, result.fun, max(q))
    diagnostics["systematic_deficiency"] = systematic_deficiency(result.fun)
    diagnostics["optimizer_failed"] = not bool(result.success)
    diagnostics["hit_numerical_bound"] = bool(np.any(result.active_mask))
    attempts = [dict(start=list(map(float, start)), success=bool(r.success),
        status=int(r.status), message=r.message, nfev=int(r.nfev), fit_sse=float(2 * r.cost),
        parameters=r.x.tolist(), active_mask=r.active_mask.tolist()) for start, r in zip(starts, fits)]
    return Fit(model, result.x, p, result.fun, diagnostics, bool(result.success),
               int(result.nfev), float(result.optimality), attempts)


def metrics(residuals):
    r = np.asarray(residuals, dtype=float)
    if r.size == 0 or not np.all(np.isfinite(r)):
        raise ValueError("Finite nonempty residuals required")
    return dict(n=len(r), mae=float(np.mean(np.abs(r))), max_abs_residual=float(np.max(np.abs(r))))


def select_model(baseline_mae, langmuir_mae, *, unstable=False):
    improves = langmuir_mae < baseline_mae
    unresolved = baseline_mae < Q_HALF and langmuir_mae < Q_HALF
    keep = not improves or unresolved or unstable
    return dict(selected="piecewise_linear" if keep else "Langmuir",
        baseline_mae=baseline_mae, langmuir_mae=langmuir_mae,
        langmuir_improves_mae=improves, both_below_digitization_halfwidth=unresolved,
        unstable_parameters=unstable, digitization_halfwidth=Q_HALF,
        reasons=(["Langmuir does not reduce pooled check MAE"] if not improves else [])
            + (["Both MAEs below digitization halfwidth; difference unresolved"] if unresolved else [])
            + (["Unstable parameters: retain interpolation (work order section 5B)"] if unstable else []))
