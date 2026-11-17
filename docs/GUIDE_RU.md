# Путеводитель по PET2MOF

Короткая карта проекта для читателя статьи и для того, кто хочет проверить расчёт. Файлы не перемещались:
путеводитель указывает на существующие документы. Историю, отрицательные результаты и исправления не удаляли.

## Этапы, ветки и зафиксированные commit

| Этап | Вопрос | Статус | Ветка | Commit, на который ссылается статья |
| --- | --- | --- | --- | --- |
| TASK-001 (v1), разведочный | оптимум PEI и влажности для рабочей ёмкости CO₂ | **данных недостаточно** | `main` (опубликован) | `66bae26af9970c3142b72d25031c844b5461708f` |
| TASK-002 (v2) | какие измеренные PEI-образцы S2 приоритетны в сухом CO₂ | два кандидата, победитель не разрешён | `task002-dry-screening` | `1558433614619e04102989d6b6f1479c50f364ce` |
| TASK-003 (v3) | способ модификации PET-derived UiO-66 и граница выигрыша | **частично выполнено**, условная карта | `task003-pet-transfer` | `70685dc686ce22505b303a60920980a02772f019` |
| TASK-004 | статья о работе с агентской системой (без новых расчётов) | черновик для согласования | `task004-article` (локальная, не отправлена) | — |

Ветки идут цепочкой: каждая следующая создана от последнего commit предыдущей. **Старый `main` показывает только
TASK-001** — README, отчёт и выводы первого этапа; материалы TASK-002/003 видны в своих ветках, пока их не влили в
`main`. Теги: `prereg-v1` (заморозка прогнозов TASK-001 до раскрытия проверочной выборки), `holdout/v1` — ветка с
проверочной выборкой; ни то ни другое не менялось. `docs/history_rewrite_map.txt` — соответствие старых и новых
хешей одной очистки неотправленной истории 16.11.2026 (решение D-09), до первой публикации.

## Поручения и правила

| Документ | Что это | Кто автор |
| --- | --- | --- |
| [work_order_v1.1_RU.md](work_order_v1.1_RU.md) | исходное поручение TASK-001 | владелец (подготовка с ChatGPT) |
| [work_order_task002_RU.md](work_order_task002_RU.md) | сужение до сухого выбора кандидатов + пакет данных | владелец (подготовка с ChatGPT) |
| [work_order_task003_RU.md](work_order_task003_RU.md) | перенос на PET-derived UiO-66 | владелец (подготовка с ChatGPT) |
| [work_order_task004_RU.md](work_order_task004_RU.md) | статья (копия без адреса приватного репозитория сайта) | владелец (подготовка с ChatGPT) |
| [../AGENTS.md](../AGENTS.md) | обязательные правила команды | руководитель (Claude Code) |
| [model_policy.md](model_policy.md) | выбор моделей исполнителей и уровней рассуждений | руководитель |
| `../tasks/T0*.md` | карточки заданий исполнителям (T001–T025v, T030–T036, T040–T045, T050–T054r) | руководитель |

## Где решения, ошибки и проверки

* Решения: [decisions.md](decisions.md) (v1), [task002/decisions.md](task002/decisions.md),
  [task003/decisions.md](task003/decisions.md); планы анализа, зафиксированные до расчёта — `task002/analysis_plan.md`,
  `task003/analysis_plan.md`; предрегистрация — [prereg_status.md](prereg_status.md).
* Ошибки и исправления: `task002/error_log.md`, `task003/error_log.md`; для v1 — ревью в `../reviews/`.
* Ревью и воспроизведения: `../reviews/` (например T016 — чистое воспроизведение v1; T035/T035r — ревью v2;
  T044/T044r — ревью v3; T045 — воспроизведение v3 без сети).
* Учёт агентов: `../reviews/agent_contributions.md` (v1), `../reports/task002/agent_contributions.md`,
  `../reports/task003/agent_contributions.md`.

## Источники и данные

* Реестр публикаций и доступ: `../sources/registry.yaml`, `../sources/audit_report.md`, права —
  `../sources/LICENSES.md` (доступность статьи не означает права перепубликации).
* Паспорта извлечения: `../data/extraction/*.yaml`; пакет TASK-002: `../data/task002/PET2MOF_Task002_DataPack_v1.0/`;
  входы TASK-003: `../data/task003/`.
* Паспорта учитываемых запусков: `../runs/<run_id>/passport.json`; предрегистрированные — `../results/prereg-v1/`.

## Отчёты

* v1: `../reports/final_report.md` (+ PDF); v2: `../reports/task002/decision_brief.md`, `final_report_task002.md`;
  v3: `../reports/task003/decision_brief.md`, `final_report.md`, `next_experiment.md`.
* Статья TASK-004: `../publications/agentic-research-pet2mof/` (`index.html` открывается локально; источник —
  `article.ru.md`; доказательные материалы — `evidence/`; полные промпты — `prompts/`).

## Воспроизведение

Окружение: `uv sync --locked` (см. README). Ключи, сеть, платный OCR и модели ИИ не нужны. Основные команды:
`make test`, `make reproduce-demo`, `make task002-screen`, `make task003-test`, `make task003-reproduce`,
`make task003-agreement`; статья — `python3 -I publications/agentic-research-pet2mof/tools/build.py` и `check.py`.
