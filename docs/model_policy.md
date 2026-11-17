# Политика выбора моделей и reasoning effort

Источники: [`docs/model_policy_sources.md`](model_policy_sources.md) (T003, сверено руководителем
2026-11-16 по S12 и S13). Доступность — `~/.codex/models_cache.json` (fetched 2026-11-16T21:29Z,
codex-cli 0.166.0) и фактические запуски.

## Матрица

| Модель | Официальная рекомендация [S9–S13] | Роль в проекте | Фактическая доступность | Поддерживаемые настройки (Codex 0.166.0) | Проверка на типовой задаче (T000) |
| --- | --- | --- | --- | --- | --- |
| `gpt-6-astra` | наиболее способная; сложные рассуждения, исследования, документы | научная постановка, литература, выбор физмоделей, независимая экспертиза | да (cache + запуск) | low/medium/high/xhigh/max/ultra; default medium | RH→влажные доли: верно (Buck 1996, p_sat 5.6268 кПа), тест пройден; 44 с; 61 k вх./1.5 k вых. токенов |
| `gpt-6.1-sol` | сложное программирование, проф. задачи; близко к Astra дешевле; API default medium | основной код, данные, расчёты, проверка информации | да | low…ultra; default low (Codex) | верно (Buck 1981, 5.6267 кПа), тест пройден; 43 с; 96 k/1.6 k |
| `gpt-6.1-terra` | быстрая; визуальный анализ, текст, ограниченные исправления кода | нормализация, оформление, малые опыты по протоколу, сбор сведений | да | low…ultra в Codex (API дополнительно `none`); default low (Codex), medium (API) | верно (Buck 1996), тест пройден; 30 с; 46 k/1.2 k. T003 (сбор документации): принято без исправлений |

Эталон: IAPWS-95 даёт p_sat(35 °C) ≈ 5.629 кПа; расхождение корреляций Buck 0.04 % — допустимо для
планирования, в расчётах используется одна зафиксированная корреляция (см. `src/pet2mof/units.py`).

Производитель не гарантирует пригодность какой-либо модели для научных экспериментов или проверки
(S9–S13 этого не утверждают). Пригодность определяется приёмкой результатов по источникам и тестам.

## Правила назначения effort

* Стартовый уровень — по сложности и цене ошибки, не максимальный: `low` — механические задачи;
  `medium` — сбор/проверка информации, обычный код; `high` — научный анализ, безопасность, модели;
  `xhigh` — только если принятый результат на `high` требовал существенных исправлений.
* `ultra` запрещён (автоделегирование делает фактические модель/настройки непрослеживаемыми).
* Экономия оценивается по качеству принятого результата и времени исправлений (журнал ниже).

## Фиксация фактических настроек

JSON-события `codex exec --json` модель и effort **не раскрывают** (только `usage`). Фактически
применённые клиентом значения берутся из записи `turn_context` rollout-файла
`~/.codex/sessions/**/rollout-*-<thread_id>.jsonl` (`scripts/agents/actual_settings.py`) и
сохраняются в `private/agent_logs/<task>.*.exit.json`; публичная сводка — `reviews/agent_contributions.md`.
Ограничение: это настройки, применённые и отправленные клиентом; маршрутизация на стороне сервера
не наблюдаема. Самоотчёт модели о своём имени ненадёжен и не используется.

## Журнал назначений

