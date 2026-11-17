# Покрытие NIST ISODB — T002

Снимок получен 16 ноября 2026 UTC. Версия API: `3.23726`.
Все записи **provisional**: SHA-256 проверяет целостность, но независимая сверка руководителем/T004 ещё не выполнена.

## Поиск и границы

Просмотрены полные каталоги: 9328 материалов, 39988 изотерм и 455 газов. Поиск по имени и всем synonyms: нормализация к нижнему регистру с удалением знаков, подстрока `uio66`; дополнительно regex `zr.?bdc`. Найдено 152 записи материала. Это воспроизводимое покрытие названий реестра, а не доказательство полноты всех химических синонимов в литературе. Имена без UiO-66/Zr-BDC и без соответствующего synonyms могут быть пропущены. Отдельно проверены PEI/polyethylenimine по всему каталогу: UiO-содержащие совпадения — 10, 20, 30 и 40PEI@UiO-66.

Отбор: температура из числового поля JSON, включительно 273–323 K; хотя бы один компонент CO2, N2, H2O по InChIKey. Сохранены 296 JSON изотерм: 287 однокомпонентных и 9 смесей. Смесь не учитывается как чистая изотерма каждого её компонента. Все функциональные производные и композиты сохранены для полноты поиска; их нельзя считать синонимами исходного UiO-66.

## Сводка однокомпонентных изотерм

Числа ниже включают категории NIST: exp=141, sim=4, mod=11, пустая/unknown=140 (по всему снимку, включая смеси). `mod` сохранено без интерпретации. Эти количества не являются количеством подтверждённых экспериментальных серий.

| Группа (точные названия ниже) | CO2 | N2 | H2O |
| --- | ---: | ---: | ---: |
| PEI@UiO-66 (название NIST) | 4 | 0 | 0 |
| UiO-66 / UiO-66(Zr) / Zr-BDC | 65 | 23 | 13 |
| UiO-66-NH2 (синонимы) | 16 | 8 | 3 |
| Прочие варианты/производные/композиты (не объединять с исходным MOF) | 86 | 55 | 14 |

## Материал × адсорбат × температура

Число в скобках — число отдельных JSON; 0 означает отсутствие в выбранном диапазоне. Смеси показаны в таблице источников отдельно. Точные имена и hashkey не сливались.

| Материал NIST | CO2: T/K (n) | N2: T/K (n) | H2O: T/K (n) |
| --- | --- | --- | --- |
| 1.5WT% Au@UiO-66 | 0 | 0 | 0 |
| 10PEI@UiO-66 | 298 (1) | 0 | 0 |
| 2.8WT% Au@UiO-66 | 0 | 0 | 0 |
| 20PEI@UiO-66 | 298 (1) | 0 | 0 |
| 25 wt% HPWs@UiO-66 | 0 | 0 | 0 |
| 30 wt% HPWs@UiO-66 | 0 | 0 | 0 |
| 30PEI@UiO-66 | 298 (1) | 0 | 0 |
| 35 wt% HPWs@UiO-66 | 0 | 0 | 0 |
| 4.0WT% Au@UiO-66 | 0 | 0 | 0 |
| 40 wt% HPWs@UiO-66 | 0 | 0 | 0 |
| 40PEI@UiO-66 | 298 (1) | 0 | 0 |
| AgI/UiO-66 (.1) | 0 | 0 | 0 |
| AgI/UiO-66 (.5) | 0 | 0 | 0 |
| AgI/UiO-66 (1) | 0 | 0 | 0 |
| AgI/UiO-66 (2) | 0 | 0 | 0 |
| ASUiO-66 | 0 | 0 | 0 |
| Au NCs-UiO-66-TU | 0 | 0 | 0 |
| Dehydrd-UiO-66 | 0 | 0 | 0 |
| Dehydrd-UiO-66-Br | 0 | 0 | 0 |
| Dehydrd-UiO-66-NH2 | 0 | 0 | 0 |
| Dehydrd-UiO-66-NO2 | 0 | 0 | 0 |
| Dehydroxylated UiO-66 | 298 (1) | 0 | 0 |
| DOPA-UiO-66(225 nm) | 0 | 0 | 0 |
| DOPA-UiO-66(25 nm) | 0 | 0 | 0 |
| Fe₃O₄@SiO₂@UiO-66 | 0 | 0 | 0 |
| HKUST-1 with 5% UiO-66 | 0 | 0 | 0 |
| Hydrd-UiO-66 | 0 | 0 | 0 |
| Hydrd-UiO-66-Br | 0 | 0 | 0 |
| Hydrd-UiO-66-NH2 | 0 | 0 | 0 |
| Hydrd-UiO-66-NO2 | 0 | 0 | 0 |
| Hydroxylated UiO-66 | 298 (1), 300 (1) | 300 (2) | 0 |
| Mg(acac)2@UiO-66-NH2 | 0 | 0 | 0 |
| NH2-UiO-66 | 308 (2) | 0 | 0 |
| NH2-Uio-66(Zr) | 273 (3) | 0 | 0 |
| Ni(acac)2@UiO-66-NH2 | 0 | 0 | 0 |
| opt-UiO-66(Zr)-(OH)2 | 273 (1), 298 (2) | 298 (2) | 0 |
| Physical mixture of UiO-66(Zr)-NH2 (47 mol%) and UiO-66(Zr)-F4 (53 mol%) | 298 (1) | 0 | 0 |
| Pre-formed UiO-66-NH2 in PAN | 0 | 0 | 0 |
| UiO-66 | 273 (17), 293 (2), 298 (9), 300 (6), 302 (1), 303 (8), 305 (2), 307 (2), 308 (2), 313 (1), 323 (2) | 273 (5), 298 (5), 303 (1), 323 (2) | 273 (1), 298 (12) |
| UiO-66 (1:1) | 0 | 0 | 0 |
| UiO-66 (24h) | 0 | 0 | 0 |
| UiO-66 (2:1) | 0 | 0 | 0 |
| UiO-66 (2h) | 0 | 0 | 0 |
| UiO-66 (3:1) | 0 | 0 | 0 |
| UiO-66 (48h) | 0 | 0 | 0 |
| UiO-66 (4:1) | 0 | 0 | 0 |
| UiO-66 (4h) | 0 | 0 | 0 |
| UiO-66 (6:1) | 0 | 0 | 0 |
| UiO-66 (72h) | 0 | 0 | 0 |
| UiO-66 (7:1) | 0 | 0 | 0 |
| UiO-66 (8h) | 0 | 0 | 0 |
| UiO-66 (solvothermal) | 0 | 0 | 273 (1) |
| UiO-66 cuboctahedron | 0 | 0 | 0 |
| UiO-66 heterogeneous agglomeration | 0 | 0 | 0 |
| UiO-66 large truncated cube | 0 | 0 | 0 |
| UiO-66 small cube | 0 | 0 | 0 |
| UiO-66 synthesized using Cyrene | 0 | 0 | 0 |
| UiO-66 synthesized using DMF | 0 | 0 | 0 |
| UiO-66 with 5% HKUST-1 | 0 | 0 | 0 |
| UiO-66(225 nm) | 0 | 0 | 0 |
| UiO-66(25 nm) | 0 | 0 | 0 |
| UiO-66(Ce0.05Zr0.95) | 0 | 0 | 0 |
| UiO-66(Zr) | 273 (1), 298 (1), 303 (11) | 273 (2), 283 (2), 293 (2), 298 (1), 303 (3) | 0 |
| UiO-66(Zr) 100 Equ. FA | 0 | 0 | 0 |
| UiO-66(Zr) 30 Equ. AA | 0 | 0 | 0 |
| UiO-66(Zr)-(CF3)2 | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH) (303K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH) (323K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH) (343K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH) (383K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH) (423K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH) (463K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH)2 | 0 | 0 | 303 (1) |
| UiO-66(Zr)-(COOH)2 (303K) | 303 (2) | 303 (1) | 0 |
| UiO-66(Zr)-(COOH)2 (323K) | 303 (1) | 0 | 0 |
| UiO-66(Zr)-(COOH)2 (343K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH)2 (348K) | 303 (1) | 0 | 0 |
| UiO-66(Zr)-(COOH)2 (373K) | 303 (1) | 0 | 0 |
| UiO-66(Zr)-(COOH)2 (383K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH)2 (423K) | 303 (2) | 303 (1) | 0 |
| UiO-66(Zr)-(COOH)2 (463K) | 0 | 0 | 0 |
| UiO-66(Zr)-(COOH)2 (473K) | 303 (1) | 0 | 0 |
| UiO-66(Zr)-(OH)2 | 0 | 0 | 0 |
| UiO-66(Zr)-Br | 298 (1) | 298 (1) | 0 |
| UiO-66(Zr)-CO2H | 0 | 0 | 0 |
| UiO-66(Zr)-F4 | 0 | 0 | 0 |
| UiO-66(Zr)-NH2 | 298 (1) | 0 | 0 |
| UiO-66(Zr)-NH2-F4-0.27 | 0 | 0 | 0 |
| UiO-66(Zr)-NH2-F4-0.53 | 298 (1) | 0 | 0 |
| UiO-66(Zr)-NH2-F4-0.72 | 0 | 0 | 0 |
| UiO-66(Zr)-NO2 | 0 | 0 | 0 |
| UiO-66(Zr)-SO3H | 0 | 0 | 0 |
| UiO-66(Zr4+)  metal/ligand ratio of 6:3 | 0 | 0 | 0 |
| UiO-66(Zr4+)  metal/ligand ratio of 6:4 | 0 | 0 | 0 |
| UiO-66(Zr4+)  metal/ligand ratio of 6:6 | 0 | 0 | 0 |
| UiO-66(Zr4+) with acetic acid | 0 | 0 | 298 (1) |
| UiO-66(Zr4+) with high concentration stearic acid | 0 | 0 | 298 (1) |
| UiO-66(Zr4+) with low concentration stearic acid | 0 | 0 | 298 (1) |
| UiO-66(Zr4+) with metal/ligand ratio 6:3 | 0 | 0 | 298 (1) |
| UiO-66(Zr4+) with metal/ligand ratio 6:4 | 0 | 0 | 298 (1) |
| UiO-66(Zr4+) with metal/ligand ratio 6:6 | 0 | 0 | 298 (1) |
| UiO-66-(CH3)2 | 273 (1), 293 (1) | 0 | 0 |
| UiO-66-(COOH)2 | 273 (1), 298 (1) | 273 (1), 298 (1) | 273 (1) |
| UiO-66-(COOH)4 | 273 (1), 298 (1) | 273 (1), 298 (1) | 273 (1) |
| UiO-66-(COOH)4-EX | 273 (1), 298 (1) | 273 (1), 298 (1) | 0 |
| UiO-66-(COOK)2-EX | 273 (1), 298 (1) | 273 (1), 298 (1) | 0 |
| UiO-66-(COOK)4-EX | 273 (1), 298 (1) | 273 (1), 298 (1) | 0 |
| UiO-66-(COOLi)2-EX | 273 (1), 298 (1) | 273 (1), 298 (1) | 0 |
| UiO-66-(COOLi)4-EX | 273 (1), 298 (1) | 273 (1), 298 (1) | 0 |
| UiO-66-(COONa)2-EX | 273 (1), 298 (1) | 273 (1), 298 (1) | 0 |
| UiO-66-(COONa)4-EX | 273 (1), 298 (1) | 273 (1), 298 (1) | 0 |
| UiO-66-(F)4 | 273 (1), 298 (1) | 273 (1), 298 (1) | 273 (1) |
| UiO-66-(OCH2CH3)2 | 273 (1), 298 (1) | 273 (1), 298 (1) | 273 (1) |
| UiO-66-(OH)2 | 273 (1), 298 (1) | 273 (2), 298 (2) | 273 (1) |
| UiO-66-(OH)2-NO2 | 0 | 273 (1), 298 (1) | 0 |
| UiO-66-Br | 273 (3), 293 (1), 298 (2), 323 (2) | 273 (2), 298 (2), 323 (2) | 0 |
| UiO-66-CH3 | 298 (1) | 298 (1) | 298 (1) |
| UiO-66-EA | 298 (1), 305 (1), 313 (1) | 0 | 0 |
| UiO-66-Me | 0 | 0 | 0 |
| UiO-66-Me2 | 0 | 0 | 0 |
| UiO-66-MM | 0 | 0 | 0 |
| UiO-66-N2 | 0 | 0 | 0 |
| UiO-66-NH2 | 273 (4), 293 (1), 298 (3), 323 (2) | 273 (3), 298 (3), 323 (2) | 273 (1), 298 (2) |
| UiO-66-NH2(100) | 0 | 0 | 0 |
| UiO-66-NH2(33) | 0 | 0 | 0 |
| UiO-66-NH2(67) | 0 | 0 | 0 |
| UiO-66-NH4 | 273 (1) | 273 (1) | 0 |
| UiO-66-NO2 | 273 (3), 293 (1), 298 (2), 323 (2) | 273 (3), 298 (3), 323 (2) | 0 |
| UiO-66-NO2-(OH)2 | 0 | 273 (1), 298 (1) | 0 |
| UiO-66-P1000 | 0 | 0 | 0 |
| UiO-66-P10000 | 0 | 0 | 0 |
| UiO-66-S1 | 300 (3) | 300 (2) | 0 |
| UiO-66-S2 | 0 | 0 | 0 |
| UiO-66-S3 | 0 | 0 | 0 |
| UiO-66-S3p | 300 (2) | 0 | 0 |
| UiO-66-S4 | 0 | 0 | 0 |
| UiO-66-S5 | 0 | 0 | 0 |
| UiO-66-TU | 0 | 0 | 0 |
| UiO-66/GO-1 | 298 (1) | 0 | 0 |
| UiO-66/GO-10 | 298 (1) | 0 | 0 |
| UiO-66/GO-5 | 273 (11), 298 (4) | 0 | 0 |
| UiO-66@AcO | 0 | 0 | 0 |
| UiO-66@LiOtBu | 0 | 0 | 0 |
| UiO-66@SiO2-0.16 | 0 | 0 | 0 |
| UiO-66@SiO2-0.32 | 0 | 0 | 0 |
| UiO-66@SiO2-0.64 | 0 | 0 | 0 |
| UiO-66@So4H | 0 | 0 | 0 |
| Zr-BDC | 0 | 0 | 0 |
| Zr-BDC with defect | 0 | 0 | 0 |
| Zr-BDC-Br | 0 | 0 | 0 |
| Zr-BDC-NH2 | 0 | 0 | 0 |
| Zr-BDC-NO2 | 0 | 0 | 0 |

