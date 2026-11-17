#!/usr/bin/env python3
"""Independent exact-arithmetic sensitivity recomputation for T033."""
import csv
import json
from decimal import Decimal, localcontext
from fractions import Fraction as F
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary'
OUT = ROOT / 'reviews/T033-control/recompute.json'
REPORT = ROOT / 'reviews/T033_independent_recompute.md'
D = [F('0.03'), F('0.05'), F('0.10')]
R = F('0.005')
TOL = F('1e-12')


def number(x):
    x = F(x)
    with localcontext() as ctx:
        ctx.prec = max(80, len(str(abs(x.numerator))) + len(str(x.denominator)) + 20)
        dec = format(Decimal(x.numerator) / Decimal(x.denominator), '.15f')
    return {'fraction': str(x), 'decimal': dec}


def rows(filename):
    with (DATA / filename).open(encoding='utf-8', newline='') as f:
        return {r['sample_id']: r for r in csv.DictReader(f)}


def bounds(q, d, rounding=R):
    return q * (1-d) - rounding, q * (1+d) + rounding


def scenario(a, b, d):
    aa, bb = bounds(a, d), bounds(b, d)
    vertices = [x/y for x, y in product(aa, bb)]
    return {'a_bounds': list(map(number, aa)), 'b_bounds': list(map(number, bb)),
            'ratio_vertices': list(map(number, vertices)),
            'ratio_min': number(min(vertices)), 'ratio_max': number(max(vertices)),
            'a_above_b': aa[0] > bb[1], 'b_above_a': bb[0] > aa[1]}


def threshold(a, b, rounding):
    # Signed root permits reporting when A is already below B at d=0.
    left, right = F(-1), F(1)
    def gap(d):
        return bounds(a, d, rounding)[0] - bounds(b, d, rounding)[1]
    assert gap(left) > 0 and gap(right) < 0
    while right - left > TOL:
        mid = (left + right) / 2
        if gap(mid) > 0:
            left = mid
        else:
            right = mid
    formula = (a-b-2*rounding)/(a+b)
    assert left <= formula <= right
    return {'bisect_lo': number(left), 'bisect_hi': number(right),
            'bisect_mid': number((left+right)/2), 'formula': number(formula),
            'absolute_error_bound': number(right-left), 'nonnegative_root': formula >= 0}


