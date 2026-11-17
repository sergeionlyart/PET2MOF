#!/usr/bin/env python3
"""Generate reproducible task002 A tables; no package reference code is imported."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from pet2mof.task002 import screening as s

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "data/task002/PET2MOF_Task002_DataPack_v1.0"
OUT = ROOT / "reports/task002/A"
REFERENCE_TABLES = {
    "nominal.csv": ("S2_nominal_metrics.csv", ("sample_id",)),
    "stress_independent.csv": ("S2_stress_intervals.csv", ("sample_id", "relative_halfwidth_design")),
    "pairwise.csv": ("S2_pairwise_thresholds.csv", ("sample_a", "sample_b")),
}


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def save(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compare_reference(actual: list[dict], expected: list[dict], keys: tuple[str, ...], tol: float) -> dict:
    """Compare every reference field, keyed by record identity; reject duplicates."""
    def key(row):
        return tuple(str(row[k]) for k in keys)
    ours = {key(row): row for row in actual}
    theirs = {key(row): row for row in expected}
    errors, max_error, count = [], 0.0, 0
    if len(ours) != len(actual) or len(theirs) != len(expected) or ours.keys() != theirs.keys():
        errors.append("record keys differ or are duplicated")
    for identity in ours.keys() & theirs.keys():
        for field, target in theirs[identity].items():
            count += 1
            value = str(ours[identity].get(field, "<missing>"))
            try:
                a, b = float(value), float(target)
            except ValueError:
                ok = value == target
            else:
                error = abs(a - b)
                ok = math.isfinite(a) and math.isfinite(b) and error <= tol
                max_error = max(max_error, error)
            if not ok:
                errors.append(dict(key=identity, field=field, actual=value, expected=target))
    return dict(passed=not errors, rows=len(actual), compared_fields=count,
                max_absolute_error=max_error, errors=errors)


def candidates_markdown(rows: list[dict], pairs: list[dict], run_id: str) -> str:
    candidates = [r for r in rows if r["sample_id"] != s.CONTROL]
    top, other = candidates
    pair = next(p for p in pairs if (p["sample_a"], p["sample_b"]) == (top["sample_id"], other["sample_id"]))
    lines = ["# Сухое сравнение S2 — кандидаты", "", f"run_id: `{run_id}`; набор: S2, Tables 1–2.", "",
        "Условия статьи: сухой чистый CO₂, 25 °C; в таблице 1 bar, в тексте 1 atm. "
        "Пересчёт на другое давление не выполняется. Приоритет задан только сухой q.", "",
        "| Образец | q, ммоль/г | Прирост, % | m, кг/кг CO₂ | PEI в m, кг | Ценовой порог | Класс |",
        "|---|---:|---:|---:|---:|---:|---|"]
    for row in rows:
        lines.append(f"| {row['sample_id']} | {row['q_dry_mmol_g']:.2f} | {row['gain_vs_base_pct']:.5f} | "
            f"{row['adsorbent_kg_per_kg_CO2_equilibrium_proxy']:.6f} | "
            f"{row['retained_PEI_kg_in_equilibrium_inventory']:.6f} | "
            f"{row['maximum_price_ratio_at_equal_single_loading_material_cost']:.6f} | "
            f"{row['nominal_class'] or row['role']} |")
    lines += ["", "q — measurement; удержанный PEI, % — author_calculated; "
              "прирост, инвентарь, PEI в инвентаре и ценовой порог — our_derived.", "",
              "| Образец | d | Сравнение с контролем | Сравнение двух кандидатов |",
              "|---|---:|---|---|"]
    for row in rows:
        for d in s.SCENARIOS:
            lines.append(f"| {row['sample_id']} | {d:.0%} | {row[f'control_class_d_{d:.2f}']} | "
                         f"{row[f'pair_class_d_{d:.2f}']} |")
    threshold = pair["max_common_relative_halfwidth_for_strict_A_gt_B"]
    lines += ["", f"Для пары {top['sample_id']}/{other['sample_id']} отношение q = {pair['q_ratio']:.10f}; "
              f"d* с округлением = {threshold:.10f} ({100*threshold:.6f}%), "
              f"без округления = {pair['d_star_without_rounding']:.10f}. "
              "Нужно строго d < d*, равенство границ не даёт преимущества. "
              "При 3/5/10% различие этой пары не разрешено; оба сохраняются для дальнейших исследований.", "",
              "Следующее измерение: повторить сухую равновесную q двух кандидатов и контроля "
              "на массе сорбента после одинакового outgassing, при одинаковых измеренных T и давлении. "
              f"Для ожидаемого разрыва обеспечить отдельные ограниченные относительные ошибки ниже {100*threshold:.6f}% "
              "при округлении не хуже ±0,005 ммоль/г; записать исходные повторы, массы, газ, влажность, "
              "калибровку и бюджет общей и независимой ошибок. Порог относится к текущим номиналам, "
              "новые измерения требуют повторной оценки. Он не задаёт число повторов или статистическую значимость.", "",
              "## Обязательные парные сравнения", "",
              "| Пара A/B | qA/qB | d* с округлением | d* без округления | Устойчиво A>B: 3/5/10% |",
              "|---|---:|---:|---:|---|"]
    for label in ("C72/C96", "C72/N72", "C96/I96"):
        a, b = ("S2-" + part for part in label.split("/"))
        p = next(p for p in pairs if (p["sample_a"], p["sample_b"]) == (a, b))
        flags = "/".join("да" if p[f"robust_A_gt_B_d_{d:.2f}"] else "нет" for d in s.SCENARIOS)
        lines.append(f"| {label} | {p['q_ratio']:.10f} | "
                     f"{p['max_common_relative_halfwidth_for_strict_A_gt_B']:.10f} | "
                     f"{p['d_star_without_rounding']:.10f} | {flags} |")
    lines += ["", "Различия подготовки и удержанного PEI не позволяют причинно приписать эффект одному фактору.", "",
              "## Вторичные свойства — рядом, вне критерия", "",
              "alpha — отношение чистогазовых ёмкостей, не селективность смеси. "
              "Поглощение смеси — суммарное CO₂+N₂, не только CO₂; коррекция авторов — производная. "
              "Влажный отклик — контекст с неуточнённой водой/RH. DSC — не энергия установки. "
              "Пустые DSC сохранены как unknown.", "",
              "| Образец | Свойство | Значение | Единица | evidence_type | allowed_use |",
              "|---|---|---:|---|---|---|"]
    metrics = ("alpha_pure_gas_capacity_ratio", "q_total_CO2_N2_mixture",
               "q_CO2_mixture_author_corrected", "q_moist_reported", "Qdes_DSC")
    for row in rows:
        for metric in metrics:
            lines.append(f"| {row['sample_id']} | {metric} | {row[metric]} | {row[metric+'_unit']} | "
                         f"{row[metric+'_evidence_type']} | {row[metric+'_allowed_use']} |")
    lines += ["", "Инвентарь описывает единственную равновесную загрузку из разгруженного материала; "
              "ценовой порог учитывает только равную стоимость материала на загрузку. "
              "Регенерация, ресурс, синтез и цикл не оценены. "
              "Сценарии — детерминированные границы, не доверительные интервалы.", "",
              "При общем множителе k отношения, приросты и ранги сохраняются (численные отклонения "
              "показаны в stress_common_factor.csv), m меняется как 1/k. "
              "Это сценарий общей шкалы, а не модель изменения изотермы с давлением.", "",
              "Источник: пакет PET2MOF_Task002_DataPack_v1.0, data/primary/S2_*.csv; "
              "S2 DOI 10.1021/acsomega.8b02319, Table 1 p.3189, Table 2 p.3192. "
              "Для C96 использовано 22,4% PEI из Table 1; 22,1% в заключении сохранено как расхождение. "
              "Смесь по расходам около 14,3% CO₂ против подписей 15%. "
              "Отдельная независимая сверка первоисточника и пересчёт — T031/T033/T035; "
              "настоящий расчёт не присваивает статус verified. "
              "Перенос на другие условия, смеси и PET-derived материал не установлен.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="debug-unregistered")
    args = parser.parse_args()
    contract = json.loads((PACK / "metadata/analysis_contract.json").read_text())
    if (tuple(contract["q_stress_halfwidth_relative"]) != s.SCENARIOS
            or contract["rounding_q_halfwidth_mmol_g"] != s.ROUNDING or contract["M_CO2_g_mol"] != s.M_CO2):
        raise ValueError("Analysis contract differs from implemented version")
    dry = load(PACK / "data/primary/S2_dry_CO2.csv")
    materials = load(PACK / "data/primary/S2_materials.csv")
    secondary = load(PACK / "data/primary/S2_secondary_properties.csv")
    qs = {r["sample_id"]: float(r["q_CO2_dry_mmol_g"]) for r in dry}
    pei = {r["sample_id"]: float(r["PEI_content_author_calculated_wt_pct"]) for r in materials}
    if len(qs) != 6 or len(dry) != 6 or len(materials) != 6 or qs.keys() != pei.keys():
        raise ValueError("Expected six unique matching S2 samples")
    nominal = s.nominal_metrics(qs, pei)
    pairs = s.pairwise_metrics(qs)
    tables = {"nominal.csv": nominal, "stress_independent.csv": s.independent_stress(qs),
              "stress_common_factor.csv": s.common_factor(qs), "pairwise.csv": pairs,
              "candidates.csv": s.candidate_metrics(qs, nominal, secondary)}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        for row in rows:
            row["run_id"] = args.run_id
        save(OUT / name, rows)
    (OUT / "candidates.md").write_text(candidates_markdown(tables["candidates.csv"], pairs, args.run_id), encoding="utf-8")
    comparisons = {}
    for name, (reference, keys) in REFERENCE_TABLES.items():
        # Re-read our emitted CSV so serialization is part of the check.
        comparisons[name] = compare_reference(load(OUT / name), load(PACK / "reference" / reference), keys,
                                              contract["numerical_check_abs_tol"])
    evidence = dict(run_id=args.run_id, absolute_tolerance=contract["numerical_check_abs_tol"],
                    passed=all(r["passed"] for r in comparisons.values()), comparisons=comparisons,
                    scope="open numerical reference reproduction, not blind or physical validation")
    (OUT / "reproduce_reference.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inputs = ["data/primary/S2_dry_CO2.csv", "data/primary/S2_materials.csv", "data/primary/S2_secondary_properties.csv",
              "metadata/analysis_contract.json", "metadata/source_discrepancies.json", "metadata/sources.json",
              "metadata/SHA256SUMS.txt", *("reference/" + ref for ref, _ in REFERENCE_TABLES.values())]
    provenance = dict(run_id=args.run_id, execution_kind="debug" if args.run_id == "debug-unregistered" else "see runs passport",
        head_sha=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        python_version=sys.version, inputs={p: hashlib.sha256((PACK / p).read_bytes()).hexdigest() for p in inputs},
        extraction_id_scope="Local calculation IDs T030-A-*; package transcriptions are cited, not newly independently verified",
        quantity_types={"q": "measurement", "retained_PEI_wt_pct": "author_calculated", "calculated_outputs": "our_derived"},
        limitations=["S2 only, source conditions; no transfer to PET-derived material", "not a cycle or process cost model",
                     "independent source verification and alternative arithmetic belong to T031/T033/T035"],
        command=["python", "scripts/task002/screen_s2.py", "--run-id", args.run_id])
    (OUT / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"S2: {len(nominal)} samples, {len(pairs)} ordered pairs; reference passed={evidence['passed']}")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
