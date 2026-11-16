# T010-integration — интеграция T002 и T005

| Поле | Значение |
| --- | --- |
| task_id | T010-integration |
| Исполнитель | gpt-6.1-sol, reasoning effort **medium** |
| Сеть | on (только uv/PyPI) |
| Проверяющий | T008 + руководитель |
| Ограничения | Только текущая директория. Не делать git commit. `UV_CACHE_DIR=$PWD/.uv-cache`. Не трогать `sources/`. |

После слияния веток T002 (NIST ISODB) и T005 (инфраструктура) `make test` даёт 2 падения:

* `tests/test_nist_isodb.py::test_manifest` — `FileNotFoundError`: манифест ссылается на файлы,
  намеренно не включённые в Git: `data/raw/nist_isodb/catalogs/*.json` (18 МБ, повторно получаемы через
  API) и `data/raw/nist_isodb/docs/*.html` (веб-страницы NIST со встроенным сторонним токеном; не нужны
  для воспроизведения).
* `tests/test_nist_isodb.py::test_fetch_restricts_host` — `ModuleNotFoundError` (`requests` нет в зависимостях).

Сделать:

1. В `manifest.csv` добавить колонку `redistributed` (`true`/`false`) и `reason`; `verify_manifest()`
   проверяет SHA-256 всех `redistributed=true` и сообщает (не падает) об отсутствии `false`-файлов;
   отсутствие `true`-файла — ошибка. Тест на оба случая.
2. Сетевой код `fetch` — на стандартной библиотеке (`urllib.request`) или `requests` как optional extra
   `fetch` с ленивым импортом; тест без сети должен проходить в базовом окружении.
3. Удалить `requirements-nist.txt`, перенести зависимости в `pyproject.toml`; `uv lock`.
4. Единый стиль: модуль `src/pet2mof/data/nist_isodb.py` использует `pet2mof.units` для конверсий
   (включая `cm3(STP)/g` → mmol/g при 273.15 K и 101.325 kPa: 22.414 cm3/mmol; обосновать константу
   в docstring), если это не ломает тесты. Изотермы ровно при 308 K (`10.1016j.memsci.2012.04.003`,
   cm3(STP)/g) должны загружаться; `cm3/m2` по-прежнему отклоняются.
5. `make test`, `make test-ocr`, `make publish-check` — все проходят. В отчёте — вывод команд.
