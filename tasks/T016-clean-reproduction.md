# T016-clean-reproduction — независимая проверка воспроизводимости из чистого клона

| Поле | Значение |
| --- | --- |
| task_id | T016-clean-reproduction |
| Исполнитель | gpt-6-astra, reasoning effort **medium** |
| Сеть | **off** (зависимости — из скопированного локального кеша uv, `UV_OFFLINE=1`) |
| Проверяющий | руководитель |
| Ограничения | Клон без `.env`, без `private/`, без сети. Не делать commit. Ничего не публиковать. CPU-тяжёлый расчёт — единственный. |

Проверить, что воспроизведение не требует Claude, Codex, платного OCR, `.env` и коммерческих ключей (AGENTS §6.4, поручение):
1. Убедиться, что `.env` и `private/` отсутствуют; `UV_OFFLINE=1 UV_CACHE_DIR=$PWD/.uv-cache uv sync --locked`.
2. На `main`: `make test`, `make test-ocr`, `make reproduce-demo`, `make report`; записать exit-коды и краткий итог.
3. `git checkout prereg-v1` → `make reproduce-full` (≈18 мин, ≈12 ГБ). Сравнить `reports/ensemble/SHA256SUMS.large` и
   хеши `artifact_hashes` из нового `reports/ensemble/summary.json` с `results/prereg-v1/ensemble/` (с `main`:
   `git show main:results/prereg-v1/ensemble/summary.json`): совпадают побайтово или нет — по каждому файлу; при
   расхождении — где и насколько (без исправлений). Затем `git checkout main`.
4. Проверить, что `results/prereg-v1/holdout_v1/*` соответствует хешам `freeze.json` и что `validation.json` содержит
   commit_sha тега.
5. После проверки удалить сгенерированные `reports/ensemble/**/samples.npz` (≈12 ГБ) в своём клоне, сохранив их хеши в отчёте.
Отчёт: `reviews/T016_clean_reproduction.md` — команды, exit-коды, время, расхождения, ограничения.
