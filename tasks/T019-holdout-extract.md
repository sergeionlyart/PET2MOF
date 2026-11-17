# T019-holdout-extract — извлечение отложенных (V) серий на ветку `holdout/v1`

| Поле | Значение |
| --- | --- |
| task_id | T019-holdout-extract |
| Исполнитель | gpt-6-astra, reasoning effort **high** |
| Сеть | on — законный доступ к первоисточникам (издатели OA, Europe PMC REST, Crossref, Unpaywall); CAPTCHA/paywall не обходить |
| Проверяющий | T019v |
| Ограничения | Только текущая директория (клон ветки `holdout/v1`). Не делать git commit. Не изменять модельный код и `configs/`. `UV_CACHE_DIR=$PWD/.uv-cache`. |

Прочитать: `AGENTS.md`, `docs/data_split.md` (ред. 3), `docs/decisions.md` (D-11, D-14, D-16, D-17),
`docs/holdout_schema.md` (из main: приложен в `tasks/T019-holdout-schema.md`), `reviews/document_extraction_benchmark.md`,
паспорта `data/extraction/records/T006-S2*`, `T006-S113-*`, `T006-S103-*`, `T006-S102-*`, инструменты `scripts/extraction/`.

V-серии (целыми сериями, по `docs/data_split.md`):
1. **S113** Fig. 5a–b — CO2/N2 на UiO-66 (порошок), 35 °C — оцифровка (проект, калибровка, наложение, ошибка).
2. **S103** Fig. 2a — CO2 на UiO-66, 27 °C — оцифровка.
3. **S2** Table 1–2 — PEI@UiO-66-NH2 (сухие): удержанная загрузка PEI (входы D-11), сухой CO2 при 1 бар и 0.15 бар,
   пористость (Vp(w)/Vp(0)); «moist» — только как качественная запись (`comparable=false`, RH unknown).
4. **S102** SI Fig. S6 (бинарные CO2/H2O на UiO-66-NH2) и **Madden et al. 2021** SI Fig. S36–S38 (влажный CO2/N2
   на UiO-66/UiO-66-NH2), если законно доступны — оцифровка; иначе запись о недоступности.

Выход в `holdout/v1/`: `conditions.csv` (без наблюдаемых значений) и `observations.csv` по схеме
`tasks/T019-holdout-schema.md`; оцифровки/паспорта `data/extraction/digitization/T019-*`, `records/T019-*`
(`provisional` до T019v); исходные PDF и отрисовки — только в игнорируемых `data/raw/pdf/`, `private/`.
Стандартные неопределённости (`u_dig` — из оцифровки, `u_exp` — только если указана в источнике, иначе пусто;
`scale` — полная шкала оси). Отчёт `reviews/T019_holdout_extraction.md`. Ничего не выдумывать: неизвестное — пусто.
