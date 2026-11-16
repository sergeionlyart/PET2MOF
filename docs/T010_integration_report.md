1. Задача: T010-integration; база HEAD `0f4ce41435a2df20a9312fb5830b2254ecd1144b`, ветка `task/T010-integration`. Запрошены gpt-6.1-sol / medium; фактические модель и effort интерфейсом не раскрыты.
2. Манифест: добавлены `redistributed` и `reason`; 484 обязательных ответа, 8 нераспространяемых (4 каталога + 4 HTML). Отсутствие обязательного файла — ошибка; отсутствие нераспространяемого — предупреждение с причиной; присутствующие файлы обеих категорий проверяются по SHA-256 и размеру. Проверена также отдельная копия только из 484 распространяемых файлов: PASS, 8 предупреждений.
3. Зависимости: удалён `requirements-nist.txt`; pandas/pytest уже входят в базовый pyproject, requests добавлен в optional extra `fetch`. Импорт requests ленивый, после проверки URL; базовое окружение не содержит requests. `UV_CACHE_DIR=$PWD/.uv-cache uv lock` и `UV_CACHE_DIR=$PWD/.uv-cache uv sync --locked` → exit 0; сеть использовалась только uv.
4. Конверсии: NIST использует `pet2mof.units`; конвенция STP 273.15 K / 101.325 kPa, RT/P ≈ 22.414 cm3/mmol описана в docstring. Загружаются 268 из 296 изотерм; 28 отклоняются по единицам. Две cm3(STP)/g при 308 K из DOI 10.1016/j.memsci.2012.04.003 загружаются, cm3/m2 отклоняются. Обновлены генератор манифеста, текст генератора покрытия и coverage.md; исторический отчёт T002 и паспорт исходного извлечения сохранены.
5. Тесты: `make test` → exit 0, 100 passed; `make test-ocr` → exit 0, 63 passed / 37 deselected. В обоих прогонах 5 DeprecationWarning из PyMuPDF/SWIG. Проверены отсутствующие true/false-файлы, целостность присутствующих true/false-файлов, запрет чужого host без установленного requests, сохранённые изотермы 308 K и отказ cm3/m2. `git diff --check` → exit 0.
6. Публикация: `make publish-check` → exit 2 (внутренний скрипт exit 1): рабочее дерево и индекс проходят; gitleaks-all-history обнаруживает два исторических HTML. Коммит `c07cb17` добавил эти страницы, `6976583` удалил их из индекса, но не из истории. История и защитные правила не изменялись; требование трёх зелёных проверок пока не выполнено. Для устранения требуется отдельная санкционированная руководителем очистка истории и повторный publish-check.
7. Сдача: изменения оставлены в текущем worktree без commit/push; `sources/` не изменён, секреты и .env не читались. Независимая проверка T008 + руководитель остаётся pending. Полный генератор покрытия требует локальных нераспространяемых каталогов; в этой задаче он не запускался.

Вывод команд (основные строки stdout, без абсолютного пути checkout и повторяющихся предупреждений):

```text
$ make test
uv run --locked --no-sync pytest
collected 100 items
tests/test_nist_isodb.py ...................                             [ 19%]
tests/test_ocr.py ...............................................        [ 66%]
tests/test_provenance_units.py ................                          [ 82%]
tests/test_publish_allowlist.py .............                            [ 95%]
tests/test_runs_publish.py .....                                         [100%]
======================= 100 passed, 5 warnings in 15.18s =======================
exit 0

$ make test-ocr
uv run --locked --no-sync pytest -m ocr
collected 100 items / 37 deselected / 63 selected
tests/test_ocr.py ...............................................        [ 74%]
tests/test_provenance_units.py ................                          [100%]
================ 63 passed, 37 deselected, 5 warnings in 2.31s =================
exit 0

$ make publish-check
uv run --locked --no-sync python scripts/publish_check.py
PASS git-untracked-readable
PASS dotenv-not-in-index
PASS dotenv-not-in-history
PASS no-workflows
PASS no-private-tracked-files
PASS noreply-git-identity
PASS public-files-readable-no-symlinks
PASS public-text:absolute-user-path:files=0
PASS public-text:non-noreply-email:files=0
PASS public-text:authorization-literal:files=0
PASS public-text:credential-literal:files=0
PASS notebooks-without-outputs
PASS gitleaks-working-tree
FAIL gitleaks-all-history
FAIL gitleaks-all-history:path="data/raw/nist_isodb/docs/copyright.html"
FAIL gitleaks-all-history:path="data/raw/nist_isodb/docs/project.html"
PASS gitleaks-staged
publish-check: 1 failed checks
make: *** [publish-check] Error 1
exit 2
```