## Около 308 K

При 308 K: 4 JSON; в интервале 303–313 K: 49 JSON (включая смеси). Все четыре записи ровно при 308 K имеют единицы cm3(STP)/g или cm3/m2: две cm3(STP)/g загружаются при STP 273.15 K, 101.325 kPa (22.414 cm3/mmol); две cm3/m2 отклоняются без массовой нормировки.

| Материал | Адсорбат | T/K | Изотерма |
| --- | --- | ---: | --- |
| UiO-66(Zr)-(COOH)2 | Water | 303 | 10.1002anie.201302682.isotherm1 |
| UiO-66(Zr) | Nitrogen | 303 | 10.1002anie.201302682.isotherm3 |
| UiO-66(Zr) | Nitrogen | 303 | 10.1002anie.201302682.isotherm4 |
| UiO-66(Zr) | Nitrogen | 303 | 10.1002anie.201302682.isotherm5 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1002chem.201003596.Isotherm4 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1002chem.201003596.Isotherm5 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1002chem.201003596.Isotherm6 |
| UiO-66 | Carbon Dioxide | 303 | 10.1016j.egypro.2013.05.082.Isotherm1 |
| UiO-66 | Nitrogen | 303 | 10.1016j.egypro.2013.05.082.Isotherm3 |
| NH2-UiO-66 | Carbon Dioxide | 308 | 10.1016j.memsci.2012.04.003.Isotherm13 |
| UiO-66 | Carbon Dioxide | 308 | 10.1016j.memsci.2012.04.003.Isotherm14 |
| NH2-UiO-66 | Carbon Dioxide | 308 | 10.1016j.memsci.2012.04.003.Isotherm3 |
| UiO-66 | Carbon Dioxide | 308 | 10.1016j.memsci.2012.04.003.Isotherm4 |
| UiO-66 | Carbon Dioxide | 303 | 10.1016j.micromeso.2014.02.014.Isotherm2 |
| UiO-66 | Carbon Dioxide | 303 | 10.1021Jp308657x.ISOTHERM12 |
| UiO-66 | Carbon Dioxide | 303 | 10.1021Jp308657x.ISOTHERM13 |
| UiO-66 | Carbon Dioxide | 303 | 10.1021Jp308657x.isotherm2 |
| UiO-66 | Carbon Dioxide | 303 | 10.1021Jp308657x.isotherm3 |
| UiO-66 | Carbon Dioxide | 303 | 10.1021Jp308657x.isotherm6 |
| UiO-66 | Carbon Dioxide | 303 | 10.1021Jp308657x.isotherm7 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021jp202633t.Isotherm1 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021jp202633t.Isotherm10 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021jp202633t.Isotherm2 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021jp202633t.Isotherm21 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021jp202633t.Isotherm22 |
| UiO-66(Zr) | Carbon Dioxide;Methane | 303 | 10.1021jp202633t.Isotherm25 |
| UiO-66(Zr) | Carbon Dioxide;Methane | 303 | 10.1021jp202633t.Isotherm26 |
| UiO-66(Zr) | Carbon Dioxide;Methane | 303 | 10.1021jp202633t.Isotherm27 |
| UiO-66(Zr) | Carbon Dioxide;Methane | 303 | 10.1021jp202633t.Isotherm28 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021jp202633t.Isotherm5 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021jp202633t.Isotherm6 |
| UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021jp202633t.Isotherm9 |
| UiO-66 | Carbon Dioxide | 307 | 10.1039c2nr30244f.isotherm3b |
| UiO-66 | Carbon Dioxide | 305 | 10.1039c2nr30244f.isotherm4b |
| UiO-66 | Carbon Dioxide | 307 | 10.1039c2nr30244f.isotherm5b |
| UiO-66(Zr)-(COOH)2 (423K) | Carbon Dioxide | 303 | 10.1039c4ta03992k.Isotherm23 |
| UiO-66(Zr)-(COOH)2 (473K) | Carbon Dioxide | 303 | 10.1039c4ta03992k.Isotherm24 |
| UiO-66(Zr)-(COOH)2 (373K) | Carbon Dioxide | 303 | 10.1039c4ta03992k.Isotherm25 |
| UiO-66(Zr)-(COOH)2 (348K) | Carbon Dioxide | 303 | 10.1039c4ta03992k.Isotherm26 |
| UiO-66(Zr)-(COOH)2 (323K) | Carbon Dioxide | 303 | 10.1039c4ta03992k.Isotherm27 |
| UiO-66(Zr)-(COOH)2 (303K) | Carbon Dioxide | 303 | 10.1039c4ta03992k.Isotherm28 |
| UiO-66(Zr)-(COOH)2 (423K) | Nitrogen | 303 | 10.1039c4ta03992k.Isotherm29 |
| UiO-66(Zr)-(COOH)2 (423K) | Carbon Dioxide | 303 | 10.1039c4ta03992k.Isotherm3 |
| UiO-66(Zr)-(COOH)2 (303K) | Nitrogen | 303 | 10.1039c4ta03992k.Isotherm30 |
| UiO-66(Zr)-(COOH)2 (303K) | Carbon Dioxide | 303 | 10.1039c4ta03992k.Isotherm4 |
| UiO-66 | Carbon Dioxide | 305 | 10.1039c5ta05997f.Isotherm3 |
| UiO-66-EA | Carbon Dioxide | 305 | 10.1039c5ta05997f.Isotherm4 |
| UiO-66-EA | Carbon Dioxide | 313 | 10.1039c5ta05997f.Isotherm5 |
| UiO-66 | Carbon Dioxide | 313 | 10.1039c5ta05997f.Isotherm6 |

## Происхождение и ограничения

Значения tabular_data: {'0': 296}. `0` означает нетабличные данные NIST; в сочетании с Figure в articleSource это признак извлечения из графика. Такие записи помечены «оцифровка рисунка NIST» в таблице ниже и несут неопределённость оцифровки. Её численная оценка в JSON отсутствует (unknown); поля digitizer и articleSource сохранены. `tabular_data=1` передаёт флаг NIST, но не подтверждает нами происхождение исходной таблицы. Самостоятельная оцифровка и чтение координат LLM не выполнялись. Наличие digitizer само по себе не доказывает оцифровку графика.

