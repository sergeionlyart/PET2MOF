# T045 — воспроизведение TASK-003 без сети

Дата: 17.11.2026. HEAD: `e8273a1932aec2dfa01c18eb1aea0b8602b2cdce`. Исходное дерево чистое. Python в `.venv`: 3.12.0 (системный `python3`: 3.11.5); uv 0.11.10; `.venv` существует. Фактические модель и reasoning effort текущий интерфейс не раскрывает; запуск через `scripts/agents/run_codex_task.sh` не подтверждён.

Локально создан временный клон этого HEAD в `/private/tmp/t045-repro-79113`; `.venv` подключено символьной ссылкой к существующему окружению, `.venv` и `.uv-cache` исключены через локальный `.git/info/exclude`. До `make task003-reproduce` `git status --porcelain` был пуст. Выполнение с `UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never`, без доступа к сети и `.env`; независимый скрипт запущен Python из `.venv`. Времена — прошедшее настенное время, секунды.

| Команда | Код | Время | Результат |
|---|---:|---:|---|
| `make task003-test` | 0 | 1,97 | 31 passed |
| `make task003-reproduce` | 0 | 26,90 | `scripts/run.py`: completed, паспорт создан |
| `.venv/bin/python scripts/task003_independent/recompute.py` | 0 | 0,05 | 232 строки, точные балансы, интервалы бисекции ≤ 10⁻¹² |
| `make report-task003` | 0 | 2,53 | три PDF построены |
| `make test` | 0 | 110,03 | 532 passed, 1 skipped, 5 warnings |

Пропуск `tests/test_c_series.py:212`: отсутствуют приватные исходные изображения `private/renders/T011-S105-Fig8A.png`, `Fig8B`, `Fig8C`, `Fig9` и `T011-S106-Fig4.png`; публичные изображения не заменяют исходное пиксельное доказательство. Предупреждения включают DeprecationWarning SWIG. `make` также сообщил о недоступности `DARWIN_USER_TEMP_DIR` и использовал `/tmp`.

## Сравнение с HEAD

Сравнение файлов в клоне с `git show HEAD:<путь>`; для CSV/JSON замена двух полных идентификаторов на один маркер выполнена на уровне байтов. Старый run_id: `20261117T083940795087Z-6b405b9f-task003-balance-map`; новый: `20261117T090136975420Z-e8273a19-task003-balance-map`.

- Все 12 созданных CSV основного расчёта (`analog_lines`, `design_window`, `input_evidence`, `material_balance`, `route_windows`, `s100_coordinate_envelopes`, `s2_pei_formula`, `sensitivity_rank`, `transfer_envelope`, `transfer_kstar`, `transfer_kstar_summary`, `uncertainty_vertices`) совпадают побайтово после замены run_id. `summary.json` также совпадает после замены run_id. Независимые `independent/recompute.csv` и `independent/recompute.json` совпадают побайтово без замены.
- `provenance.json` дополнительно отличается `commit_sha`, хешем `Makefile`, добавленной записью `scripts/task003/compare_independent.py` в implementation и хешами выходных файлов. Исходный provenance относится к более раннему коммиту `6b405b9f85d876aba81dd0d821b16f52dc95b5df`; текущий отражает HEAD и текущий состав реализации. Хеши выходов меняются вследствие run_id в CSV/JSON/MD и PNG. Поле `status` в обоих файлах — `debug_uncommitted_implementation`: оно определяется после записи результатов по текущему `git status`, поэтому новые отличия выходов делают дерево грязным, хотя перед запуском оно было чистым. Паспорт `scripts/run.py` сообщает `completed` и фиксирует HEAD.
- PNG сравнивались попиксельно в RGBA; размеры совпадают. Все отличия внутри подписи run_id: `analog_lines.png` — прямоугольник `[180, 829, 476, 843)`, размер 1680×868; `design_window.png` — `[172, 1077, 468, 1091)`, 1540×1120; `transfer_window.png` — `[172, 639, 468, 653)`, 1540×672. За этими областями пиксельных отличий нет.
- `decision_brief.pdf` и `next_experiment.pdf` идентичны побайтово. `final_report.pdf` имеет тот же размер 14 046 042 байта, отличается 19 005 байтами; первое и последнее отличие — смещения 5 833 487 и 13 823 406 (с нуля). При отрисовке обеих версий через `pdftoppm -r 72 -png` различаются только страницы 4–6, в областях подписей трёх графиков с run_id; остальные страницы пиксельно идентичны.

Отслеживаемые файлы исходного рабочего дерева не изменялись; commit не создан. Сравнение `independent_agreement.json` показало побайтовое совпадение с HEAD, но перечисленные команды его не пересоздают. Отдельный временный клон использован для защиты исходного дерева; это не самостоятельное воспроизведение установки окружения из `uv.lock`. Отдельное сетевое ограничение ОС для процесса не проверялось, но сетевые вызовы не выполнялись и uv работал в offline-режиме.
