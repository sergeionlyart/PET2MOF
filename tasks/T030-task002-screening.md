# T030-task002-screening — приёмка пакета (обёртка) и расчёт А: сухое сравнение кандидатов S2

| Поле | Значение |
| --- | --- |
| task_id | T030-task002-screening |
| Исполнитель | gpt-6.1-sol, reasoning effort **high** |
| Сеть | off |
| Проверяющий | T033 (независимый пересчёт другим исполнителем и способом), T035 (научное ревью), руководитель |
| Ограничения | Клон ветки `task002-dry-screening`. Не делать commit. Не менять `data/task002/` (только чтение), v1-код и v1-документы, `src/pet2mof/calibration/`, `results/`, `configs/`. Новый код — `src/pet2mof/task002/`, `scripts/task002/`, тесты — `tests/test_task002_*.py`, выходы — `reports/task002/`. `UV_CACHE_DIR=$PWD/.uv-cache`. Linear в проекте не используется; это поручение — этот файл. |

Прочитать: `docs/work_order_task002_RU.md` (§§4.1, 5А, 7, 9), `docs/task002/analysis_plan.md` (раздел А — правила
обязательны), `docs/task002/intake.md`, `data/task002/PET2MOF_Task002_DataPack_v1.0/` (README_RU, docs/DATA_DICTIONARY_RU,
metadata/*, scripts/*, reference/*).

## 1. Обёртка приёмки пакета

`scripts/task002/accept_pack.py`: копирует пакет во временный каталог, проверяет манифест (две строки файлов поручения
исключаются явно и печатаются как исключение), запускает `scripts/check_data.py`, `python -m unittest discover -s tests`
и `scripts/reference_baseline.py` пакета **текущим интерпретатором** в копии, сравнивает побайтово `reference/*` и
`checks/data_check.json` с переданными, проверяет Git blob SHA-1 пяти `legacy_original/*.csv` против
`66bae26:data/processed/c_series/` и AST-идентичность `audit_fixture/prediction_excerpt.py` (`_number`, `evaluate`) с
`66bae26:src/pet2mof/calibration/prediction.py`. Выход — `reports/task002/intake/acceptance.json`. Ничего не пишет в
`data/task002/`.

## 2. Расчёт А

`src/pet2mof/task002/screening.py` (чистые функции) + `scripts/task002/screen_s2.py` → `reports/task002/A/`:

* `nominal.csv`: q, прирост к контролю, инвентарь `m` (кг/кг CO2), удержанный PEI в инвентаре, ценовой порог `q_i/q_0`;
  колонка типа величины (`measurement` / `author_calculated` / `our_derived`).
* `stress_independent.csv`: для d ∈ {0.03, 0.05, 0.10} интервалы q, прироста к контролю, `m`; флаг устойчивого
  преимущества над контролем. Соглашение пакета (`q(1±d)±0.005`).
* `stress_common_factor.csv`: общий множитель k = 1 ± d: отношения/ранги (инвариантны — показать численно) и `m`.
* `pairwise.csv`: все упорядоченные пары: отношение, интервалы отношения при d, флаг устойчивости, `d*` (с округлением,
  соглашение пакета) и `d*` без округления. Отдельно отметить C72/C96, C72/N72, C96/I96.
* `candidates.csv` и `candidates.md` (рус.): не более двух приоритетных кандидатов + контроль; классы «первый по
  номиналу» / «устойчиво выше контроля при d» / «различие не разрешено при d»; требуемая точность различения пары
  кандидатов; рядом (не в критерии) вторичные свойства с их `evidence_type` и `allowed_use`: alpha (отношение
  чистогазовых ёмкостей, не селективность смеси), суммарное поглощение смеси (не только CO2), авторская коррекция
  смеси (производная), влажный отклик (контекст), DSC (не энергия установки; пустые — `unknown`, не 0).
* `reproduce_reference.json`: наши `nominal`/`stress`/`pairwise` против `reference/S2_*.csv` пакета, допуск 1e-10
  (`metadata/analysis_contract.json`). Любое иное соглашение — в отдельных колонках, не вместо.

Запрещено: вероятности, p-value, Монте-Карло-усреднение сценариев, «победитель» при неразрешённом различии, перенос на
другое давление/температуру/смесь/PET-derived материал, отбор по вторичным свойствам вместо q.

## 3. Тесты и цели

`tests/test_task002_screening.py`: синтетические случаи формул (интервалы, d*, инвариантность к k, запрет пустого DSC
как 0), соответствие reference пакета. Цели Makefile: `task002-intake`, `task002-screen` (через `uv run --locked
--no-sync`). `make test` проходит целиком.

## 4. Сдача

Отчёт `reviews/T030_screening_report.md`: что сделано, точные команды для учитываемого запуска через `scripts/run.py`
(руководитель запустит после коммита), отклонения, ограничения. Не делать commit.