PEI-композиты: присутствуют четыре именованные загрузки; точные газы, T и DOI приведены ниже. Название UiO-66 в этих записях не устанавливает тождество PET-derived материалу или PEI@UiO-66-NH2 из S2. Наличие влажных смесей и H2O следует оценивать по точным строкам, а не по CO2-данным.

Не загружаются в нормализованные единицы без дополнительных допущений: 28 JSON. Исходники сохранены независимо от возможности конверсии. Поддержаны bar, Pa, kPa, MPa, mbar, atm, Torr, mmHg → bar; mmol/g, mol/kg, mol/g, mmol/kg, cm3(STP)/g → mmol/g. Для cm3(STP)/g используется 22.414 cm3/mmol при 273.15 K и 101.325 kPa; cm3/g и cm3/m2 отклоняются. Mixture pressure_bar — полное давление; ёмкость — для конкретного компонента; состав и его тип сохраняются.

| pressureUnits | adsorptionUnits | JSON |
| --- | --- | ---: |
| bar | cm3(STP)/cm3 | 17 |
| bar | cm3(STP)/g | 43 |
| bar | cm3/m2 | 2 |
| bar | kmol/m3 | 4 |
| bar | mg/g | 3 |
| bar | mmol/g | 223 |
| bar | mol/g | 2 |
| bar | wt% | 2 |

## Источник каждой изотермы

