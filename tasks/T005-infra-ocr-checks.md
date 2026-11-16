# T005-infra-ocr-checks — окружение, OCR-адаптер, паспорта, локальные проверки

| Поле | Значение |
| --- | --- |
| task_id | T005-infra-ocr-checks |
| Исполнитель | gpt-6.1-sol, reasoning effort **high** (безопасность секретов и прослеживаемость — высокий риск ошибки) |
| Сеть | on (только установка Python-пакетов через uv/PyPI) |
| Проверяющий | T008 (gpt-6-astra, независимое ревью кода безопасности) + руководитель |
| Ограничения | Только текущая директория. Не делать git commit. Не создавать `.github/`. Не создавать `.env`. Кэш uv: `export UV_CACHE_DIR=$PWD/.uv-cache` (вне директории запись запрещена sandbox). Платные/внешние OCR-вызовы НЕ выполнять — их нет в этой задаче. |

Прочитать сначала: `AGENTS.md`, `docs/security.md`, `docs/work_order_v1.1_RU.md` §§4.1–4.5, §8, §9, §10.

## 1. Окружение

* `pyproject.toml` (пакет `pet2mof` в `src/`), `requires-python = ">=3.11"`; зависимости с нижними
  и верхними границами: numpy, scipy, pandas, matplotlib, pyyaml, pymupdf, pillow, jsonschema, pytest.
  Внешние OCR-клиенты (`google-cloud-documentai`, `google-auth`, `requests`) — **optional extra**
  `ocr-cloud`, импортируются лениво; без них всё остальное работает.
* `uv lock` → `uv.lock` (зафиксированное окружение). `.venv/` через `uv sync`. Добавить `.uv-cache/` в `.gitignore`.

## 2. OCR-адаптер `src/pet2mof/ocr/`

* `config.py`: читает **только** корневой `.env` (путь — корень репозитория или явный аргумент),
  построчно, без `os.environ` и без экспорта; принимает только ключи из allowlist:
  `OCR_PROVIDER, OCR_EXTERNAL_ENABLED, OCR_BUDGET_USD, OCR_PAGE_LIMIT, OCR_PRICE_USD_PER_PAGE,
  MISTRAL_API_KEY, MISTRAL_OCR_MODEL, GOOGLE_CLOUD_PROJECT, GOOGLE_DOCUMENT_AI_LOCATION,
  GOOGLE_DOCUMENT_AI_PROCESSOR_ID, GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION, GOOGLE_SERVICE_ACCOUNT_JSON`.
  Прочие ключи (OPENAI_*, ANTHROPIC_*, STRIPE_* и т.д.) игнорируются, не хранятся в памяти.
  Секреты хранятся в объекте-обёртке, чей `repr/str` = `'***'`.
  Семантика: платный путь разрешён **только если** `OCR_EXTERNAL_ENABLED=true` И `OCR_PROVIDER ∈
  {mistral, google_docai}` И `OCR_BUDGET_USD > 0` И `OCR_PAGE_LIMIT > 0` И
  `OCR_PRICE_USD_PER_PAGE > 0` (неизвестная цена ⇒ запрет) И есть авторизация выбранного провайдера.
  Отсутствие `.env` или любых переменных ⇒ `local`. Нули ⇒ запрет, не «без ограничений».
  Добавить `OCR_PRICE_USD_PER_PAGE=` в `.env.example` и описать семантику в `docs/methodology.md` (§OCR).
* `readiness()` → dict статусов (`env_file: present/absent`, `provider`, `external_allowed: bool`,
  `reason`, `mistral_key: present/absent`, `google_credentials: absent/service_account_json/adc`)
  — **никогда** значения.
* Google: `GOOGLE_SERVICE_ACCOUNT_JSON` (соглашение проекта) разбирается в памяти,
  проверяются `type=="service_account"`, `project_id`, `token_uri=="https://oauth2.googleapis.com/token"`,
  затем `google.oauth2.service_account.Credentials.from_service_account_info(info, scopes=[cloud-platform])`
  без временных файлов. Альтернатива — ADC (`google.auth.default`). Mistral — `MISTRAL_API_KEY`,
  модель из `MISTRAL_OCR_MODEL` (пусто ⇒ запрет; `latest` допустим только с записью фактической версии из ответа).
* `ledger.py`: бюджет в `private/ocr_cache/ledger.json` — резервирование до вызова (страницы × цена),
  подтверждение/освобождение после; повторы при сбое (≤ 2) считаются оплачиваемыми; при достижении
  лимита, неизвестной цене, ошибке авторизации — остановка платного пути, без автопереключения на
  другой платный сервис. Файловая блокировка для параллельных задач.
* `cache.py`: ключ = SHA-256(входного файла) + страницы/области + преобразования + движок+версия +
  параметры; исходный ответ — неизменным в `private/ocr_cache/raw/<key>.json` (запись один раз,
  повторная запись запрещена); очищенная копия (без заголовков авторизации, подписанных URL,
  идентификаторов аккаунта) — отдельной функцией `sanitize()`.
