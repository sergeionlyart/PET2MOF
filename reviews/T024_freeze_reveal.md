# T024-freeze-reveal — независимое раскрытие V

Роль: независимый проверяющий · платформа: OpenAI Codex.
Назначено: gpt-6.1-sol / medium; фактические модель и effort интерфейсом не раскрыты, самоотчётом не подтверждаются.
В данной сессии модель и прогнозы не разрабатывались. Сеть не использовалась.
Карточка T024 получена явно в поручении пользователя; в snapshot тега файла tasks/T024-freeze-reveal.md нет.
Локальных .agents/skills и .claude/rules нет; применены AGENTS.md и docs/post_tag_procedure.md §§3–4.

## До раскрытия

Проверки завершены UTC: `2026-11-17T02:05:50.751870+00:00`. Эта запись сохранена до извлечения observations.csv.
HEAD detached и совпадает с prereg-v1: `e6dc3bd5550fb8d4092e2df6bd12afe9f7aaccfd`.
Ветка holdout/v1: `7f43d1de3fe884a315793d77936477b3d4e5f605`.
Исходное дерево чистое; observations.csv и freeze.json отсутствуют.
Полный пакет из четырёх файлов присутствует. conditions.csv побайтово равен git show holdout/v1:holdout/v1/conditions.csv.
Все четыре внутренних SHA-256 метаданных совпали, включая frozen_parameters.yaml.
metadata status=frozen_prediction, commit_sha равен тегу; все 2868 строк прогнозов имеют run_status=frozen_prediction.

| Файл | SHA-256 до раскрытия |
| --- | --- |
| conditions.csv | `1e6c89cf3d202feb5faf6b617f54d3853822ebdd85603a8a23b8d3ecfa400e5f` |
| predictions.csv | `a189a916ded2ceb3c32869787c54eec6e2f46753d81ea3c6af78cb3b333e9fc1` |
| model_derivatives.csv | `22e5774d15b4a8688afd39b918330ff046d93da7df76b4053044a1f221fd0f2c` |
| prediction_metadata.json | `cee52b5d38387b6a48e020515fb4f85b31c2b665438eee7d9b68a4e6e3b3369b` |

Проверки выполнены локальным Python (hashlib/csv/json) и read-only git; assertions пройдены, exit code 0. validate.py не запускался.

## Раскрытие

Команда: `git archive holdout/v1 holdout/v1/observations.csv | tar -x -C .` (exit code 0).
Завершено UTC: `2026-11-17T02:05:58.250455+00:00`.
observations.csv SHA-256: `d6530f7779ea57d87c6fc413a56dd4ec3bfb6a0c3c87fb3a8d8b89c0ea0de084`.

## Чек-лист §4

Проверено 239 строк, 20 серий: ключи уникальны, условия и наблюдения согласованы по series/point_id/source_id/extraction_id/observable. Раскрытый файл побайтово равен версии holdout/v1.

- Единицы: 227 строк mmol/g, 12 безразмерных отношений (unit=1). S103: cm³(STP)/g → mmol/g через 22.414 cm³/mmol (273.15 K, 101.325 kPa); S102: mol/kg численно равен mmol/g, неоднозначное давление не назначено total/partial.
- Массовая база: 220 dry_sorbent, 19 unknown; все unknown имеют comparable=false, inputs_known=false. S2 retained PEI — доля композита, не повторное преобразование label; отношения имеют общий знаменатель родительского образца.
- Флаги: comparable=true 104 / false 135; inputs_known=true 6 / false 233. Единственные true/true — 6 S2-Table1-Vp-ratio. Отсутствующие q: 6 качественных moist S2 и 4 S117 capacity placeholders, все false/false. S117 C/C0 не выдан за ёмкость. S103 десорбция и одиночный endpoint UiO66_160-adsorption исключены; S102 false/false.
- Неопределённости: u_exp и u_T пусты во всех 239 строках; u_a=0 только в 12 явно сухих строках, иначе пуста. u_p пуста в 49 строках; u_dig пуста в 34 (S2/S117). Заполненные u_* конечны и неотрицательны; общие dq_* пусты, производные остаются в model_derivatives.csv. Неизвестные не заменялись нулями и не оценивались по остаткам.
- Для всех 205 заполненных u_dig независимо пересчитана формула abs(slope)*sqrt((bound²+(1−t)²+t²)/3) из сохранённых pixel coordinates, per-point bounds и калибровок проектов ветки holdout/v1; совпадение rel_tol=1e-12. Экспериментальный 3 %-пол отсутствует. Паспорт задаёт стандартную неопределённость k=1 и прямоугольные границы; общая ошибка калибровки коррелирована между точками. S2 сообщает <3% без покрытия/распределения: u_exp, u_dig и scale оставлены пустыми.
- Происхождение scale проверено для всех 205 строк по scale_source_units проекта и фактору перевода: S113 Fig5a=1.6, Fig5b=0.16; S102 FigS6a/b/c=0.2; S103 Fig2a=95/22.414=4.238422414562327. Для S103 диапазон −5…90 cm³(STP)/g включает документированную нижнюю границу −5, выведенную из рамки и равномерных делений, а не амплитуду наблюдений. Для S2/S117 шкала ёмкости не придумана.

Источники проверки — git show holdout/v1:scripts/extraction/extract_holdout_v1.py, data/extraction/digitization/T019-*.digitization.yaml и data/extraction/records/T019-*.yaml в той же ветке (read-only, без checkout и исполнения extraction scripts).

## Замечания и пределы

1. S2: остаются неоднозначность 1 bar / 1 atm и состава потока, неизвестный RH смешанного опыта и незавершённая сверка исходного издательского макета. Численные dry/ratio/secondary строки имеют inputs_known=false; их допуск не утверждается. Vp-ratio true/true — декларация входов, не полный бюджет неопределённости и не вердикт валидации.
2. S103/S113: RH неизвестен, S102: T/RH/массовая база/смысл давления неизвестны. Это явно сохранено пустыми полями/флагами. S103 — неполные подмножества маркеров, не полные изотермы; возможная общая линия синтеза S103/S106 отмечена в условиях.
3. Паспорта остаются provisional/sensitivity_only с историческими pending-review записями. Эта проверка раскрытия не присваивает данным verified и не заменяет независимую визуальную сверку первоисточников. Новая оцифровка и проверка исходных страниц в данной задаче не выполнялись; проверены сохранённые проекты, формулы и происхождение шкал. Файлы не исправлялись.
4. Расхождений экспортированных u_dig/scale с проектами и нарушений порядка передачи в данном checkout не выявлено. Время/хеши фиксируют локальную последовательность данной сессии; утверждения о доступе иных участников за её пределами не делаются.

## Freeze и завершение

Создан holdout/v1/freeze.json строго с 8 полями §4; reviewer задан поручением. predictions_precede_disclosure=true подтверждает выполненную здесь последовательность: проверка и запись четырёх хешей до git archive observations. Исходный пакет повторно проверен по предраскрытийной записи, неизменен. validate.py не запускался.

UTC создания freeze: `2026-11-17T02:07:30.598557+00:00`; SHA-256 freeze.json: `1e8cd3ac72076f64f1ca2b1b0aa126d3bfb7ce0f5d26d19abe0b0a3b8306adcf`.

Итоговые проверки (Python assertions + git, exit code 0): HEAD остаётся exact prereg-v1; tracked/staged diff пусты; единственный untracked файл — этот отчёт; holdout/v1/freeze.json игнорируется; все пять хешей freeze совпали. Commit, push, переключение HEAD, validate.py и сеть не выполнялись.
