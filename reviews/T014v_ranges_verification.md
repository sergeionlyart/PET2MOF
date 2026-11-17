# T014v — независимая сверка источниковых диапазонов

Проверен HEAD `238dda1bab405c7d6d70765052edf13f04f398b7`, ветка `task/T014v-ranges-verify`, дата 2026-11-17. Роль: независимый проверяющий · платформа: OpenAI Codex. Назначено: `gpt-6.1-sol`, effort `high`, сеть on. Фактические model/effort и способ запуска интерфейс этой сессии не раскрывает; по самоотчёту модели они не подтверждаются. Карточка: `tasks/T014v-ranges-verify.md`. Локальных `.agents/skills/` и `.claude/rules/` нет; применён доступный скилл `pdf` для визуальной сверки.

Вердикт: **исправить метаданные условий и локаторы (F01–F03)**. Все 65 записей величин в 12 пакетах совпали с первоисточниками либо с явно обозначенным проектным допущением/пересчётом. Ошибок численной транскрипции и арифметики не найдено. Исключать сами литературные наблюдения не требуется. `verified` ниже подтверждает только выписку, тип и указанный пересчёт; это не валидация модели и не измерение PEI@UiO-66. Публичные записи T014 не изменены и автоматически в `verified` не переведены.

Собственная сверка и первоначальный текст этого отчёта зафиксированы **до** открытия `reviews/T014_ranges.md`; результат последующего сопоставления добавляется в конце. V-файлы S2, S113, S103, S102 и S117/Madden 2021, holdout-датасеты и `.env` не открывались. Названия V в правилах и декларациях слепоты не использовались как численные данные. Новые агенты не запускались, внешнего CI, платного OCR, commit и push не было.

Проверка охватывает `configs/sourced_ranges.yaml`, все `data/extraction/T014/*.json`, 12 паспортов `data/extraction/records/T014-*.yaml` и три новые записи реестра. Обозначения S105 и т. п. в таблицах ниже — первоисточники, ссылки перечислены далее. Для каждого пакета проверены условия, единицы, метод и классификация, а не только наличие `extraction_id`. Числа в массивах сверены поэлементно; дубликаты конфигурации проверены на равенство каноническому пакету.

## Первичные источники и условия