* `local.py`: локальный путь — текстовый слой PyMuPDF; `pdftotext -layout` (если есть); tesseract
  (`/opt/homebrew/bin/tesseract`) для указанных страниц по рендеру 300 dpi. Метрики качества
  текстового слоя постранично (доля непечатаемых/заменяющих символов, доля цифр, признаки
  перемешанных колонок) — только как сигнал, не как критерий.
* `adapter.py`: `extract(input_path, pages, mode="local"|"external", purpose=...)`. Внешний режим
  вызывает сеть только при `external_allowed`. Логирование через фильтр, маскирующий любые значения
  секретов и строки вида `Bearer …`, `"private_key": …`.

## 3. Паспорта и данные

* `src/pet2mof/provenance/extraction.py` + JSON Schema `data/extraction/schema/extraction.schema.json`:
  поля §4.5 (`extraction_id`, `source_id`, doi/url, `input_sha256`, `pdf_page`, `api_page_map`,
  `figure_or_table`, `region`, `tool`, `tool_version`, `params`, `date`, `raw_response_ref`,
  `unit_conversions`, `derived_sha256`, `status ∈ {verified, provisional, excluded}`, `reviewer`,
  `corrections`, `error_estimate`, `data_kind ∈ {measured_table, digitized_markers, author_fit,
  simulation, text_value}`). Функция `require_measurement(record)` бросает исключение, если статус не
  `verified` или `data_kind ∈ {author_fit, simulation}`; `allow_provisional=True` разрешено только с
  пометкой `sensitivity_only`.
* `src/pet2mof/units.py`: конверсии ёмкости (mmol/g, mol/kg, mg/g, cm3(STP)/g, wt%), давления
  (bar, kPa, Pa, mbar, Torr, atm), нормировки «на массу MOF» ↔ «на массу композита» по загрузке PEI;
  разбор степеней и экспонент в строках (`1.2×10−3`, `1.2e-3`, `10^-3`, юникодный минус);
  неизвестные единицы ⇒ исключение.
* `src/pet2mof/extraction/digitize.py`: преобразование пикселей в данные по калибровочным точкам для
  линейных и логарифмических осей, распространение пиксельной погрешности в погрешность данных;
  чтение/запись проекта оцифровки (`*.digitization.yaml`: хеш изображения, калибровочные точки в
  пикселях и значениях, тип шкал, серии и пиксели маркеров, версия кода).
* `src/pet2mof/runs.py` + `scripts/run.py`: `run_id` (`<UTC>-<short-sha>-<name>`); отказ при грязном
  дереве (кроме `--allow-dirty` ⇒ `status: debug`); паспорт `runs/<run_id>/passport.json` по §8
  (гипотеза/назначение, commit SHA, версии python/библиотек, входы+SHA-256, параметры с единицами,
  seed, команда без секретов, время, статус, код выхода, ресурсы, выходы+хеши, проверки, ограничения).

## 4. Проверки

* `tests/` (pytest, без сети). `make test-ocr` запускает тесты с маркером `ocr`: локальный режим
  без ключей; отсутствие `.env` ⇒ local; нулевые лимиты ⇒ запрет; `OCR_EXTERNAL_ENABLED=true` без
  цены ⇒ запрет; чужие ключи (OPENAI_API_KEY=…) не читаются; маскирование в логах (фиктивные маркеры
  вида `TESTSECRET-<uuid>` в tmp `.env` — **не** реальные ключи) не появляются ни в логах, ни в
  `readiness()`, ни в кэше sanitize; неизменность raw-кэша; ledger (резерв/повтор/лимит);
  единицы/степени/лог-оси; `require_measurement`; паспорт извлечения валидируется схемой.
* `scripts/publish_check.py` → `make publish-check`: (а) `.env` не в индексе (`git ls-files`) и не
  в истории (`git log --all --format=%H -- .env '*.env'`), без чтения содержимого; (б) нет
  `.github/workflows/`; (в) `gitleaks detect --redact` по рабочему дереву (`--no-git`, с исключением
  `.venv`, `.uv-cache`, `private`) и по истории git; `gitleaks protect --staged --redact`;
  (г) поиск в отслеживаемых файлах: абсолютных путей `/Users/`, e-mail вне noreply-домена GitHub,
  `Bearer `, `private_key`; (д) `git config user.email` оканчивается на `@users.noreply.github.com`;
  (е) нет отслеживаемых файлов в `private/`, `data/raw/pdf/`, `data/raw/html/`; (ж) ноутбуки без
  выходов. Выход ≠ 0 при любой проблеме; вывод без значений секретов.
* `Makefile`: `test`, `test-ocr`, `publish-check`, `env` (uv sync); `reproduce-demo`, `reproduce-full`,
  `report` — пока цели, печатающие «not implemented yet (stage N)» и возвращающие код 2.

## Критерии приёмки

`make test` и `make test-ocr` проходят; `make publish-check` проходит на текущем дереве (без
коммита у вас он проверит рабочее дерево). В финальном сообщении: дерево файлов, результаты команд,
известные ограничения.
