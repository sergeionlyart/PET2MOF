#!/usr/bin/env python3
"""Regenerate Russian coverage and extraction passport offline from the snapshot."""
import collections
import csv
import hashlib
import platform
import importlib.metadata
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pet2mof.data.nist_isodb import ROOT, load_isotherm, verify_manifest


def family(name):
    norm = re.sub('[^a-z0-9]', '', name.lower())
    if 'pei' in norm:
        return 'PEI@UiO-66 (название NIST)'
    if norm in {'uio66', 'uio66zr', 'zrbdc'}:
        return 'UiO-66 / UiO-66(Zr) / Zr-BDC'
    if norm in {'uio66nh2', 'nh2uio66', 'nh2uio66zr', 'uio66zrnh2', 'zrbdcnh2'}:
        return 'UiO-66-NH2 (синонимы)'
    return 'Прочие варианты/производные/композиты (не объединять с исходным MOF)'


def main():
    verify_manifest()
    rows = list(csv.DictReader((ROOT / 'manifest.csv').open()))
    iso = [r for r in rows if r['filename'].startswith('isotherms/')]
    mats = json.loads((ROOT / 'catalogs/materials.json').read_bytes())
    mats = [m for m in mats if 'uio66' in re.sub('[^a-z0-9]', '', ' '.join([m['name']]+m['synonyms']).lower())
            or re.search('zr.?bdc', ' '.join([m['name']]+m['synonyms']), re.I)]
    lines = ['# Покрытие NIST ISODB — T002', '',
        'Снимок получен 16 ноября 2026 UTC. Версия API: `' + json.loads((ROOT/'catalogs/version.json').read_bytes())['version'] + '`.',
        'Все записи **provisional**: SHA-256 проверяет целостность, но независимая сверка руководителем/T004 ещё не выполнена.', '',
        '## Поиск и границы', '',
        'Просмотрены полные каталоги: 9328 материалов, 39988 изотерм и 455 газов. '
        'Поиск по имени и всем synonyms: нормализация к нижнему регистру с удалением знаков, '
        'подстрока `uio66`; дополнительно regex `zr.?bdc`. Найдено 152 записи материала. '
        'Это воспроизводимое покрытие названий реестра, а не доказательство полноты всех химических синонимов в литературе. '
        'Имена без UiO-66/Zr-BDC и без соответствующего synonyms могут быть пропущены. '
        'Отдельно проверены PEI/polyethylenimine по всему каталогу: UiO-содержащие совпадения — 10, 20, 30 и 40PEI@UiO-66.', '',
        'Отбор: температура из числового поля JSON, включительно 273–323 K; '
        'хотя бы один компонент CO2, N2, H2O по InChIKey. '
        'Сохранены 296 JSON изотерм: 287 однокомпонентных и 9 смесей. '
        'Смесь не учитывается как чистая изотерма каждого её компонента. '
        'Все функциональные производные и композиты сохранены для полноты поиска; их нельзя считать синонимами исходного UiO-66.', '',
        '## Сводка однокомпонентных изотерм', '',
        'Числа ниже включают категории NIST: exp=141, sim=4, mod=11, пустая/unknown=140 '
        '(по всему снимку, включая смеси). `mod` сохранено без интерпретации. '
        'Эти количества не являются количеством подтверждённых экспериментальных серий.', '',
        '| Группа (точные названия ниже) | CO2 | N2 | H2O |', '| --- | ---: | ---: | ---: |']
    groups = collections.defaultdict(collections.Counter)
    for r in iso:
        if ';' not in r['adsorbate']:
            groups[family(r['material'])][r['adsorbate']] += 1
    for f,c in sorted(groups.items()):
        lines.append(f'| {f} | {c["Carbon Dioxide"]} | {c["Nitrogen"]} | {c["Water"]} |')
    lines += ['', '## Материал × адсорбат × температура', '',
        'Число в скобках — число отдельных JSON; 0 означает отсутствие в выбранном диапазоне. '
        'Смеси показаны в таблице источников отдельно. Точные имена и hashkey не сливались.', '',
        '| Материал NIST | CO2: T/K (n) | N2: T/K (n) | H2O: T/K (n) |', '| --- | --- | --- | --- |']
    for m in mats:
        cells=[]
        for g in ['Carbon Dioxide','Nitrogen','Water']:
            counter=collections.Counter(r['T_K'] for r in iso if r['material']==m['name'] and r['adsorbate']==g)
            cells.append(', '.join(f'{t} ({n})' for t,n in sorted(counter.items(),key=lambda item:float(item[0]))) or '0')
        lines.append('| '+m['name']+' | '+' | '.join(cells)+' |')
    near = [r for r in iso if abs(float(r['T_K'])-308)<=5]
    lines += ['', '## Около 308 K', '', f'При 308 K: {sum(float(r["T_K"])==308 for r in iso)} JSON; '
              f'в интервале 303–313 K: {len(near)} JSON (включая смеси). '
              'Все четыре записи ровно при 308 K имеют единицы cm3(STP)/g или cm3/m2: '
              'две cm3(STP)/g загружаются при STP 273.15 K, 101.325 kPa (22.414 cm3/mmol); '
              'две cm3/m2 отклоняются без массовой нормировки.', '',
              '| Материал | Адсорбат | T/K | Изотерма |', '| --- | --- | ---: | --- |']
    for r in near:
        lines.append(f'| {r["material"]} | {r["adsorbate"]} | {r["T_K"]} | {Path(r["filename"]).stem} |')
    flags=collections.Counter(r['tabular_data'] for r in iso)
    units=collections.Counter((r['pressure_units'],r['adsorption_units']) for r in iso)
    unsupported=[]
    for r in iso:
        try: load_isotherm(ROOT/r['filename'])
        except ValueError: unsupported.append(r['filename'])
    lines += ['', '## Происхождение и ограничения', '',
        f'Значения tabular_data: {dict(flags)}. `0` означает нетабличные данные NIST; '
        'в сочетании с Figure в articleSource это признак извлечения из графика. '
        'Такие записи помечены «оцифровка рисунка NIST» в таблице ниже и несут неопределённость оцифровки. '
        'Её численная оценка в JSON отсутствует (unknown); поля digitizer и articleSource сохранены. '
        '`tabular_data=1` передаёт флаг NIST, но не подтверждает нами происхождение исходной таблицы. '
        'Самостоятельная оцифровка и чтение координат LLM не выполнялись. '
        'Наличие digitizer само по себе не доказывает оцифровку графика.', '',
        'PEI-композиты: присутствуют четыре именованные загрузки; точные газы, T и DOI приведены ниже. '
        'Название UiO-66 в этих записях не устанавливает тождество PET-derived материалу или PEI@UiO-66-NH2 из S2. '
        'Наличие влажных смесей и H2O следует оценивать по точным строкам, а не по CO2-данным.', '',
        f'Не загружаются в нормализованные единицы без дополнительных допущений: {len(unsupported)} JSON. '
        'Исходники сохранены независимо от возможности конверсии. '
        'Поддержаны bar, Pa, kPa, MPa, mbar, atm, Torr, mmHg → bar; mmol/g, mol/kg, mol/g, mmol/kg, cm3(STP)/g → mmol/g. '
        'Для cm3(STP)/g используется 22.414 cm3/mmol при 273.15 K и 101.325 kPa; cm3/g и cm3/m2 отклоняются. '
        'Mixture pressure_bar — полное давление; ёмкость — для конкретного компонента; состав и его тип сохраняются.', '',
        '| pressureUnits | adsorptionUnits | JSON |', '| --- | --- | ---: |']
    for (p,q),n in sorted(units.items()): lines.append(f'| {p} | {q} | {n} |')
    lines += ['', '## Источник каждой изотермы', '',
        '| JSON | Материал | Адсорбат | T/K | DOI статьи | articleSource | Происхождение | digitizer | category |',
        '| --- | --- | --- | ---: | --- | --- | --- | --- | --- |']
    for r in iso:
        origin=('табличные (флаг NIST)' if r['tabular_data']=='1' else
                'оцифровка рисунка NIST' if 'fig' in r['articleSource'].lower() else 'нетабличные; способ unknown')
        lines.append(f'| [{Path(r["filename"]).stem}]({r["filename"]}) | {r["material"]} | {r["adsorbate"]} | {r["T_K"]} | {r["DOI"]} | {r["articleSource"]} | {origin} | {r["digitizer"]} | {r["category"]} |')
    lines += ['', '## API, права и воспроизведение', '',
        'Документация: https://adsorption.nist.gov/isodb/index.php#apis ; '
        'сохранён ответ `docs/api_reference.html`. Каталог `/api/` не является страницей документации и перенаправляет на 404. '
        'Рабочие GET: `api/version.json`, `materials.json`, `material/{name or hashkey}.json`, '
        '`gases.json`, `gas/{name or InChIKey}.json`, `isotherms.json` (краткие записи), '
        '`isotherm/{filename}.json`, `biblios.json`, `biblio/{DOI or title}.json`; '
        'также `biblio-material/{name or hashkey}.json`, `biblio-gas/{name or InChIKey}.json`, '
        '`biblio-isotherm/{filename}.json`. Все пути относительно `https://adsorption.nist.gov/isodb/`. '
        'Сохранены отдельные JSON всех 152 отобранных материалов и библиография всех DOI отобранных изотерм.', '',
        'Условия: https://www.nist.gov/copyrights-disclaimers и disclaimer в HTML ISODB (`docs/site.html`). '
        'NIST разрешает распространение публичной информации, кроме отдельно отмеченных copyrighted материалов, '
        'и просит указание источника. Для стандартных справочных данных действуют отдельные условия. '
        'В footer ISODB присутствует copyright notice; сама доступность API не устанавливает CC-лицензию. '
        'Эти копии сохраняют исходные ответы NIST для исследовательской прослеживаемости; '
        'они не включают PDF статей/рисунки издателей. Перед публичным выпуском руководителю следует отдельно '
        'проверить применимость прав к извлечённым из публикаций данным. NIST не гарантирует отсутствие ошибок. '
        'Атрибуция: NIST/ARPA-E Database of Novel and Emerging Adsorbent Materials, версия 3.23726, '
        'дата доступа из manifest.csv; для каждого набора также cite DOI исходной статьи.', '',
        'Локальный тест: `python3 -m pytest tests/test_nist_isodb.py` '
        '(эквивалентно `pytest tests/test_nist_isodb.py`, если executable доступен в PATH). Зависимости: `pyproject.toml` и `uv.lock`; fetch требует `uv sync --extra fetch`; '
        'источники импортируются через tests/conftest.py. '
        'Сеть только при явном `python scripts/fetch_nist_isodb.py`; '
        'отчёт пересоздаётся без сети: `python scripts/summarize_nist_isodb.py`. '
        'Manifest покрывает все исходные ответы; производные coverage.md и паспорт не являются ответами API. '
        'Копии JSON не пересериализованы. SHA-256 относится к телу HTTP-ответа после транспортной декомпрессии.', '',
        'Исполнитель: OpenAI Codex. Запрошены gpt-6.1-sol / medium; фактические модель и effort '
        'интерфейсом не раскрыты. Независимая проверка: руководитель + T004, pending.']
    (ROOT/'coverage.md').write_text('\n'.join(lines)+'\n')
    passport={'task_id':'T002-nist-isodb','status':'provisional','reviewer':'руководитель + T004 (pending)',
        'tool':'scripts/fetch_nist_isodb.py; requests; NIST ISODB API 3.23726',
        'versions':{name:importlib.metadata.version(name) for name in ['requests','pandas','pytest']},
        'python':platform.python_version(),
        'loader_sha256':hashlib.sha256((ROOT.parents[2]/'src/pet2mof/data/nist_isodb.py').read_bytes()).hexdigest(),
        'tool_sha256':hashlib.sha256(Path(__file__).with_name('fetch_nist_isodb.py').read_bytes()).hexdigest(),
        'model_settings':{'requested_model':'gpt-6.1-sol','requested_effort':'medium',
                          'actual_model':'not disclosed by interface','actual_effort':'not disclosed by interface'},
        'parameters':{'T_K':[273,323],'gases_InChIKey':sorted({'CURLTUGMZLYLDI-UHFFFAOYSA-N', 'IJGRMHOSHXDMSA-UHFFFAOYSA-N', 'XLYOFNOQVPJJNP-UHFFFAOYSA-N'})},
        'raw_response':'unchanged bytes in manifest.csv paths',
        'transformations':'none on raw; optional unit conversions documented in nist_isodb.py',
        'digitization_error':'unknown; not provided by API','corrections':[],
        'operations':[dict(r, page='not applicable: JSON', region=r['articleSource'],
                            derived_sha256='not applicable: no normalized file saved') for r in iso]}
    out=ROOT.parents[1]/'extraction';out.mkdir(exist_ok=True)
    (out/'T002-nist-isodb.yaml').write_text(json.dumps(passport,ensure_ascii=False,indent=2)+'\n')
    print('pure groups:',dict(groups));print('near 308 K:',len(near),'exact:',sum(float(r['T_K'])==308 for r in iso))
    print('units',units,'unsupported',len(unsupported),'flags',flags)

if __name__=='__main__': main()
