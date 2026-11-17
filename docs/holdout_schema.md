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

Контракт T018 (не изменяет критерии проверки):

* `model` — `M1/<structure>/<reading>` или `B1/<structure>/<reading>`; структуры
  `v1`, `v1.1-mof`, `v1.1-connectivity`, прочтения `composite`, `ratio`.
  Удержанная загрузка `retained` уже является массовой долей и повторно не пересчитывается.
* `model_derivatives.csv` — `series,point_id,model,dq_dp,dq_dT,dq_da,u_num`;
  отдельный выход прогнозирования. Проверяющий не должен вручную переносить одну
  производную в общую колонку наблюдений для всех моделей.
* При наличии sidecar `freeze.json` дополнительно содержит
  `model_derivatives.csv_sha256` и `prediction_metadata.json_sha256`.
  Метаданные прогнозирования фиксируют хеши условий, параметров, прогнозов и производных.
* Пустая производная означает неизвестный отклик. Она даёт нулевой вклад в бюджет
  только при **точно нулевой** соответствующей входной неопределённости;
  неизвестная/ненулевая входная неопределённость делает такое сравнение `not_testable`.
  Неизвестный RH не считается сухим газом; неизвестная база не пересчитывается.
* T018 реализует количественный сухой оператор. Влажная химия PEI, водная ветвь
  без идентичности дефектного образца и температурный перенос однотемпературных
  параметров не идентифицированы: прогноз получает `not_testable` с причиной.
  Для S2 носитель — только S105 UiO-66-NH2, PEI — только S100, по D-11.
* `--dry-run --directory <synthetic-directory>` допускает только синтетический
  каталог внутри checkout вне `holdout/`; выход помечается `debug` и непригоден
  для `freeze.json`. Обычный запуск требует exact `prereg-v1` и неизменных
  научных файлов. Скрипт не открывает `observations.csv`.