| Источник / открытое место | Независимо проверенные условия и метод | Оценка записи T014 |
| --- | --- | --- |
| S105, PDF pp.3,5,8,10, §2.2/2.3/3.4, Table 1 | UiO-66 без NH2/GO/PEI. N2 при −196 °C (округлённо 77 K), подготовка 393 K, 12 h (§2.2); отдельно CO2 при 273/298/318 K, расчёт Qst при 0.01–0.1 MPa. §2.3 указывает ambient-vacuum 12 h, §3.4 — 393 K-vacuum 12 h для CO2. Qst — авторский расчёт Clausius–Clapeyron, не калориметрия. | Числа и типы верны; конфликт подготовки CO2 реально есть. Перенос этого конфликта и давления CO2 на N2-порометрию ошибочен, F02. |
| S106, repository PDF pp.3–5,8 (article pp.2–4,7), Tables 1–2, §3 | N2-порометрия 77 K; vacuum 60 °C 1 h, затем 150 °C 2 h; t-plot micropore volumes для UiO-66_220/_160/_100. Шесть теплот — расчёт MC/Widom при нулевом покрытии, RASPA, TIP4P-Ew и настроенные заряды; Fig.8 задаёт 293.15 K для изотерм. Порядок структур Table 2: _0/_1/_2/_8/_32a/_32. | Корректно отделены измеренная порометрия и симуляция; теплоты не идентифицируют Q_W и не являются независимой калориметрией. |
| S110, PDF pp.2–4, Table 1, §2 | 30 wt% BPEI/SiO2 и отдельный 30 wt% LPEI/SiO2; 25 °C, dry/73.9% RH, dew point 20 °C. BPEI Mw ≈25000, Mn ≈10000; LPEI Mw 250000 g/mol. 5000 ppm CO2/He, 200 mL/min, 100 °C He 10 min; ёмкость mg CO2/g всего адсорбента по breakthrough. | Верно. Диапазон двух отношений объединяет две архитектуры PEI только как явно названный envelope; это не интервал BPEI и не gamma. Давление остаётся unknown. |
| S116, PDF pp.3,5, §2.2/2.3 и текст перед Fig.7 | Hyperbranched PEI, MM 1800, silica, авторская формулировка mass ratio 40% без ясного знаменателя. Adsorption 60 °C; regeneration 120 °C после предварительного нагрева. Steam 10/19 L/min плюс неизменный N2, steam fraction 80/90 vol%; это не RH. Для меньшего/большего steam flow t80 ≈45/30 min, t90 ≈75/45 min. Fig.7 даёт полный stripping flow 12/21 L/min. | Верно: числа T014 10/19 относятся к steam, а не полному потоку. τ — наш условный экспоненциальный эквивалент реакторных порогов; не авторская подгонка и не водная/внутричастичная константа. |
| S119, PMC HTML Tables 1–2 и NMR characterization | Polysciences B-PEI; supplier MW 600/1800/10000; GPC Mw 2100/1400/19000, Mn 470/1100/12000 g/mol. По тем же строкам tertiary N 24/29/32%. Авторы оценивают состав деконволюцией 1H NMR; 13C параметры не оптимизированы для количественного анализа. Температура NMR не установлена. | Верно; f3 — диапазон аналогов трёх коммерческих партий, не состав целевого PEI. Не навязано теоретическое 25/50/25. |
| S121, SI pp.3,14–16, Table S3; main §CO2 Adsorption… | Branched PEI Mw ≈800 (LS), Mn ≈600 (GPC); silica/ePTFE, метки 30/40/50 wt%. Только 35 °C колонка, RH 0/20/50/80%, 400 ppm CO2/N2, prehydration humid N2. g_sorbent включает PEI+silica+ePTFE (main Fig.3/сопровождающий текст, SI Fig.S5/S19). SI §4.1 p.14: single sheet, 100 или 200 mL/min по режиму; Fig.S8 p.15 — setup. Main Fig.4b и его текст — протокол presaturation. Table S3 сама не печатает единицу ёмкости: mmol CO2/g_sorbent подтверждено main/SI figures. | Числа, единицы и знак wet/dry верны; ссылка на SI Fig.S7 как протокол/активацию неверна, F01. Не подменять отсутствующий однозначный fixed-bed activation режимом TGA/DRIFTS. |
| S124, PDF pp.3–4,9–10,13; Tables 2/3/7, Eq.(2) | APTES-grafted MSG20 и дополнительно PEI-impregnated MSG20I30, авторская метка PEI 30 wt%. PEI Fluka, stock 50% m/v; Mw unknown. Калориметрия 25 °C, anhydrous, Setaram C80/manometric dosing, vacuum 10−3 mbar, 120 °C 4 h. N2-порометрия −196 °C, p/p0≈0.985, vacuum 10−6 bar, 120 °C 4 h (эквивалентное давление). | Верно. 110–120 kJ/mol — начальные дифференциальные теплоты двух функционализированных материалов; 73.2 — отдельная представительная теплота MSG20I30 в Table 7, использованная при API 50/75 °C. 1274 s — максимальный fitted heat-signal parameter MSG20I30; Eq.(2) печатает log без основания. 354 s MSG20 не включены в границы PEI. |
| DESIGN-T014, configs/scenarios.yaml, configs/revision.yaml, model_spec §§3–4, D-07/D-08 | Проектный режим adsorption 308.15 K, RH grid 0/40/70%; времена t_ads/t_des 600–3600 s. Стресс-границы, а не литературные priors. Для W_max нижняя граница расширена с 1 до физического zero-water 0; f3 0–1 — полный допустимый интервал доли при simplex constraint. | Допущения и unknown отмечены честно. Две производные τ/t требуют составного описания условий числителя и знаменателя, F03. |

## Проверка каждой записи

Колонка «тип верен?» оценивает `type` вместе с `evidence_kind`/`data_kind`: `derived` от измерения не объявляется новым измерением. Для проектных unknown подтверждена корректность сохранения незнания в рамках изученных разрешённых источников; отсутствие подходящего источника во всей литературе не доказано. `исправить` в строках F01–F03 относится к метаданным, численные значения совпадают.

