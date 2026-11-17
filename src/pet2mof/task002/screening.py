"""Pure deterministic S2 screening; scenarios are bounds, not probabilities.

Input q is mmol/g adsorbent. Inventory is kg adsorbent/kg CO2 for one
equilibrium loading, with no cycle, process or material-transfer model.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

CONTROL = "S2-BASE"
SCENARIOS = (0.03, 0.05, 0.10)
ROUNDING = 0.005
M_CO2 = 44.01
HIGHLIGHTED = {
    frozenset(("S2-C72", "S2-C96")): "C72/C96",
    frozenset(("S2-C72", "S2-N72")): "C72/N72",
    frozenset(("S2-C96", "S2-I96")): "C96/I96",
}


def positive(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("A finite positive value is required")
    return value


def capacity_bounds(q: float, d: float, rounding: float = ROUNDING) -> tuple[float, float]:
    q = positive(q)
    if not math.isfinite(d) or not 0 <= d < 1:
        raise ValueError("Relative halfwidth must be in [0, 1)")
    if not math.isfinite(rounding) or rounding < 0:
        raise ValueError("Rounding halfwidth must be finite and nonnegative")
    lo, hi = q * (1 - d) - rounding, q * (1 + d) + rounding
    positive(lo)
    return lo, hi


def ratio_bounds(qa: float, qb: float, d: float, rounding: float = ROUNDING) -> tuple[float, float]:
    alo, ahi = capacity_bounds(qa, d, rounding)
    blo, bhi = capacity_bounds(qb, d, rounding)
    return alo / bhi, ahi / blo


def strict_threshold(qa: float, qb: float, rounding: float = ROUNDING) -> float:
    """A>B strictly only for d<d*. Negative thresholds are retained, not clipped."""
    qa, qb = positive(qa), positive(qb)
    if not math.isfinite(rounding) or rounding < 0:
        raise ValueError("Invalid rounding halfwidth")
    return (qa - qb - 2 * rounding) / (qa + qb)


def inventory(q: float, molar_mass: float = M_CO2) -> float:
    return 1000 / (positive(molar_mass) * positive(q))


def secondary_value(value: str) -> float | str:
    """An unreported heat (or other secondary value) is explicitly unknown."""
    if not value.strip():
        return "unknown"
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite secondary value")
    return number


def nominal_metrics(qs: Mapping[str, float], pei_pct: Mapping[str, float]) -> list[dict]:
    q0 = positive(qs[CONTROL])
    rows = []
    for sid, q in qs.items():
        q = positive(q)
        pei = float(pei_pct[sid])
        if not math.isfinite(pei) or not 0 <= pei <= 100:
            raise ValueError("Retained PEI must be a mass percentage in [0, 100]")
        mass = inventory(q)
        rows.append(dict(
            sample_id=sid, q_dry_mmol_g=q, gain_vs_base_pct=100 * (q / q0 - 1),
            adsorbent_kg_per_kg_CO2_equilibrium_proxy=mass,
            retained_PEI_kg_in_equilibrium_inventory=mass * pei / 100,
            maximum_price_ratio_at_equal_single_loading_material_cost=q / q0,
            interpretation="dry_single_loading_proxy_NOT_cycle_or_process_cost",
            q_quantity_type="measurement", retained_PEI_wt_pct=pei,
            retained_PEI_wt_pct_quantity_type="author_calculated",
            derived_quantity_type="our_derived",
            extraction_id=f"T030-A-nominal-{sid}",
            source_file="data/primary/S2_dry_CO2.csv;data/primary/S2_materials.csv",
            source_locator="S2 Table 2 p.3192; Table 1 p.3189",
        ))
    return rows


def independent_stress(qs: Mapping[str, float], scenarios: Sequence[float] = SCENARIOS) -> list[dict]:
    rows = []
    for sid, q in qs.items():
        for d in scenarios:
            lo, hi = capacity_bounds(q, d)
            blo, bhi = capacity_bounds(qs[CONTROL], d)
            rows.append(dict(
                sample_id=sid, relative_halfwidth_design=d, q_low=lo, q_high=hi,
                gain_low_pct=100 * (lo / bhi - 1) if sid != CONTROL else 0.0,
                gain_high_pct=100 * (hi / blo - 1) if sid != CONTROL else 0.0,
                robustly_above_base=lo > bhi if sid != CONTROL else False,
                interval_type="bounded_independent_stress_NOT_confidence_interval",
                inventory_low_kg_per_kg_CO2=inventory(hi),
                inventory_high_kg_per_kg_CO2=inventory(lo),
                quantity_type="our_derived", extraction_id=f"T030-A-stress-{sid}-{d}",
                source_file="data/primary/S2_dry_CO2.csv",
                source_locator="S2 Table 2 p.3192",
            ))
    return rows


def pairwise_metrics(qs: Mapping[str, float], scenarios: Sequence[float] = SCENARIOS) -> list[dict]:
    rows = []
    for a, qa in qs.items():
        for b, qb in qs.items():
            if a == b:
                continue
            threshold = strict_threshold(qa, qb)
            row = dict(
                sample_a=a, sample_b=b, q_ratio=qa / qb, gain_pct=100 * (qa / qb - 1),
                max_common_relative_halfwidth_for_strict_A_gt_B=threshold,
                negative_threshold_means_no_nominal_advantage=threshold < 0,
                interpretation="independent_symmetric_bounds_plus_0.005_rounding_per_value_NOT_probability",
                d_star_without_rounding=strict_threshold(qa, qb, 0),
                highlighted_pair=HIGHLIGHTED.get(frozenset((a, b)), ""),
                comparison_with_control=CONTROL in (a, b),
                quantity_type="our_derived", extraction_id=f"T030-A-pair-{a}-{b}",
                source_file="data/primary/S2_dry_CO2.csv", source_locator="S2 Table 2 p.3192",
            )
            for d in scenarios:
                tag = f"d_{d:.2f}"
                lo, hi = ratio_bounds(qa, qb, d)
                row[f"ratio_low_{tag}"] = lo
                row[f"ratio_high_{tag}"] = hi
                row[f"robust_A_gt_B_{tag}"] = capacity_bounds(qa, d)[0] > capacity_bounds(qb, d)[1]
            rows.append(row)
    return rows


def common_factor(qs: Mapping[str, float], scenarios: Sequence[float] = SCENARIOS) -> list[dict]:
    """Pure multiplicative scenario; no independent rounding noise is added."""
    rows = []
    rank = {sid: 1 + sum(other > q for other in qs.values()) for sid, q in qs.items()}
    for d in scenarios:
        for k in (1 - d, 1 + d):
            scaled = {sid: positive(q) * positive(k) for sid, q in qs.items()}
            for sid, q in qs.items():
                ratio = scaled[sid] / scaled[CONTROL]
                rows.append(dict(
                    sample_id=sid, relative_halfwidth_design=d, k=k, q_scaled_mmol_g=scaled[sid],
                    ratio_to_base_nominal=q / qs[CONTROL], ratio_to_base_scaled=ratio,
                    ratio_delta=ratio - q / qs[CONTROL],
                    gain_nominal_pct=100 * (q / qs[CONTROL] - 1), gain_scaled_pct=100 * (ratio - 1),
                    rank_nominal=rank[sid],
                    rank_scaled=1 + sum(other > scaled[sid] for other in scaled.values()),
                    max_abs_all_pair_ratio_delta=max(
                        abs(scaled[sid] / scaled[b] - q / qb) for b, qb in qs.items()),
                    inventory_nominal_kg_per_kg_CO2=inventory(q),
                    inventory_scaled_kg_per_kg_CO2=inventory(scaled[sid]),
                    inventory_expected_1_over_k=inventory(q) / k,
                    quantity_type="our_derived", extraction_id=f"T030-A-common-{sid}-{d}-{k}",
                    source_file="data/primary/S2_dry_CO2.csv", source_locator="S2 Table 2 p.3192",
                ))
    return rows


def candidate_metrics(qs: Mapping[str, float], nominal: Sequence[dict], secondary: Sequence[dict],
                      scenarios: Sequence[float] = SCENARIOS) -> list[dict]:
    """Choose at most two by dry q alone; secondary properties never enter selection."""
    selected = sorted((s for s in qs if s != CONTROL), key=lambda s: (-qs[s], s))[:2]
    threshold = strict_threshold(qs[selected[0]], qs[selected[1]]) if len(selected) == 2 else None
    rows = []
    for sid in selected + [CONTROL]:
        row = dict(next(r for r in nominal if r["sample_id"] == sid))
        row["extraction_id"] = f"T030-A-candidate-{sid}"
        row["role"] = "контроль" if sid == CONTROL else "приоритетный кандидат"
        row["nominal_class"] = "первый по номиналу" if sid == selected[0] else ""
        row["candidate_pair"] = "/".join(selected)
        row["required_relative_halfwidth_strictly_below"] = threshold
        row["selection_criterion"] = "только сухая q; вторичные свойства — контекст"
        for d in scenarios:
            row[f"control_class_d_{d:.2f}"] = (
                "контроль" if sid == CONTROL else
                "устойчиво выше контроля при d" if capacity_bounds(qs[sid], d)[0] > capacity_bounds(qs[CONTROL], d)[1]
                else "преимущество над контролем не разрешено при d")
            row[f"pair_class_d_{d:.2f}"] = (
                "не применяется к контролю" if sid == CONTROL or threshold is None else
                "различие не разрешено при d" if d >= threshold else "различие разрешено при d")
        for prop in secondary:
            if prop["sample_id"] != sid:
                continue
            metric = prop["metric"]
            row[metric] = secondary_value(prop["value"])
            for key in ("unit", "evidence_type", "allowed_use", "source_id", "source_locator", "missing_reason"):
                row[f"{metric}_{key}"] = prop[key]
            row[f"{metric}_extraction_id"] = f"T030-A-secondary-{sid}-{metric}"
        rows.append(row)
    return rows
