# T034-task002-s100-model — Б: база кусочно-линейной интерполяции против минимальной изотермы (S100, 298 K)

| Поле | Значение |
| --- | --- |
| task_id | T034-task002-s100-model |
| Исполнитель | gpt-6.1-sol, reasoning effort **high** |
| Сеть | off |
| Проверяющий | T035 (gpt-6-astra, научное ревью), руководитель |
| Ограничения | Клон ветки `task002-dry-screening`. Не делать commit. Не менять `data/task002/` (только чтение), `docs/task002/analysis_plan.md` (правила обязательны, изменение — только через руководителя), v1-код и документы, `src/pet2mof/calibration/`, `src/pet2mof/task002/screening.py`. Новый код — `src/pet2mof/task002/s100.py`, `scripts/task002/s100_model.py`, тест `tests/test_task002_s100.py`, выходы — `reports/task002/B/`. `UV_CACHE_DIR=$PWD/.uv-cache`. Linear не используется; поручение — этот файл. |

Прочитать: `docs/work_order_task002_RU.md` §§4.2, 5Б; `docs/task002/analysis_plan.md` раздел Б (**все пункты 1–6
обязательны, в том числе правило выбора и правило подключения Toth, зафиксированные до подгонки**); пакет:
`data/benchmark/S100_dry_isotherms.csv`, `metadata/S100_internal_split.csv`, `data/quarantine/` (не использовать),
`scripts/reference_baseline.py`, `reference/S100_*`, `reference/baseline_summary.json`.

1. Независимая реализация базы (не импорт `reference_baseline.py`), повтор `S100_internal_baseline_residuals.csv`,
   `S100_nominal_shapes.csv`, MAE 0.028573177766352747 с допуском 1e-10 → `reports/task002/B/reproduce_baseline.json`.
2. Langmuir по fit-точкам, отдельно на образец; метрики проверки (MAE, max|res| на образец и суммарно) против базы;
   стандартные ошибки параметров по якобиану; флаги неустойчивости по плану → `langmuir_fit.csv`,
   `check_residuals.csv` (база и Langmuir рядом), `decision.json` (применённое правило выбора с числами).
3. Toth — только при срабатывании правила систематического недостатка; иначе в `decision.json` записать, что правило
   не сработало и Toth не подгонялся.
4. Чувствительность к полуширинам оцифровки (сдвиги q ±0.105, p ±0.042 по отдельности) → `sensitivity.csv`.
5. Рисунки: кривые с точками fit/проверки, база и Langmuir; остатки на проверке с полосой ±0.105 → PNG в
   `reports/task002/B/` с подписью наборов данных; рисунки детерминированы (фиксированные метаданные matplotlib).
6. Описательная подгонка по всем 48 точкам — отдельным файлом с пометкой «описание, не проверка».
7. Цель Makefile `task002-s100`; `make test` проходит. Отчёт `reviews/T034_s100_model_report.md` (рус.) с точной
   командой учитываемого запуска через `scripts/run.py`. Запрещено: экстраполяция, абсолютный расход сорбента по S100,
   регрессия по «истинной доле PEI», «оптимальные 30 мас.%», совместная подгонка S2 и S100, слова «слепая»/«внешняя
   проверка». Не делать commit.