| параметр | запись | значение T014 | значение по первоисточнику | совпадает? | тип верен? | вердикт (verified / исправить / excluded) |
| --- | --- | --- | --- | --- | --- | --- |
| `reported_Qst` | `T014-S105-Qphys` | [22.9, 24.3] kJ/mol CO2 | [22.9, 24.3]; S105 p.10 §3.4 | да | да: literature_range, author_calculation | verified |
| `Q_phys` | `T014-S105-Qphys` | [22900, 24300] J/mol | [22900, 24300]; S105 p.10 §3.4 | да | да: derived, author_calculation | verified |
| `total_volume` | `T014-S105-pores` | 0.245 cm3/g MOF | 0.245; S105 p.5 Table 1 | да | да: literature_range, direct_measurement | исправить (F02) |
| `micropore_volume` | `T014-S105-pores` | 0.224 cm3/g MOF | 0.224; S105 p.5 Table 1 | да | да: literature_range, direct_measurement | исправить (F02) |
| `micropore_volumes` | `T014-S106-pores` | [0.353, 0.376, 0.46] cm3/g MOF | [0.353, 0.376, 0.46]; S106 PDF p.5 Table 1 | да | да: literature_range, direct_measurement | verified |
| `V_p0_proxy` | `T014-S106-pores` | [0.353, 0.46] cm3/g MOF | [0.353, 0.46]; S106 PDF p.5 Table 1 | да | да: derived, direct_measurement | verified |
| `zero_coverage_heats` | `T014-S106-Qwater` | [46.51, 50.7, 51.69, 52.91, 54.2, 57.71] kJ/mol H2O | [46.51, 50.7, 51.69, 52.91, 54.2, 57.71]; S106 PDF p.8 Table 2 | да | да: literature_range, simulation | verified |
| `Q_water_simulation` | `T014-S106-Qwater` | [46510, 57710] J/mol | [46510, 57710]; S106 PDF p.8 Table 2 | да | да: derived, simulation | verified |
| `BPEI_dry` | `T014-S110-humidity` | 41.2 mg CO2/g adsorbent | 41.2; S110 p.4 Table 1 | да | да: literature_range, direct_measurement | verified |
| `BPEI_humid` | `T014-S110-humidity` | 77.5 mg CO2/g adsorbent | 77.5; S110 p.4 Table 1 | да | да: literature_range, direct_measurement | verified |
| `LPEI_dry` | `T014-S110-humidity` | 37.6 mg CO2/g adsorbent | 37.6; S110 p.4 Table 1 | да | да: literature_range, direct_measurement | verified |
| `LPEI_humid` | `T014-S110-humidity` | 68.59999999999999 mg CO2/g adsorbent | 68.59999999999999; S110 p.4 Table 1 | да | да: literature_range, direct_measurement | verified |
| `BPEI_wet_dry_ratio` | `T014-S110-humidity` | 1.881067961165048 1 | 1.881067961165048; S110 p.4 Table 1 | да | да: derived, direct_measurement | verified |
| `wet_dry_ratio_analog_envelope` | `T014-S110-humidity` | [1.824468085106383, 1.881067961165048] 1 | [1.824468085106383, 1.881067961165048]; S110 p.4 Table 1 | да | да: derived, direct_measurement | verified |
| `t80_minutes` | `T014-S116-desorption` | [30, 45] min | [30, 45]; S116 p.5 text/Fig.7 | да | да: literature_range, direct_measurement | verified |
| `t90_minutes` | `T014-S116-desorption` | [45, 75] min | [45, 75]; S116 p.5 text/Fig.7 | да | да: literature_range, direct_measurement | verified |
| `fractions` | `T014-S116-desorption` | [0.8, 0.9] 1 | [0.8, 0.9]; S116 p.5 text/Fig.7 | да | да: literature_range, direct_measurement | verified |
| `tau_equivalents` | `T014-S116-desorption` | [1118.402882207301, 1677.604323310952, 1172.59510113878, 1954.325168564633] s | [1118.402882207301, 1677.604323310952, 1172.59510113878, 1954.325168564633]; S116 p.5 text/Fig.7 | да | да: derived, conditional_exponential_equivalent | verified |
| `tau_CO2_des` | `T014-S116-desorption` | [1118.402882207301, 1954.325168564633] s | [1118.402882207301, 1954.325168564633]; S116 p.5 text/Fig.7 | да | да: derived, conditional_exponential_equivalent | verified |
| `tertiary_percent` | `T014-S119-f3` | [24, 29, 32] % | [24, 29, 32]; S119 Table 2 | да | да: literature_range, author_NMR_deconvolution | verified |
| `f3` | `T014-S119-f3` | [0.24, 0.32] 1 | [0.24, 0.32]; S119 Table 2 | да | да: derived, author_NMR_deconvolution | verified |
| `RH` | `T014-S121-humidity` | [0, 20, 50, 80] % | [0, 20, 50, 80]; S121 SI p.16 Table S3, 35 °C | да | да: literature_range, direct_measurement | исправить (F01) |
| `loading_labels` | `T014-S121-humidity` | [30, 40, 50] % | [30, 40, 50]; S121 SI p.16 Table S3, 35 °C | да | да: literature_range, direct_measurement | исправить (F01) |
| `q_30` | `T014-S121-humidity` | [0.99, 1.07, 1.01, 0.8100000000000001] mmol CO2/g sorbent | [0.99, 1.07, 1.01, 0.8100000000000001]; S121 SI p.16 Table S3, 35 °C | да | да: literature_range, direct_measurement | исправить (F01) |
| `q_40` | `T014-S121-humidity` | [1.45, 1.7, 1.57, 1.33] mmol CO2/g sorbent | [1.45, 1.7, 1.57, 1.33]; S121 SI p.16 Table S3, 35 °C | да | да: literature_range, direct_measurement | исправить (F01) |
| `q_50` | `T014-S121-humidity` | [1.62, 2.09, 2.05, 1.84] mmol CO2/g sorbent | [1.62, 2.09, 2.05, 1.84]; S121 SI p.16 Table S3, 35 °C | да | да: literature_range, direct_measurement | исправить (F01) |
| `ratio_30` | `T014-S121-humidity` | [1.080808080808081, 1.02020202020202, 0.8181818181818182] 1 | [1.080808080808081, 1.02020202020202, 0.8181818181818182]; S121 SI p.16 Table S3, 35 °C | да | да: derived, direct_measurement | исправить (F01) |
| `ratio_40` | `T014-S121-humidity` | [1.172413793103448, 1.082758620689655, 0.9172413793103449] 1 | [1.172413793103448, 1.082758620689655, 0.9172413793103449]; S121 SI p.16 Table S3, 35 °C | да | да: derived, direct_measurement | исправить (F01) |
| `ratio_50` | `T014-S121-humidity` | [1.290123456790123, 1.265432098765432, 1.135802469135802] 1 | [1.290123456790123, 1.265432098765432, 1.135802469135802]; S121 SI p.16 Table S3, 35 °C | да | да: derived, direct_measurement | исправить (F01) |
| `wet_dry_ratio` | `T014-S121-humidity` | [0.8181818181818182, 1.290123456790123] 1 | [0.8181818181818182, 1.290123456790123]; S121 SI p.16 Table S3, 35 °C | да | да: derived, direct_measurement | исправить (F01) |
| `initial_heat` | `T014-S124-heat` | [110, 120] kJ/mol CO2 | [110, 120]; S124 p.9 text/Fig.5 | да | да: literature_range, direct_measurement | verified |
| `Q_d_initial_proxy` | `T014-S124-heat` | [110000, 120000] J/mol | [110000, 120000]; S124 p.9 text/Fig.5 | да | да: derived, direct_measurement | verified |
| `representative_heat` | `T014-S124-heat` | 73.2 kJ/mol CO2 | 73.2; S124 p.13 Table 7, MSG20I30 | да | да: literature_range, direct_measurement | verified |
| `tau_heat_max` | `T014-S124-kinetics` | 1274 s | 1274; S124 p.10 Table 3 / p.4 Eq.(2) | да | да: literature_range, author_exponential_heat_signal_fit | verified |
| `V_parent` | `T014-S124-pores` | 0.96 cm3/g MSG20 | 0.96; S124 p.9 Table 2 | да | да: literature_range, direct_measurement | verified |
| `V_loaded` | `T014-S124-pores` | 0.06 cm3/g MSG20I30 | 0.06; S124 p.9 Table 2 | да | да: literature_range, direct_measurement | verified |
| `specific_volume_ratio` | `T014-S124-pores` | 0.0625 1 | 0.0625; S124 p.9 Table 2 | да | да: derived, direct_measurement | verified |
| `Q_W` | `T014-DESIGN` | [0, 80000] J/mol | [0, 80000]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `gamma` | `T014-DESIGN` | [-1, 2] 1 | [-1, 2]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `kappa` | `T014-DESIGN` | [0, 2.3] 1 | [0, 2.3]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `V_p0` | `T014-DESIGN` | [0.1, 2] cm3/g MOF | [0.1, 2]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `alpha_in` | `T014-DESIGN` | [0, 1] 1 | [0, 1]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `h_max` | `T014-DESIGN` | [0, 1] 1 | [0, 1]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `Q_phys` | `T014-DESIGN` | [0, 60000] J/mol | [0, 60000]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `Q_d` | `T014-DESIGN` | [0, 120000] J/mol | [0, 120000]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `W_max` | `T014-DESIGN` | [0, 200] mmol/g PEI | [0, 200]; scenarios.yaml [1,200] + exact zero-water limit | да | да: assumption_range, assumption_range | verified |
| `f3` | `T014-DESIGN` | [0, 1] 1 | [0, 1]; model_spec §4.1: доля, full simplex | да | да: assumption_range, assumption_range | verified |
| `water_volume_transfer` | `T014-DESIGN` | [0.25, 4] 1 | [0.25, 4]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `tau_over_t` | `T014-DESIGN` | [0, 10] 1 | [0, 10]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `Q_W_unknown` | `T014-DESIGN` | unknown (null) J/mol | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `gamma_unknown` | `T014-DESIGN` | unknown (null) 1 | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `kappa_unknown` | `T014-DESIGN` | unknown (null) 1 | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `V_p0_unknown` | `T014-DESIGN` | unknown (null) cm3/g MOF | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `alpha_in_unknown` | `T014-DESIGN` | unknown (null) 1 | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `h_max_unknown` | `T014-DESIGN` | unknown (null) 1 | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `Q_phys_unknown` | `T014-DESIGN` | unknown (null) J/mol | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `Q_d_unknown` | `T014-DESIGN` | unknown (null) J/mol | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `W_max_unknown` | `T014-DESIGN` | unknown (null) mmol/g PEI | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `f3_unknown` | `T014-DESIGN` | unknown (null) 1 | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `water_volume_transfer_unknown` | `T014-DESIGN` | unknown (null) 1 | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `tau_over_t_unknown` | `T014-DESIGN` | unknown (null) 1 | unknown (null); разрешённые источники не определяют целевой параметр | да | да: unknown, unknown | verified |
| `kappa_connectivity` | `T014-DESIGN` | [0, 10] 1 | [0, 10]; revision.yaml separate connectivity branch | да | да: assumption_range, assumption_range | verified |
| `stage_time` | `T014-DESIGN` | [600, 3600] s | [600, 3600]; проектное допущение / исходный config | да | да: assumption_range, assumption_range | verified |
| `tau_over_t_des_analog` | `T014-DESIGN` | [0.3106674672798059, 3.257208614274389] 1 | [0.3106674672798059, 3.257208614274389]; S116 τ / design [600,3600] s | да | да: derived, conditional_exponential_equivalent | исправить (F03) |
| `tau_over_t_heat_analog` | `T014-DESIGN` | [0.3538888888888889, 2.123333333333334] 1 | [0.3538888888888889, 2.123333333333334]; S124 1274 / design [600,3600] s | да | да: derived, conditional_heat_signal_proxy | исправить (F03) |

