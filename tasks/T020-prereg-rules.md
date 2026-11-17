# T020-prereg-rules — реализация D-18 и репетиция цепочки после тега

| Поле | Значение |
| --- | --- |
| task_id | T020-prereg-rules |
| Исполнитель | gpt-6.1-sol, reasoning effort **high** |
| Сеть | on — только uv/PyPI и официальный документ IAPWS SR1-86 |
| Проверяющий | T021 (независимая проверка до тега) |
| Ограничения | Только текущая директория. Не делать git commit/tag в этом репозитории (репетиция — только в отдельном временном клоне внутри текущей директории, например `.uv-cache/rehearsal/`). **Не открывать V-данные** (ветка `holdout/v1`, S2, S113, S103, S102, S117). Допуски/критерии не менять. `UV_CACHE_DIR=$PWD/.uv-cache`. |

Прочитать: `docs/decisions.md` (D-11, D-16…D-18), `docs/holdout_schema.md`, `docs/validation_protocol.md`,
`scripts/predict_holdout.py`, `scripts/validate.py`, `src/pet2mof/calibration/prediction.py`, `final.py`,
`scripts/reproduce_full.py`, `reviews/T018_freeze_prep.md`.

1. Реализовать **D-18** в `predict_holdout.py`/`prediction.py` (производные/применимость) и `validate.py`
   (условный режим, причины, раздельная отчётность полных и условных сравнений). Тесты на синтетике для каждого
   пункта D-18 (сухая серия; совпадающая T и неизвестная u_T; T вне калибровки; неизвестная u_exp).
2. **IAPWS:** сверить `model/gas.py` с официальным документом IAPWS SR1-86(1992) (коэффициенты и контрольные
   значения документа); сравнить с независимым значением p_sat(293 K)=0.02317544979505042 бар из T011. Тест.
3. **Однократность операторов:** тест, что MOF-база (`v1.1-mof`) и оператор D-11 применяются ровно один раз
   в пути `conditions → predictions` и согласованы с калибровкой на C.
4. **Определение U:** C-сторона (T015/T018) и V-сторона (`validate.py`) используют одно определение (равномерные
   границы/√3, общая/независимая доля); задокументировать в `docs/validation_protocol.md` как пояснение (без
   изменения допусков) и отличие от исторического T013.
5. Удалить или пересоздать `configs/frozen_parameters_provisional.yaml` (сейчас устарел; после T011c все C
   verified); после всех правок кода/конфигураций пересчитать `configs/frozen_parameters.yaml` и убедиться, что
   `scripts/calibrate_final.py` воспроизводит его побайтово.
6. **Репетиция цепочки** во временном клоне: временный тег `prereg-v1`, синтетические `holdout/v1/conditions.csv`,
   `observations.csv`; прогнать `make reproduce-full` с малым N (флаг/переменная только для репетиции),
   `predict_holdout.py`, синтетический `freeze.json`, `validate.py`. Выяснить и задокументировать, где лежат
   holdout-файлы, пока HEAD должен равняться тегу (не грязнит ли дерево; `.gitignore`?), и исправить препятствия.
   Итог — пошаговая инструкция `docs/post_tag_procedure.md`.
7. `make test` проходит. Отчёт `reviews/T020_prereg_rules.md`.
