# T009-registry-update — внесение исправлений T004 в реестр

| Поле | Значение |
| --- | --- |
| task_id | T009-registry-update |
| Исполнитель | gpt-6.1-terra, reasoning effort **medium** (нормализация таблиц и метаданных) |
| Сеть | on (только Crossref API для двух новых DOI) |
| Проверяющий | руководитель (diff реестра против `reviews/T004_registry_check.md` §8) |
| Ограничения | Только текущая директория. Не делать git commit. Не менять научные выводы; не добавлять чисел, которых нет в T004/реестре. |

Вход: `sources/registry.yaml`, `reviews/T004_registry_check.md` (особенно §§3, 5, 7, 8), инструменты
`sources/tools/*.py`.

Сделать:

1. Внести в `sources/registry.yaml` все исправления §8 T004 (пункты 1–7): новый `data_item` S100 для
   основного Fig. 4 (NIST Isotherm6–9, чужая оцифровка, mmol/g, 298 K, provisional; загрузка —
   номинальная метка, Mw unknown); S102 SI Fig. S6/S7; S111 SI Fig. S20 (RH 80 %), расхождение
   селективности 35/42; лицензии SI S100/S102/S111 — CC BY-NC 4.0 (Figshare); S104 давление
   0.0002–1 bar и вакуум 150 °C (длительность unknown); S106 locator «§2 Experimental»; S3 — файл
   `P39_LS.txt`; S105 — конфликт диапазона N2 (0–1 bar в тексте vs ось 1.2 bar).
2. Добавить записи S117 (Madden et al. 2021, DOI 10.1039/D1FD00017A, роль `validation` candidate для
   влажного носителя) и S118 (Magnin et al. 2022, DOI 10.1021/acs.jpcc.1c09914, роль `context`,
   влажный CO2 — только симуляция), сверив метаданные через Crossref.
3. Поле `reviewed_by: T004` и `review_notes` у каждой записи — кратко из таблицы §2 T004.
4. Перегенерировать паспорта (`sources/tools/finalize_audit.py`, если применимо) и запустить
   `python3 sources/tools/validate_audit.py`; обновить `sources/validation_report.json`.
5. `sources/registry_changes.md`: список изменений с ссылкой на пункт T004.

Критерий: каждое изменение прослеживается к пункту T004; валидатор проходит.
