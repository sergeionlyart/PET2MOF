#!/usr/bin/env python3
"""Task002 B: deterministic S100 interpolation/model comparison, without network."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

# Keep the local font cache inside the writable, ignored project cache.
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2] / ".uv-cache/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pet2mof.task002 import s100 as s

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "data/task002/PET2MOF_Task002_DataPack_v1.0"
OUT = ROOT / "reports/task002/B"
DATASET = "S100 / SI Fig. S5 / T006-S100-FigS5 / 298 K"
SOURCE = "data/task002/PET2MOF_Task002_DataPack_v1.0/data/benchmark/S100_dry_isotherms.csv"
INPUTS = [SOURCE, "data/task002/PET2MOF_Task002_DataPack_v1.0/metadata/S100_internal_split.csv",
    "docs/task002/analysis_plan.md", "docs/work_order_task002_RU.md",
    "src/pet2mof/task002/s100.py", "scripts/task002/s100_model.py",
    "data/task002/PET2MOF_Task002_DataPack_v1.0/reference/S100_internal_baseline_residuals.csv",
    "data/task002/PET2MOF_Task002_DataPack_v1.0/reference/S100_nominal_shapes.csv",
    "data/task002/PET2MOF_Task002_DataPack_v1.0/reference/baseline_summary.json"]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: "unknown" if v is None else v for k, v in row.items()} for row in rows)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def provenance_rows(rows, run_id, operation):
    for i, row in enumerate(rows, 1):
        row.update(run_id=run_id, extraction_id=f"T034-B-{operation}-{i:03d}",
            source_file=SOURCE, source_locator="S100 SI Fig. S5 / legacy T006",
            source_extraction_id="T006-S100-FigS5", quantity_type="our_derived",
            mass_basis="unresolved_reported_gram")
    return rows


def compare_reference(actual, expected, keys):
    """Every numeric reference field is checked after CSV serialization."""
    def keyed(rows):
        return {tuple(str(r[k]) for k in keys): r for r in rows}
    ours, theirs = keyed(actual), keyed(expected)
    errors, maximum, numeric_count = [], 0., 0
    if len(ours) != len(actual) or len(theirs) != len(expected) or ours.keys() != theirs.keys():
        errors.append("Missing or duplicate record keys")
    for key in sorted(ours.keys() & theirs.keys()):
        for field, target in theirs[key].items():
            value = ours[key].get(field, "<missing>")
            try:
                a, b = float(value), float(target)
            except (ValueError, TypeError):
                ok = str(value) == str(target)
            else:
                numeric_count += 1
                delta = abs(a - b)
                maximum = max(maximum, delta)
                ok = np.isfinite(a) and np.isfinite(b) and delta <= s.TOL
            if not ok:
                errors.append(dict(key=key, field=field, actual=value, expected=target))
    return dict(passed=not errors, rows=len(actual), numeric_fields_checked=numeric_count,
                max_absolute_error=maximum, errors=errors)


def fit_record(c, fit, purpose):
    d = fit.diagnostics
    mask = np.ones(len(c.ids), bool) if purpose == "описание, не проверка" else c.fit
    row = dict(sample_label=c.sample, model=fit.model, purpose=purpose, n_fit=len(fit.residuals),
        source_point_ids=";".join(pid for pid, use in zip(c.ids, mask) if use),
        p_min_bar=float(fit.support[0]), p_max_bar=float(fit.support[-1]),
        q_s_reported=float(fit.parameters[0]), b_per_bar=float(fit.parameters[1]),
        q_s_se=d["standard_errors"][0], b_se=d["standard_errors"][1],
        q_s_relative_se=d["relative_standard_errors"][0], b_relative_se=d["relative_standard_errors"][1],
        q_s_unit="mmol_per_reported_g", b_unit="bar^-1",
        jacobian_rank=d["jacobian_rank"], jacobian_condition=d["jacobian_condition"],
        degrees_of_freedom=d["degrees_of_freedom"], residual_variance=d["residual_variance"],
        covariance_qs_b=None if d["covariance"] is None else d["covariance"][0][1],
        relative_se_gt_50pct=d["relative_se_gt_50pct"], qs_gt_3maxq=d["qs_gt_3maxq"], unstable=d["unstable"],
        max_q_fitted=float(max(c.q[mask])),
        fit_mae=s.metrics(fit.residuals)["mae"], fit_max_abs_residual=s.metrics(fit.residuals)["max_abs_residual"],
        fit_sign_changes=d["systematic_deficiency"]["sign_changes"],
        fit_systematic_deficiency=d["systematic_deficiency"]["triggered"], success=fit.success,
        optimizer_failed=d["optimizer_failed"],
        hit_numerical_bound=d["hit_numerical_bound"],
        nfev=fit.nfev, optimality=fit.optimality)
    if fit.model == "Toth":
        row.update(t=float(fit.parameters[2]), t_se=d["standard_errors"][2], t_relative_se=d["relative_standard_errors"][2])
    return row


def compare_models(curves, fits):
    residuals, per_sample = [], {}
    for c in curves:
        mask = ~c.fit
        base = s.interpolate(c.p[c.fit], c.q[c.fit], c.p[mask])
        model = fits[c.sample].predict(c.p[mask])
        per_sample[c.sample] = dict(piecewise_linear=s.metrics(base - c.q[mask]),
                                   Langmuir=s.metrics(model - c.q[mask]))
        for i, b, m in zip(np.flatnonzero(mask), base, model):
            residuals.append(dict(point_id=c.ids[i], sample_label=c.sample, p_bar=float(c.p[i]),
                observed_q_reported=float(c.q[i]), baseline_prediction=float(b), langmuir_prediction=float(m),
                baseline_residual=float(b - c.q[i]), langmuir_residual=float(m - c.q[i]),
                q_digitization_halfwidth=s.Q_HALF, role=s.CHECK,
                fit_point_ids=";".join(pid for pid, use in zip(c.ids, c.fit) if use)))
    pooled = dict(piecewise_linear=s.metrics([r["baseline_residual"] for r in residuals]),
                  Langmuir=s.metrics([r["langmuir_residual"] for r in residuals]))
    return residuals, per_sample, pooled


def sensitivity(curves, nominal_fits, nominal_per, nominal_pooled):
    rows = []
    for scenario, dq, dp in (("nominal", 0., 0.), ("q_plus", s.Q_HALF, 0.),
            ("q_minus", -s.Q_HALF, 0.), ("p_plus", 0., s.P_HALF), ("p_minus", 0., -s.P_HALF)):
        shifted = [c.shifted(dp=dp, dq=dq) for c in curves]
        fits = nominal_fits if scenario == "nominal" else {c.sample: s.fit_isotherm(c) for c in shifted}
        _, per_sample, pooled = compare_models(shifted, fits)
        for c in shifted:
            fit, original = fits[c.sample], nominal_fits[c.sample]
            row = dict(scenario=scenario, sample_label=c.sample, dq_reported=dq, dp_bar=dp,
                scope="shift_all_48_coordinates_then_refit_same_39_and_check_same_9",
                interpretation="deterministic_shift_NOT_SD_or_confidence_interval",
                p_min_bar=float(c.p[0]), p_max_bar=float(c.p[-1]),
                q_s_reported=float(fit.parameters[0]), b_per_bar=float(fit.parameters[1]),
                delta_q_s=float(fit.parameters[0] - original.parameters[0]),
                delta_b=float(fit.parameters[1] - original.parameters[1]),
                relative_delta_q_s=float(fit.parameters[0] / original.parameters[0] - 1),
                relative_delta_b=float(fit.parameters[1] / original.parameters[1] - 1),
                unstable=fit.diagnostics["unstable"])
            for model in ("piecewise_linear", "Langmuir"):
                row[f"{model}_check_mae"] = per_sample[c.sample][model]["mae"]
                row[f"{model}_delta_check_mae"] = per_sample[c.sample][model]["mae"] - nominal_per[c.sample][model]["mae"]
                row[f"{model}_check_max_abs_residual"] = per_sample[c.sample][model]["max_abs_residual"]
                row[f"{model}_pooled_check_mae"] = pooled[model]["mae"]
                row[f"{model}_delta_pooled_check_mae"] = pooled[model]["mae"] - nominal_pooled[model]["mae"]
            row["selected_in_scenario"] = s.select_model(pooled["piecewise_linear"]["mae"], pooled["Langmuir"]["mae"],
                unstable=any(f.diagnostics["unstable"] for f in fits.values()))["selected"]
            rows.append(row)
    return rows


def plot_results(curves, fits, residuals, out, run_id):
    # Agg, fixed rcParams, fixed PNG metadata; no timestamps or random numbers.
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 9, "figure.dpi": 100,
                         "savefig.dpi": 140, "axes.formatter.useoffset": False}):
        for kind in ("curves", "residuals"):
            fig, axes = plt.subplots(2, 3, figsize=(12, 7), squeeze=False)
            for ax, c in zip(axes.flat, curves):
                if kind == "curves":
                    grid = np.linspace(c.p[c.fit][0], c.p[c.fit][-1], 300)
                    ax.plot(grid, s.interpolate(c.p[c.fit], c.q[c.fit], grid), label="piecewise linear", color="C0")
                    ax.plot(grid, fits[c.sample].predict(grid), label="Langmuir (fit only)", color="C1")
                    ax.scatter(c.p[c.fit], c.q[c.fit], marker="o", s=24, label="fit (digitized)", color="black")
                    ax.scatter(c.p[~c.fit], c.q[~c.fit], marker="s", s=40, facecolors="none", edgecolors="C3", label="internal check")
                    ax.set_ylabel("q, mmol / reported g")
                else:
                    rr = [r for r in residuals if r["sample_label"] == c.sample]
                    ax.axhspan(-s.Q_HALF, s.Q_HALF, color="grey", alpha=.18, label="digitization halfwidth ±0.105")
                    ax.axhline(0, color="black", lw=.6)
                    ax.plot([r["p_bar"] for r in rr], [r["baseline_residual"] for r in rr], "o-", label="piecewise linear", color="C0")
                    ax.plot([r["p_bar"] for r in rr], [r["langmuir_residual"] for r in rr], "s--", label="Langmuir", color="C1")
                    extent = 1.15 * max(s.Q_HALF, max(abs(r[key]) for r in residuals
                        for key in ("baseline_residual", "langmuir_residual")))
                    ax.set_ylim(-extent, extent)
                    ax.set_ylabel("Residual q, mmol / reported g")
                ax.set_title(c.sample)
                ax.set_xlabel("p, bar")
                ax.grid(alpha=.2)
            legend = axes.flat[-1]
            legend.axis("off")
            handles, labels = axes.flat[0].get_legend_handles_labels()
            legend.legend(handles, labels, loc="upper left", bbox_to_anchor=(0, .9), fontsize=8)
            note = "39 fit / 9 internal check\nMass basis unresolved\nAdsorption branch only"
            if kind == "residuals":
                note += "\nResidual = prediction − digitized q"
            legend.text(.03, .28, note, va="top", transform=legend.transAxes, fontsize=8)
            fig.suptitle(f"{DATASET} — {kind}")
            fig.text(.02, .015, f"run_id: {run_id}\nDataset: {SOURCE}", fontsize=7)
            fig.tight_layout(rect=(0, .07, 1, .95))
            fig.savefig(out / f"{kind}.png", metadata={"Software": "PET2MOF task002 S100 deterministic plot"})
            plt.close(fig)


def generate(out=OUT, run_id="debug-unregistered", *, plots=True):
    curves = s.load_curves(PACK)
    out.mkdir(parents=True, exist_ok=True)
    baseline, shapes = s.baseline(curves)
    comparisons = {}
    for name, rows, keys in (("S100_internal_baseline_residuals.csv", baseline, ("point_id",)),
                             ("S100_nominal_shapes.csv", shapes, ("sample_label", "p_bar"))):
        write_csv(out / name, provenance_rows(rows, run_id, name.removesuffix(".csv")))
        comparisons[name] = compare_reference(s.read_csv(out / name), s.read_csv(PACK / "reference" / name), keys)
    mae = s.metrics([r["residual"] for r in baseline])["mae"]
    reference_mae = json.loads((PACK / "reference/baseline_summary.json").read_text())["S100_internal_MAE_reported_units"]
    reproduction = dict(run_id=run_id, extraction_id="T034-B-baseline-reproduction", source_file=SOURCE,
        tolerance=s.TOL, mae=mae, expected_mae=s.EXPECTED_MAE, reference_mae=reference_mae,
        absolute_mae_error=abs(mae - s.EXPECTED_MAE), comparisons=comparisons,
        passed=all(v["passed"] for v in comparisons.values()) and abs(mae - s.EXPECTED_MAE) <= s.TOL and abs(mae - reference_mae) <= s.TOL)
    write_json(out / "reproduce_baseline.json", reproduction)
    if not reproduction["passed"]:
        raise RuntimeError("Independent baseline does not reproduce the open reference")
    fits = {c.sample: s.fit_isotherm(c) for c in curves}
    write_csv(out / "langmuir_fit.csv", provenance_rows([fit_record(c, fits[c.sample], "fit_only") for c in curves], run_id, "langmuir"))
    residuals, per_sample, pooled = compare_models(curves, fits)
    write_csv(out / "check_residuals.csv", provenance_rows(residuals, run_id, "check"))
    toth_fits, triggers = {}, {}
    for c in curves:
        trigger = fits[c.sample].diagnostics["systematic_deficiency"]
        triggers[c.sample] = dict(**trigger, toth_attempted=trigger["triggered"])
        if trigger["triggered"]:
            toth_fits[c.sample] = s.fit_isotherm(c, "Toth")
            triggers[c.sample].update(optimizer_success=toth_fits[c.sample].success,
                unstable=toth_fits[c.sample].diagnostics["unstable"],
                hit_numerical_bound=toth_fits[c.sample].diagnostics["hit_numerical_bound"],
                accepted_as_primary=False)
    toth_metrics = {}
    if toth_fits:
        write_csv(out / "toth_fit.csv", provenance_rows([fit_record(c, toth_fits[c.sample],
            "diagnostic_unstable_fit_NOT_accepted" if toth_fits[c.sample].success else "diagnostic_nonconverged_iterate_NOT_accepted_fit")
            for c in curves if c.sample in toth_fits], run_id, "toth"))
        toth_rows = []
        for c in curves:
            if c.sample not in toth_fits:
                continue
            pred = toth_fits[c.sample].predict(c.p[~c.fit])
            toth_metrics[c.sample] = dict(**s.metrics(pred - c.q[~c.fit]),
                optimizer_success=toth_fits[c.sample].success,
                interpretation="diagnostic only; nonconverged iterates are not accepted fits")
            for i, q in zip(np.flatnonzero(~c.fit), pred):
                toth_rows.append(dict(point_id=c.ids[i], sample_label=c.sample, p_bar=float(c.p[i]),
                    prediction=float(q), observed_q_reported=float(c.q[i]), residual=float(q - c.q[i]),
                    optimizer_success=toth_fits[c.sample].success, purpose="diagnostic_only"))
        write_csv(out / "toth_check_residuals.csv", provenance_rows(toth_rows, run_id, "toth-check"))
    write_json(out / "optimizer_attempts.json", dict(run_id=run_id, extraction_id="T034-B-optimizer-attempts",
        source_file=SOURCE, Langmuir={k: v.attempts for k, v in fits.items()},
        Toth={k: v.attempts for k, v in toth_fits.items()}))
    decision = dict(run_id=run_id, extraction_id="T034-B-decision", source_file=SOURCE,
        plan="docs/task002/analysis_plan.md section B, frozen before fits", n_fit=39, n_check=9,
        residual_convention="prediction_minus_digitized_observation", per_sample=per_sample, pooled=pooled,
        rule="Keep interpolation if Langmuir MAE >= baseline MAE OR both MAEs < 0.105; unstable parameters also retain interpolation (work order 5B)",
        selection=s.select_model(pooled["piecewise_linear"]["mae"], pooled["Langmuir"]["mae"], unstable=any(f.diagnostics["unstable"] for f in fits.values())),
        instability_rule="relative Jacobian SE > 50% for qs or b OR qs > 3 max(q_fit); rank loss = unknown SE / unstable",
        toth=dict(rule="fit n >= 8 AND pressure-ordered residual sign changes <= 2; exact zeros omitted",
            per_sample=triggers, attempted=bool(toth_fits), check_metrics=toth_metrics,
            explanation="Toth attempted only for triggered curves; inspect optimizer_success and instability" if toth_fits else "Rule did not trigger for any curve; Toth was not fitted",
            selection_policy="No additional Toth selection threshold preregistered; any triggered fit is diagnostic only"),
        standard_error_method="SSE/(n-k) times inverse(J.T J) via SVD; local OLS diagnostics, not digitization error SD",
        baseline_shapes="all 48 digitized points; within-sample adsorption branch ratios, not cycle capacity",
        interpretation="retrospective internal pressure-block interpolation check; no new independent observations")
    write_json(out / "decision.json", decision)
    write_csv(out / "sensitivity.csv", provenance_rows(sensitivity(curves, fits, per_sample, pooled), run_id, "sensitivity"))
    # Deliberately last: these parameters never enter the fit/check comparison.
    descriptive = [fit_record(c, s.fit_isotherm(c, all_points=True), "описание, не проверка") for c in curves]
    write_csv(out / "descriptive_all48.csv", provenance_rows(descriptive, run_id, "description"))
    if plots:
        plot_results(curves, fits, residuals, out, run_id)
    passport_path = ROOT / "runs" / run_id / "passport.json"
    status = json.loads(passport_path.read_text())["status"] if passport_path.exists() else "debug-unregistered"
    provenance = dict(run_id=run_id, registration_status_at_generation=status, extraction_id="T034-B-provenance", dataset=DATASET,
        commit_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        inputs=[dict(path=p, sha256=hashlib.sha256((ROOT / p).read_bytes()).hexdigest()) for p in INPUTS],
        source_extraction_id="T006-S100-FigS5", n_points=48, quarantine_used=False,
        requested_agent=dict(model="gpt-6.1-sol", reasoning_effort="high", network="off"),
        actual_agent_settings="not exposed by this interface; require launcher/rollout evidence from supervisor",
        optimizer=dict(method="scipy.optimize.least_squares / trf", weights="unweighted",
            bounds="each parameter >= 1e-12; Toth log(parameters) <= 690 as overflow guard", starts="qs=2max(q_fit); b=(0.1,1,10)/median(p_fit); Toth t=(0.5,1,2) only if triggered",
            selection="minimum successful fit SSE; if no Toth success, minimum failed SSE retained as diagnostic iterate", ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=10000,
            langmuir_jacobian="analytic", toth_jacobian="analytic in log coordinates, transformed to physical parameter Jacobian for SE; only if triggered"),
        limitations=["Mass denominator and retained PEI loading unresolved", "Digitization halfwidths are bounded scenarios, not standard deviations",
            "No extrapolation; shifted pressures evaluated within shifted fit support", "No empirical status upgrade or transfer to other materials"],
        outputs=sorted(p.name for p in out.iterdir() if p.is_file() and p.name != "provenance.json"))
    write_json(out / "provenance.json", provenance)
    print(f"S100 baseline MAE={mae:.17g}; Langmuir MAE={pooled['Langmuir']['mae']:.17g}; selected={decision['selection']['selected']}; Toth attempted={bool(toth_fits)}")
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="debug-unregistered")
    args = parser.parse_args()
    generate(run_id=args.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
