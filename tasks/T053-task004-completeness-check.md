# T053-task004-completeness-check — проверка ссылок, реестров и комплектности статьи TASK-004

| Поле | Значение |
| --- | --- |
| task_id | T053-task004-completeness-check |
| Исполнитель | gpt-6.1-terra, reasoning effort **medium** |
| Сеть | off |
| Проверяющий | руководитель |
| Ограничения | Клон ветки `task004-article` на commit, указанном руководителем. Только чтение, кроме `publications/agentic-research-pet2mof/review/T053_completeness.md` и `publications/agentic-research-pet2mof/review/T053_checks/` (скрипты и JSON-выходы). Не делать commit. Не править статью и реестры. Не читать `.env`; сеть не использовать. |

## Что проверить (механически, скриптами stdlib, `python -I`)

1. **Комплект §11** `docs/work_order_task004_RU.md`: наличие каждого файла и каталога в
   `publications/agentic-research-pet2mof/`; перечислить отсутствующие.
2. **Ссылки статьи** `article.ru.md` и `index.html`: каждая `https://github.com/sergeionlyart/PET2MOF/blob|tree/<sha>/<path>`
   — sha из трёх зафиксированных и путь существует (`git cat-file -e <sha>:<path>`); каждый якорь `#…` есть в
   `index.html`; каждый локальный `src`/`href` существует; в `index.html` нет загрузок внешних ресурсов (`<script src>`,
   `<link href>`, `<img src>`, `url()`, `@import` на http/https).
3. **Реестр утверждений** `evidence/claims.csv`: для каждой строки путь существует на указанном commit; само
   утверждение найдено в источнике (число/формулировка — указать файл и строку/ячейку, где найдено); статус:
   `confirmed` / `mismatch` (с объяснением) / `not_checkable_mechanically`.
4. **Числа рисунков**: для каждого рисунка из `evidence/assets_manifest.csv` — файлы PNG/SVG существуют, есть alt и
   подпись в статье, числа в подписях совпадают с CSV-источником манифеста.
5. **Промпты**: `python -I publications/agentic-research-pet2mof/evidence/check_excerpts.py` — код выхода и вывод;
   каждый фрагмент из статьи (раздел «Промпты…») найден дословно в `evidence/prompts_manifest.csv` и в исходнике на
   commit.
6. **Сборка**: `python -I publications/agentic-research-pet2mof/tools/build.py` воспроизводит `index.html` байт-в-байт
   (сравнить хеши до/после во временном каталоге; рабочие файлы не менять); `tools/check.py` — код выхода и вывод.
7. **Научные выходы не изменены**: `git diff --stat 70685dc686ce22505b303a60920980a02772f019 -- reports data runs src
   scripts configs results holdout Makefile pyproject.toml uv.lock` — пусто.

## Выход

`review/T053_completeness.md`: таблица «проверка | результат | доказательство»; список несоответствий с точными
местами; что не проверено.
