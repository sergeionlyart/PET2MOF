# T054r-task004-recheck — повторная проверка исправлений после T054

| Поле | Значение |
| --- | --- |
| task_id | T054r-task004-recheck |
| Исполнитель | gpt-6-astra, reasoning effort **high** |
| Сеть | off |
| Проверяющий | руководитель |
| Ограничения | Клон ветки `task004-article` на commit, указанном руководителем. Только чтение, кроме `publications/agentic-research-pet2mof/review/T054r_recheck.md`. Не делать commit, не править статью, не читать `.env`. |

## Что проверить

1. `git diff 1d23d0ee8b5b04eeeff26fabb0e1922021447823 HEAD -- publications/agentic-research-pet2mof/article.ru.md
   publications/agentic-research-pet2mof/evidence/claims.csv publications/agentic-research-pet2mof/tools/make_figures.py`
   — для каждого замечания T054-01…T054-09 из `review/T054_rewrite_review.md`: закрыто / частично / не закрыто,
   с местом в тексте и доказательством из первоисточников проекта (на `66bae26…`, `1558433…`, `70685dc…`).
2. Не внесли ли правки **новых** неверных или преувеличенных утверждений (каждый изменённый фрагмент).
3. Надпись на `assets/fig04_task002_dry.png` совпадает с подписью статьи и `data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary/S2_dry_CO2.csv` на `1558433…`.
4. Строки `claims.csv` C14, C33, C34, C42, C43, C45: пути существуют, ограничения соответствуют тексту.

## Выход

`review/T054r_recheck.md`: таблица `T054-id | итог | место | доказательство`; новые замечания (если есть) с уровнем;
что не проверено.