## Дефекты

| id | серьёзность | файл | дефект | воспроизведение | исправление |
| --- | --- | --- | --- | --- | --- |
| F01 | средняя | `configs/sourced_ranges.yaml` literature_ranges.wet_dry_ratio; `data/extraction/T014/T014-S121-humidity.json`; `data/extraction/records/T014-S121-humidity.yaml` | В locator/conditions.activation Fig.S7 названа fixed-bed protocol. В действительности это карта климатических зон. SI §1.2 содержит материалы/методы отдельных приборов и не заменяет специальный fixed-bed §4.1. Режим активации fixed-bed по данной ссылке не восстанавливается. | Открыть повторно скачанный `S121_SI.pdf`: p.12 Fig.S7 (climate map), p.14 §4.1 (fixed-bed setup), p.15 Fig.S8 (reactor), p.16 Table S3; main article Fig.4b/текст CO2 adsorption — presaturation humid N2. Значения Table S3 при этом совпадают. | Заменить неверные локаторы на SI §4.1 pp.14–15/Fig.S8 и main Fig.4b с текстом presaturation. Явно написать `fixed-bed activation unknown/not independently specified`, если конкретный режим не найден, не переносить на него активацию TGA/DRIFTS. Обновить packet/passport hashes и дубликаты вместе. |
| F02 | средняя | `data/extraction/T014/T014-S105-pores.json` conditions (верхний блок и обе quantities) | В условия N2-порометрии скопированы давление 0.01–0.1 MPa и конфликт ambient/393 K из опыта/расчёта CO2. Эти параметры не являются условиями Table 1. Для порометрии §2.2 однозначно задаёт −196 °C и подготовку 393 K 12 h; §2.2 сам не уточняет vacuum. | Сравнить S105 PDF p.3 §2.2 (N2) и §2.3 (CO2), p.8 §3.4, p.10 Eq.(2)/теплоты. Числа 0.245/0.224 cm3/g Table 1 p.5 совпадают. | Оставить N2 T≈77 K, подготовку 393 K 12 h со ссылкой на §2.2; pressure указать как relative-pressure isotherm/unknown numeric limits, не CO2 heat interval; vacuum для порометрии отдельно не утверждать без источника. Конфликт активации сохранить в S105-Qphys, где он подтверждён §2.3 vs §3.4. |
| F03 | низкая | `configs/sourced_ranges.yaml` literature_ranges.tau_over_t_des_analog / tau_over_t_heat_analog; `data/extraction/T014/T014-DESIGN.json` те же quantities | `conditions` обеих analog τ/t содержит только целевые 308.15 K, RH 0/40/70, PEI/UiO-66 и project-assumption method. Это описывает проектный знаменатель, но не экспериментальный числитель: S116 regeneration 120 °C/steam/silica либо S124 heat signal 25 °C/anhydrous/APTES+PEI/silica. Условия числителя доступны лишь по derived_from и отдельному пакету. Числа, analog и ограничения корректны, целевое измерение явно отрицается. | Сравнить conditions этих двух quantities с conditions `T014-S116-desorption:tau_CO2_des` и `T014-S124-kinetics:tau_heat_max`. | Разделить source_numerator_conditions и target_stage_design_conditions либо явно перечислить оба в conditions; сохранить отсутствие целевого τ и статус conditional analog. Не менять числа. |

