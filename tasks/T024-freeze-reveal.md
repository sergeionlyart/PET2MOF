# T024-freeze-reveal — независимое раскрытие V и freeze.json (после `prereg-v1`)

| Поле | Значение |
| --- | --- |
| task_id | T024-freeze-reveal |
| Исполнитель | gpt-6.1-sol, reasoning effort **medium** (не разрабатывал модель и прогнозы) |
| Сеть | off |
| Проверяющий | руководитель |
| Ограничения | Клон с `main` на теге `prereg-v1` и веткой `holdout/v1`. Не делать commit, не менять отслеживаемые файлы, не переключать HEAD с тега. Запись — только в игнорируемый `holdout/v1/` и свой отчёт `reviews/T024_freeze_reveal.md` (неотслеживаемый файл вне научных путей). |

Строго по `docs/post_tag_procedure.md` §§3–4:
1. **До раскрытия**: проверить, что `holdout/v1/` содержит полный пакет прогнозов (`conditions.csv`, `predictions.csv`,
   `model_derivatives.csv`, `prediction_metadata.json`) и **не** содержит `observations.csv`; записать в отчёт UTC-время и
   SHA-256 четырёх файлов; сверить внутренние хеши `prediction_metadata.json`, `status=frozen_prediction`, SHA тега и
   `run_status` всех строк; `conditions.csv` побайтово равен `git show holdout/v1:holdout/v1/conditions.csv`.
2. **Раскрытие**: `git archive holdout/v1 holdout/v1/observations.csv | tar -x -C .`; записать UTC-время и SHA-256.
3. Проверить чек-лист §4 (единицы, основа массы, comparable/inputs_known, отсутствие 3 %-пола в `u_dig`, неизвестные `u_*`
   пусты, происхождение шкалы) — без изменения файлов; расхождения записать как замечания.
4. Создать `holdout/v1/freeze.json` строго по схеме §4; `reviewer` = `T024-freeze-reveal (gpt-6.1-sol/medium)`;
   `predictions_precede_disclosure: true` только если п.1 действительно выполнен до п.2.
`validate.py` не запускать (это делает руководитель).
