# Защита секретов и приватных данных (рабочая методология, поручение §10)

## Состояние на 2026-11-16 (этап 0)

| Проверка | Результат |
| --- | --- |
| Корневой `.env` | **Отсутствует.** Внешний OCR отключён: `OCR_EXTERNAL_ENABLED` не задан ⇒ `false`, бюджет 0. |
| `.gitignore` до первого коммита | Да (`.env`, `.env.*`, `private/`, credential-файлы, ключи). |
| `.env` в индексе/истории | Проверяется `make publish-check` (`git ls-files`, `git log --all -- .env`), без вывода содержимого. |
| `.dockerignore` | Создан; Docker в цепочке воспроизведения не используется. |
| Сканер секретов | gitleaks (локально, `--redact`) — рабочее дерево, staged и вся история. |
| GitHub Actions | `.github/workflows/` не создаётся; Actions в настройках репозитория отключаются до первого push. |
| Git identity | `sergeionlyart <131160732+sergeionlyart@users.noreply.github.com>` (noreply). |

## Модель изоляции и её честные пределы

* `.env` читает только `src/pet2mof/ocr/adapter.py`, и только перечисленные ключи (`OCR_*`,
  `MISTRAL_API_KEY`, `MISTRAL_OCR_MODEL`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_DOCUMENT_AI_*`,
  `GOOGLE_SERVICE_ACCOUNT_JSON`). Файл разбирается построчно без экспорта в `os.environ`.
* `GOOGLE_SERVICE_ACCOUNT_JSON` — **соглашение проекта**, не стандартная переменная Google.
  Адаптер разбирает JSON в памяти и вызывает
  `google.oauth2.service_account.Credentials.from_service_account_info(...)` без временных файлов;
  проверяет `type == "service_account"`, наличие `project_id`, `token_uri == https://oauth2.googleapis.com/token`.
  Альтернатива — уже настроенный ADC. `GOOGLE_APPLICATION_CREDENTIALS`, если используется, — путь к файлу.
* Субагенты Codex запускаются `scripts/agents/run_codex_task.sh`: `--ignore-user-config`
  (пользовательский конфиг Codex с `danger-full-access` и плагинами почты/Drive не применяется),
  `env -i`, `shell_environment_policy.inherit=core`, отдельный git worktree, созданный из коммита
  (неотслеживаемые `.env` и `private/` в нём отсутствуют).
* **Ограничение:** все процессы работают под одним пользователем macOS. Sandbox Codex (seatbelt,
  `workspace-write`) ограничивает запись, но не чтение файлов вне рабочей директории. Права `600`
  и инструкция «не читать `.env`» не изолируют процессы одного пользователя. Поэтому мы **не
  утверждаем**, что ключи недоступны агентам. Реальная граница (отдельный пользователь macOS или
  контейнер без bind-mount корня проекта) пока не создана; до её создания владельцу рекомендуется
  не размещать в `.env` ключей с широкими правами и задавать минимальные IAM-роли
  (`roles/documentai.apiUser` на один процессор).
* Локальные ADC-файлы (`~/.config/gcloud/application_default_credentials.json`) также секретны;
  агентам доступ к ним не передаётся, но та же оговорка о чтении действует.

## Процедура при утечке

Публикация затронутого пакета блокируется; владелец уведомляется без значения секрета; ключ
отзывается/заменяется у провайдера; затем согласованно очищается история (`git filter-repo`) и
артефакты. Удаление файла следующим коммитом утечку не устраняет [S16].