| JSON | Материал | Адсорбат | T/K | DOI статьи | articleSource | Происхождение | digitizer | category |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| [10.1002adsu.201700092.Isotherm11](isotherms/10.1002adsu.201700092.Isotherm11.json) | UiO-66(Zr)-NH2-F4-0.53 | Carbon Dioxide | 298 | 10.1002/adsu.201700092 | Figure 7 | оцифровка рисунка NIST | Gabrielle Magid | exp |
| [10.1002adsu.201700092.Isotherm12](isotherms/10.1002adsu.201700092.Isotherm12.json) | UiO-66(Zr)-NH2 | Carbon Dioxide | 298 | 10.1002/adsu.201700092 | Figure 7 | оцифровка рисунка NIST | Gabrielle Magid | exp |
| [10.1002adsu.201700092.Isotherm13](isotherms/10.1002adsu.201700092.Isotherm13.json) | Physical mixture of UiO-66(Zr)-NH2 (47 mol%) and UiO-66(Zr)-F4 (53 mol%) | Carbon Dioxide | 298 | 10.1002/adsu.201700092 | Figure 7 | оцифровка рисунка NIST | Gabrielle Magid | exp |
| [10.1002aic.15837.Isotherm1](isotherms/10.1002aic.15837.Isotherm1.json) | opt-UiO-66(Zr)-(OH)2 | Carbon Dioxide;Nitrogen | 298 | 10.1002/aic.15837 | Table S5 | нетабличные; способ unknown | BISON-20 Team | exp |
| [10.1002aic.15837.Isotherm10](isotherms/10.1002aic.15837.Isotherm10.json) | opt-UiO-66(Zr)-(OH)2 | Carbon Dioxide | 298 | 10.1002/aic.15837 | Figure 2C | оцифровка рисунка NIST | Patrick Donahue | exp |
| [10.1002aic.15837.Isotherm12](isotherms/10.1002aic.15837.Isotherm12.json) | opt-UiO-66(Zr)-(OH)2 | Nitrogen | 298 | 10.1002/aic.15837 | Figure 2C | оцифровка рисунка NIST | Patrick Donahue | exp |
| [10.1002aic.15837.Isotherm3](isotherms/10.1002aic.15837.Isotherm3.json) | opt-UiO-66(Zr)-(OH)2 | Carbon Dioxide;Nitrogen | 298 | 10.1002/aic.15837 | Table S5 | нетабличные; способ unknown | BISON-20 Team | exp |
| [10.1002aic.15837.Isotherm4](isotherms/10.1002aic.15837.Isotherm4.json) | opt-UiO-66(Zr)-(OH)2 | Carbon Dioxide | 298 | 10.1002/aic.15837 | Figure S4a | оцифровка рисунка NIST | BISON-20 Team | exp |
| [10.1002aic.15837.Isotherm5](isotherms/10.1002aic.15837.Isotherm5.json) | opt-UiO-66(Zr)-(OH)2 | Nitrogen | 298 | 10.1002/aic.15837 | Figure S4c | оцифровка рисунка NIST | BISON-20 Team | exp |
| [10.1002aic.15837.Isotherm9](isotherms/10.1002aic.15837.Isotherm9.json) | opt-UiO-66(Zr)-(OH)2 | Carbon Dioxide | 273 | 10.1002/aic.15837 | Figure 2C | оцифровка рисунка NIST | Patrick Donahue | exp |
| [10.1002anie.201302682.isotherm1](isotherms/10.1002anie.201302682.isotherm1.json) | UiO-66(Zr)-(COOH)2 | Water | 303 | 10.1002/anie.201302682 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002anie.201302682.isotherm3](isotherms/10.1002anie.201302682.isotherm3.json) | UiO-66(Zr) | Nitrogen | 303 | 10.1002/anie.201302682 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002anie.201302682.isotherm4](isotherms/10.1002anie.201302682.isotherm4.json) | UiO-66(Zr) | Nitrogen | 303 | 10.1002/anie.201302682 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002anie.201302682.isotherm5](isotherms/10.1002anie.201302682.isotherm5.json) | UiO-66(Zr) | Nitrogen | 303 | 10.1002/anie.201302682 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002chem.201003596.Isotherm4](isotherms/10.1002chem.201003596.Isotherm4.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1002/chem.201003596 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002chem.201003596.Isotherm5](isotherms/10.1002chem.201003596.Isotherm5.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1002/chem.201003596 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002chem.201003596.Isotherm6](isotherms/10.1002chem.201003596.Isotherm6.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1002/chem.201003596 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002chem.201301728.isotherm1](isotherms/10.1002chem.201301728.isotherm1.json) | NH2-Uio-66(Zr) | Carbon Dioxide | 273 | 10.1002/chem.201301728 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002chem.201301728.isotherm2](isotherms/10.1002chem.201301728.isotherm2.json) | UiO-66(Zr) | Carbon Dioxide | 273 | 10.1002/chem.201301728 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002chem.201301728.isotherm3](isotherms/10.1002chem.201301728.isotherm3.json) | NH2-Uio-66(Zr) | Carbon Dioxide | 273 | 10.1002/chem.201301728 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002chem.201301728.isotherm4](isotherms/10.1002chem.201301728.isotherm4.json) | NH2-Uio-66(Zr) | Carbon Dioxide | 273 | 10.1002/chem.201301728 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1002chem.201503078.Isotherm12](isotherms/10.1002chem.201503078.Isotherm12.json) | UiO-66-(COOLi)4-EX | Carbon Dioxide | 273 | 10.1002/chem.201503078 | Figure 8a- UiO 66 COOLi 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm13](isotherms/10.1002chem.201503078.Isotherm13.json) | UiO-66 | Carbon Dioxide | 273 | 10.1002/chem.201503078 | Figure 8a- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm14](isotherms/10.1002chem.201503078.Isotherm14.json) | UiO-66-(COONa)2-EX | Carbon Dioxide | 273 | 10.1002/chem.201503078 | Figure 8a- UiO 66 COONa 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm15](isotherms/10.1002chem.201503078.Isotherm15.json) | UiO-66-(COOLi)2-EX | Carbon Dioxide | 273 | 10.1002/chem.201503078 | Figure 8a- UiO 66 COOLi 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm16](isotherms/10.1002chem.201503078.Isotherm16.json) | UiO-66-(COOH)4-EX | Carbon Dioxide | 273 | 10.1002/chem.201503078 | Figure 8a- UiO 66 COOH 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm17](isotherms/10.1002chem.201503078.Isotherm17.json) | UiO-66-(COOK)2-EX | Carbon Dioxide | 273 | 10.1002/chem.201503078 | Figure 8a- UiO 66 COOK 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm18](isotherms/10.1002chem.201503078.Isotherm18.json) | UiO-66-(COONa)4-EX | Carbon Dioxide | 273 | 10.1002/chem.201503078 | Figure 8a- UiO 66 COONa 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm19](isotherms/10.1002chem.201503078.Isotherm19.json) | UiO-66-(COOK)4-EX | Carbon Dioxide | 273 | 10.1002/chem.201503078 | Figure 8a- UiO 66 COOK 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm20](isotherms/10.1002chem.201503078.Isotherm20.json) | UiO-66-(COOLi)4-EX | Carbon Dioxide | 298 | 10.1002/chem.201503078 | Figure 8b- UiO 66 COOLi 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm21](isotherms/10.1002chem.201503078.Isotherm21.json) | UiO-66 | Carbon Dioxide | 298 | 10.1002/chem.201503078 | Figure 8b- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm22](isotherms/10.1002chem.201503078.Isotherm22.json) | UiO-66-(COONa)2-EX | Carbon Dioxide | 298 | 10.1002/chem.201503078 | Figure 8b- UiO 66 COONa 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm23](isotherms/10.1002chem.201503078.Isotherm23.json) | UiO-66-(COOLi)2-EX | Carbon Dioxide | 298 | 10.1002/chem.201503078 | Figure 8b- UiO 66 COOLi 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm24](isotherms/10.1002chem.201503078.Isotherm24.json) | UiO-66-(COOH)4-EX | Carbon Dioxide | 298 | 10.1002/chem.201503078 | Figure 8b- UiO 66 COOH 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm25](isotherms/10.1002chem.201503078.Isotherm25.json) | UiO-66-(COOK)2-EX | Carbon Dioxide | 298 | 10.1002/chem.201503078 | Figure 8b- UiO 66 COOK 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm26](isotherms/10.1002chem.201503078.Isotherm26.json) | UiO-66-(COONa)4-EX | Carbon Dioxide | 298 | 10.1002/chem.201503078 | Figure 8b- UiO 66 COONa 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm27](isotherms/10.1002chem.201503078.Isotherm27.json) | UiO-66-(COOK)4-EX | Carbon Dioxide | 298 | 10.1002/chem.201503078 | Figure 8b- UiO 66 COOK 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm28](isotherms/10.1002chem.201503078.Isotherm28.json) | UiO-66-(COOLi)4-EX | Nitrogen | 273 | 10.1002/chem.201503078 | Figure 8c- UiO 66 COOLi 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm29](isotherms/10.1002chem.201503078.Isotherm29.json) | UiO-66-(COONa)2-EX | Nitrogen | 273 | 10.1002/chem.201503078 | Figure 8c- UiO 66 COONa 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm30](isotherms/10.1002chem.201503078.Isotherm30.json) | UiO-66 | Nitrogen | 273 | 10.1002/chem.201503078 | Figure 8c- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm31](isotherms/10.1002chem.201503078.Isotherm31.json) | UiO-66-(COOLi)2-EX | Nitrogen | 273 | 10.1002/chem.201503078 | Figure 8c- UiO 66 COOLi 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm32](isotherms/10.1002chem.201503078.Isotherm32.json) | UiO-66-(COONa)4-EX | Nitrogen | 273 | 10.1002/chem.201503078 | Figure 8c- UiO 66 COONa 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm33](isotherms/10.1002chem.201503078.Isotherm33.json) | UiO-66-(COOH)4-EX | Nitrogen | 273 | 10.1002/chem.201503078 | Figure 8c- UiO 66 COOH 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm34](isotherms/10.1002chem.201503078.Isotherm34.json) | UiO-66-(COOK)2-EX | Nitrogen | 273 | 10.1002/chem.201503078 | Figure 8c- UiO 66 COOK 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm35](isotherms/10.1002chem.201503078.Isotherm35.json) | UiO-66-(COOK)4-EX | Nitrogen | 273 | 10.1002/chem.201503078 | Figure 8c- UiO 66 COOK 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm36](isotherms/10.1002chem.201503078.Isotherm36.json) | UiO-66-(COOLi)4-EX | Nitrogen | 298 | 10.1002/chem.201503078 | Figure 8d- UiO 66 COOLi 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm37](isotherms/10.1002chem.201503078.Isotherm37.json) | UiO-66-(COONa)2-EX | Nitrogen | 298 | 10.1002/chem.201503078 | Figure 8d- UiO 66 COONa 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm38](isotherms/10.1002chem.201503078.Isotherm38.json) | UiO-66 | Nitrogen | 298 | 10.1002/chem.201503078 | Figure 8d- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm39](isotherms/10.1002chem.201503078.Isotherm39.json) | UiO-66-(COOLi)2-EX | Nitrogen | 298 | 10.1002/chem.201503078 | Figure 8d- UiO 66 COOLi 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm40](isotherms/10.1002chem.201503078.Isotherm40.json) | UiO-66-(COONa)4-EX | Nitrogen | 298 | 10.1002/chem.201503078 | Figure 8d- UiO 66 COONa 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm41](isotherms/10.1002chem.201503078.Isotherm41.json) | UiO-66-(COOK)2-EX | Nitrogen | 298 | 10.1002/chem.201503078 | Figure 8d- UiO 66 COOK 2 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm42](isotherms/10.1002chem.201503078.Isotherm42.json) | UiO-66-(COOH)4-EX | Nitrogen | 298 | 10.1002/chem.201503078 | Figure 8d- UiO 66 COOH 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1002chem.201503078.Isotherm43](isotherms/10.1002chem.201503078.Isotherm43.json) | UiO-66-(COOK)4-EX | Nitrogen | 298 | 10.1002/chem.201503078 | Figure 8d- UiO 66 COOK 4 EX | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1016j.cej.2015.04.087.Isotherm12](isotherms/10.1016j.cej.2015.04.087.Isotherm12.json) | UiO-66(Zr) | Nitrogen | 293 | 10.1016/j.cej.2015.04.087 | Figure 3b- UiO 66 Zr experiment | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1016j.cej.2015.04.087.Isotherm13](isotherms/10.1016j.cej.2015.04.087.Isotherm13.json) | UiO-66(Zr) | Nitrogen | 293 | 10.1016/j.cej.2015.04.087 | Figure 3b- UiO 66 Zr Dual LF | оцифровка рисунка NIST | Julie Yagodich | mod |
| [10.1016j.cej.2015.04.087.Isotherm32](isotherms/10.1016j.cej.2015.04.087.Isotherm32.json) | UiO-66(Zr) | Nitrogen | 283 | 10.1016/j.cej.2015.04.087 | Figure S1- N2 at 283 UiO 66 Zr experiment | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1016j.cej.2015.04.087.Isotherm33](isotherms/10.1016j.cej.2015.04.087.Isotherm33.json) | UiO-66(Zr) | Nitrogen | 283 | 10.1016/j.cej.2015.04.087 | Figure S1- N2 at 283 UiO 66 Zr Dual LF | оцифровка рисунка NIST | Julie Yagodich | mod |
| [10.1016j.cej.2015.04.087.Isotherm38](isotherms/10.1016j.cej.2015.04.087.Isotherm38.json) | UiO-66(Zr) | Nitrogen | 273 | 10.1016/j.cej.2015.04.087 | Figure S1- N2 at 273 UiO 66 Zr experiment | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1016j.cej.2015.04.087.Isotherm39](isotherms/10.1016j.cej.2015.04.087.Isotherm39.json) | UiO-66(Zr) | Nitrogen | 273 | 10.1016/j.cej.2015.04.087 | Figure S1- N2 at 273 UiO 66 Zr Dual LF | оцифровка рисунка NIST | Julie Yagodich | mod |
| [10.1016j.egypro.2013.05.082.Isotherm1](isotherms/10.1016j.egypro.2013.05.082.Isotherm1.json) | UiO-66 | Carbon Dioxide | 303 | 10.1016/j.egypro.2013.05.082 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.egypro.2013.05.082.Isotherm3](isotherms/10.1016j.egypro.2013.05.082.Isotherm3.json) | UiO-66 | Nitrogen | 303 | 10.1016/j.egypro.2013.05.082 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.jcis.2011.09.060.isotherm1](isotherms/10.1016j.jcis.2011.09.060.isotherm1.json) | UiO-66 | Nitrogen | 273 | 10.1016/j.jcis.2011.09.060 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.jcis.2011.09.060.isotherm2](isotherms/10.1016j.jcis.2011.09.060.isotherm2.json) | UiO-66-NH4 | Nitrogen | 273 | 10.1016/j.jcis.2011.09.060 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.jcis.2011.09.060.isotherm3](isotherms/10.1016j.jcis.2011.09.060.isotherm3.json) | UiO-66 | Carbon Dioxide | 273 | 10.1016/j.jcis.2011.09.060 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.jcis.2011.09.060.isotherm5](isotherms/10.1016j.jcis.2011.09.060.isotherm5.json) | UiO-66-NH4 | Carbon Dioxide | 273 | 10.1016/j.jcis.2011.09.060 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.jece.2016.01.017.Isotherm1](isotherms/10.1016j.jece.2016.01.017.Isotherm1.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure  1 | оцифровка рисунка NIST | Matthew Weiss | mod |
| [10.1016j.jece.2016.01.017.Isotherm10](isotherms/10.1016j.jece.2016.01.017.Isotherm10.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure 4 | оцифровка рисунка NIST | Matthew Weiss | mod |
| [10.1016j.jece.2016.01.017.Isotherm11](isotherms/10.1016j.jece.2016.01.017.Isotherm11.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure 6 | оцифровка рисунка NIST | Matthew Weiss | mod |
| [10.1016j.jece.2016.01.017.Isotherm12](isotherms/10.1016j.jece.2016.01.017.Isotherm12.json) | UiO-66/GO-5 | Carbon Dioxide | 298 | 10.1016/j.jece.2016.01.017 | Figure 7 | оцифровка рисунка NIST | Matthew Weiss | mod |
| [10.1016j.jece.2016.01.017.Isotherm13](isotherms/10.1016j.jece.2016.01.017.Isotherm13.json) | UiO-66/GO-5 | Carbon Dioxide | 298 | 10.1016/j.jece.2016.01.017 | Figure 7 | оцифровка рисунка NIST | Matthew Weiss | mod |
| [10.1016j.jece.2016.01.017.Isotherm14](isotherms/10.1016j.jece.2016.01.017.Isotherm14.json) | UiO-66/GO-5 | Carbon Dioxide | 298 | 10.1016/j.jece.2016.01.017 | Figure 7 | оцифровка рисунка NIST | Matthew Weiss | mod |
| [10.1016j.jece.2016.01.017.Isotherm2](isotherms/10.1016j.jece.2016.01.017.Isotherm2.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure  1 | оцифровка рисунка NIST | Matthew Weiss | mod |
| [10.1016j.jece.2016.01.017.Isotherm3](isotherms/10.1016j.jece.2016.01.017.Isotherm3.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure  1 | оцифровка рисунка NIST | Matthew Weiss | mod |
| [10.1016j.jece.2016.01.017.Isotherm4](isotherms/10.1016j.jece.2016.01.017.Isotherm4.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure  2 | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1016j.jece.2016.01.017.Isotherm5](isotherms/10.1016j.jece.2016.01.017.Isotherm5.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure  2 | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1016j.jece.2016.01.017.Isotherm6](isotherms/10.1016j.jece.2016.01.017.Isotherm6.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure  2 | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1016j.jece.2016.01.017.Isotherm7](isotherms/10.1016j.jece.2016.01.017.Isotherm7.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure  3 | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1016j.jece.2016.01.017.Isotherm8](isotherms/10.1016j.jece.2016.01.017.Isotherm8.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure  3 | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1016j.jece.2016.01.017.Isotherm9](isotherms/10.1016j.jece.2016.01.017.Isotherm9.json) | UiO-66/GO-5 | Carbon Dioxide | 273 | 10.1016/j.jece.2016.01.017 | Figure 4 | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1016j.jiec.2014.12.021.Isotherm10](isotherms/10.1016j.jiec.2014.12.021.Isotherm10.json) | UiO-66/GO-1 | Carbon Dioxide | 298 | 10.1016/j.jiec.2014.12.021 | Figure 7 | оцифровка рисунка NIST | Yamuna E. Satsangi | exp |
| [10.1016j.jiec.2014.12.021.Isotherm11](isotherms/10.1016j.jiec.2014.12.021.Isotherm11.json) | UiO-66/GO-10 | Carbon Dioxide | 298 | 10.1016/j.jiec.2014.12.021 | Figure 7 | оцифровка рисунка NIST | Yamuna E. Satsangi | exp |
| [10.1016j.jiec.2014.12.021.Isotherm7](isotherms/10.1016j.jiec.2014.12.021.Isotherm7.json) | UiO-66 | Nitrogen | 298 | 10.1016/j.jiec.2014.12.021 | Figure 7 | оцифровка рисунка NIST | Yamuna E. Satsangi | exp |
| [10.1016j.jiec.2014.12.021.Isotherm8](isotherms/10.1016j.jiec.2014.12.021.Isotherm8.json) | UiO-66 | Carbon Dioxide | 298 | 10.1016/j.jiec.2014.12.021 | Figure 7 | оцифровка рисунка NIST | Yamuna E. Satsangi | exp |
| [10.1016j.jiec.2014.12.021.Isotherm9](isotherms/10.1016j.jiec.2014.12.021.Isotherm9.json) | UiO-66/GO-5 | Carbon Dioxide | 298 | 10.1016/j.jiec.2014.12.021 | Figure 7 | оцифровка рисунка NIST | Yamuna E. Satsangi | exp |
| [10.1016j.memsci.2012.04.003.Isotherm13](isotherms/10.1016j.memsci.2012.04.003.Isotherm13.json) | NH2-UiO-66 | Carbon Dioxide | 308 | 10.1016/j.memsci.2012.04.003 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.memsci.2012.04.003.Isotherm14](isotherms/10.1016j.memsci.2012.04.003.Isotherm14.json) | UiO-66 | Carbon Dioxide | 308 | 10.1016/j.memsci.2012.04.003 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.memsci.2012.04.003.Isotherm3](isotherms/10.1016j.memsci.2012.04.003.Isotherm3.json) | NH2-UiO-66 | Carbon Dioxide | 308 | 10.1016/j.memsci.2012.04.003 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.memsci.2012.04.003.Isotherm4](isotherms/10.1016j.memsci.2012.04.003.Isotherm4.json) | UiO-66 | Carbon Dioxide | 308 | 10.1016/j.memsci.2012.04.003 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1016j.micromeso.2014.02.014.Isotherm2](isotherms/10.1016j.micromeso.2014.02.014.Isotherm2.json) | UiO-66 | Carbon Dioxide | 303 | 10.1016/j.micromeso.2014.02.014 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ie202325p.Isotherm3](isotherms/10.1021Ie202325p.Isotherm3.json) | UiO-66 | Water | 298 | 10.1021/ie202325p | Figure 2 | оцифровка рисунка NIST | Daniel W. Siderius | exp |
| [10.1021Ie202325p.Isotherm4](isotherms/10.1021Ie202325p.Isotherm4.json) | UiO-66-NH2 | Water | 298 | 10.1021/ie202325p | Figure 2 | оцифровка рисунка NIST | Daniel W. Siderius | exp |
| [10.1021Ie4011035.Isotherm15](isotherms/10.1021Ie4011035.Isotherm15.json) | UiO-66(Zr) | Nitrogen | 298 | 10.1021/Ie4011035 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ie4011035.Isotherm16](isotherms/10.1021Ie4011035.Isotherm16.json) | UiO-66(Zr)-Br | Nitrogen | 298 | 10.1021/Ie4011035 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ie4011035.Isotherm3](isotherms/10.1021Ie4011035.Isotherm3.json) | UiO-66(Zr) | Carbon Dioxide | 298 | 10.1021/Ie4011035 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ie4011035.Isotherm4](isotherms/10.1021Ie4011035.Isotherm4.json) | UiO-66(Zr)-Br | Carbon Dioxide | 298 | 10.1021/Ie4011035 | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm17](isotherms/10.1021Ja404514r.isotherm17.json) | Hydroxylated UiO-66 | Carbon Dioxide | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm18](isotherms/10.1021Ja404514r.isotherm18.json) | UiO-66-S1 | Carbon Dioxide | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm27](isotherms/10.1021Ja404514r.isotherm27.json) | UiO-66-S3p | Carbon Dioxide | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm28](isotherms/10.1021Ja404514r.isotherm28.json) | UiO-66-S1 | Carbon Dioxide | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm3](isotherms/10.1021Ja404514r.isotherm3.json) | UiO-66-S3p | Carbon Dioxide | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm31](isotherms/10.1021Ja404514r.isotherm31.json) | Hydroxylated UiO-66 | Nitrogen | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm32](isotherms/10.1021Ja404514r.isotherm32.json) | UiO-66-S1 | Nitrogen | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm35](isotherms/10.1021Ja404514r.isotherm35.json) | Hydroxylated UiO-66 | Nitrogen | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm36](isotherms/10.1021Ja404514r.isotherm36.json) | UiO-66-S1 | Nitrogen | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm4](isotherms/10.1021Ja404514r.isotherm4.json) | UiO-66-S1 | Carbon Dioxide | 300 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm47](isotherms/10.1021Ja404514r.isotherm47.json) | Hydroxylated UiO-66 | Carbon Dioxide | 298 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja404514r.isotherm50](isotherms/10.1021Ja404514r.isotherm50.json) | Dehydroxylated UiO-66 | Carbon Dioxide | 298 | 10.1021/Ja404514r | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Ja500330a.Isotherm3](isotherms/10.1021Ja500330a.Isotherm3.json) | UiO-66 | Water | 298 | 10.1021/Ja500330a | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Jp308657x.ISOTHERM12](isotherms/10.1021Jp308657x.ISOTHERM12.json) | UiO-66 | Carbon Dioxide | 303 | 10.1021/Jp308657x | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Jp308657x.ISOTHERM13](isotherms/10.1021Jp308657x.ISOTHERM13.json) | UiO-66 | Carbon Dioxide | 303 | 10.1021/Jp308657x | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Jp308657x.isotherm2](isotherms/10.1021Jp308657x.isotherm2.json) | UiO-66 | Carbon Dioxide | 303 | 10.1021/Jp308657x | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Jp308657x.isotherm3](isotherms/10.1021Jp308657x.isotherm3.json) | UiO-66 | Carbon Dioxide | 303 | 10.1021/Jp308657x | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Jp308657x.isotherm6](isotherms/10.1021Jp308657x.isotherm6.json) | UiO-66 | Carbon Dioxide | 303 | 10.1021/Jp308657x | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021Jp308657x.isotherm7](isotherms/10.1021Jp308657x.isotherm7.json) | UiO-66 | Carbon Dioxide | 303 | 10.1021/Jp308657x | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021acs.chemmater.5b00665.Isotherm10](isotherms/10.1021acs.chemmater.5b00665.Isotherm10.json) | UiO-66(Zr4+) with metal/ligand ratio 6:6 | Water | 298 | 10.1021/acs.chemmater.5b00665 | Figure 4 | оцифровка рисунка NIST | Kailey M. Stracka | exp |
| [10.1021acs.chemmater.5b00665.Isotherm11](isotherms/10.1021acs.chemmater.5b00665.Isotherm11.json) | UiO-66(Zr4+) with metal/ligand ratio 6:4 | Water | 298 | 10.1021/acs.chemmater.5b00665 | Figure 4 | оцифровка рисунка NIST | Kailey M. Stracka | exp |
| [10.1021acs.chemmater.5b00665.Isotherm12](isotherms/10.1021acs.chemmater.5b00665.Isotherm12.json) | UiO-66(Zr4+) with metal/ligand ratio 6:3 | Water | 298 | 10.1021/acs.chemmater.5b00665 | Figure 4 | оцифровка рисунка NIST | Kailey M. Stracka | exp |
| [10.1021acs.chemmater.5b00665.Isotherm7](isotherms/10.1021acs.chemmater.5b00665.Isotherm7.json) | UiO-66(Zr4+) with high concentration stearic acid | Water | 298 | 10.1021/acs.chemmater.5b00665 | Figure 4 | оцифровка рисунка NIST | Kailey M. Stracka | exp |
| [10.1021acs.chemmater.5b00665.Isotherm8](isotherms/10.1021acs.chemmater.5b00665.Isotherm8.json) | UiO-66(Zr4+) with low concentration stearic acid | Water | 298 | 10.1021/acs.chemmater.5b00665 | Figure 4 | оцифровка рисунка NIST | Kailey M. Stracka | exp |
| [10.1021acs.chemmater.5b00665.Isotherm9](isotherms/10.1021acs.chemmater.5b00665.Isotherm9.json) | UiO-66(Zr4+) with acetic acid | Water | 298 | 10.1021/acs.chemmater.5b00665 | Figure 4 | оцифровка рисунка NIST | Kailey M. Stracka | exp |
| [10.1021acs.iecr.5b03517.Isotherm5](isotherms/10.1021acs.iecr.5b03517.Isotherm5.json) | UiO-66 | Carbon Dioxide | 298 | 10.1021/acs.iecr.5b03517 | Figure 4 | оцифровка рисунка NIST | Soojin Jang | exp |
| [10.1021acs.iecr.5b03517.Isotherm6](isotherms/10.1021acs.iecr.5b03517.Isotherm6.json) | 10PEI@UiO-66 | Carbon Dioxide | 298 | 10.1021/acs.iecr.5b03517 | Figure 4 | оцифровка рисунка NIST | Soojin Jang | exp |
| [10.1021acs.iecr.5b03517.Isotherm7](isotherms/10.1021acs.iecr.5b03517.Isotherm7.json) | 20PEI@UiO-66 | Carbon Dioxide | 298 | 10.1021/acs.iecr.5b03517 | Figure 4 | оцифровка рисунка NIST | Soojin Jang | exp |
| [10.1021acs.iecr.5b03517.Isotherm8](isotherms/10.1021acs.iecr.5b03517.Isotherm8.json) | 30PEI@UiO-66 | Carbon Dioxide | 298 | 10.1021/acs.iecr.5b03517 | Figure 4 | оцифровка рисунка NIST | Soojin Jang | exp |
| [10.1021acs.iecr.5b03517.Isotherm9](isotherms/10.1021acs.iecr.5b03517.Isotherm9.json) | 40PEI@UiO-66 | Carbon Dioxide | 298 | 10.1021/acs.iecr.5b03517 | Figure 4 | оцифровка рисунка NIST | Soojin Jang | exp |
| [10.1021acs.iecr.5b04061.Isotherm10](isotherms/10.1021acs.iecr.5b04061.Isotherm10.json) | UiO-66-NO2-(OH)2 | Nitrogen | 273 | 10.1021/acs.iecr.5b04061 | Figure 6B | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1021acs.iecr.5b04061.Isotherm11](isotherms/10.1021acs.iecr.5b04061.Isotherm11.json) | UiO-66-(OH)2 | Nitrogen | 273 | 10.1021/acs.iecr.5b04061 | Figure 6B | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1021acs.iecr.5b04061.Isotherm12](isotherms/10.1021acs.iecr.5b04061.Isotherm12.json) | UiO-66-(OH)2-NO2 | Nitrogen | 273 | 10.1021/acs.iecr.5b04061 | Figure 6B | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1021acs.iecr.5b04061.Isotherm5](isotherms/10.1021acs.iecr.5b04061.Isotherm5.json) | UiO-66-NO2 | Nitrogen | 298 | 10.1021/acs.iecr.5b04061 | Figure 6A | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1021acs.iecr.5b04061.Isotherm6](isotherms/10.1021acs.iecr.5b04061.Isotherm6.json) | UiO-66-NO2-(OH)2 | Nitrogen | 298 | 10.1021/acs.iecr.5b04061 | Figure 6A | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1021acs.iecr.5b04061.Isotherm7](isotherms/10.1021acs.iecr.5b04061.Isotherm7.json) | UiO-66-(OH)2-NO2 | Nitrogen | 298 | 10.1021/acs.iecr.5b04061 | Figure 6A | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1021acs.iecr.5b04061.Isotherm8](isotherms/10.1021acs.iecr.5b04061.Isotherm8.json) | UiO-66-(OH)2 | Nitrogen | 298 | 10.1021/acs.iecr.5b04061 | Figure 6A | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1021acs.iecr.5b04061.Isotherm9](isotherms/10.1021acs.iecr.5b04061.Isotherm9.json) | UiO-66-NO2 | Nitrogen | 273 | 10.1021/acs.iecr.5b04061 | Figure 6B | оцифровка рисунка NIST | Matthew Weiss | exp |
| [10.1021acs.iecr.5b04739.Isotherm2](isotherms/10.1021acs.iecr.5b04739.Isotherm2.json) | UiO-66 | Water | 298 | 10.1021/acs.iecr.5b04739 | Figure 5 | оцифровка рисунка NIST | Patrick Donahue | exp |
| [10.1021acs.iecr.5b04739.Isotherm3](isotherms/10.1021acs.iecr.5b04739.Isotherm3.json) | UiO-66-CH3 | Water | 298 | 10.1021/acs.iecr.5b04739 | Figure 5 | оцифровка рисунка NIST | Patrick Donahue | exp |
| [10.1021acs.iecr.5b04739.Isotherm4](isotherms/10.1021acs.iecr.5b04739.Isotherm4.json) | UiO-66-CH3 | Carbon Dioxide | 298 | 10.1021/acs.iecr.5b04739 | Figure 6 | оцифровка рисунка NIST | Patrick Donahue | exp |
| [10.1021acs.iecr.5b04739.Isotherm5](isotherms/10.1021acs.iecr.5b04739.Isotherm5.json) | UiO-66-CH3 | Nitrogen | 298 | 10.1021/acs.iecr.5b04739 | Figure 6 | оцифровка рисунка NIST | Patrick Donahue | exp |
| [10.1021acs.iecr.7b02839.Isotherm4](isotherms/10.1021acs.iecr.7b02839.Isotherm4.json) | UiO-66-TU | Au(III);Water | 298 | 10.1021/acs.iecr.7b02839 | Figure 6a | оцифровка рисунка NIST | Sophia Deng | exp |
| [10.1021acs.iecr.7b02839.Isotherm6](isotherms/10.1021acs.iecr.7b02839.Isotherm6.json) | UiO-66 | Au(III);Water | 298 | 10.1021/acs.iecr.7b02839 | Figure S7A | оцифровка рисунка NIST | Sophia Deng | exp |
| [10.1021acs.iecr.7b02839.Isotherm7](isotherms/10.1021acs.iecr.7b02839.Isotherm7.json) | UiO-66-NH2 | Au(III);Water | 298 | 10.1021/acs.iecr.7b02839 | Figure S7A | оцифровка рисунка NIST | Sophia Deng | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm10](isotherms/10.1021acs.inorgchem.5b00435.Isotherm10.json) | UiO-66-(COOH)2 | Carbon Dioxide | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4a- UiO 66 COOH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm11](isotherms/10.1021acs.inorgchem.5b00435.Isotherm11.json) | UiO-66-(F)4 | Carbon Dioxide | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4a- UiO 66 F4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm12](isotherms/10.1021acs.inorgchem.5b00435.Isotherm12.json) | UiO-66 | Carbon Dioxide | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4a- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm13](isotherms/10.1021acs.inorgchem.5b00435.Isotherm13.json) | UiO-66-(OCH2CH3)2 | Carbon Dioxide | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4a- UiO 66 OCH2CH3 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm14](isotherms/10.1021acs.inorgchem.5b00435.Isotherm14.json) | UiO-66-(COOH)4 | Carbon Dioxide | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4a- UiO 66 COOH 4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm15](isotherms/10.1021acs.inorgchem.5b00435.Isotherm15.json) | UiO-66-(OH)2 | Carbon Dioxide | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4- UiO 66 OH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm16](isotherms/10.1021acs.inorgchem.5b00435.Isotherm16.json) | UiO-66-(COOH)2 | Carbon Dioxide | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4- UiO 66 COOH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm17](isotherms/10.1021acs.inorgchem.5b00435.Isotherm17.json) | UiO-66-NH2 | Carbon Dioxide | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4- UiO 66 NH2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm18](isotherms/10.1021acs.inorgchem.5b00435.Isotherm18.json) | UiO-66 | Carbon Dioxide | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm19](isotherms/10.1021acs.inorgchem.5b00435.Isotherm19.json) | UiO-66-(F)4 | Carbon Dioxide | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4- UiO 66 F4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm20](isotherms/10.1021acs.inorgchem.5b00435.Isotherm20.json) | UiO-66-(OCH2CH3)2 | Carbon Dioxide | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4- UiO 66 OCH2CH3 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm21](isotherms/10.1021acs.inorgchem.5b00435.Isotherm21.json) | UiO-66-(COOH)4 | Carbon Dioxide | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4- UiO 66 COOH 4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm22](isotherms/10.1021acs.inorgchem.5b00435.Isotherm22.json) | UiO-66-(F)4 | Nitrogen | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4c- UiO 66 F4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm23](isotherms/10.1021acs.inorgchem.5b00435.Isotherm23.json) | UiO-66-(OH)2 | Nitrogen | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4c- UiO 66 OH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm24](isotherms/10.1021acs.inorgchem.5b00435.Isotherm24.json) | UiO-66 | Nitrogen | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4c- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm25](isotherms/10.1021acs.inorgchem.5b00435.Isotherm25.json) | UiO-66-(COOH)2 | Nitrogen | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4c- UiO 66 COOH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm26](isotherms/10.1021acs.inorgchem.5b00435.Isotherm26.json) | UiO-66-NH2 | Nitrogen | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4c- UiO 66 NH2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm27](isotherms/10.1021acs.inorgchem.5b00435.Isotherm27.json) | UiO-66-(COOH)4 | Nitrogen | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4c- UiO 66 COOH 4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm28](isotherms/10.1021acs.inorgchem.5b00435.Isotherm28.json) | UiO-66-(OCH2CH3)2 | Nitrogen | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4c- UiO 66 OCH2CH3 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm29](isotherms/10.1021acs.inorgchem.5b00435.Isotherm29.json) | UiO-66-(F)4 | Nitrogen | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4d- UiO 66 F4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm30](isotherms/10.1021acs.inorgchem.5b00435.Isotherm30.json) | UiO-66-(COOH)2 | Nitrogen | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4d- UiO 66 COOH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm31](isotherms/10.1021acs.inorgchem.5b00435.Isotherm31.json) | UiO-66-(OH)2 | Nitrogen | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4d- UiO 66 OH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm32](isotherms/10.1021acs.inorgchem.5b00435.Isotherm32.json) | UiO-66-NH2 | Nitrogen | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4d- UiO 66 NH2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm33](isotherms/10.1021acs.inorgchem.5b00435.Isotherm33.json) | UiO-66 | Nitrogen | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4d- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm34](isotherms/10.1021acs.inorgchem.5b00435.Isotherm34.json) | UiO-66-(COOH)4 | Nitrogen | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4d- UiO 66 COOH 4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm35](isotherms/10.1021acs.inorgchem.5b00435.Isotherm35.json) | UiO-66-(OCH2CH3)2 | Nitrogen | 298 | 10.1021/acs.inorgchem.5b00435 | Figure 4d- UiO 66 OCH2CH3 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm36](isotherms/10.1021acs.inorgchem.5b00435.Isotherm36.json) | UiO-66 (solvothermal) | Water | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 6- UiO 66 Solvothermal | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm37](isotherms/10.1021acs.inorgchem.5b00435.Isotherm37.json) | UiO-66-NH2 | Water | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 6- UiO 66 NH2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm38](isotherms/10.1021acs.inorgchem.5b00435.Isotherm38.json) | UiO-66-(COOH)2 | Water | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 6- UiO 66 COOH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm39](isotherms/10.1021acs.inorgchem.5b00435.Isotherm39.json) | UiO-66-(F)4 | Water | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 6- UiO 66 F4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm40](isotherms/10.1021acs.inorgchem.5b00435.Isotherm40.json) | UiO-66 | Water | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 6- UiO 66 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm41](isotherms/10.1021acs.inorgchem.5b00435.Isotherm41.json) | UiO-66-(OH)2 | Water | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 6- UiO 66 OH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm42](isotherms/10.1021acs.inorgchem.5b00435.Isotherm42.json) | UiO-66-(COOH)4 | Water | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 6- UiO 66 COOH 4 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm43](isotherms/10.1021acs.inorgchem.5b00435.Isotherm43.json) | UiO-66-(OCH2CH3)2 | Water | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 6- UiO 66 OCH2CH3 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm8](isotherms/10.1021acs.inorgchem.5b00435.Isotherm8.json) | UiO-66-NH2 | Carbon Dioxide | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4a- UiO 66 NH2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021acs.inorgchem.5b00435.Isotherm9](isotherms/10.1021acs.inorgchem.5b00435.Isotherm9.json) | UiO-66-(OH)2 | Carbon Dioxide | 273 | 10.1021/acs.inorgchem.5b00435 | Figure 4a- UiO 66 OH 2 | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021ar500272n.Isotherm17](isotherms/10.1021ar500272n.Isotherm17.json) | UiO-66 | Carbon Dioxide | 298 | 10.1021/ar500272n | Figure 5- UiO66 experiment | оцифровка рисунка NIST | Julie Yagodich | exp |
| [10.1021ar500272n.Isotherm18](isotherms/10.1021ar500272n.Isotherm18.json) | UiO-66 | Carbon Dioxide | 298 | 10.1021/ar500272n | Figure 5- UiO66 simulation | оцифровка рисунка NIST | Julie Yagodich | sim |
| [10.1021ja302787x.Isotherm1](isotherms/10.1021ja302787x.Isotherm1.json) | UiO-66 | Water | 298 | 10.1021/ja302787x | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021ja302787x.Isotherm2](isotherms/10.1021ja302787x.Isotherm2.json) | UiO-66 | Water | 298 | 10.1021/ja302787x | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021jp202633t.Isotherm1](isotherms/10.1021jp202633t.Isotherm1.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021/jp202633t | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021jp202633t.Isotherm10](isotherms/10.1021jp202633t.Isotherm10.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021/jp202633t | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021jp202633t.Isotherm2](isotherms/10.1021jp202633t.Isotherm2.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021/jp202633t | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021jp202633t.Isotherm21](isotherms/10.1021jp202633t.Isotherm21.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021/jp202633t | Figure 2 | оцифровка рисунка NIST | John Luo | exp |
| [10.1021jp202633t.Isotherm22](isotherms/10.1021jp202633t.Isotherm22.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021/jp202633t | Figure 2 | оцифровка рисунка NIST | John Luo | sim |
| [10.1021jp202633t.Isotherm25](isotherms/10.1021jp202633t.Isotherm25.json) | UiO-66(Zr) | Carbon Dioxide;Methane | 303 | 10.1021/jp202633t | Figure 2 | оцифровка рисунка NIST | John Luo | exp |
| [10.1021jp202633t.Isotherm26](isotherms/10.1021jp202633t.Isotherm26.json) | UiO-66(Zr) | Carbon Dioxide;Methane | 303 | 10.1021/jp202633t | Figure 2 | оцифровка рисунка NIST | John Luo | sim |
| [10.1021jp202633t.Isotherm27](isotherms/10.1021jp202633t.Isotherm27.json) | UiO-66(Zr) | Carbon Dioxide;Methane | 303 | 10.1021/jp202633t | Figure 2 | оцифровка рисунка NIST | John Luo | exp |
| [10.1021jp202633t.Isotherm28](isotherms/10.1021jp202633t.Isotherm28.json) | UiO-66(Zr) | Carbon Dioxide;Methane | 303 | 10.1021/jp202633t | Figure 2 | оцифровка рисунка NIST | John Luo | sim |
| [10.1021jp202633t.Isotherm5](isotherms/10.1021jp202633t.Isotherm5.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021/jp202633t | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021jp202633t.Isotherm6](isotherms/10.1021jp202633t.Isotherm6.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021/jp202633t | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1021jp202633t.Isotherm9](isotherms/10.1021jp202633t.Isotherm9.json) | UiO-66(Zr) | Carbon Dioxide | 303 | 10.1021/jp202633t | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm1](isotherms/10.1039C2cp23839j.Isotherm1.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm100](isotherms/10.1039C2cp23839j.Isotherm100.json) | UiO-66-NO2 | Carbon Dioxide | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm101](isotherms/10.1039C2cp23839j.Isotherm101.json) | UiO-66-NO2 | Carbon Dioxide | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm102](isotherms/10.1039C2cp23839j.Isotherm102.json) | UiO-66-NO2 | Carbon Dioxide | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm121](isotherms/10.1039C2cp23839j.Isotherm121.json) | UiO-66-NO2 | Nitrogen | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm122](isotherms/10.1039C2cp23839j.Isotherm122.json) | UiO-66-NO2 | Nitrogen | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm123](isotherms/10.1039C2cp23839j.Isotherm123.json) | UiO-66-NO2 | Nitrogen | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm124](isotherms/10.1039C2cp23839j.Isotherm124.json) | UiO-66-NO2 | Nitrogen | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm125](isotherms/10.1039C2cp23839j.Isotherm125.json) | UiO-66-NO2 | Nitrogen | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm126](isotherms/10.1039C2cp23839j.Isotherm126.json) | UiO-66-NO2 | Nitrogen | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm2](isotherms/10.1039C2cp23839j.Isotherm2.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm25](isotherms/10.1039C2cp23839j.Isotherm25.json) | UiO-66 | Nitrogen | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm26](isotherms/10.1039C2cp23839j.Isotherm26.json) | UiO-66 | Nitrogen | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm27](isotherms/10.1039C2cp23839j.Isotherm27.json) | UiO-66 | Nitrogen | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm28](isotherms/10.1039C2cp23839j.Isotherm28.json) | UiO-66 | Nitrogen | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm29](isotherms/10.1039C2cp23839j.Isotherm29.json) | UiO-66 | Nitrogen | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm3](isotherms/10.1039C2cp23839j.Isotherm3.json) | UiO-66 | Carbon Dioxide | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm30](isotherms/10.1039C2cp23839j.Isotherm30.json) | UiO-66 | Nitrogen | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm33](isotherms/10.1039C2cp23839j.Isotherm33.json) | UiO-66-Br | Carbon Dioxide | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm34](isotherms/10.1039C2cp23839j.Isotherm34.json) | UiO-66-Br | Carbon Dioxide | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm35](isotherms/10.1039C2cp23839j.Isotherm35.json) | UiO-66-Br | Carbon Dioxide | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm36](isotherms/10.1039C2cp23839j.Isotherm36.json) | UiO-66-Br | Carbon Dioxide | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm37](isotherms/10.1039C2cp23839j.Isotherm37.json) | UiO-66-Br | Carbon Dioxide | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm38](isotherms/10.1039C2cp23839j.Isotherm38.json) | UiO-66-Br | Carbon Dioxide | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm4](isotherms/10.1039C2cp23839j.Isotherm4.json) | UiO-66 | Carbon Dioxide | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm5](isotherms/10.1039C2cp23839j.Isotherm5.json) | UiO-66 | Carbon Dioxide | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm57](isotherms/10.1039C2cp23839j.Isotherm57.json) | UiO-66-Br | Nitrogen | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm58](isotherms/10.1039C2cp23839j.Isotherm58.json) | UiO-66-Br | Nitrogen | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm59](isotherms/10.1039C2cp23839j.Isotherm59.json) | UiO-66-Br | Nitrogen | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm6](isotherms/10.1039C2cp23839j.Isotherm6.json) | UiO-66 | Carbon Dioxide | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm60](isotherms/10.1039C2cp23839j.Isotherm60.json) | UiO-66-Br | Nitrogen | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm61](isotherms/10.1039C2cp23839j.Isotherm61.json) | UiO-66-Br | Nitrogen | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm62](isotherms/10.1039C2cp23839j.Isotherm62.json) | UiO-66-Br | Nitrogen | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm65](isotherms/10.1039C2cp23839j.Isotherm65.json) | UiO-66-NH2 | Nitrogen | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm66](isotherms/10.1039C2cp23839j.Isotherm66.json) | UiO-66-NH2 | Nitrogen | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm67](isotherms/10.1039C2cp23839j.Isotherm67.json) | UiO-66-NH2 | Nitrogen | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm68](isotherms/10.1039C2cp23839j.Isotherm68.json) | UiO-66-NH2 | Nitrogen | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm69](isotherms/10.1039C2cp23839j.Isotherm69.json) | UiO-66-NH2 | Nitrogen | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm70](isotherms/10.1039C2cp23839j.Isotherm70.json) | UiO-66-NH2 | Nitrogen | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm73](isotherms/10.1039C2cp23839j.Isotherm73.json) | UiO-66-NH2 | Carbon Dioxide | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm74](isotherms/10.1039C2cp23839j.Isotherm74.json) | UiO-66-NH2 | Carbon Dioxide | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm75](isotherms/10.1039C2cp23839j.Isotherm75.json) | UiO-66-NH2 | Carbon Dioxide | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm76](isotherms/10.1039C2cp23839j.Isotherm76.json) | UiO-66-NH2 | Carbon Dioxide | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm77](isotherms/10.1039C2cp23839j.Isotherm77.json) | UiO-66-NH2 | Carbon Dioxide | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm78](isotherms/10.1039C2cp23839j.Isotherm78.json) | UiO-66-NH2 | Carbon Dioxide | 323 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm97](isotherms/10.1039C2cp23839j.Isotherm97.json) | UiO-66-NO2 | Carbon Dioxide | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm98](isotherms/10.1039C2cp23839j.Isotherm98.json) | UiO-66-NO2 | Carbon Dioxide | 273 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2cp23839j.Isotherm99](isotherms/10.1039C2cp23839j.Isotherm99.json) | UiO-66-NO2 | Carbon Dioxide | 298 | 10.1039/C2cp23839j | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm1](isotherms/10.1039C2dt30950e.Isotherm1.json) | UiO-66-(CH3)2 | Carbon Dioxide | 293 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm10](isotherms/10.1039C2dt30950e.Isotherm10.json) | UiO-66-Br | Carbon Dioxide | 273 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm2](isotherms/10.1039C2dt30950e.Isotherm2.json) | UiO-66-NH2 | Carbon Dioxide | 293 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm3](isotherms/10.1039C2dt30950e.Isotherm3.json) | UiO-66-NO2 | Carbon Dioxide | 293 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm4](isotherms/10.1039C2dt30950e.Isotherm4.json) | UiO-66 | Carbon Dioxide | 293 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm5](isotherms/10.1039C2dt30950e.Isotherm5.json) | UiO-66-Br | Carbon Dioxide | 293 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm6](isotherms/10.1039C2dt30950e.Isotherm6.json) | UiO-66-(CH3)2 | Carbon Dioxide | 273 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm7](isotherms/10.1039C2dt30950e.Isotherm7.json) | UiO-66-NH2 | Carbon Dioxide | 273 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm8](isotherms/10.1039C2dt30950e.Isotherm8.json) | UiO-66-NO2 | Carbon Dioxide | 273 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C2dt30950e.Isotherm9](isotherms/10.1039C2dt30950e.Isotherm9.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C2dt30950e | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C3cc40470f.isotherm1](isotherms/10.1039C3cc40470f.isotherm1.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C3cc40470f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C3cc40470f.isotherm2](isotherms/10.1039C3cc40470f.isotherm2.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C3cc40470f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C3cc40470f.isotherm3](isotherms/10.1039C3cc40470f.isotherm3.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C3cc40470f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C3cc40470f.isotherm4](isotherms/10.1039C3cc40470f.isotherm4.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C3cc40470f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C3cc40470f.isotherm5](isotherms/10.1039C3cc40470f.isotherm5.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C3cc40470f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C3cc40470f.isotherm6](isotherms/10.1039C3cc40470f.isotherm6.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C3cc40470f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C3cc40470f.isotherm7](isotherms/10.1039C3cc40470f.isotherm7.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/C3cc40470f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm1](isotherms/10.1039C4cc04945d.Isotherm1.json) | UiO-66 | Water | 298 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm10](isotherms/10.1039C4cc04945d.Isotherm10.json) | UiO-66 | Carbon Dioxide | 300 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm11](isotherms/10.1039C4cc04945d.Isotherm11.json) | UiO-66 | Carbon Dioxide | 300 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm12](isotherms/10.1039C4cc04945d.Isotherm12.json) | UiO-66 | Carbon Dioxide | 300 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm2](isotherms/10.1039C4cc04945d.Isotherm2.json) | UiO-66 | Water | 298 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm3](isotherms/10.1039C4cc04945d.Isotherm3.json) | UiO-66 | Water | 298 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm4](isotherms/10.1039C4cc04945d.Isotherm4.json) | UiO-66 | Water | 298 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm5](isotherms/10.1039C4cc04945d.Isotherm5.json) | UiO-66 | Water | 298 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm6](isotherms/10.1039C4cc04945d.Isotherm6.json) | UiO-66 | Water | 298 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm7](isotherms/10.1039C4cc04945d.Isotherm7.json) | UiO-66 | Carbon Dioxide | 300 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm8](isotherms/10.1039C4cc04945d.Isotherm8.json) | UiO-66 | Carbon Dioxide | 300 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cc04945d.Isotherm9](isotherms/10.1039C4cc04945d.Isotherm9.json) | UiO-66 | Carbon Dioxide | 300 | 10.1039/C4cc04945d | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cs00078a.Isotherm10](isotherms/10.1039C4cs00078a.Isotherm10.json) | UiO-66-NH2 | Water | 298 | 10.1039/C4cs00078a | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039C4cs00078a.Isotherm9](isotherms/10.1039C4cs00078a.Isotherm9.json) | UiO-66 | Water | 298 | 10.1039/C4cs00078a | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c2nr30244f.isotherm2](isotherms/10.1039c2nr30244f.isotherm2.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/c2nr30244f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c2nr30244f.isotherm2b](isotherms/10.1039c2nr30244f.isotherm2b.json) | UiO-66 | Carbon Dioxide | 302 | 10.1039/c2nr30244f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c2nr30244f.isotherm3](isotherms/10.1039c2nr30244f.isotherm3.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/c2nr30244f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c2nr30244f.isotherm3b](isotherms/10.1039c2nr30244f.isotherm3b.json) | UiO-66 | Carbon Dioxide | 307 | 10.1039/c2nr30244f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c2nr30244f.isotherm4](isotherms/10.1039c2nr30244f.isotherm4.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/c2nr30244f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c2nr30244f.isotherm4b](isotherms/10.1039c2nr30244f.isotherm4b.json) | UiO-66 | Carbon Dioxide | 305 | 10.1039/c2nr30244f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c2nr30244f.isotherm5](isotherms/10.1039c2nr30244f.isotherm5.json) | UiO-66 | Carbon Dioxide | 273 | 10.1039/c2nr30244f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c2nr30244f.isotherm5b](isotherms/10.1039c2nr30244f.isotherm5b.json) | UiO-66 | Carbon Dioxide | 307 | 10.1039/c2nr30244f | UNKNOWN | нетабличные; способ unknown | UNKNOWN |  |
| [10.1039c4ta03992k.Isotherm23](isotherms/10.1039c4ta03992k.Isotherm23.json) | UiO-66(Zr)-(COOH)2 (423K) | Carbon Dioxide | 303 | 10.1039/c4ta03992k | Figure S12b | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm24](isotherms/10.1039c4ta03992k.Isotherm24.json) | UiO-66(Zr)-(COOH)2 (473K) | Carbon Dioxide | 303 | 10.1039/c4ta03992k | Figure S12b | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm25](isotherms/10.1039c4ta03992k.Isotherm25.json) | UiO-66(Zr)-(COOH)2 (373K) | Carbon Dioxide | 303 | 10.1039/c4ta03992k | Figure S12b | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm26](isotherms/10.1039c4ta03992k.Isotherm26.json) | UiO-66(Zr)-(COOH)2 (348K) | Carbon Dioxide | 303 | 10.1039/c4ta03992k | Figure S12b | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm27](isotherms/10.1039c4ta03992k.Isotherm27.json) | UiO-66(Zr)-(COOH)2 (323K) | Carbon Dioxide | 303 | 10.1039/c4ta03992k | Figure S12b | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm28](isotherms/10.1039c4ta03992k.Isotherm28.json) | UiO-66(Zr)-(COOH)2 (303K) | Carbon Dioxide | 303 | 10.1039/c4ta03992k | Figure S12b | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm29](isotherms/10.1039c4ta03992k.Isotherm29.json) | UiO-66(Zr)-(COOH)2 (423K) | Nitrogen | 303 | 10.1039/c4ta03992k | Figure S13a | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm3](isotherms/10.1039c4ta03992k.Isotherm3.json) | UiO-66(Zr)-(COOH)2 (423K) | Carbon Dioxide | 303 | 10.1039/c4ta03992k | Figure 11 | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm30](isotherms/10.1039c4ta03992k.Isotherm30.json) | UiO-66(Zr)-(COOH)2 (303K) | Nitrogen | 303 | 10.1039/c4ta03992k | Figure S13a | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c4ta03992k.Isotherm4](isotherms/10.1039c4ta03992k.Isotherm4.json) | UiO-66(Zr)-(COOH)2 (303K) | Carbon Dioxide | 303 | 10.1039/c4ta03992k | Figure 11 | оцифровка рисунка NIST | David A. Anderegg | exp |
| [10.1039c5ta05997f.Isotherm1](isotherms/10.1039c5ta05997f.Isotherm1.json) | UiO-66 | Carbon Dioxide | 298 | 10.1039/c5ta05997f | Figure 2a | оцифровка рисунка NIST | Adithya Varadan | exp |
| [10.1039c5ta05997f.Isotherm2](isotherms/10.1039c5ta05997f.Isotherm2.json) | UiO-66-EA | Carbon Dioxide | 298 | 10.1039/c5ta05997f | Figure 2a | оцифровка рисунка NIST | Adithya Varadan | exp |
| [10.1039c5ta05997f.Isotherm3](isotherms/10.1039c5ta05997f.Isotherm3.json) | UiO-66 | Carbon Dioxide | 305 | 10.1039/c5ta05997f | Figure 2a | оцифровка рисунка NIST | Adithya Varadan | exp |
| [10.1039c5ta05997f.Isotherm4](isotherms/10.1039c5ta05997f.Isotherm4.json) | UiO-66-EA | Carbon Dioxide | 305 | 10.1039/c5ta05997f | Figure 2a | оцифровка рисунка NIST | Adithya Varadan | exp |
| [10.1039c5ta05997f.Isotherm5](isotherms/10.1039c5ta05997f.Isotherm5.json) | UiO-66-EA | Carbon Dioxide | 313 | 10.1039/c5ta05997f | Figure 2a | оцифровка рисунка NIST | Adithya Varadan | exp |
| [10.1039c5ta05997f.Isotherm6](isotherms/10.1039c5ta05997f.Isotherm6.json) | UiO-66 | Carbon Dioxide | 313 | 10.1039/c5ta05997f | Figure 2a | оцифровка рисунка NIST | Adithya Varadan | exp |
| [10.1504ijnt.2015.067898.Isotherm1](isotherms/10.1504ijnt.2015.067898.Isotherm1.json) | UiO-66 | Carbon Dioxide | 293 | 10.1504/ijnt.2015.067898 | Figure 4 | оцифровка рисунка NIST | Soojin Jang | exp |

