# T011c-apply-reverification — применение вердикта T011v2 к C-сериям

| Поле | Значение |
| --- | --- |
| task_id | T011c-apply-reverification |
| Исполнитель | gpt-6.1-terra, reasoning effort **medium** |
| Сеть | off |
| Проверяющий | руководитель |
| Ограничения | Только текущая директория. Не делать git commit. **Координаты/значения не менять.** Не изменять `reviews/T011v*`, `data/extraction/digitization/T011v*-control/`. `UV_CACHE_DIR=$PWD/.uv-cache`. |

`reviews/T011v2_reverification.md` признал **verified** все 7 серий, исправленных T011b (S105 Fig8A UiO-66, Fig8A UiO-66/GO,
Fig8C UiO-66/GO, Fig9 UiO-66, Fig9 UiO-66-NH2, Fig9 UiO-66/GO, S106 Fig4 UiO-66_160), в сохранённом диапазоне
(`usable_p_min_bar`), без исключаемых строк.

1. Внести T011v2 как источник решения в механизм статусов (`src/pet2mof/extraction/c_series_review.py` и связанные
   входы `scripts/extraction/build_c_series.py`): `status: verified`, `reviewer: T011v2`,
   `review_ref: reviews/T011v2_reverification.md`, `pending_review: null` для этих 7 серий.
2. Обновить строки `status` в CSV оцифровок, проекты, паспорта (`params.series.*`, общий `status`/`reviewer` паспорта,
   если все серии verified), `derived_sha256`; пересобрать `data/processed/c_series/` и `manifest.json` скриптом.
3. Проверить числовую неизменность: все столбцы, кроме `status`, побайтово равны прежним значениям (тест).
4. `make test` проходит (если `uv` не может разрешить зависимости offline — используйте `uv run --locked --no-sync`
   из каталога с `.venv`, или сообщите точную причину). Финальное сообщение — изменённые файлы и проверка.