## Пересчёты и происхождение

Независимый расчёт использовал значения, вручную сверенные в первоисточниках, а затем сравнил результат с пакетами, а не подставлял ожидаемые T014 результаты как входы. Все 65 quantity keys охвачены; 12 packet SHA-256 и все 6 файлов design_basis совпали. Дубликаты quantities в config точно равны evidence_ref, все source_id зарегистрированы; численных ссылок на V нет. Одни и те же наблюдения в packet/config не считаются независимыми измерениями.

Для S116 применена только условная модель `f(t)=1−exp(−t/τ)`, то есть `τ=−60*t_min/ln(1−f)`:

| поток steam | t80 / τ80 | t90 / τ90 |
| --- | --- | --- |
| 19 L/min, 90 vol% steam | 30 min / 1118.4028822073012 s | 45 min / 1172.5951011387800 s |
| 10 L/min, 80 vol% steam | 45 min / 1677.6043233109517 s | 75 min / 1954.3251685646330 s |

Даже в одном режиме τ80 и τ90 различаются; единая экспонента не установлена. Envelope `[1118.4028822073012,1954.325168564633]` s, делённый на design time `[600,3600]` s, даёт `[0.3106674672798059,3.2572086142743886]`. Это диапазон разных реакторных условий и выбранных длительностей, не интервал статистической неопределённости.