## API, права и воспроизведение

Документация: https://adsorption.nist.gov/isodb/index.php#apis ; сохранён ответ `docs/api_reference.html`. Каталог `/api/` не является страницей документации и перенаправляет на 404. Рабочие GET: `api/version.json`, `materials.json`, `material/{name or hashkey}.json`, `gases.json`, `gas/{name or InChIKey}.json`, `isotherms.json` (краткие записи), `isotherm/{filename}.json`, `biblios.json`, `biblio/{DOI or title}.json`; также `biblio-material/{name or hashkey}.json`, `biblio-gas/{name or InChIKey}.json`, `biblio-isotherm/{filename}.json`. Все пути относительно `https://adsorption.nist.gov/isodb/`. Сохранены отдельные JSON всех 152 отобранных материалов и библиография всех DOI отобранных изотерм.

Условия: https://www.nist.gov/copyrights-disclaimers и disclaimer в HTML ISODB (`docs/site.html`). NIST разрешает распространение публичной информации, кроме отдельно отмеченных copyrighted материалов, и просит указание источника. Для стандартных справочных данных действуют отдельные условия. В footer ISODB присутствует copyright notice; сама доступность API не устанавливает CC-лицензию. Эти копии сохраняют исходные ответы NIST для исследовательской прослеживаемости; они не включают PDF статей/рисунки издателей. Перед публичным выпуском руководителю следует отдельно проверить применимость прав к извлечённым из публикаций данным. NIST не гарантирует отсутствие ошибок. Атрибуция: NIST/ARPA-E Database of Novel and Emerging Adsorbent Materials, версия 3.23726, дата доступа из manifest.csv; для каждого набора также cite DOI исходной статьи.

Локальный тест: `python3 -m pytest tests/test_nist_isodb.py` (эквивалентно `pytest tests/test_nist_isodb.py`, если executable доступен в PATH). Зависимости: `pyproject.toml` и `uv.lock`; fetch требует `uv sync --extra fetch`; источники импортируются через tests/conftest.py. Сеть только при явном `python scripts/fetch_nist_isodb.py`; отчёт пересоздаётся без сети: `python scripts/summarize_nist_isodb.py`. Manifest покрывает все исходные ответы; производные coverage.md и паспорт не являются ответами API. Копии JSON не пересериализованы. SHA-256 относится к телу HTTP-ответа после транспортной декомпрессии.

Исполнитель: OpenAI Codex. Запрошены gpt-6.1-sol / medium; фактические модель и effort интерфейсом не раскрыты. Независимая проверка: руководитель + T004, pending.
