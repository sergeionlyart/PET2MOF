#!/usr/bin/env python3
"""Validate T006 provenance, create the digitization passport and human report."""
import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pet2mof.extraction.digitize import read_project
from pet2mof.provenance.extraction import read_extraction,validate_extraction
from pet2mof.ocr.cache import RawCache

DATA=ROOT/'data/extraction/benchmark'
ID='T006-S100-FigS5'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):return json.loads((DATA/name).read_text())


def main():
    pages=read('pages.json')
    summary=read('summary.json')
    engine_summary=read('engine_summary.json')
    results=read('field_results.json')
    engines=read('engines.json')
    tsv=read('tesseract_regions.json')
    digitization=ROOT/f'data/extraction/digitization/{ID}.digitization.yaml'
    project=read_project(digitization)
    csvpath=digitization.with_name(ID+'.csv')
    csvrows=list(csv.DictReader(csvpath.open()))
    raw_data=json.loads((ROOT/f'private/renders/{ID}_components.json').read_text())
    key=hashlib.sha256(json.dumps(raw_data,sort_keys=True).encode()).hexdigest()
    cache=RawCache(ROOT)
    try:raw=cache.write_once(key,raw_data)
    except FileExistsError:raw=cache.path(key)
    assert sha(ROOT/project['image_ref'])==project['image_sha256']
    record=dict(extraction_id=ID,source_id='S100',doi='10.1021/acs.iecr.5b03517',url=None,
                input_sha256=project['source_pdf_sha256'],pdf_page=7,api_page_map={'1':7},figure_or_table='SI Figure S5',
                region={'coordinate_system':'200 dpi page pixels; top-left origin','crop':project['crop_page_pixels'],
                        'image_ref':project['image_ref'],'image_sha256':project['image_sha256']},
                tool='scripts/extraction/digitize_s100.py; NumPy/Pillow connected components',
                tool_version=project['code_version'],params={'project':str(digitization.relative_to(ROOT)),
                'project_sha256':sha(digitization),'export':str(csvpath.relative_to(ROOT)),
                'overlay':'private/renders/overlay_S100_FigS5.png','overlay_sha256':sha(ROOT/'private/renders/overlay_S100_FigS5.png'),
                'temperature_K':'unknown','RH':'unknown','PEI_loading_basis':'unknown',
                'x_label_verbatim':project['x_label_verbatim'],'axis_issue':project['axis_issue'],
                'units':'displayed kPa and mmol/g; no conversions; pressure interpretation provisional'},
                date=datetime.now(timezone.utc).isoformat(),raw_response_ref=str(raw.relative_to(ROOT)),
                unit_conversions=[],derived_sha256=sha(csvpath),status='provisional',reviewer=None,
                corrections=[{'action':'exclude unresolved blue marker overlapped by green near x=45 on displayed scale',
                              'coordinates_imputed':False},
                             {'action':'exclude shared origin; no points sampled from DSL lines'}],
                error_estimate={'readout_bound_px':2,'calibration_endpoint_bound_px':1,
                                'method':'worst-case linear sum, not a confidence interval',
                                'x_bound_kPa_min':min(float(r['x_bound_kPa']) for r in csvrows),
                                'x_bound_kPa_max':max(float(r['x_bound_kPa']) for r in csvrows),
                                'uptake_bound_mmol_g':max(float(r['uptake_bound_mmol_g']) for r in csvrows),
                                'source_experimental_uncertainty':'unknown','nist_comparison':'not performed: identity not established'},
                data_kind='digitized_markers',sensitivity_only=True)
    validate_extraction(record)
    (ROOT/f'data/extraction/records/{ID}.yaml').write_text(yaml.safe_dump(record,sort_keys=False,allow_unicode=True))
    versions={n:importlib.metadata.version(n) for n in ['PyMuPDF','numpy','Pillow','PyYAML','jsonschema','pytest']}
    evidence={'base_git_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'protocol_sha256':sha(DATA/'protocol_frozen.md'),'python':platform.python_version(),'packages':versions,
              'scripts':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'scripts/extraction').glob('*.py'))},
              'settings':{'requested_model':'gpt-6.1-sol','requested_reasoning_effort':'high',
                          'actual_model_and_effort':'not exposed by this tool interface; not independently confirmed',
                          'sandbox':'workspace-write','approval_policy':'never','network':'source downloads only'},
              'numeric_policy':'all expected strings are benchmark annotations; fits/simulations not measured data',
              'generated_at':datetime.now(timezone.utc).isoformat()}
    (DATA/'execution.json').write_text(json.dumps(evidence,indent=2)+'\n')
    # NIST identity audit stores metadata only; no point-wise comparison.
    nist=[]
    for n in range(6,10):
        f=ROOT/f'data/raw/nist_isodb/isotherms/10.1021acs.iecr.5b03517.Isotherm{n}.json'
        data=json.loads(f.read_text())
        nist.append(dict(file=str(f.relative_to(ROOT)),sha256=sha(f),articleSource=data['articleSource'],
                         temperature=data['temperature'],adsorptionUnits=data['adsorptionUnits'],
                         pressureUnits=data['pressureUnits'],adsorbent=data['adsorbent']['name']))
    (DATA/'nist_identity.json').write_text(json.dumps({'records':nist,'decision':'identity not established; no numerical comparison',
           'reason':'Main Figure 4 not available for visual cross-check; S5 caption gives no temperature; x label ambiguous'},indent=2)+'\n')
    # Validate actual referenced inputs and all records, not just YAML syntax.
    for page in pages:
        assert sha(ROOT/page['input'])==page['input_sha256']
        assert sha(ROOT/page['render'])==page['render_sha256']
        assert (ROOT/page['raw_response_ref']).is_file()
    for p in (ROOT/'data/extraction/records').glob('T006-*.yaml'):
        r=read_extraction(p)
        assert r['status']=='provisional' and r['reviewer'] is None and r['sensitivity_only']
        if r['extraction_id']==ID:derived=csvpath
        else:derived=DATA/(r['extraction_id']+'.json')
        assert sha(derived)==r['derived_sha256']
        assert (ROOT/r['raw_response_ref']).is_file()
    validation={'pages':len(pages),'fields':len(results),'digitized_markers':len(csvrows),
                'passports':len(list((ROOT/'data/extraction/records').glob('T006-*.yaml'))),
                'schema_and_hash_checks':'passed','independent_T007_review':'pending'}
    (DATA/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    report=[(DATA/'protocol_frozen.md').read_text(), '\n## Выполнено и границы пилота\n',
    f"Базовый Git SHA: `{evidence['base_git_sha']}`; коммит не создавался. SHA-256 предварительного протокола: `{evidence['protocol_sha256']}`. "
    "Роль — исполнитель T006 на OpenAI Codex. Запрошены gpt-6.1-sol / high; фактические model/effort интерфейс инструментов не раскрывает, независимо не подтверждены. "
    "Настройки sandbox workspace-write, approval never; все записи provisional, T007 pending. Отдельные новые субагенты не запускались.\n",
    "Выбраны **19 исходных PDF-страниц**, все calibration/validation. Ни одна не является сканом: читаемый текстовый слой сочетается с растровыми рисунками. "
    "Растровый график внутри цифровой статьи не классифицирован как скан. Нет изменения pyproject.toml/uv.lock, установки пакетов, внешнего OCR, чтения .env, commit/push/CI.\n",
    "## Выборка и исходные файлы\n",
    "| Источник | PDF-файл | SHA-256 |\n|---|---|---|\n"]
    unique={p['source_id']:p for p in pages}
    for sid,p in unique.items():report.append(f"| {sid} | `{p['input']}` | `{p['input_sha256']}` |\n")
    report.append('\nСкачивания и неудачные попытки: `data/extraction/benchmark/downloads_T006.json`. Python urllib не доверял локальной цепочке сертификатов; '
                  'curl со штатной проверкой TLS получил PDF S103/S105/S113. PDF S2 через Europe PMC вернул 403; CAPTCHA не обходилась. '
                  'Первый endpoint SI S102 вернул пустой HTTP 202; получен точный PDF по издательской ссылке из T004. '
                  'HTML-заглушки прежних S2.pdf/S113.pdf не использовались.\n')
    content={
        'S100-p02':'§S1: синтез и активация parent; вверху также оглавление',
        'S100-p03':'§S2: fixed-bed, точность T/RH, состав газа',
        'S100-p04':'Fig. S1: аппаратурная схема; Eq. (1)',
        'S100-p05':'Eq. (2)–(3): интеграл и отношение селективности',
        'S100-p07':'Fig. S4: площадь; Fig. S5: масса, символы и DSL-fit',
        'S100-p09':'Fig. S8: humid breakthrough parent; Table S1: DSL-fit',
        'S106-p03':'две колонки, Experimental: массы и температуры',
        'S106-p04':'две колонки, степени, Eq. excess/absolute, Fig. 2',
        'S106-p05':'Fig. 3/4 N₂/H₂O; Table 1 PV/BET',
        'S106-p06':'Fig. 5/6: QE-TPDA, эксперимент/расчёт',
        'S106-p07':'две колонки, обсуждение; Fig. 7 occupation (расчёт)',
        'S105-p08':'§3.4; Fig. 8A/B: CO₂, модели Langmuir',
        'S105-p09':'Fig. 8C/подпись A–C; численная ёмкость в тексте',
        'S113-p06':'Eq. (6)/(7), Methods/Results, индексы',
        'S113-p07':'Fig. 3; Table 1: BET, поры, footnotes',
        'S113-p09':'Fig. 5a/b: CO₂/N₂; легенды и условия',
        'S103-p02':'две колонки; Table 1: энергии DFT+D (симуляция)',
        'S103-p03':'Table 2 PV/BET; Fig. 2a эксперимент / 2b расчёт',
        'S102-p05':'SI Fig. S6: экспериментальные binary versus IAST'}
    report.append('\n| extraction_id | PDF ↔ печатная | Содержание | Эталон PNG (200 dpi) | Поля / правки |\n|---|---|---|---|---|\n')
    for p in pages:
        q=[r for r in results if r['extraction_id']==p['extraction_id']]
        failed=sum(r['result']!='correct' for r in q)
        report.append(f"| {p['extraction_id']} | {p['pdf_page']} ↔ {p['printed_page']} | {content[p['extraction_id'][5:]]} | `{p['render']}` | {len(q)} / {failed} |\n")
    report.append('\nХеш каждого PNG, размеры страницы, показатели текстового слоя и wall-clock — `pages.json`; '
                  'нумерация S106 включает репозиторную обложку, поэтому PDF = печатная + 1. '
                  'S102 PDF p.5 = S5 (отдельной обложки нет).\n')
    report.append('\n## Эталон и сравнение\n\nЭталон вводился после визуального просмотра всех указанных PNG. '
                  '`reference_fields.json` содержит точную строку, extraction_id, нормированную область от верхнего левого угла и локатор; '
                  '`field_results.json` дополнительно хранит сырой текст области и SHA PNG. Эталон нуждается в независимой сверке T007. '
                  'Исполнитель — агент; независимая человеческая проверка не заявляется.\n\n'
                  '**Метрика — сохранность строки в указанной области**, а не качество автономного парсера. '
                  'Число засчитывается, если его точный токен сохранился в области; расположение колонок этим не доказывается. '
                  'Для plain-text путей связь не восстанавливается из простого совместного появления слов: все невыданные структурные связи — пропуски. '
                  'Автоматический `PyMuPDF.find_tables()` с default settings не обнаружил таблиц на S100 p.9, S106 p.5, S113 p.7, S103 pp.2–3. '
                  'Это не тест всех режимов table detection. Ручная разметка областей уже является частью труда. '
                  'Суперскрипты/субскрипты в эталоне транскрибированы Unicode; plain text baseline считается ошибкой по строгому протоколу. '
                  'Это не означает потерю всей информации о начертании в PDF: dict/spans могут её сохранить и требуют отдельного восстановления.\n\n'
                  '«Пропуск» здесь означает, что не найдено точной строки или указанного в эталоне известного lossy-варианта. '
                  'Неверное OCR-слово без такого варианта также попадает в retrieval-пропуски; это не утверждение, что движок не выдал символов. '
                  'Известные lossy-строки отдельно посчитаны как несовпадения. Метрика поиска с известным эталоном даёт верхнюю оценку сохранности.\n\n'
                  '| Поле | PyMuPDF верно / всего | % | Пропуски | Несовпадения | pdftotext верно / всего |\n|---|---|---|---|---|---|\n')
    for cat,label in [('numbers','Числа'),('units','Единицы/значение с единицей'),('symbols','Знаки, степени, индексы'),('relationships','Связи ячейки/кривые/формулы')]:
        q=summary[cat];e=engine_summary['pdftotext'][cat]
        report.append(f"| {label} | {q['correct']}/{q['total']} | {q['fraction']*100:.1f} | {q['omissions']} | {q['mismatches']} | {e['correct']}/{e['total']} |\n")
    report.append('\nВсего 211 полей. Повторяющиеся числа в разных ячейках — отдельные поля. '
                  'Результаты не являются универсальной оценкой OCR и не усредняются до единого процента научной достоверности. '
                  'Неправильно обрезанная область сначала была расширена до полной строки подписи S102; '
                  'числовой matcher исправлен, чтобы завершающая пунктуация не считалась десятичной частью. '
                  'Допуски и эталонные значения ради повышения результата не менялись.\n')
    report.append('\n### Локальный OCR на проблемных страницах\n\nTesseract применён только к S100 p.7, S106 p.6, S113 p.9: '
                  'встроенные растровые графики не дают подписи в текстовом слое. Сырые ответы text/TSV неизменны в `private/ocr_cache/raw/`. '
                  '`tesseract_regions.json` задаёт SHA рендера 300 dpi; `engine_field_results.json` — сравнение тех же полей в тех же областях.\n\n'
                  '| Категория | tesseract верно / всего (только 3 страницы) | Пропуски | Несовпадения |\n|---|---|---|---|\n')
    for cat in ['numbers','units','symbols','relationships']:
        q=engine_summary['tesseract'][cat]
        report.append(f"| {cat} | {q['correct']}/{q['total']} | {q['omission']} | {q['mismatch']} |\n")
    report.append('\nTesseract возвращает часть делений и единиц, но путает легенды и индексы; '
                  'цвет/форму маркера и связь с материалом не восстанавливает. Сравнивать его проценты с 19 страницами как равные выборки нельзя. '
                  'Полные результаты обоих движков сохраняются отдельно; OCR-ошибки в эталон не переносятся.\n')
    total_fail=sum(r['result']!='correct' for r in results)
    report.append(f'\n### Исправления и трудоёмкость\n\nPyMuPDF требует {total_fail} полевых вмешательств: '
                  f"{summary['units']['omissions']+summary['units']['mismatches']} для единиц, "
                  f"{summary['symbols']['omissions']+summary['symbols']['mismatches']} для обозначений, "
                  f"{summary['numbers']['omissions']} для чисел, {summary['relationships']['omissions']} для структуры. "
                  'Они перечислены в `corrections` паспортов; исходные ответы не исправляются. '
                  'Эталон — отдельная транскрипция, не результат тайной правки raw. '
                  'Человекоминуты не измерялись; число полей — объём ручной работы, а не оценка времени человека. '
                  'Секунды инструментов по страницам/движкам лежат в pages.json, engines.json, tesseract_regions.json; '
                  'повторный воспроизводящий запуск может иметь другие длительности. Денежные вызовы внешнего OCR: 0.\n')
    report.append('\n### S2 и ограничения доступа\n\nСтруктурный XML Europe PMC принят первым путём: '
                  '`S2_xml_tables.json` сохраняет Tables 1–3 со строками, ячейками и сносками. SHA XML: '
                  f"`{read('S2_xml_tables.json')['sha256']}`. Tables 1–2 не включены в метрику и не названы визуально проверенными: "
                  'оригинальная PDF-вёрстка не получена. Синтетическая HTML-страница не выдана за страницу издателя. '
                  'Существующие Fig. 6/9 остаются доступными в data/raw/figures_full, но T006 не добавляет из них численных измерений. '
                  'Схема T005 требует положительный pdf_page и не поддерживает непагинированный XML; '
                  'поэтому для этой вспомогательной выгрузки не создаётся фиктивный PDF-паспорт. '
                  'Нужна точечная оригинальная визуальная проверка S2 руководителем/T007 при законном доступе.\n')
    ncounts={s['name']:len(s['pixels']) for s in project['series']}
    report.append('\n## Пробная оцифровка S100 SI Fig. S5\n\n'
                  f"extraction_id `{ID}`; PDF p.7 ↔ S7; исходный SHA PDF `{project['source_pdf_sha256']}`; "
                  f"SHA изображения `{project['image_sha256']}`. Crop `{project['crop_page_pixels']}` от PNG 200 dpi. "
                  'Две точки X: (152 px, 0), (667 px, 100); две точки Y: (601 px, 0), (105 px, 3.5). '
                  'Шкалы линейные. Чёрные пиксельные полосы по row=609 и column=142 дают по 8 проверочных '
                  'основных делений; координаты и residual каждого сохранены в calibration_checks проекта. '
                  f"Максимальный residual X = {project['calibration_checks']['max_residual_x_data']:.6f}, "
                  f"Y = {project['calibration_checks']['max_residual_y_data']:.6f} mmol/g (0.5 px). "
                  'Исходная подпись X `P/P₀ (kPa)` размерностно неоднозначна: экспорт `x_display_kPa` сохраняет отображаемую шкалу, '
                  'а не доказывает физический смысл давления. Y — mmol/g. '
                  'Температура, RH и знаменатель загрузки PEI в Fig. S5 не установлены; температура из соседней S4 не перенесена.\n\n'
                  '`digitize_s100.py` использует RGB-маски, бинарное closing 3 px для пересечения маркеров тонкой линией, '
                  'эрозию 3 px и 8-connected components с фильтром размера/компактности. Центр — середина bbox ядра маркера. '
                  'RGB оригинала не улучшается и не дорисовывается; параметры бинарной сегментации и маски зафиксированы скриптом. '
                  'DSL-линии красные и тонкие; они не экспортированы как измерения. Полос ошибок на рисунке не видно. '
                  'Overlay просмотрен после выделения; это самопроверка, не независимый T007.\n\n'
                  '| Серия | Различимых извлечённых маркеров |\n|---|---|\n')
    for s,count in ncounts.items():report.append(f'| {s} | {count} |\n')
    report.append(f"\nВсего {len(csvrows)} маркеров. Общий ноль серий исключён из-за наложения; один синий маркер около "
                  'отображаемого X≈45 закрыт зелёным. Скрытые точки не восстанавливались по тренду или соседям. '
                  'Первый тест сегментации с эрозией 5 px терял тонкие/перечёркнутые маркеры; это неудачный малый прогон, '
                  'причина сохранена здесь и в `segmentation_trials.json`. Финальный алгоритм выбран по overlay, без просмотра NIST-отклонений.\n\n'
                  f"Для точек внутри калибровки граница X = ±{100/515*3:.6f} в отображаемых kPa; "
                  f"Y = ±{3.5/496*3:.6f} mmol/g. Для X вне последнего калибровочного деления граница "
                  f"слегка растёт до ±{record['error_estimate']['x_bound_kPa_max']:.6f}; точные границы есть в каждой строке CSV. "
                  'Это консервативная сумма 2 px readout + ошибок двух калибровочных точек по 1 px, '
                  'не доверительный интервал и не погрешность исходного опыта. Оценка по цветовым ядрам требует сверки T007; '
                  'при более крупной остаточной ошибке локализации граница должна быть увеличена.\n\n'
                  f"Проект: `data/extraction/digitization/{ID}.digitization.yaml`; экспорт: `{csvpath.relative_to(ROOT)}`; "
                  'наложение: `private/renders/overlay_S100_FigS5.png`; паспорт: '
                  f'`data/extraction/records/{ID}.yaml`. S100 SI — CC BY-NC 4.0 по T004/поручению, '
                  'реестр ещё хранит прежнее unknown. Публикуемая уменьшенная картинка не создавалась: '
                  'условие карточки для изображения — CC BY, а здесь NC. Научные координаты и provenance сохранены для приёмки.\n\n'
                  '**С NIST сравнение не выполнено.** `nist_identity.json` фиксирует только метаданные Isotherm6–9: '
                  'main Figure 4, материалы, 298 K, bar, mmol/g. Основной Fig.4 не осмотрен, '
                  'температура S5 и размерностная подпись X не разрешены. Совпадение названий серий и визуальная похожесть '
                  'не устанавливают тождество. RMSE/эмпирическая ошибка по NIST не вычислялись. '
                  'NIST и S5 не принимаются как независимые экспериментальные повторности.\n')
    report.append('\n## Решение и передача T007\n\nЛокальный путь достаточен для этого пилота **с визуальной разметкой и независимой приёмкой**, '
                  'но plain-text извлечение само по себе непригодно для автоматической загрузки критических единиц, индексов и связей. '
                  'Нужны структурный XML, точечные ручные сетки таблиц, отдельная оцифровка графиков и проверка T007. '
                  'Docling/GROBID/torch не требуются: доступные XML сохраняют структуру, PDF-числа читаемы, '
                  'остаточные поля восстанавливаются локальной визуальной разметкой. Внешний OCR **не нужен и не вызывался**; '
                  'недоступный оригинальный PDF S2 является ограничением доступа, а не задачей для платного OCR.\n\n'
                  'T007: открыть каждый PNG по pages.json, проверить expected/region/locator, особенно заголовок d₂ и 1.7583E-4 '
                  'в S100 Table S1, индексы/знаки формул, единицы cm³ STP/g у S103 и experimental/calculated в Fig.2; '
                  'проверить калибровку и все точки overlay, оценку ±2 px, неоднозначную ось S5 и исключённый синий маркер. '
                  'До этого все 20 паспортов provisional/sensitivity_only, reviewer=null; научные модели не калибровались. '
                  'Таблица S100 — author_fit; Table 1 S103 — simulation; BET/PV — экспериментальная характеристика/авторская обработка; '
                  'числа из Methods и деления осей не объявлены измерениями ёмкости.\n\n'
                  'Не подтверждалась независимость серий S103/S106; наличие двух статей не используется как разделение calibration/validation.\n')
    report.append('\n## Воспроизведение и проверки\n\nПакеты уже присутствовали: '+', '.join(f"{n} {v}" for n,v in versions.items())+
                  '. Дополнительно нужны системные pdftotext и tesseract (eng). scipy/matplotlib/torch/Docling не нужны. '
                  'Новые зависимости не устанавливались. Для uv использовать `UV_CACHE_DIR=$PWD/.uv-cache`; '
                  'в данном прогоне использован существующий python3.\n\n'
                  'Из корня worktree, при наличии перечисленных PDF (URL/хеши в downloads_T006.json):\n\n'
                  '```sh\npython3 scripts/extraction/prepare_pilot.py\npython3 scripts/extraction/score_pilot.py\n'
                  'python3 scripts/extraction/compare_local_engines.py\npython3 scripts/extraction/digitize_s100.py\n'
                  'python3 scripts/extraction/finalize_pilot.py\npython3 -m pytest -q\n```\n\n'
                  'Скрипты не обращаются к сети/.env. Отсутствующие приватные рендеры/raw-кэши регенерируются из PDF. '
                  'Загрузки исходников — отдельная операция, не платный OCR; скачанные PDF не публикуются. '
                  'Автоматическая проверка schema/hash/counts: `data/extraction/benchmark/validation.json`. '
                  'Фактические команды/exit codes тестов: `data/extraction/benchmark/checks.json` и `general_checks.json`.\n\n'
                  'Профильные тесты OCR/provenance: **63 passed**, exit 0. Полный набор: **94 passed, 1 failed**, exit 1; '
                  'причина — отсутствует игнорируемый `data/raw/nist_isodb/catalogs/gases.json` в данном worktree. '
                  'Первый полный запуск также остановился на отсутствующем родительском `.uv-cache`; каталог создан, '
                  'инфраструктурные ошибки tempdir устранены. NIST-каталоги не скачивались вне разрешённого сетевого scope T006.\n\n'
                  '`python3 scripts/publish_check.py`: exit 1. Текущее дерево и staged scan прошли; '
                  'all-history scan отмечает прежние `data/raw/nist_isodb/docs/copyright.html` и `project.html`. '
                  'Это блокер публикации существующей истории, а не утечка в артефактах T006. '
                  'Значения находок не выводились; историю в T006 не переписывали. Коммит и публикация не выполнялись.\n')
    formatted=re.sub(r'(?m)^(#{1,6} .+)\n(?!\n)',r'\1\n\n',''.join(report))
    (ROOT/'reviews/document_extraction_benchmark.md').write_text(formatted)
    print(json.dumps(validation,indent=2))


if __name__=='__main__':main()
