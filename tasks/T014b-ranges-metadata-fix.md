# T014b-ranges-metadata-fix — исправление метаданных условий T014 по T014v

| Поле | Значение |
| --- | --- |
| task_id | T014b-ranges-metadata-fix |
| Исполнитель | gpt-6.1-terra, reasoning effort **medium** |
| Сеть | off |
| Проверяющий | руководитель (сверка с `reviews/T014v_ranges_verification.md`) |
| Ограничения | Только текущая директория. Не делать git commit. **Численные значения не менять.** Не открывать V-источники. `UV_CACHE_DIR=$PWD/.uv-cache`. |

Исправить дефекты **F01, F02, F03** из `reviews/T014v_ranges_verification.md` (раздел «Дефекты») ровно по
предложенным исправлениям: метаданные `conditions`/`locator` в `configs/sourced_ranges.yaml`,
`data/extraction/T014/*.json`, `data/extraction/records/T014-*.yaml`. Затем:
* пересчитать все зависящие хеши (`derived_sha256` в паспортах, хеши пакетов в `data/extraction/T014/inputs.json`
  или где они записаны) тем же способом, что T014 (найдите по коду/тестам);
* статусы записей T014 перевести в `verified` с `reviewer: T014v` и ссылкой на отчёт T014v (численные значения
  T014v признал совпадающими во всех 65 записях); `analog`/`unknown`/`assumption_range` пометки сохранить;
* `make test` целиком проходит. Финальное сообщение — список изменённых полей и файлов.
