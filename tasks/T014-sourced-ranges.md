# T014-sourced-ranges — источниковые диапазоны параметров, от которых зависит вердикт

| Поле | Значение |
| --- | --- |
| task_id | T014-sourced-ranges |
| Исполнитель | gpt-6-astra, reasoning effort **high** |
| Сеть | on — законный доступ к литературе (издатели OA, Europe PMC REST, Crossref, Unpaywall, NIST); CAPTCHA/paywall не обходить |
| Проверяющий | T014v / T016 |
| Ограничения | Только текущая директория. Не делать git commit. **Не открывать** V-источники (`docs/data_split.md`: S2, S113, S103, S102, Madden 2021) и их данные. Не менять модельный код и допуски. `UV_CACHE_DIR=$PWD/.uv-cache`. |

Прочитать: `AGENTS.md`, `docs/decisions.md` (D-06…D-17), `docs/model_spec.md`, `docs/parameters.md`,
`reviews/T015_screening.md`, `configs/scenarios.yaml`, `configs/revision.yaml`, `sources/registry.yaml`.

## Задача

Для параметров, от которых зависит вердикт (D-17 п.3): **τ/t** (время релаксации CO2/H2O на PEI-сорбентах при
адсорбции/регенерации), **Q_W** (теплота адсорбции воды на UiO-66), **γ** (влияние влажности на доступность аминов
PEI), **κ / V_p0 / α_in** (потеря порового объёма/доступности при импрегнировании PEI в UiO-66 и родственные MOF),
**W_max, h_max** (сорбция воды PEI, доля бикарбонатного пути), **Q_phys** (теплота физсорбции CO2 на UiO-66),
**Q_d** (теплота хемосорбции CO2 на PEI), **f3** (доля третичных аминов разветвлённого PEI) — найти первичные
количественные данные и задать **диапазоны** (не точки) с происхождением.

* Каждый диапазон: значение(я), единицы, условия (T, RH, материал, Mw PEI, метод), тип записи (прямое измерение /
  авторская подгонка / симуляция / аналог), `source_id` (новые источники — в `sources/registry.yaml` с DOI,
  сверенным Crossref, лицензией) и `extraction_id` (паспорт `data/extraction/records/T014-*.yaml` по схеме).
* Аналоги (PEI/SiO2, PEI в других MOF) допустимы только как помеченные `analog` с обоснованием переносимости.
* Если первичных данных нет — `unknown` и широкий стресс-диапазон с явной пометкой `assumption_range`; не
  подменять догадкой LLM.
* Выход: `configs/sourced_ranges.yaml` (машиночитаемо; формат совместим с `configs/scenarios.yaml`:
  value/range, unit, type, source_id, extraction_id, status `provisional`), `reviews/T014_ranges.md`
  (таблица параметр | диапазон | источник/страница/таблица | тип | переносимость | ограничения), тест загрузки
  `tests/test_sourced_ranges.py` (каждое число имеет происхождение). `make test` проходит.
