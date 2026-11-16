# T008c-security-rereview — повторная проверка исправлений T008b

| Поле | Значение |
| --- | --- |
| task_id | T008c-security-rereview |
| Исполнитель | gpt-6-astra, reasoning effort **medium** |
| Сеть | off; sandbox **read-only** |
| Проверяющий | руководитель |

Вход: `reviews/T008_security_review.md` (исходные замечания), `reviews/T008b_security_fixes.md` (отчёт
исполнителя — читать **после** собственной проверки), код `src/pet2mof/ocr/*`, `scripts/publish_check.py`,
`configs/publish_allowlist.yaml`, `.gitleaks.toml`, `.gitignore`, `.dockerignore`, `tests/test_security_fixes.py`.

Для каждого T008-01…08: исправлено полностью / частично / нет; воспроизведите исходный сценарий на новом коде
(в памяти или в `/tmp`-подобном пути, которое разрешает sandbox; если нельзя — анализом кода, с пометкой).
Ищите **новые** дефекты, внесённые исправлениями (обход грамматики `.env`, ложные PASS publish-check,
слишком широкие исключения allowlist). Финальное сообщение: таблица `id | статус | доказательство | остаток`,
затем новые находки в формате T008.
