# T002-nist-isodb — машиночитаемые изотермы NIST ISODB

| Поле | Значение |
| --- | --- |
| task_id | T002-nist-isodb |
| Исполнитель | gpt-6.1-sol, reasoning effort **medium** (получение данных, код, тесты) |
| Сеть | on (только adsorption.nist.gov и сайты документации NIST) |
| Проверяющий | руководитель (выборочная сверка JSON с веб-интерфейсом ISODB) + T004 |
| Ограничения | Работать только в текущей директории. Не делать git commit. Не создавать `.github/`. |

## Цель

Установить, какие **машиночитаемые** изотермы CO2, N2 и H2O для UiO-66, UiO-66-NH2 и
PEI-модифицированных UiO-материалов есть в NIST/ARPA-E Database of Novel and Emerging Adsorbent
Materials (ISODB), и сохранить их неизменными копиями с происхождением.

## Шаги

1. Изучить API: https://adsorption.nist.gov/isodb/api/ (описание: https://adsorption.nist.gov/isodb/index.php#apis,
   https://www.nist.gov/programs-projects/nist-data-resources-adsorption). Определить эндпоинты
   материалов, адсорбатов, изотерм, библиографии. Зафиксировать условия использования данных NIST.
2. Найти материалы: все синонимы UiO-66 (включая «UiO-66(Zr)», «Zr-BDC», дефектные варианты),
   UiO-66-NH2, PEI-содержащие композиты.
3. Скачать JSON всех изотерм CO2, N2, H2O для них при 273–323 K. Сохранить **как получено** в
   `data/raw/nist_isodb/isotherms/<filename>.json`, плюс JSON материалов/библиографии.
4. `data/raw/nist_isodb/manifest.csv`: filename, url, sha256, bytes, accessed_utc, isotherm DOI/
   источник (поле публикации в ISODB), material, adsorbate, T_K, pressure_units, adsorption_units,
   n_points, category (exp/sim, если указано), digitizer (если указано).
5. `src/pet2mof/data/nist_isodb.py`: функции `fetch(...)` (сеть, только по явному вызову) и
   `load_isotherm(path) -> pandas.DataFrame` (давление в бар, ёмкость в ммоль/г, с явной конверсией
   единиц из полей JSON; неизвестные единицы → исключение, не догадка), `verify_manifest()` (SHA-256).
6. `tests/test_nist_isodb.py` (pytest, без сети): загрузка 1–2 сохранённых JSON, проверка конверсии
   единиц и SHA-256 манифеста.
7. `data/raw/nist_isodb/coverage.md` (русский): таблица покрытия материал × адсорбат × T, источник
   (DOI статьи) каждой изотермы, замечания (оцифровано ли NIST из рисунка — это важно: такие данные
   несут погрешность оцифровки и должны так помечаться), есть ли PEI-композиты, есть ли H2O.

## Критерии приёмки

* `pytest tests/test_nist_isodb.py` проходит без сети.
* Все файлы в манифесте с SHA-256; конверсия единиц явная.
* В финальном сообщении: сколько изотерм по каждому материалу/адсорбату, есть ли данные при 308 K
  или близких, каких данных нет.