S124: `1274/3600=0.35388888888888886`, `1274/600=2.1233333333333335`. Eq.(2) задаёт `log(D/Dm)=−t/τ` и не определяет основание. Поэтому эти числа верны как отношение **напечатанного heat-signal parameter** к design time. При log10 соответствующее e-fold время равно `1274/ln(10)=553.2911699447428` s, и отношения дополнительно делятся на ln(10). Измерение CO2/H2O mass uptake этим не создаётся. В T014 это ограничение уже явно записано.

Остальные независимые операции: kJ/mol ×1000; min/max шести S106 теплот и трёх S106 micropore volumes; S119 min/max tertiary percent /100; S110 `77.5/41.2`, `68.6/37.6`; S121 каждый из трёх wet capacities / собственный dry capacity, без pooling dry разных загрузок; S124 `0.06/0.96=0.0625`. Последнее — отношение удельных объёмов на разных mass bases, не доля геометрически заблокированных пор. Без подтверждённого retained loading оно не идентифицирует kappa.

Проектные bounds имеют происхождение в существующих конфигурациях/решениях. `[0,1]` для долей и exact zero-water предел допустимы как стресс-допущения. Числа 0.25–4 для water_volume_transfer и 0–10 для connectivity kappa не стали источниковыми физическими диапазонами: в T014 они корректно названы design assumptions. Параметры целевого материала `tau_over_t,Q_W,gamma,kappa,V_p0,alpha_in,W_max,h_max,Q_phys,Q_d,f3,water_volume_transfer` оставлены unknown. Ни одно из наблюдений не определяет эти target values напрямую.

## Переносимость аналогов

Пометка `analog` обоснована для контекстного анализа чувствительности. S105/S106 — та же базовая framework chemistry, однако другие партии/дефектность и отсутствие PEI/PET-derived подтверждения; общий Vpore и micropore нельзя объединять. S119 характеризует коммерческие свободные PEI с известными различиями Mw; она ограничивает лишь условную композиционную ветвь. Неизвестный целевой Mw/партия не заменены догадкой.

