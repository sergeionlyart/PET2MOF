# T036: независимое воспроизведение Task 002

Проверено 2026-11-17; исходный HEAD `fde8ceaa415b012af93126c36a48cca475b29de5`, ветка `task/T036-task002-clean-repro`. Запрошены gpt-6.1-terra / medium; фактические модель, effort и способ запуска через `scripts/agents/run_codex_task.sh` интерфейсом не подтверждены. Вывод: команды успешны, но заявленная идентичность только после нормализации `run_id` **не выполнена**, а полная сетевая изоляция и чистота импортов не доказаны.

## Подготовка и среда

- `git clone --no-hardlinks --no-local . .repro/clean` — код 0, HEAD совпадает. `test ! -e .repro/clean/.env` — 0 до и после запуска; `.env` вручную не открывался. Инструментального трассирования файловых открытий не было, поэтому отсутствие попыток чтения кода не доказано.
- `env -i HOME="$HOME" PATH="$PATH" LANG=C UV_CACHE_DIR=<основной клон>/.uv-cache uv sync --locked --offline` — код 2: при открытии `sdists-v9/.git` кэша получен `Operation not permitted`. Использована существующая `.venv` исходного worktree через симлинк `.repro/clean/.venv`; это fallback из карточки. Она содержит editable-установку `pet2mof`, указывающую на исходный worktree, а не на чистую копию. `git diff --exit-code HEAD -- src/pet2mof` — 0, но это ограничение независимости окружения. Симлинк `.venv` виден Git как неотслеживаемый файл в чистой копии; запуски не зарегистрированы и имеют `debug-unregistered`.
- Python 3.12.0, uv 0.11.10; numpy 2.5.5, scipy 1.18.1, pandas 3.1.1, matplotlib 3.11.2, pillow 12.3.0, pytest 9.2.0, PyYAML 6.0.3, pet2mof 0.1.0.
- `.repro/` в исходном worktree не игнорируется Git и отображается как untracked; commit не выполнялся.

## Команды и сеть

Каждая команда выполнена в `.repro/clean` через `env -i HOME="$HOME" PATH="$PWD/.venv/bin:$PATH" LANG=C /bin/bash`, без прокси в окружении. Время — настенные секунды с разрешением 1 с; журнал `.repro/commands.log`.

| Команда | Код | Секунды | Результат |
|---|---:|---:|---|
| `make test` | 0 | 88 | 501 passed, 1 skipped, 5 warnings |
| `make task002-intake` | 0 | 1 | acceptance passed |
| `make task002-screen` | 0 | 0 | reference passed |
| `make task002-s100` | 0 | 20 | выбран piecewise_linear |
| `python scripts/task002_independent/recompute.py` | 0 | 0 | выполнено |
| `python scripts/task002/compare_independent.py` | 0 | 0 | passed; max abs diff 1.4210854715202004e-14, несовпадений флагов 0 |

`env -i` не запрещает сетевые соединения и не доказывает отсутствие попыток. Попытка включить `(deny network*)` через `sandbox-exec` завершилась `sandbox_apply: Operation not permitted` (код 71); системного сетевого трассирования не было. В `tests/conftest.py` autouse fixture запрещает Python socket connect/create_connection/getaddrinfo в тестах, но не покрывает все дочерние процессы. Поиск `rg -n -i 'openai|anthropic|claude|codex|https?://|requests|urllib|socket|httpx|api|\.env' scripts/task002 scripts/task002_independent src/pet2mof/task002` не выявил обращений к LLM/API, сети или `.env` (совпадения `os.environ` — ложные по шаблону `.env`). Это статический поиск, не доказательство отсутствия косвенных вызовов зависимостей и не журнал сетевых попыток. В скриптах есть локальные subprocess-вызовы Git и Python.

## Сравнение с HEAD

Каждый отслеживаемый файл перечисленных каталогов сравнен побайтово с `git show HEAD:<путь>`. Для текстовых расхождений повторное побайтовое сравнение после замены токенов зарегистрированного `run_id` и `debug-unregistered` на общий маркер; иных полей не нормализовали. PNG дополнительно прочитаны Pillow и сравнены массивы numpy.

