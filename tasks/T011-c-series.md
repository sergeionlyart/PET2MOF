# T011-c-series — извлечение калибровочных (C) серий носителя

| Поле | Значение |
| --- | --- |
| task_id | T011-c-series |
| Исполнитель | gpt-6.1-sol, reasoning effort **high** |
| Сеть | on (только законный доступ к первоисточникам: издатели OA, Europe PMC REST, Crossref, Unpaywall API) |
| Проверяющий | T011v (gpt-6-astra, независимая сверка) |
| Ограничения | Только текущая директория. Не делать git commit. **Не открывать** V-источники S2, S113, S103 и их данные (`docs/data_split.md`). CAPTCHA/paywall не обходить. `UV_CACHE_DIR=$PWD/.uv-cache`. |

Прочитать: `AGENTS.md`, `docs/decisions.md` (D-12, D-14, D-15), `docs/data_split.md`, `docs/parameters.md`,
инструмент оцифровки `scripts/extraction/` и паспорта `data/extraction/records/T006-S100-FigS5.yaml` (образец).

## 1. Сухая физсорбция CO2/N2 носителя (C-PHYS), порядок D-14

1. Установить законную доступность исходных рисунков для NIST-серий `10.1021/acs.inorgchem.5b00435`
   (UiO-66, UiO-66-NH2; CO2/N2; 273/298 K) и `10.1039/C2cp23839j` (273/298/323 K): OA-статус (Unpaywall API
   `https://api.unpaywall.org/v2/<DOI>?email=pet2mof@users.noreply.github.com`), страница издателя.
   * Если рисунок доступен: сохранить изображение (SHA-256), переоцифровать **все** серии рисунка инструментом
     `scripts/extraction/` (проект, калибровка, наложение, ошибка) и сопоставить с NIST JSON так же, как
     `scripts/checks/s5_vs_nist.py`. Это и есть основная C-серия.
   * Если недоступен: NIST-серия остаётся `provisional` (чувствительность), переходите к п. 2.
2. **S105** (Cao et al., Materials 2018, CC BY 4.0; `data/raw/pdf/` или издатель MDPI): оцифровать Fig. 8A–C
   (CO2, 273/298/318 K, UiO-66 и UiO-66-NH2 и прочие серии рисунка — все) и Fig. 9 (N2, 298 K). Записать
   конфликт режима активации (§§2.3/3.4) и диапазона N2 (текст 0–1 бар vs ось до 1.2 бар) в паспорт.
   Table 3 (авторский Langmuir-fit) — отдельный `author_fit`, не измерение.

## 2. Вода на носителе (C-WATER)

**S106** Fig. 4 (Jajko et al., MMM 2022, CC BY 4.0; `data/raw/pdf/S106.pdf`, p.5): вода при 293 K, cm3(STP)/g
против p/p0 — оцифровать все серии; конверсия в ммоль/г с явной константой (22.414 cm3(STP)/mmol, 273.15 K,
101.325 kPa); p/p0 → RH. Отметить ветви адсорбции/десорбции, если есть.

## 3. Выходы

* `data/extraction/digitization/T011-*.digitization.yaml` + CSV + наложения (`private/renders/`, не публикуются),
  паспорта `data/extraction/records/T011-*.yaml` (`provisional` до T011v).
* Нормализованный набор `data/processed/c_series/<series_id>.csv` со столбцами:
  `series_id, source_id, extraction_id, material, gas, T_K, p_bar, q_mmol_g, q_err_mmol_g, p_err_bar,
  data_kind, status` (давление — абсолютное, бар; ёмкость — ммоль/г сухого адсорбента). Скрипт сборки
  `scripts/extraction/build_c_series.py` (детерминированный, из CSV оцифровок и NIST JSON).
  Включить также S100 Fig. S5 (`T006-S100-FigS5`, verified) и две NIST-точки, перекрытые в S5 (provisional).
* `reviews/T011_c_series_report.md`: что найдено/доступно, решения по порядку D-14, ошибки оцифровки,
  ограничения (активация, межобразцовые различия).
* Тесты `tests/test_c_series.py` (без сети): схема CSV, единицы, отсутствие V-источников в наборе.