Silica поддерживает иной размер/доступность пор, распределение PEI и водную среду. S110 использует Mw≈25000 BPEI либо Mw250000 LPEI и 5000 ppm CO2 при 25 °C; S121 — Mw≈800, ePTFE+silica, 400 ppm при 35 °C и предварительное увлажнение. Их отношения не идентифицируют отдельно gamma, h_max, W_max, alpha_in либо Q_W и не задают единый влажностный множитель. В S121 при RH 80% отношения для 30/40 wt% ниже 1, для 50 wt% выше 1; отрицательные эффекты сохранены.

S116 — кипящий слой, нагрев и steam stripping; S124 — сухая калориметрия двойной функционализации APTES+PEI. Ни один не определяет общую релаксацию шести пулов, τ воды или скорость PEI@UiO-66. У S124 начальная теплота 110–120 kJ/mol — высокоэнергетический хвост; представительная 73.2 kJ/mol — другая наблюдаемая. Q_W сдвига ступени, simulated zero-coverage H2O heat и mean water regeneration heat не подменены друг другом.

Следовательно, T014 не доказывает переносимость численных интервалов на целевой сорбент, но корректно ограничивает их статус наблюдениями аналогов. Применение этих envelope как автоматических priors/target measurements следует исключить; таких утверждений в проверенной конфигурации нет. Оснований объявлять числа догадками LLM по результатам прямой сверки не найдено; это не доказательство того, каким инструментом автор первоначально выполнял выписку.

## DOI, метаданные и лицензии

Новые запросы Crossref выполнены независимо от сохранённых ответов T014. Сверены DOI, полное название, **все** авторы, журнал и год с тремя записями `sources/registry.yaml`: совпали. Статус `doi_verified` не трактуется как численная проверка.

