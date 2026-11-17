# T018-freeze-prep — подготовка фиксации модели (`prereg-v1`)

| Поле | Значение |
| --- | --- |
| task_id | T018-freeze-prep |
| Исполнитель | gpt-6.1-sol, reasoning effort **high** |
| Сеть | on — только uv/PyPI |
| Проверяющий | T016, руководитель |
| Ограничения | Только текущая директория. Не делать git commit. **Не искать, не открывать V-данные** (ветка `holdout/v1`, S2, S113, S103, S102, Madden). Не менять допуски/критерии `docs/validation_protocol.md`, `docs/hypotheses.md`. `UV_CACHE_DIR=$PWD/.uv-cache`. |

Прочитать: `AGENTS.md`, `docs/decisions.md` (D-06…D-17), `docs/holdout_schema.md`, `docs/validation_protocol.md`,
`docs/hypotheses.md`, `reviews/T015_revision_report.md`, `reviews/T015_screening.md`, `reviews/T014_ranges.md`,
`configs/sourced_ranges.yaml`, `scripts/validate.py`.

1. **`scripts/predict_holdout.py`** — читает только `holdout/v1/conditions.csv` (схема `docs/holdout_schema.md`),
   отказывает, если HEAD ≠ `prereg-v1` (флаг `--dry-run` для синтетических тестов без тега), пишет
   `holdout/v1/predictions.csv` и заполняет производные `dq_dp, dq_dT, dq_da` и `u_num` для `observations.csv`
   (отдельный файл `holdout/v1/model_derivatives.csv`, без чтения наблюдений). Модели: M1 (все структурные ветви
   v1/v1.1-mof/v1.1-connectivity × прочтения загрузки — отдельные `model`-метки) и B1. Для S2 — правило D-11
   (материал-носитель UiO-66-NH2 из C S105; PEI-параметры из S100-калибровки без переподгонки; несравнимые
   наблюдаемые — `not_testable`). Интервалы прогноза `prediction_low/high` — из неопределённости параметров
   калибровки (профили/ансамбль), с описанием метода. `scripts/validate.py` дополнить перебором всех `model`-меток.
2. **Итоговая калибровка** по `data/processed/c_series/` только `verified` (флаг для включения `provisional`
   как чувствительности): носитель UiO-66 и UiO-66-NH2 (S105), PEI (S100), вода (S106, три образца).
   Детерминированный скрипт `scripts/calibrate_final.py` → `configs/frozen_parameters.yaml` (с хешами входов).
3. **Продуктивный ансамбль** `scripts/ensemble.py`: по каждой ветви (механизм × структура × прочтение × перенос
   носителя × дефектность) 4 цепочки/повтора × 4096 наборов; две меры неизвестных — (а) стресс-диапазоны
   `configs/scenarios.yaml`, (б) ветвь чувствительности с аналоговыми диапазонами `configs/sourced_ranges.yaml`
   (только где они заданы; `unknown` остаются стрессовыми). Решающие правила `docs/hypotheses.md` (P(rank=1) ≥ 0.8,
   95 % контраст, 90 % интервалы w*) — вычислить по ветвям, **не объединяя ветви** в один prior. Сходимость:
   согласие повторов, удвоение сетки w на подвыборке. Время: сначала малый прогон; полный — оценить и доложить
   (CPU-тяжёлые расчёты по одному). Выход — `reports/ensemble/` (сводки JSON + карты состав × влажность
   по ветвям, PNG), крупные сырые массивы — в игнорируемые `*.npz` с SHA-256 в `SHA256SUMS.large`.
4. `make reproduce-full` — калибровка + ансамбль (полный); `make reproduce-demo` остаётся < 2 мин.
5. Тесты: синтетический `conditions.csv` → предсказания; отказ без тега; отсутствие чтения `observations.csv`
   в `predict_holdout.py`; детерминизм ансамбля по seed. `make test` проходит.

Отчёт `reviews/T018_freeze_prep.md`: что заморожено, команды, оценка времени полного ансамбля, результаты малого
прогона ансамбля (debug), ограничения.
