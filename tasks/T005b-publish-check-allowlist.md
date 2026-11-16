# T005b-publish-check-allowlist — точные исключения для publish-check

| Поле | Значение |
| --- | --- |
| task_id | T005b-publish-check-allowlist |
| Исполнитель | gpt-6.1-sol, reasoning effort **medium** (ограниченная доработка своего кода) |
| Сеть | off |
| Проверяющий | T008 (ревью безопасности) + руководитель |
| Ограничения | Только текущая директория. Не делать git commit. Не переписывать историю git. Не ослаблять правила глобально. |

Контекст (установлено руководителем): `make publish-check` падает только на ложных срабатываниях:

1. gitleaks `generic-api-key` (639 раз) — поле `"hashkey": "NIST-MATDB-<32 hex>"` в `data/raw/nist_isodb/**` —
   публичные идентификаторы материалов NIST ISODB.
2. gitleaks `generic-api-key` (1 раз) — поле `"key": "<цифры>_…"` в `sources/metadata/*.crossref.json` —
   ключи цитирований Crossref.
3. Текстовые правила (`absolute-user-path`, `authorization-literal`, `credential-literal`) срабатывают на
   **определения шаблонов** в `scripts/publish_check.py`, `src/pet2mof/ocr/security.py` и на описания правил
   в карточках `tasks/*.md`; `non-noreply-email` — на `test@example.org` в тестах.

Сделать:

* `.gitleaks.toml`: `[extend] useDefault = true` и **узкие** allowlist по regex совпадения (с `regexTarget = "match"`)
  и пути для п.1–2; не отключать правила целиком. Использовать этот конфиг во всех вызовах gitleaks в
  `scripts/publish_check.py` (рабочее дерево, staged, история). Проверить, что настоящий тестовый маркер
  (например фиктивный `sk-...`/`AIza...`-подобный ключ во временном файле **вне репозитория**, в `tmp_path`)
  по-прежнему ловится — добавить pytest.
* Текстовые правила: (а) e-mail в зарезервированных доменах RFC 2606 (`example.com/.org/.net`, `*.test`, `*.invalid`)
  не считать нарушением; (б) файл `configs/publish_allowlist.yaml`: записи `{path, check, reason, sha256}` —
  исключение действует, только пока SHA-256 файла совпадает (изменение файла ⇒ снова FAIL до повторного ревью);
  внести записи для перечисленных файлов с конкретными причинами; (в) в выводе publish-check печатать **пути**
  файлов с нарушениями (не содержимое совпадений), чтобы проверяющий мог разобраться.
* Тесты: allowlist по хешу работает и устаревает при изменении файла; RFC 2606-домены проходят, реальный
  домен — нет; gitleaks-конфиг не скрывает фиктивный секрет.
* Добавить `.gitleaks.toml` и `configs/publish_allowlist.yaml` в описание `docs/methodology.md` (раздел публикации).

Критерий приёмки: `make test`, `make test-ocr` проходят; `make publish-check` проходит на текущем дереве и
истории; новые тесты демонстрируют, что исключения узкие.