| source_id | Crossref и первичный текст | Результат |
| --- | --- | --- |
| S119 | [Crossref](https://api.crossref.org/works/10.1002%2Fmabi.201200052), [PMC Tables 1–2](https://pmc.ncbi.nlm.nih.gov/articles/PMC3970578/#T2) | Gibney и 6 соавторов, Macromolecular Bioscience, online 2012-08-03. Crossref даёт Wiley terms/TDM license, а не CC. PMC — author manuscript; свободная CC reuse license не установлена. Запись реестра корректна. |
| S121 | [Crossref](https://api.crossref.org/works/10.1021/jacsau.5c01294), [main XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12728659/fullTextXML), [Figshare metadata](https://api.figshare.com/v2/articles/30708201), [SI](https://ndownloader.figshare.com/files/59832669) | Ryu и 5 соавторов, JACS Au, online 2025-11-25 (print 2025-12-22). Main article CC BY 4.0 по Crossref/XML; SI — **CC BY-NC 4.0** по Figshare. File 59832669, SI DOI 10.1021/jacsau.5c01294.s001, MD5 db254eb0fedda0d4a1cd9bee7d025f30 совпал. Лицензии не объединены в одну. |
| S124 | [Crossref](https://api.crossref.org/works/10.3390/ma11060887), [publisher article](https://www.mdpi.com/1996-1944/11/6/887), [PDF](https://mdpi-res.com/d_attachment/materials/materials-11-00887/article_deploy/materials-11-00887.pdf) | Sánchez-Zambrano и 6 соавторов, Materials, 2018-05-25; CC BY 4.0. Запись реестра корректна. |

Первый Crossref S119 запрос вернул 429; повторный запрос с URL-encoded DOI успешно дал метаданные. Ограничения доступа не обходились. Первоначально Python urllib не принял локальную цепочку CA; штатный curl скачал источники с обычной TLS-проверкой (без `-k`/отключения верификации).

Для прежних источников заново открыты именно разрешённые первичные файлы: [S105](https://mdpi-res.com/d_attachment/materials/materials-11-00589/article_deploy/materials-11-00589.pdf), [S106](https://pure.tue.nl/ws/portalfiles/portal/193896004/1_s2.0_S1387181121006818_main_1_.pdf), [S110](https://mdpi-res.com/d_attachment/energies/energies-15-01075/article_deploy/energies-15-01075.pdf), [S116](https://uhra.herts.ac.uk/id/eprint/8235/1/1_s2_0_S1750583618306789_main.pdf). S111 SI из inputs.json не использовано: оно не является операндом ни одной записи T014; claims отчёта исполнителя о просмотре S111 в настоящей проверке не подтверждаются и не опровергаются.

## Повторная загрузка и визуальная проверка

Первичные статьи и новые ответы лежат в игнорируемом `private/T014v/`, без замены `private/T014/` или паспортов автора. Выполнена визуальная сверка оригинальных PDF-страниц: S105 pp.5/10, S106 repository pp.5/8, S110 p.4, S116 p.5, S121 SI pp.15/16, S124 pp.4/9/10/13; условия также проверены в текстовом слое указанных выше страниц. Таблицы S119 T1/T2 заново извлечены из оригинального HTML DOM и отрисованы PyMuPDF Story без ручной вставки чисел. Никаких координат кривых и оцифровки не выполнялось. Дополнительно открыт исходный main S121 Fig.4 (setup) по CDN PMC, без извлечения точек.

| Повторно полученный файл | SHA-256 новых bytes | Совпадает с T014 inputs.json? |
| --- | --- | --- |
| `S105.pdf` | `1cfc9239318c9992491baab739415ee621ea061ef72dc7efd09ebe0090ba228a` | да |
| `S106.pdf` | `8f90209c81c26d74883ad00e08264ee87ad49b8ee718dee3726aae57cb551f89` | да |
| `S110.pdf` | `edb265354f629087f860b6322235efe89d292945e9000d566d451b560e61d49c` | да |
| `S116.pdf` | `d172a162fe8a217a981cc3622c275086bf0c62c5dcdcbe7b61cc155732997178` | да |
| `S119-source.html` | `631657d9ef6ba4cb15c168eba9c08be428349a0e75dfd9cf967d4d25d8c18fd3` | нет; см. оговорку ниже |
| `S121_SI.pdf` | `8d56f90d06607abb009bbf0389756773e60e532f40e75027b9078f784a38d6fa` | да |
| `S124.pdf` | `8fa2dee9b43718b833bd0254784ca00a06ba10c6f4e48f9624f92bb7a22a0f93` | да |
| `S121.xml` | `4dbdbf2980fde32db126866402af17f28bea59d103e1cfd8ddc5868a2b580955` | да |

HTML S119 имеет новый hash `631657d9ef6ba4cb15c168eba9c08be428349a0e75dfd9cf967d4d25d8c18fd3` вместо авторского `2d82ede2409539830a2163e45faeea7c91f9ef52c9643f44d6eac2c6899e0ac6`. Численные строки T1/T2 и NMR method независимо подтверждены; страница — статья PMC3970578 с тем же DOI, не access-check HTML. Старого приватного HTML в checkout нет, поэтому точную причину различия bytes установить нельзя. Динамическая разметка — возможная причина, а не доказанный diff. Паспорт и исходный hash не заменены. Для проверки исходных bytes руководителю нужен сохранённый автором `private/T014/S119-source.html`; для содержательной проверки данный report явно идентифицирует новую версию.

## Локальная проверка и итоговое сопоставление

```sh
# Независимая арифметика; локальный скрипт и operands — в private/T014v/.
python3 private/T014v/verify.py
# Штатные offline checks T014, без V и без модельного прогона.
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked pytest tests/test_sourced_ranges.py -q
# Проверка пробелов/формата нового отчёта.
git diff --check -- reviews/T014v_ranges_verification.md
```

Первый вызов: exit 0, `PASS: 65 packet quantities; 12 passport packet hashes; 6 design origin hashes; config joins; no forbidden numeric source IDs`. Все исходные литеральные operands перечислены в основной таблице; формулы выше позволяют воспроизвести вычисления без приватного скрипта. Штатный pytest: exit 0, **11 passed in 1.30s**. Он проверяет lineage/schema/арифметику, но сам не устанавливает физическую переносимость; соответствующие выводы сделаны по первичным текстам. Оригиналы T014 отсутствуют, поэтому его optional checks исходных файлов не считаются выполненными этим тестом; собственное сравнение новых загрузок приведено отдельно.

После фиксации собственной сверки прочитан `reviews/T014_ranges.md`. Его оговорки о Q_W vs zero-coverage heat, NMR deconvolution, wet/dry sign changes, APTES+PEI и неопределённом log для τ_heat подтверждены независимо. Числа и округления его основной таблицы согласуются с пакетами. Его сведения о чужом запуске 234 tests и publish-check в настоящей сессии не перепроверялись; результат этой сессии — только указанные 11 tests и независимая источниковая сверка. Рекомендации F01–F03 остаются в силе. Решение о приёмке и изменении статусов принимает руководитель после исправления метаданных; новые значения параметров цели настоящая проверка не устанавливает.

Финальный контроль нового untracked отчёта: `git diff --no-index --check -- /dev/null reviews/T014v_ranges_verification.md` — exit 0 (обычный git diff не включает untracked файлы). Дополнительная проверка — 65 строк требуемой таблицы, по 7 колонок, без trailing whitespace; 30 защищённых файлов T014/config/registry/авторского отчёта побайтово совпали с HEAD. В `git status --short` единственный новый неигнорируемый файл — настоящий отчёт. Коммит не создан.