| task_id | Запрошено | Фактически (rollout) | Итог приёмки | Исправления руководителя |
| --- | --- | --- | --- | --- |
| T000-smoke ×3 | terra/sol/astra, low | совпало | принято | нет |
| T003-model-docs | terra, medium | terra, medium | принято | нет |
| T001-source-audit | astra, high | astra, high | принято для независимой проверки; T004 нашла 7 пунктов исправлений и 1 пропущенный источник | исправления внесены через T009 |
| T002-nist-isodb | sol, medium | sol, medium | принято (SHA-256 сверен повторным запросом) | каталоги 18 МБ и веб-страницы NIST исключены из Git руководителем; 2 интеграционных теста — T010 |
| T004-audit-check | sol, medium | sol, medium | принято | нет |
| T005-infra-ocr-checks | sol, high | sol, high | принято после T005b; ревью T008 впереди | конфликт `tests/conftest.py` при слиянии разрешён руководителем |
| T005b-publish-check-allowlist | sol, medium | sol, medium | принято | нашёл сторонний Mapbox-токен в сохранённых страницах NIST (верно) |
| T006-extraction-pilot | sol, high | sol, high | принято после T007; V-часть — только на `holdout/v1` | условия S5 установлены руководителем сверкой с NIST (D-15) |
| T007-extraction-review | astra, medium | astra, medium | принято | нет |
| T008-security-review | astra, medium | astra, medium | принято: 8 дефектов | нет |
| T008b-security-fixes | sol, high | sol, high | принято после T008c | T008-09 исправлен руководителем |
| T008c-security-rereview | astra, medium, read-only | astra, medium, read-only | принято: 8/8 исправлены, найден T008-09 | исправление и регрессии — руководитель |
| T009-registry-update | terra, medium | terra, medium | принято | нет |
| T010-integration | sol, medium | sol, medium | принято | нет |
| T012-model-design | astra, high | astra, high | принято (D-06) | нет |
| T011-c-series | sol, high | sol, high | влито как `provisional`; ожидает T011v | нет |
| T013-implement-m1 | sol, high | sol, high | влито как debug; контроль S100 не пройден (D-16) | абсолютный путь в паспортах: переносимые пути, история переписана до влития; журналы stdout/stderr debug-прогонов не сохранены (клон удалён до копирования `private/run_logs`) |
| T011v-c-series-verify | astra, high | astra, high | принято: дефекты T011v-* → T011b | нет |
| T011b-c-series-fix | sol, high | sol, high | принято после T011v2 | нет |
| T011v2-c-series-reverify | astra, high | astra, high | принято: все 19 оцифрованных серий verified | нет |
| T011c-apply-reverification | terra, medium | terra, medium | принято | конфликт `tests/test_c_series.py` с T018 разрешён руководителем |
| T014-sourced-ranges | astra, high | astra, high | принято после T014v/T014b | нет |
| T014v-ranges-verify | sol, high | sol, high | принято | нет |
| T014b-ranges-metadata-fix | terra, medium | terra, medium | принято | нет |
| T015-model-revision | sol, high | sol, high | принято (D-17) | файлы npz 47 МБ убраны из коммита в `private/large_outputs/`; сужение `tests/test_nist_isodb.py` отменено |
| T018-freeze-prep | sol, high | sol, high | принято | конфликт слияния и импорт `hashlib` — руководитель |
| T019-holdout-extract | astra, high | astra, high | только `holdout/v1`; T019v нашёл 9 дефектов | нет |
| T019v-holdout-verify | sol, high | sol, high | принято: дефекты T019v-01…09 | нет |
| T019b-holdout-fix | astra, high | astra, high | принято после T019v2 с ограничениями (см. T023) | нет |
| T020-prereg-rules | sol, high | sol, high | принято (D-18, `docs/post_tag_procedure.md`) | нет |
| T021-pretag-review | astra, high, read-only | astra, high, read-only | принято: 3 существенных дефекта → T022 | нет |
| T022-pretag-fixes | sol, high | sol, high | принято после T021r | в истории `main` удалены абсолютные пути из отчёта T021 (руководитель) |
| T019v2-holdout-reverify | sol, high | sol, high | принято: 0 verified / 2 исправить / 4 excluded / 14 not_testable | 22 изображения S117 (лицензия не установлена) не публикуются; добавлены атрибуции |
| T021r-pretag-rereview | astra, high, read-only | astra, high, read-only | принято: T021-01…03 закрыты, тег допустим | нет |
| T023-holdout-testability | terra, high | terra, high | принято: по D-18 нет ни одной количественно проверяемой серии | нет |
| T019c-holdout-marker-fix | astra, medium | astra, medium | принято (T019v2-01) | нет |
| T019c2-holdout-consistency | terra, medium | terra, medium | принято | нет |
