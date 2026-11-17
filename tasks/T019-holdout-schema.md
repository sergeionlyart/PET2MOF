# Схема отложенной проверки (контракт между извлечением V и замороженной моделью)

Файлы в `holdout/v1/` (только на ветке `holdout/v1` до тега `prereg-v1`):

* `conditions.csv` — **без наблюдаемых значений**; передаётся замороженному `scripts/predict_holdout.py`:
  `series, point_id, source_id, extraction_id, material, gas, observable, unit, basis, T_K, p_total_bar,
  p_partial_bar, y_CO2_dry, RH_fraction, w_PEI, w_reading, Mw_PEI, notes`.
  * `material`: `UiO-66` | `UiO-66-NH2` | `PEI@UiO-66-NH2` | иное (тогда `comparable=false` в наблюдениях).
  * `gas`: `CO2` | `N2` | `H2O` | `CO2+H2O`; `observable`: `q_CO2` | `q_N2` | `q_H2O` | `q_CO2_ratio_to_w0` |
    `Vp_ratio_to_w0`; `unit`: `mmol/g` | `1`; `basis`: `dry_sorbent` | `dry_MOF` | `unknown`.
  * Неизвестное — пустая ячейка (не 0). `w_PEI` и `w_reading` (`label`/`retained`) — входы D-11.
* `observations.csv` — столбцы `scripts/validate.py` (`series, point_id, source_id, extraction_id, q, u_exp, u_dig,
  u_p, u_T, u_a, dq_dp, dq_dT, dq_da, scale, observable, comparable, inputs_known`); `dq_*` заполняет
  `predict_holdout.py` (производные модели), остальное — извлечение V.
* `predictions.csv` — пишет только `scripts/predict_holdout.py` из `conditions.csv` при HEAD = `prereg-v1`.
* `freeze.json` — `commit_sha` (= `prereg-v1`), `reviewer`, `predictions_precede_disclosure: true`,
  SHA-256 `observations.csv` и `predictions.csv`.
