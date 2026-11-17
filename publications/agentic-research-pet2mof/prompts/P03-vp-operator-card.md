<!-- PET2MOF historical prompt
source_path: tasks/T032-task002-vp-operator.md
commit: ff214d87acf37cbdefab8412432edfb5e171b5de
blob_sha256: e792104cc46b3f0355c270d65058388821bcd4086658314e600db60f518be487
cleaning_edits: без правок
-->
# T032-task002-vp-operator — оператор отношения объёмов пор без лишних требований газовой адсорбции

| Поле | Значение |
| --- | --- |
| task_id | T032-task002-vp-operator |
| Исполнитель | gpt-6.1-sol, reasoning effort **medium** |
| Сеть | off |
| Проверяющий | T035 (gpt-6-astra, независимое ревью) и руководитель |
| Ограничения | Клон ветки `task002-dry-screening`. Не делать commit. Менять только `src/pet2mof/calibration/prediction.py` (функция `evaluate` и, при необходимости, вспомогательная функция рядом) и добавить `tests/test_task002_vp_operator.py`. Не менять `configs/`, `results/prereg-v1/`, `holdout/`, хешируемые документы v1, `scripts/predict_holdout.py`, `scripts/validate.py`, `data/task002/` (только чтение). `UV_CACHE_DIR=$PWD/.uv-cache`. Linear не используется; поручение — этот файл. |

Прочитать: `docs/work_order_task002_RU.md` §5В; `docs/task002/analysis_plan.md` раздел В;
`data/task002/PET2MOF_Task002_DataPack_v1.0/audit_fixture/` (исторический воспроизводитель дефекта на искусственных
данных — он **не** проверяет исправление); `src/pet2mof/calibration/prediction.py`; реальные строки `S2-Table1-Vp-ratio`
в `git show holdout/v1:holdout/v1/conditions.csv` (форма: `gas=N2`, `T_K=77`, RH и p пустые, `observable=Vp_ratio_to_w0`,
`unit=1`, `basis=dry_sorbent`, `w_reading=retained`, `Mw_PEI=600` для PEI-образцов).

## Дефект

`evaluate` для `Vp_ratio_to_w0` требует RH, `p_partial_bar`, CO2-носитель и совпадение температуры с T_fit PEI, хотя
возвращаемое выражение (`scale` или `scale/(1−w)`) от них не зависит.

## Что сделать

1. Вычислять `Vp_ratio_to_w0` веткой, которая не требует RH, `p_partial_bar`, газа CO2, CO2-носителя и температурного
   коэффициента PEI; `T_K` не обязателен (если задан — конечен и > 0). Сохранить требования: материал, basis, unit = `1`,
   `w_PEI` в [0, 1) и согласованность с материалом, `w_reading` ∈ {label, retained}, D-11 для S2 (retained и Mw = 600),
   прочтение `label`→`ratio`, `scale ≥ 0`. Для всех остальных наблюдаемых поведение побайтово прежнее.
2. Тест `tests/test_task002_vp_operator.py` импортирует **актуальную** `pet2mof.calibration.prediction.evaluate`
   (не копию из пакета) и проверяет на строке реальной формы S2 (без RH/p, N2, 77 K):
   * значение = формуле каждой модели/версии (B1, v1, v1.1-connectivity) для basis `dry_sorbent` и `dry_MOF`;
   * отказ сохраняется: неизвестный basis, неверная единица, w вне диапазона, w у немодифицированного материала,
     нарушение D-11, `scale < 0`;
   * `q_CO2` и `q_CO2_ratio_to_w0` по-прежнему требуют RH и `p_partial_bar` (отказ при их отсутствии);
   * тест **падает** на коде `66bae26` (проверить: временно восстановить старый `prediction.py` в клоне, прогнать,
     вернуть; результат записать в отчёт).
3. `make test` проходит целиком (включая `tests/test_freeze_prep.py`, `tests/test_prereg_rules.py`).
4. Отчёт `reviews/T032_vp_operator_report.md`: diff по смыслу, решение по температуре (почему T не требуется), вывод
   теста на старом и новом коде, что не меняется (прогнозы и проверка `prereg-v1` не пересчитываются; v1-статус
   `S2-Table1-Vp-ratio` остаётся `not_testable` из-за прочих блокеров T023). Не делать commit.