| Файл | Результат |
|---|---|
| `reports/task002/A/candidates.csv` | только run_id |
| `reports/task002/A/candidates.md` | только run_id |
| `reports/task002/A/independent_agreement.json` | только run_id |
| `reports/task002/A/nominal.csv` | только run_id |
| `reports/task002/A/pairwise.csv` | только run_id |
| `reports/task002/A/provenance.json` | отличается |
| `reports/task002/A/reproduce_reference.json` | только run_id |
| `reports/task002/A/stress_common_factor.csv` | только run_id |
| `reports/task002/A/stress_independent.csv` | только run_id |
| `reports/task002/B/S100_internal_baseline_residuals.csv` | только run_id |
| `reports/task002/B/S100_nominal_shapes.csv` | только run_id |
| `reports/task002/B/check_residuals.csv` | только run_id |
| `reports/task002/B/curves.png` | отличается; PNG пиксели отличаются: shape (980, 1680, 4)/(980, 1680, 4), elements 7182 |
| `reports/task002/B/decision.json` | только run_id |
| `reports/task002/B/descriptive_all48.csv` | только run_id |
| `reports/task002/B/langmuir_fit.csv` | только run_id |
| `reports/task002/B/optimizer_attempts.json` | только run_id |
| `reports/task002/B/provenance.json` | отличается |
| `reports/task002/B/reproduce_baseline.json` | только run_id |
| `reports/task002/B/residuals.png` | отличается; PNG пиксели отличаются: shape (980, 1680, 4)/(980, 1680, 4), elements 7182 |
| `reports/task002/B/sensitivity.csv` | только run_id |
| `reports/task002/B/toth_check_residuals.csv` | только run_id |
| `reports/task002/B/toth_fit.csv` | только run_id |
| `reports/task002/intake/acceptance.json` | отличается |
| `reviews/T033-control/recompute.json` | идентичен |

Оба PNG имеют размер 1680×980 RGBA; в каждом отличаются 2394 пикселя (7182 компонента), ограничивающий прямоугольник x=87..434, y=937..951. Код `scripts/task002/s100_model.py:193` помещает `run_id` в нижнюю подпись; расположение и одинаковая область отличий соответствуют изменению этой подписи. Вне этого прямоугольника пиксели идентичны.

Дополнительные различия JSON установлены через `git diff`: `A/provenance.json` — `execution_kind` и `head_sha`; `B/provenance.json` — `registration_status_at_generation`, `commit_sha` и SHA-256 `docs/task002/analysis_plan.md`; `intake/acceptance.json` — `head_sha`. Это реальные отличия сверх `run_id`, в том числе изменение входного документа, и они не скрыты нормализацией.

## Приёмка руководителем

Принято с ограничениями. Все числовые выходы А/Б совпали с точностью до `run_id`; различия `provenance.json` и
`acceptance.json` — метаданные: SHA текущего коммита (учитываемые запуски сделаны на более ранних коммитах),
вид исполнения и SHA-256 `docs/task002/analysis_plan.md`, изменённого поправкой E-05 **после** учитываемого запуска Б
(паспорт Б фиксирует план до поправки). PNG отличаются только в полосе подписи `run_id` (y = 937…951). Сетевую
изоляцию дополнительно подтверждает журнал запуска: фактический sandbox исполнителя `network_access = false` (rollout
`turn_context`). Ограничения: офлайн `uv sync` в sandbox не выполнился (нет доступа к кэшу), использован готовый
`.venv` с editable-установкой исходного клона (код `src/pet2mof` совпадал с HEAD).

## Дополнительное воспроизведение руководителем (закрытие ограничений T036)

Свежий `git clone --no-local` итогового коммита `032cb5a` во временный каталог; `.env` отсутствует; **собственное**
окружение `uv sync --locked --offline` (Python 3.12.0, `UV_OFFLINE=1`, кэш uv только для чтения пакетов) — `pet2mof`
импортируется из чистой копии. Все команды с `env -i` (HOME, PATH, LANG): `make test` (501 passed, 1 skipped),
`make task002-intake`, `make task002-screen`, `make task002-s100`, `scripts/task002_independent/recompute.py`,
`scripts/task002/compare_independent.py`, `make report-task002`, `make report` — все exit 0.
Сравнение с HEAD: 21 файл А/Б совпал до `run_id`; `provenance.json` и `acceptance.json` — только SHA коммита, вид
исполнения, статус регистрации и SHA-256 плана (поправка E-05 после учитываемого запуска Б); PNG — 2394 пикселя в
строках 937–951 (подпись `run_id`). PDF: `decision_brief.pdf` и v1 `final_report.pdf` побайтово совпали;
`final_report_task002.pdf` совпал побайтово после восстановления закоммиченных PNG (отличие было только во встроенной
подписи `run_id`). `reviews/T033-control/recompute.json` идентичен.
