# Сухое сравнение S2 — кандидаты

run_id: `debug-unregistered`; набор: S2, Tables 1–2.

Условия статьи: сухой чистый CO₂, 25 °C; в таблице 1 bar, в тексте 1 atm. Пересчёт на другое давление не выполняется. Приоритет задан только сухой q.

| Образец | q, ммоль/г | Прирост, % | m, кг/кг CO₂ | PEI в m, кг | Ценовой порог | Класс |
|---|---:|---:|---:|---:|---:|---|
| S2-C72 | 3.26 | 22.09738 | 6.969972 | 1.352175 | 1.220974 | первый по номиналу |
| S2-C96 | 3.15 | 17.97753 | 7.213368 | 1.615794 | 1.179775 | приоритетный кандидат |
| S2-BASE | 2.67 | 0.00000 | 8.510153 | 0.000000 | 1.000000 | контроль |

q — measurement; удержанный PEI, % — author_calculated; прирост, инвентарь, PEI в инвентаре и ценовой порог — our_derived.

| Образец | d | Сравнение с контролем | Сравнение двух кандидатов |
|---|---:|---|---|
| S2-C72 | 3% | устойчиво выше контроля при d | различие не разрешено при d |
| S2-C72 | 5% | устойчиво выше контроля при d | различие не разрешено при d |
| S2-C72 | 10% | преимущество над контролем не разрешено при d | различие не разрешено при d |
| S2-C96 | 3% | устойчиво выше контроля при d | различие не разрешено при d |
| S2-C96 | 5% | устойчиво выше контроля при d | различие не разрешено при d |
| S2-C96 | 10% | преимущество над контролем не разрешено при d | различие не разрешено при d |
| S2-BASE | 3% | контроль | не применяется к контролю |
| S2-BASE | 5% | контроль | не применяется к контролю |
| S2-BASE | 10% | контроль | не применяется к контролю |

Для пары S2-C72/S2-C96 отношение q = 1.0349206349; d* с округлением = 0.0156006240 (1.560062%), без округления = 0.0171606864. Нужно строго d < d*, равенство границ не даёт преимущества. При 3/5/10% различие этой пары не разрешено; оба сохраняются для дальнейших исследований.

Следующее измерение: повторить сухую равновесную q двух кандидатов и контроля на массе сорбента после одинакового outgassing, при одинаковых измеренных T и давлении. Для ожидаемого разрыва обеспечить отдельные ограниченные относительные ошибки ниже 1.560062% при округлении не хуже ±0,005 ммоль/г; записать исходные повторы, массы, газ, влажность, калибровку и бюджет общей и независимой ошибок. Порог относится к текущим номиналам, новые измерения требуют повторной оценки. Он не задаёт число повторов или статистическую значимость.

## Обязательные парные сравнения

| Пара A/B | qA/qB | d* с округлением | d* без округления | Устойчиво A>B: 3/5/10% |
|---|---:|---:|---:|---|
| C72/C96 | 1.0349206349 | 0.0156006240 | 0.0171606864 | нет/нет/нет |
| C72/N72 | 1.0903010033 | 0.0416000000 | 0.0432000000 | да/нет/нет |
| C96/I96 | 1.6844919786 | 0.2529880478 | 0.2549800797 | да/да/да |

Различия подготовки и удержанного PEI не позволяют причинно приписать эффект одному фактору.

## Вторичные свойства — рядом, вне критерия

alpha — отношение чистогазовых ёмкостей, не селективность смеси. Поглощение смеси — суммарное CO₂+N₂, не только CO₂; коррекция авторов — производная. Влажный отклик — контекст с неуточнённой водой/RH. DSC — не энергия установки. Пустые DSC сохранены как unknown.

| Образец | Свойство | Значение | Единица | evidence_type | allowed_use |
|---|---|---:|---|---|---|
| S2-C72 | alpha_pure_gas_capacity_ratio | 40.6 | 1 | author_derived_from_pure_gas_measurements | secondary_screening_not_mixture_selectivity |
| S2-C72 | q_total_CO2_N2_mixture | 2.17 | mmol_total/g | reported_mixed_gas_total_measurement | secondary_total_not_CO2_only |
| S2-C72 | q_CO2_mixture_author_corrected | 2.12 | mmol/g | author_calculated_from_total_and_alpha | scenario_only_not_independent_CO2_measurement |
| S2-C72 | q_moist_reported | 3.43 | mmol/g | reported_wet_response_with_water_interference | context_only_not_fit_or_CO2_only_validation |
| S2-C72 | Qdes_DSC | 67.3 | kJ/mol | author_reported_DSC_heat | context_not_process_energy |
| S2-C96 | alpha_pure_gas_capacity_ratio | 48.0 | 1 | author_derived_from_pure_gas_measurements | secondary_screening_not_mixture_selectivity |
| S2-C96 | q_total_CO2_N2_mixture | 2.38 | mmol_total/g | reported_mixed_gas_total_measurement | secondary_total_not_CO2_only |
| S2-C96 | q_CO2_mixture_author_corrected | 2.33 | mmol/g | author_calculated_from_total_and_alpha | scenario_only_not_independent_CO2_measurement |
| S2-C96 | q_moist_reported | 3.33 | mmol/g | reported_wet_response_with_water_interference | context_only_not_fit_or_CO2_only_validation |
| S2-C96 | Qdes_DSC | 68.0 | kJ/mol | author_reported_DSC_heat | context_not_process_energy |
| S2-BASE | alpha_pure_gas_capacity_ratio | 25.5 | 1 | author_derived_from_pure_gas_measurements | secondary_screening_not_mixture_selectivity |
| S2-BASE | q_total_CO2_N2_mixture | 2.06 | mmol_total/g | reported_mixed_gas_total_measurement | secondary_total_not_CO2_only |
| S2-BASE | q_CO2_mixture_author_corrected | 1.98 | mmol/g | author_calculated_from_total_and_alpha | scenario_only_not_independent_CO2_measurement |
| S2-BASE | q_moist_reported | 2.13 | mmol/g | reported_wet_response_with_water_interference | context_only_not_fit_or_CO2_only_validation |
| S2-BASE | Qdes_DSC | unknown | kJ/mol | author_reported_DSC_heat | context_not_process_energy |

Инвентарь описывает единственную равновесную загрузку из разгруженного материала; ценовой порог учитывает только равную стоимость материала на загрузку. Регенерация, ресурс, синтез и цикл не оценены. Сценарии — детерминированные границы, не доверительные интервалы.

При общем множителе k отношения, приросты и ранги сохраняются (численные отклонения показаны в stress_common_factor.csv), m меняется как 1/k. Это сценарий общей шкалы, а не модель изменения изотермы с давлением.

Источник: пакет PET2MOF_Task002_DataPack_v1.0, data/primary/S2_*.csv; S2 DOI 10.1021/acsomega.8b02319, Table 1 p.3189, Table 2 p.3192. Для C96 использовано 22,4% PEI из Table 1; 22,1% в заключении сохранено как расхождение. Смесь по расходам около 14,3% CO₂ против подписей 15%. Отдельная независимая сверка первоисточника и пересчёт — T031/T033/T035; настоящий расчёт не присваивает статус verified. Перенос на другие условия, смеси и PET-derived материал не установлен.