def main():
    dry, materials = rows('S2_dry_CO2.csv'), rows('S2_materials.csv')
    q = {s: F(r['q_CO2_dry_mmol_g']) for s, r in dry.items()}
    ids = ['S2-BASE', 'S2-C48', 'S2-C72', 'S2-N72', 'S2-C96', 'S2-I96']
    assert set(q) == set(ids) and all(v > 0 for v in q.values())
    base = q['S2-BASE']
    samples = {}
    for s in ids:
        m = F(1000)/(F('44.01')*q[s])
        pei = F(materials[s]['PEI_content_author_calculated_wt_pct'])
        samples[s] = {'q_mmol_g': number(q[s]), 'ratio_to_base': number(q[s]/base),
                      'gain_fraction': number(q[s]/base-1), 'gain_percent': number(100*(q[s]/base-1)),
                      'inventory_kg': number(m), 'author_estimated_pei_pct': number(pei),
                      'author_estimated_pei_inventory_kg': number(m*pei/100)}
    pairs = [('S2-C72','S2-C96'), ('S2-C72','S2-N72'), ('S2-C96','S2-I96')]
    pairs += [(s,'S2-BASE') for s in ids if s != 'S2-BASE']
    comparisons = {}
    for a, b in pairs:
        comparisons[a+'/'+b] = {'ratio': number(q[a]/q[b]),
            'scenarios': {str(float_d): scenario(q[a],q[b],d) for float_d,d in zip(('0.03','0.05','0.10'),D)},
            'threshold_with_rounding': threshold(q[a],q[b],R),
            'threshold_without_rounding': threshold(q[a],q[b],F(0))}
    rank = sorted(ids, key=lambda s: q[s], reverse=True)
    common = {}
    for label, d in zip(('0.03','0.05','0.10'),D):
        common[label] = {}
        for side, k in [('minus',1-d),('plus',1+d)]:
            assert sorted(ids,key=lambda s:q[s]*k,reverse=True) == rank
            assert all((q[a]*k)/(q[b]*k) == q[a]/q[b] for a,b in pairs)
            common[label][side] = {'k':number(k), 'inventory_multiplier':number(1/k),
                'ranking': rank, 'inventory_kg': {s:number(F(1000)/(F('44.01')*q[s]*k)) for s in ids}}
    result = {'task_id':'T033-task002-recompute', 'input':'data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary/S2_dry_CO2.csv',
              'source_locator':dry['S2-BASE']['source_locator'], 'source_id':'S2',
              'extraction_id':'not present in permitted CSV inputs', 'status':'provisional sensitivity analysis',
              'rounding_half_width_mmol_g':number(R), 'samples':samples, 'comparisons':comparisons,
              'common_multiplier':common, 'nominal_ranking':rank}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    def dec(obj, digits=6):
        return format(Decimal(obj['decimal']), f'.{digits}f')
    lines = ['# T033 — независимый пересчёт сухих данных S2', '',
        'Запуск из корня: `python3 scripts/task002_independent/recompute.py`. Машинный результат: `reviews/T033-control/recompute.json`.', '',
        'Источник: `data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary/S2_dry_CO2.csv`, S2, Table 2 dry, p. 3192; §§2.2 и 4.6. Доля PEI — `S2_materials.csv`, Table 1, p. 3189, авторский расчёт p. 3190. В разрешённых CSV `extraction_id` отсутствует; независимая сверка с первоисточником не выполнялась. Статус: предварительный анализ чувствительности. 1 bar в таблице и 1 atm в тексте — альтернативные указания источника.', '',
        'Ёмкость — ммоль/г массы сорбента после дегазации. Инвентарь — кг сорбента на однократную равновесную загрузку 1 кг CO₂; PEI — авторская оценка удержанного количества, а не результат отдельного взвешивания. Отношение к контролю также является порогом относительной цены при равной стоимости материала на загрузку, без затрат процесса.', '',
        '| Образец | q | Прирост к BASE, % | q/BASE | m, кг | Оценка PEI в m, кг |', '|---|---:|---:|---:|---:|---:|']
    for s in ids:
        x=samples[s]; lines.append(f"| {s} | {dec(x['q_mmol_g'],2)} | {dec(x['gain_percent'],4)} | {dec(x['ratio_to_base'])} | {dec(x['inventory_kg'])} | {dec(x['author_estimated_pei_inventory_kg'])} |")
    lines += ['', 'Независимые ограниченные отклонения: `q(1−d)−0.005 … q(1+d)+0.005`. Все четыре отношения вершин вычислены точно; показаны минимум и максимум. Строгое условие устойчивости A выше B: `lo_A > hi_B`. Это сценарии, не доверительные интервалы.', '', '| A/B | Номинал | d=3%: интервал; A>B | d=5%: интервал; A>B | d=10%: интервал; A>B | d* с округлением | d* без округления |', '|---|---:|---|---|---|---:|---:|']
    for a,b in pairs:
        c=comparisons[a+'/'+b]; cells=[]
        for d in ('0.03','0.05','0.10'):
            z=c['scenarios'][d]; cells.append(f"[{dec(z['ratio_min'])}, {dec(z['ratio_max'])}]; {'да' if z['a_above_b'] else 'нет'}")
        lines.append(f"| {a}/{b} | {dec(c['ratio'])} | {' | '.join(cells)} | {dec(c['threshold_with_rounding']['bisect_mid'],9)} | {dec(c['threshold_without_rounding']['bisect_mid'],9)} |")
    lines += ['', 'Порог найден бисекцией точных дробей с шириной скобки ≤ 10⁻¹²; в JSON сохранены обе границы и сравнение с точной формулой `(q_A−q_B−0.01)/(q_A+q_B)` (без округления вместо 0.01 — 0). При равенстве границы преимущество уже не является строгим. Отрицательный порог I96/BASE — продолжение уравнения на отрицательные d: при допустимых d ≥ 0 преимущества I96 нет.', '', '| d | Устойчиво выше BASE | Различие C72 и C96 разрешено? |', '|---|---|---|']
    for label in ('0.03','0.05','0.10'):
        above=[s for s in ids if s!='S2-BASE' and comparisons[s+'/S2-BASE']['scenarios'][label]['a_above_b']]
        c=comparisons['S2-C72/S2-C96']['scenarios'][label]
        lines.append(f"| {label} | {', '.join(above) if above else 'нет'} | {'да' if c['a_above_b'] or c['b_above_a'] else 'нет'} |")
    lines += ['', 'Номинальный порядок: ' + ' > '.join(rank) + '. Для разрешения C72/C96 по принятой модели нужно совместное ограничение независимых относительных отклонений обоих измерений ниже указанного d* с учётом округления; только общее смещение калибровки различие не меняет.', '', '| d | k = 1−d: множитель m | k = 1+d: множитель m |', '|---|---:|---:|']
    for label in ('0.03','0.05','0.10'):
        lines.append(f"| {label} | {dec(common[label]['minus']['inventory_multiplier'])} | {dec(common[label]['plus']['inventory_multiplier'])} |")
    lines += ['', 'При общем положительном k точные отношения, приросты и порядок сохраняются; m(k) = m(1)/k. В JSON приведены значения m для каждого образца и каждого k. Общее масштабирование — отдельный сценарий, сам по себе он не описывает индивидуальную ошибку или перевод между давлениями.', '', 'Расчёт выполнен по указанным CSV без обращения к T030. Поскольку дерево исходно содержит удалённые файлы и карточка запрещает коммит, это незакоммиченный независимый контроль, а не учтённый воспроизводимый запуск с паспортом `runs/`. Запрошены gpt-6.1-terra / high / сеть off; фактические модель, effort, способ запуска и сетевой режим интерфейсом не раскрыты и не подтверждены. Независимая приёмка руководителем предстоит.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')

if __name__ == '__main__':
    main()
