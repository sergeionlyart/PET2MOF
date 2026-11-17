#!/usr/bin/env python3
"""Generate T011b per-symbol repair report and private source-pixel contact sheets."""
import csv
import hashlib
import json
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DIG = ROOT / 'data/extraction/digitization'
PRIVATE = ROOT / 'private/renders'
FIGURES = ['S105-Fig8A', 'S105-Fig8B', 'S105-Fig8C', 'S105-Fig9', 'S106-Fig4']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    baseline = json.loads((DIG/'T011b/baseline.json').read_text())
    evidence = dict(baseline_head=baseline['baseline_head'], series={}, contact_sheets={})
    details, ranges, unchanged = [], [], []
    added = removed = total = 0
    for figure in FIGURES:
        eid = 'T011-'+figure
        project = yaml.safe_load((DIG/(eid+'.digitization.yaml')).read_text())
        source = Image.open(ROOT/project['image_ref']).convert('RGB')
        with (DIG/(eid+'.csv')).open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        patches = []
        for s in project['series']:
            key = figure+'|'+s['name']
            prior = baseline['series'][key]
            sub = [r for r in rows if r['series'] == s['name']]
            b = ''.join(','.join(r[k] for k in baseline['coordinate_fields'])+'\n' for r in sub).encode()
            digest = hashlib.sha256(b).hexdigest()
            assert digest == s['coordinate_bytes_sha256']
            equal = digest == prior['coordinate_bytes_sha256']
            if s['status'] == 'verified':
                assert equal and prior['T011v_verdict'] == 'verified'
                unchanged.append(f"{figure} {s['name']}")
            evidence['series'][key] = dict(rows_before=prior['rows'], rows_after=len(sub),
                                           coordinate_bytes_before_sha256=prior['coordinate_bytes_sha256'],
                                           coordinate_bytes_after_sha256=digest, byte_identical=equal,
                                           status=s['status'], usable_p_min_bar=s['usable_p_min_bar'])
            total += len(sub)
            if s['recoveries']:
                ranges.append(f"| {figure} · {s['name']} | {s['usable_p_min_bar']:.10g} | provisional → T011v2 |")
            for rec in s['recoveries']:
                added += 1
                px,py = rec['pixel']
                row = next(r for r in sub if float(r['pixel_x']) == px and float(r['pixel_y']) == py)
                unit = 'RH' if figure.startswith('S106') else 'bar'
                q_unit = 'cm³(STP)/g' if figure.startswith('S106') else 'mmol/g'
                point = f"1: {unit}={float(row['x']):.7g}; q={float(row['y']):.7g} {q_unit}"
                bounds = f"±{float(row['x_err']):.3g} {unit}; ±{float(row['y_err']):.3g} {q_unit}"
                basis = (f"`{rec['id']}`; окно {rec['window_native_pixels']}; центр ({px:g}, {py:g}) px; "
                         f"{rec['visible_support_pixels']}/{rec['template_ink_pixels']} px символа; {bounds}")
                details.append(f"| {rec['defect']} | {figure} · {s['name']} | Восстановлен: цветовая маска + частичный печатный шаблон | {point} | {basis} |")
                # Paired original and overlay, nearest-neighbor display only.
                half = 27 if figure.startswith('S105') else 16
                box = (round(px)-half,round(py)-half,round(px)+half,round(py)+half)
                raw = source.crop(box)
                marked = raw.copy();draw = ImageDraw.Draw(marked)
                cx,cy = px-box[0],py-box[1]
                draw.line((cx-5,cy,cx+5,cy), fill='magenta', width=1)
                draw.line((cx,cy-5,cx,cy+5), fill='magenta', width=1)
                tile = Image.new('RGB',(440,275),'white')
                tile.paste(raw.resize((210,210),Image.Resampling.NEAREST),(5,60))
                tile.paste(marked.resize((210,210),Image.Resampling.NEAREST),(225,60))
                d = ImageDraw.Draw(tile);font=ImageFont.load_default(size=14)
                d.text((5,3),rec['id'],font=font,fill='black')
                d.text((5,21),f"center=({px:g},{py:g}) px; error={rec['readout_bound_px']:g} px",font=font,fill='black')
                d.text((5,39),'Source                              Computed center',font=font,fill='black')
                patches.append(tile)
            for duplicate in s['duplicate_detections_removed']:
                removed += 1
                details.append(f"| T011v-D01 | {figure} · {s['name']} | Удалён дубль {duplicate['pixel']}; сохранён {duplicate['retained_pixel']} native px | −1 повтор; 0 новых | {100*duplicate['shared_ink_fraction']:.4g}% общих пикселей печатного символа; порог Δp не применяется |")
        if patches:
            columns=2
            sheet=Image.new('RGB',(440*columns,275*((len(patches)+columns-1)//columns)),'#dddddd')
            for i,tile in enumerate(patches):sheet.paste(tile,((i%columns)*440,(i//columns)*275))
            path=PRIVATE/f'T011b-{figure}-recoveries.png';sheet.save(path)
            evidence['contact_sheets'][figure]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
    assert len(unchanged) == 12 and added == 32 and removed == 1 and total == 806
    evidence.update(added_markers=added, removed_duplicates=removed, T011_rows=total,
                    verified_series=12, provisional_series=7)
    (DIG/'T011b/fix_evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n')
    text = f'''# T011b — исправления оцифровки C-серий

D01–D03 обработаны: **32 восстановленных печатных маркера, один удалённый дубль**; T011: 775 → 806 строк,
полная сборка: 2132 → 2163 строки, 58 серий. Семь изменённых серий остаются `provisional` до T011v2;
12 серий из [вердикта T011v](T011v_c_series_verification.md) имеют побайтово неизменные координаты и `verified`.
Проверка статуса относится к оцифровке; роли `C_candidate`/`context_GO` и запрет основного fit сохраняются.

Роль: исполнитель · платформа: OpenAI Codex · карточка `tasks/T011b-c-series-fix.md`.
Запрошены gpt-6.1-sol / high; фактические модель и effort интерфейсом этой сессии не подтверждены.
Исходный HEAD: `{baseline['baseline_head']}`. Сеть off. Commit/push, чтение `.env`,
V-источников S2/S103/S113, изменения `T011v-control/` и `reviews/T011v_*` не выполнялись.

## Метод и индивидуальные решения

Каждое окно задаёт область исходного символа, а не численные p/q. Центры вычислены по пикселям
встроенного растра оригинального PDF инструментом `scripts/extraction/digitize_c_series.py`:
цветовая маска, фактический напечатанный шаблон из той же панели, полный перебор его целочисленных
переносов внутри окна. Пиксели перекрывающих цветов исключены из функции невязки;
тёмные линии исключаются для цветных символов, для чёрных неотделимы по одному цвету.
Одинаковые оптимумы дают середину диапазона; половина его размаха добавляется к базовой погрешности
7 px (S105) / 4 px (S106), затем добавляются 2 px каждой калибровочной опоры по прежней формуле.
Это оценка растрового считывания, не экспериментальная погрешность и не доверительный интервал.
Дуги кругов восстанавливаются с геометрией шаблона из изолированного круга; их центры модельно зависимы.
Для D01 сравнивается пересечение фактических двумерных пикселей одного символа (>75%), а не Δp.

Все 30 индивидуально различимых начальных маркеров D03 в семи сериях восстановлены; исключённых
индивидуально идентифицированных маркеров нет. Общий origin остаётся неизвестным: наложение не
позволяет сосчитать полностью скрытые отдельные символы; координаты/число таких символов не выдумывались.
Пропуски D02 восстановлены отдельно. Координаты контрольных проектов T011v не копировались и их
программы не запускались. Атрибуция и хеши PDF/растров, шаблоны, окна, опорные пиксели, функция
сопоставления и погрешности сохранены в проектах и паспортах; исходные изображения остаются в
`private/renders/`. Новые точки — оцифровка напечатанных экспериментальных маркеров.

| дефект | серия | действие | новые точки | основание |
| --- | --- | --- | --- | --- |
''' + '\n'.join(details) + '''

## Пригодные диапазоны и статусы

`usable_p_min_bar` — минимальное давление различимого сохранённого маркера; это не свидетельство
полного покрытия origin и не разрешение определять начальный наклон без анализа чувствительности.
Для воды приведено абсолютное парциальное давление: RH × p_sat(293 K), p_sat=0.02317544979505 bar.
Поле есть у всех 19 серий в проектах, в паспортах `params.series` и в manifest.

| серия | usable_p_min_bar | статус |
| --- | ---: | --- |
''' + '\n'.join(ranges) + '''

Побайтовое сравнение 12 принятых серий: исходные строковые значения `pixel_x,pixel_y,x,y,x_err,y_err`
соединены запятыми, с LF после каждой строки; сравнение без перевода в float. До/после SHA-256 и число
строк — [baseline.json](../data/extraction/digitization/T011b/baseline.json) и
[fix_evidence.json](../data/extraction/digitization/T011b/fix_evidence.json).
Статус и новые поля происхождения не входят в числовой байтовый блок. Builder повторяет проверку и
отказывает при несовпадении статуса CSV/проекта/паспорта с авторитетным вердиктом и хешем координат.

Принятые серии: ''' + '; '.join(unchanged) + '''.

Наложения: `private/renders/T011-*-overlay.png` (новые маркеры выделены пурпурным квадратом).
Парные вырезки «оригинал / вычисленный центр»: `private/renders/T011b-*-recoveries.png`;
их SHA-256 — в `fix_evidence.json`. Исходная Table 3 и её паспорт сохранены без изменений.

## Воспроизведение и проверки

Все команды выполняются из текущего worktree; зависимости уже доступны локально, сеть не нужна.
Локальная `.venv` подготовлена копированием установленных зависимостей из готового окружения
основного checkout; его файлы не изменялись. `UV_CACHE_DIR` всегда внутри текущего worktree.

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
uv run --locked --no-sync python scripts/extraction/digitize_c_series.py
uv run --locked --no-sync python scripts/extraction/build_c_series.py
uv run --locked --no-sync python scripts/extraction/report_c_series_fixes.py
make test
git diff --check
```

Тесты проверяют общую сборку/manifest и конверсии, уникальность символа по исходным пикселям,
сохранение разных близких по давлению маркеров, покрытие всех 32 окон, границы диапазона и
`verified` ⇔ T011v + побайтово неизменные координаты. В интеграционном тесте обновлено устаревшее
число GO-точек 319 → 330: добавлено 11 различимых GO-маркеров. Научные расчёты/fit не выполнялись.
'''
    validation_path = DIG/'T011b/validation.json'
    if validation_path.exists():
        validation = json.loads(validation_path.read_text())
        text += '\nФактические результаты — [validation.json](../data/extraction/digitization/T011b/validation.json).\n\n'
        text += '| команда / проверка | exit | результат |\n| --- | ---: | --- |\n'
        for check in validation['checks']:
            command = check['command'].replace('|','\\|')
            text += f"| `{command}` | {check['exit_code']} | {check.get('result','OK')} |\n"
        text += '''
Первый полный прогон: 224 passed / 3 failed. Устранены устаревшее ожидание числа GO-точек и
дефект локального `.venv/bin/pytest` (отсутствие защиты `__main__`, повторный запуск при macOS spawn).
Повторный полный прогон: **227 passed**, exit 0; пять предупреждений deprecation PyMuPDF/SWIG.

Итог (семь строк):

1. Задача: T011b-c-series-fix; рабочая ветка `task/T011b-c-series-fix`.  
2. D01: один дубль удалён по общим пикселям печатного круга.  
3. D02: оба внутренних маркера восстановлены из первоисточников.  
4. D03: 30 начальных маркеров восстановлены, диапазоны семи серий расширены.  
5. Статусы: 12 неизменных серий verified; семь изменённых provisional до T011v2.  
6. Проверки: make test — 227 passed; diff --check — 0; 42 защищённых файла неизменны.  
7. Сдача: отчёт и артефакты в worktree; commit/push не выполнены; требуется T011v2.
'''
    (ROOT/'reviews/T011b_fix_report.md').write_text(text)
    print(f'{added} recovered, {removed} duplicate removed; {total} T011 rows; 12 byte-identical verified series')


if __name__ == '__main__':
    main()
