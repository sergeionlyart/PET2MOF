#!/usr/bin/env python3
"""T025: descriptive reduction of frozen branch summaries, never a model refit.

Execute via scripts/run.py; {run_id} is substituted by the runner. No samples.npz
or network access is needed. Branch frequencies describe a factorial design,
not probabilities of hypotheses. A3 and monotonicity diagnostics add no new
preregistered decision threshold.
"""

import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SUMMARY = 'results/prereg-v1/ensemble/summary.json'
VALIDATION = 'results/prereg-v1/validation/validation.json'
DEMO = 'reports/T015/demo.json'
DIMS = ('measure', 'model_version', 'interpretation', 'mechanism', 'carrier', 'defect')
REGS = ('R1', 'R2')
RHS = (0, 40, 70)
CELLS = tuple(f'{r}_RH{rh}' for r in REGS for rh in RHS)
W = (0., .1, .2, .3)
DATASETS = ('T006-S100-FigS5', 'T011-S105-Fig8A', 'T011-S105-Fig8B',
            'T011-S105-Fig8C', 'T011-S105-Fig9', 'T011-S106-Fig4')
METRICS = ('winner_resolved', 'interior', 'interior_resolved', 'H1a',
           'unresolved_winner', 'A1_p_ge_095_diagnostic', 'A2_p_ge_095_diagnostic',
           'A1_adjacent_positive_marginal', 'A2_adjacent_negative_marginal',
           'A3_all_adjacent_include_zero', 'A3_all_pair_intervals_include_zero')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads((ROOT / path).read_text())


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict))
                             else v for k, v in row.items()})


def cell_record(label, branch, key):
    c = branch['summary'][key]
    q = np.asarray(c['q_work_quantiles'])
    adjacent = np.asarray(c['adjacent_contrast_95'])
    assert q.shape == (3, 4) and np.isfinite(q).all()
    assert np.all(np.diff(q, axis=0) >= 0)
    assert adjacent.shape == (2, 30) and np.isfinite(adjacent).all()
    p = np.asarray(c['rank1_probabilities'])
    winner = int(np.argmax(p))
    assert c['candidate'] == W[winner]
    resolved = (c['rank1_lower95_MC'][winner] >= .8 and
                min(c['winner_contrast_lower95_simultaneous']) > 0)
    lo, hi = c['w_star_90']
    interior = c['delta_95'][0] > 0 and lo > 0 and hi < .3
    assert resolved == c['winner_resolved'] and interior == c['interior']
    assert 0 <= lo <= hi <= .3 and c['delta_95'][0] <= c['delta_95'][1]
    # RH0 is a working-capacity contrast, not the dry equilibrium contrast in
    # H1a_pairs; its all-pair working intervals cannot be recovered from marginals.
    wet = not key.endswith('RH0')
    for pair in c['H1a_pairs']:
        if wet:
            d, w = pair['dry_simultaneous_95'], pair['wet_simultaneous_95']
            supported = (pair['probability'] >= .95 and d[0]*d[1] > 0 and
                         w[0]*w[1] > 0 and d[0]*w[0] < 0)
            assert supported == pair['supported']
        else:
            assert not pair['supported']
    return dict(branch=label, convergence=branch['convergence']['status'],
                **dict(zip(DIMS, label.split('/'), strict=True)), cell=key,
                candidate=c['candidate'], w_star_90=c['w_star_90'], delta_95=c['delta_95'],
                rank1_probabilities=c['rank1_probabilities'],
                rank1_lower95_MC=c['rank1_lower95_MC'],
                winner_contrast_lower95_simultaneous=c['winner_contrast_lower95_simultaneous'],
                winner_resolved=bool(resolved), interior=bool(interior),
                interior_resolved=bool(interior and resolved),
                H1a=any(p['supported'] for p in c['H1a_pairs']),
                H1a_pairs=c['H1a_pairs'], q_work_quantiles=c['q_work_quantiles'],
                monotone_up_probability=c['monotone_up_probability'],
                monotone_down_probability=c['monotone_down_probability'],
                A1_p_ge_095_diagnostic=c['monotone_up_probability'] >= .95,
                A2_p_ge_095_diagnostic=c['monotone_down_probability'] >= .95,
                A1_adjacent_positive_marginal=bool(np.all(adjacent[0] > 0)),
                A2_adjacent_negative_marginal=bool(np.all(adjacent[1] < 0)),
                A3_all_adjacent_include_zero=bool(np.all((adjacent[0] <= 0) & (adjacent[1] >= 0))),
                A3_all_pair_intervals_include_zero=(all(p['wet_simultaneous_95'][0] <= 0 <=
                    p['wet_simultaneous_95'][1] for p in c['H1a_pairs']) if wet else None),
                unresolved_winner=not resolved)


def distribution(rows):
    """Empirical distribution of branch descriptors; no pooled model draws."""
    if not rows:
        return dict(n=0, candidate_counts={}, w_star_90_counts={}, endpoint_distribution=None)
    endpoints = {}
    for key in ('w_star_90', 'delta_95'):
        endpoints[key] = {side: np.quantile([r[key][i] for r in rows],
            [0, .25, .5, .75, 1]).tolist() for i, side in enumerate(('lower', 'upper'))}
    for key in ('monotone_up_probability', 'monotone_down_probability'):
        endpoints[key] = np.quantile([r[key] for r in rows], [0, .25, .5, .75, 1]).tolist()
    return dict(n=len(rows), candidate_counts=dict(Counter(str(r['candidate']) for r in rows)),
                w_star_90_counts=dict(Counter(json.dumps(r['w_star_90']) for r in rows)),
                endpoint_distribution=endpoints)


def aggregate(labels, branches, records, dimension, level, state):
    selected = [k for k in labels if branches[k]['convergence']['status'] == state]
    rows = [r for k in selected for r in records[k]]
    n = len(selected)
    regs = {}
    for reg in REGS:
        regs[reg] = {metric: sum(branches[k]['summary'][reg][metric] for k in selected)
                     for metric in ('conditional_H1', 'w_star_shift_resolved')}
    cells = {}
    for cell in CELLS:
        subset = [r for r in rows if r['cell'] == cell]
        counts = {m: dict(numerator=sum(bool(r[m]) for r in subset),
                         denominator=sum(r[m] is not None for r in subset)) for m in METRICS}
        cells[cell] = dict(n=n, counts=counts, distributions=distribution(subset))
    # Heatmap measures are branch events: "at least one condition". Frequencies
    # do not average capacities or uncertainty measures across branches.
    any_counts = {m: sum(any(r[m] is True for r in records[k]) for k in selected) for m in METRICS}
    any_counts['conditional_H1'] = sum(any(branches[k]['summary'][r]['conditional_H1'] for r in REGS) for k in selected)
    any_counts['w_star_shift_resolved'] = sum(any(branches[k]['summary'][r]['w_star_shift_resolved'] for r in REGS) for k in selected)
    return dict(dimension=dimension, level=level, convergence=state, n=n,
                regimes=regs, cells=cells, any_condition_counts=any_counts)


def representative_labels(branches):
    # Fixed factorial slice, independent of H1 results: paired measures,
    # structures and label interpretations, then all other mechanisms. No claim
    # to numerical representativeness of the unplotted carrier/defect branches.
    labels = []
    for measure in ('stress', 'analog'):
        for version in ('v1', 'v1.1-mof', 'v1.1-connectivity'):
            for interpretation in ('composite', 'ratio'):
                labels.append('/'.join((measure, version, interpretation, 'neutral',
                                        'S105-full-carrier', 'UiO-66_100')))
    for mechanism in ('availability', 'bicarbonate', 'suppression', 'affinity'):
        labels.append('/'.join(('stress', 'v1.1-connectivity', 'ratio', mechanism,
                                'S105-full-carrier', 'UiO-66_100')))
    assert all(k in branches for k in labels)
    return labels


def make_plots(out, source, groups, labels, run_id, status):
    # runs.py deliberately passes a minimal environment: configure local font
    # cache here instead of depending on an inherited MPLCONFIGDIR.
    os.environ['MPLCONFIGDIR'] = str(ROOT / '.uv-cache' / 'matplotlib-T025')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    caption = (f'T025 {status}: {run_id}\nsource run: {source["run_id"]}\n'
               'C extraction_id: S100=T006-S100-FigS5; S105=T011-S105-Fig8A/B/C,Fig9; '
               'S106=T011-S106-Fig4')
    maps = []
    for i, label in enumerate(labels, 1):
        branch = source['branches'][label]
        fig, axes = plt.subplots(2, 3, figsize=(11.5, 7.4), layout='constrained')
        vmax = max(np.max(branch['summary'][c]['q_work_quantiles']) for c in CELLS)
        vmin = min(0, min(np.min(branch['summary'][c]['q_work_quantiles']) for c in CELLS))
        for row, reg in enumerate(REGS):
            for col, name in enumerate(('q2.5', 'q50', 'q97.5')):
                values = np.array([branch['summary'][f'{reg}_RH{rh}']['q_work_quantiles'][col] for rh in RHS])
                ax = axes[row, col]
                mesh = ax.imshow(values, origin='lower', aspect='auto', vmin=vmin, vmax=vmax,
                                 cmap='viridis', interpolation='nearest')
                for y in range(3):
                    for x in range(4):
                        ax.text(x, y, f'{values[y,x]:.3g}', ha='center', va='center', fontsize=8,
                                color='white' if values[y,x] < (vmin+vmax)/2 else 'black')
                ax.set(xticks=range(4), xticklabels=(0, 10, 20, 30), yticks=range(3),
                       yticklabels=RHS, xlabel='PEI, wt% of dry composite', ylabel='RH, % (discrete)',
                       title=f'{reg}: {name}')
        fig.colorbar(mesh, ax=axes, label='q_work, mmol CO2 / g dry composite', shrink=.8)
        fig.suptitle(label + '\nconditional forecast; convergence=' + branch['convergence']['status'], fontsize=10)
        fig.supxlabel(caption, fontsize=7)
        filename = f'map_{i:02d}.png'
        fig.savefig(out / filename, dpi=150)
        plt.close(fig)
        maps.append(dict(path=filename, branch=label, convergence=branch['convergence']['status']))
    metrics = ('conditional_H1', 'w_star_shift_resolved', 'interior_resolved', 'H1a',
               'A1_p_ge_095_diagnostic', 'A2_p_ge_095_diagnostic',
               'A3_all_pair_intervals_include_zero', 'unresolved_winner')
    populated = [g for g in groups if g['n']]
    fig, ax = plt.subplots(figsize=(13, 10), layout='constrained')
    values = np.array([[g['any_condition_counts'][m]/g['n'] for m in metrics] for g in populated])
    mesh = ax.imshow(values, aspect='auto', vmin=0, vmax=1, cmap='YlGnBu')
    ax.set(xticks=range(len(metrics)), xticklabels=('H1', 'RH shift', 'interior + winner', 'H1a',
           'P(up)>=.95*', 'P(down)>=.95*', 'all-pair zero*', 'unresolved winner*'),
           yticks=range(len(populated)), yticklabels=[f'{g["dimension"]}={g["level"]} | {g["convergence"]} | n={g["n"]}' for g in populated])
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=9)
    for y, g in enumerate(populated):
        for x, m in enumerate(metrics):
            count = g['any_condition_counts'][m]
            ax.text(x, y, f'{count}/{g["n"]}', ha='center', va='center', fontsize=8,
                    color='white' if values[y,x] > .6 else 'black')
    fig.colorbar(mesh, ax=ax, label='Fraction of design branches (not hypothesis probability)')
    ax.set_title('At least one applicable cell / regeneration per branch; *diagnostic only\n'
                 'No certified-converged branches: empty denominator omitted, not zero probability')
    fig.supxlabel(caption, fontsize=7)
    fig.savefig(out / 'branch_fractions.png', dpi=150)
    plt.close(fig)
    return maps


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---']*len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows])


def report(out, result, source, demo, maps):
    total_groups = [g for g in result['groups'] if g['dimension'] == 'all']
    populated = next(g for g in total_groups if g['n'])
    cell_rows = []
    for cell, value in populated['cells'].items():
        c = value['counts']
        cell_rows.append([cell, value['n'], c['winner_resolved']['numerator'], c['interior']['numerator'],
                          c['interior_resolved']['numerator'], c['H1a']['numerator'],
                          value['distributions']['candidate_counts']])
    group_rows = [[g['dimension'], g['level'], g['n'],
                   g['any_condition_counts']['interior_resolved'],
                   g['any_condition_counts']['A1_p_ge_095_diagnostic'],
                   g['any_condition_counts']['A3_all_pair_intervals_include_zero']]
                  for g in result['groups'] if g['n']]
    alt_rows = []
    distribution_rows = []
    for cell, v in populated['cells'].items():
        c = v['counts']
        def count(m):
            d = c[m]
            return f'{d["numerator"]}/{d["denominator"]}' if d['denominator'] else 'unknown'
        alt_rows.append([cell, count('A1_p_ge_095_diagnostic'), count('A2_p_ge_095_diagnostic'),
                         count('A1_adjacent_positive_marginal'), count('A3_all_adjacent_include_zero'),
                         count('A3_all_pair_intervals_include_zero'), count('unresolved_winner')])
        dist = v['distributions']['endpoint_distribution']
        def triple(values, scale=1):
            return ' / '.join(f'{scale*values[i]:.5g}' for i in (0, 2, 4))
        distribution_rows.append([cell, triple(dist['w_star_90']['lower'], 100),
            triple(dist['w_star_90']['upper'], 100), triple(dist['delta_95']['lower']),
            triple(dist['delta_95']['upper']), triple(dist['monotone_up_probability']),
            triple(dist['monotone_down_probability'])])
    c_rows = []
    for fit in demo['fits']:
        for model in ('M1', 'B1'):
            m = fit['models'][model]['metrics']
            c_rows.append([fit['model_version'], fit['interpretation'], model,
                           *[f'{m[k]:.6f}' for k in ('RMSE', 'MAE', 'Bias')],
                           f'{100*m["fraction_within_U"]:.2f}%', m['all_series_numerical_criteria']])
    captions = '\n\n'.join(f'![{m["branch"]}]({m["path"]})\n\n'
        f'{m["path"]}: `{m["branch"]}`; run_id `{result["run_id"]}` ({result["status"]}); '
        f'ансамбль `{source["run_id"]}`, наборы/extraction_id: ' + ', '.join(DATASETS) + '.' for m in maps)
    text = f'''# T025 — состав × влажность и решения по H1

Научный статус H1: **данных недостаточно**.

Это одна формула поручения §11. Внешняя количественная проверка недоступна,
контроль PEI на C не прошёл совокупность критериев, а сходимость ансамбля не удостоверена.
Нулевой `conditional_H1` означает отсутствие поддержки полного решающего условия
в данном условном прогнозе; он не доказывает отсутствие максимума у реального материала.

Роль: исполнитель T025 · платформа OpenAI Codex. Назначено gpt-6.1-sol/high;
фактические модель/effort и запуск через launcher интерфейсом не подтверждены.
Локальных `.agents/skills/` и `.claude/rules/` нет. Прямое поручение задаёт карточку,
существующий worktree и сдачу без commit; сетевые обращения — только `uv sync --locked`.
Независимая приёмка T025v этим отчётом не заменяется.

## Происхождение и границы

Анализ: run_id `{result['run_id']}`, статус **{result['status']}**,
HEAD `{result['head']}`. Исходный продуктивный ансамбль:
`{source['run_id']}`; тег `prereg-v1` — `{result['prereg_sha']}`.
Источник всех следующих чисел ветвей — `{SUMMARY}`,
SHA-256 `{result['inputs'][SUMMARY]}`; расчёт производных — `scripts/analysis/h1_maps.py`.
Полный журнал происхождения: [analysis.json](analysis.json); паспорт запуска сохраняется штатным runner.
Расчётные числа не являются новым извлечением эксперимента. Связь с C:
{', '.join(DATASETS)}. Это существующие extraction_id, новые measured/verified записи не создавались.
Выводы T025 до независимой приёмки — provisional-анализ, не статус исходных C-записей.

Каждая ветвь сохраняет отдельную меру, структуру, прочтение, механизм, перенос носителя
и водную дефектность. Частоты ветвей — счёт равнопредставленных элементов факторного
дизайна, **не вероятность H1** и не доля реальных материалов. `stress` — мера дизайна;
`analog` — условная чувствительность к аналогам, не prior для целевого PET-композита.
Нет усреднения q_work, параметров или MC-выборок между ветвями.
На ветвь: {source['repeats']} независимых повтора × {source['samples_per_repeat']} наборов;
seeds {source['repeat_seeds']}. Это повторности MC, не экспериментальные образцы.
Входные SHA-256, размеры групп и точные дескрипторы доступны для проверки.
Сырые `samples.npz` не нужны: карты восстановлены только в четырёх сохранённых
составах, между ними и между RH ничего не интерполировано.

## Три уровня доказательств

**Внешняя проверка V.** `{VALIDATION}`, run_id
`20261117T022438705845Z-e6dc3bd5-prereg-v1-validate`:
{result['validation']['unique_series']} уникальных серий, полных сравнений
{result['validation']['full']}, условных {result['validation']['conditional']};
{result['validation']['records']} записей not_testable (S2 Vp повторена по моделям).
Это отказ применимости сравнения, не численный fail прогноза. S106 откалиброван,
независимой V по воде нет. Подтверждение извлечения и известность условий разделены
в T019v2/T023; оригинальные материалы заново не оцифровывались.
Прочитаны `reviews/T019v2_holdout_reverification.md` и
`reviews/T023_holdout_testability.md` из рабочего дерева; их хеши в analysis.json.
Закреплённый SHA holdout `{result['holdout_sha']}` взят из сообщения тега `prereg-v1`;
локальная ветка holdout для воспроизведения не нужна.
S2 — отдельный PEI@UiO-66-NH2 контроль переноса, не целевой PET-derived материал.

**Контроль на C.** Данные S100, extraction_id `T006-S100-FigS5`, и
`reviews/T013_implementation_report.md`, `reviews/T015_revision_report.md`, D-16/D-17:
ни одна структура не прошла все критерии целых изотерм. Уменьшение ошибки после
ревизии по тем же C — подгонка. Сравнение ниже рассчитано из `reports/T015/demo.json`
(run_id `{demo['run_id']}`, debug), с одинаковыми CSV-весами T015, не смешано с
архивным бюджетом ошибок T013. Единицы RMSE/MAE/Bias: ммоль/г наблюдательной базы
S100 соответствующей структуры; mean(U) = {demo['fits'][0]['models']['M1']['metrics']['mean_U']:.6f}.

{table(['Структура', 'Прочтение', 'Модель', 'RMSE', 'MAE', 'Bias', 'В U', 'Все целые серии'], c_rows)}

У connectivity малый суммарный Bias маскирует Bias 10PEI/20PEI; прохождение одной
агрегированной метрики не отменяет провал серий. Показатель связности упирается
в верхнюю границу 12, AICc M1 по четырём независимым изотермам не определён.
B1 линейна по w и выбирает край (при нулевом наклоне максимум — весь интервал).
Поэтому отсутствие у B1 внутреннего максимума не является доказательством
превосходства M1; предпочтение моделей обсуждается только по C-метрикам выше.

**Условный прогноз.** Все числа далее — модельные, номинальные режимы;
скрининг T015 с варьированием управлений нерешающий и не объединён с ансамблем.
`verdict` — константа в producer-коде; в T025 она не используется для подсчёта H1.
Проверены `conditional_H1`, интервалы и остальные признаки непосредственно в summary.

## Сходимость и решающие признаки

{table(['convergence.status', 'Число ветвей', 'H1 R1 / R2', 'Сдвиг R1 / R2'], [[g['convergence'], g['n'], f"{g['regimes']['R1']['conditional_H1']} / {g['regimes']['R2']['conditional_H1']}", f"{g['regimes']['R1']['w_star_shift_resolved']} / {g['regimes']['R2']['w_star_shift_resolved']}"] for g in total_groups])}

Группа `established` пуста: её доли **не определены**, а не равны нулю.
`not_established` здесь не означает доказанную численную расходимость:
у всех неизвестна target observational U и нельзя удостоверить допуск 0.1 U для q/Δ.
Дополнительно probability_checks_pass выполнен у {result['convergence']['probability_pass']} ветвей,
не выполнен у {result['convergence']['probability_fail']}; grid_location_pass выполнен у
{result['convergence']['grid_pass']}, не выполнен у {result['convergence']['grid_fail']}.
Эти частичные проверки не заменяют полный статус; N после просмотра не увеличивался.

H1 требует в RH70 внутренний разрешённый максимум, неперекрывающиеся 90%-интервалы
w* при RH0/RH70 и 95%-интервал изменения Δ, не включающий ноль.
Разрешение кандидата дополнительно требует нижнюю MC-границу P(rank=1) ≥0.8
и положительные одновременные контрасты. `interior` отдельно проверяет Δ_low>0,
w*_low>0, w*_high<0.3; «внутренний разрешённый» = interior AND winner_resolved.
H1a — хотя бы одна устойчивая инверсия пары между сухой **равновесной** ёмкостью
при 35 °C и влажной рабочей; RH0 q_work не подменяет сухую равновесную ёмкость.

{table(['Ячейка', 'n not_established', 'Разрешённый кандидат', 'interior', 'Внутренний разрешённый', 'H1a', 'candidate: число'], cell_rows)}

Ни один сдвиг w* не разрешён; A4 не отвергнута. Это не доказательство постоянства
истинного оптимума. H1a не установлена ни в одной применимой влажной ячейке.
`candidate` — argmax вероятности ранга среди 0/10/20/30%, не непрерывный w*.
Распределения candidate и точных пар границ w_star_90, а также min/Q25/median/Q75/max
каждого конца delta_95 и вероятностей монотонности — по каждой группе и ячейке
в [analysis.json](analysis.json). Это распределения дескрипторов отдельных ветвей,
не объединённый интервал прогноза. Все исходные границы и квантили сохранены в
[cells.csv](cells.csv), полные ветвевые итоги — [branches.json](branches.json).

Ниже min / median / max **по дескрипторам ветвей** для каждой границы;
это не интервал объединённого оптимума. w* переведён в мас.% сухого композита,
Δ — ммоль/г сухого композита. Два столбца вероятностей относятся к A1/A2.

{table(['Ячейка', 'w*_low, %', 'w*_high, %', 'Δ_low', 'Δ_high', 'P(up)', 'P(down)'], distribution_rows)}

## A1/A2/A3: диагностика, не новые решающие правила

Для A1/A2 приводятся вероятности монотонности по сетке 1 мас.% в каждой ветви.
Порог 0.95 в таблице — явно post hoc описательный фильтр, **не предрегистрация**;
он не даёт права объявить альтернативу установленной. Положительность всех
нижних маргинальных 95%-границ соседних разностей — отдельная диагностика,
без одновременной защиты 30 разностей; отрицательные верхние границы аналогично A2.

Для A3 различаются: (а) не разрешён единственный победитель; (б) все соседние
маргинальные интервалы включают ноль; (в) все шесть одновременных интервалов
пар q_work включают ноль. Только (в) непосредственно описывает неразличимость
всех четырёх кандидатов при принятом бюджете. Для RH0 (в) **unknown**:
summary не содержит таких парных интервалов рабочей ёмкости; их нельзя вывести
вычитанием маргинальных квантилей. Ни (а), ни включение нуля не доказывают
эквивалентность составов. A1/A2/A3 не образуют взаимоисключающую классификацию.

{table(['Ячейка', 'P(up)≥.95', 'P(down)≥.95', 'Все adj_low>0', 'Все adj CI∋0', 'Все pair CI∋0', 'Нет winner'], alt_rows)}

## Разбивка по измерениям ветви

Таблица: число ветвей с признаком хотя бы в одной применимой ячейке;
все строки ниже — not_established. Пустые established-группы также сохранены
в JSON. По каждой ячейке и режиму доступны отдельные числители/знаменатели,
не только объединение событий. Совместные сочетания измерений остаются в branches.json/cells.csv.

{table(['Измерение', 'Значение', 'n', 'Внутренний разрешённый', 'P(up)≥.95*', 'Все pair CI∋0*'], group_rows)}

![Доли ветвей](branch_fractions.png)

Рисунок: доли элементов дизайна с признаком хотя бы в одной ячейке; звёздочкой
отмечена диагностика. run_id `{result['run_id']}` ({result['status']}),
ансамбль `{source['run_id']}`, extraction_id {', '.join(DATASETS)}.
Строки перекрываются, их нельзя суммировать как независимые выборки.

## Карты q_work

Одна карта — одна ветвь, R1/R2 × квантили 2.5/50/97.5%; единицы — ммоль CO2/г
сухого композита. Цветовая шкала общая внутри карты, между картами различается.
RH показана дискретными равномерно размещёнными строками 0/40/70%, не непрерывной
координатой. Номинальные условия: T_ads=308.15 K, P_ads=1 bar, сухой z_CO2=0.05,
t_ads=t_des=1800 s; R1: 383.15 K/1 bar, R2: 363.15 K/0.1 bar;
y_CO2=y_H2O=0.001 для R1, 0.01 для R2 (входной газ регенерации).
Ограничение D-08/D-17 (`docs/decisions.md`): цикл квазиравновесный;
релаксация — условное сценарное допущение, интегратор потоков не реализован.
Общий τ шести пулов бикарбонатной ветви — ограничение модели,
а не установленная кинетика.
Все сохранённые знаки квантилей оставлены, в том числе малые отрицательные
численные значения около нуля; обрезки к нулю не выполнялось.

Выбран фиксированный факторный срез: обе меры × три структуры × два прочтения
при neutral; дополнительно четыре механизма при stress/connectivity/ratio.
Носитель S105-full-carrier и водная ветвь UiO-66_100 фиксированы для сопоставимости.
Это иллюстрация семейств, а не отбор по лучшему результату; альтернативные
носитель/дефектность покрываются полной таблицей, визуальное обобщение на них не заявляется.

{captions}

## Приоритеты следующей проверки

Ни один состав не рекомендуется как установленный лучший. Три приоритета ниже —
проверки причин неопределённости, а не обещание результата.

1. **Идентифицировать массу и размещение PEI до новой подгонки.** Для одной
   родительской партии и нескольких загрузок определить сухую удержанную массу
   PEI и MOF независимо (например, элементный анализ с холостым носителем плюс
   согласованный массовый баланс/TGA с учётом воды). Записать одновременно
   r=m_PEI/m_MOF и w=m_PEI/(m_PEI+m_MOF), потери при обработке, неопределённости
   и базу каждого q. Так различаются прочтения `ratio` (w=r/(1+r)) и `composite`
   (w=label/100) при полной удержанности; одной изотермой их не разрешить.
   Для метки 30 различие проектных прочтений: 23.08% против 30%, не измеренный состав.
   Измерить q одновременно на г сухого композита и пересчётом на г MOF: это
   снимает v1/v1.1-mof неоднозначность оператора. Независимая порометрия до/после
   PEI по загрузкам и временны́е отклики CO2 проверят плавное объёмное блокирование
   против резкой потери связности v1.1-connectivity; нужны также структурные/водные
   характеристики носителя, а не назначение дефектности по названию PET.

2. **Получить минимальную матрицу рабочей ёмкости с полным бюджетом U.**
   Проектный минимум: w=0/0.10/0.20/0.30 (фактически измеренные), RH=0/40/70%,
   оба номинальных R1/R2 выше; одна родительская партия, одинаковое время и газ,
   минимум три независимых приготовления на состав (стартовый дизайн, мощность
   ещё unknown). Равновесные сухие q при 35 °C на тех же образцах нужны отдельно
   для H1a. Измерять q_ads и q_des, CO2 отдельно от воды, RH/точку росы у образца,
   T/P/состав и расход газа, массу сухого композита; распространить их ковариации
   в разности, ранги и интервалы. Из повторных временных отсчётов не делать
   независимые образцы. Целевая экспериментальная U позволит проверить численные
   допуски сходимости; произвольно назначать U ради pass нельзя. Если грубая сетка
   обнаружит внутреннюю область, новая заранее зафиксированная стадия уточняет
   её и края; эти уточняющие данные не объявляются прежней независимой V.
   Партии/режимы для fit и V разделить целиком и зарегистрировать до измерений;
   необходимое число повторов уточнить по пилотной U и мощности до решающего этапа.

3. **Закрыть конкретные блокеры V или заменить серии новыми данными.**
   Для S113/S103 нужны документированный RH и u_T (активация не свидетельствует
   о сухости потока); N2 вне 298 K требует T-зависимости либо нового опыта в
   калибровочной T. Для S102 нужны T/RH/массовая база/total или partial pressure
   и независимая сверка первичных маркеров. Для S2 — законная оригинальная
   вёрстка, давление 1 bar/1 atm, RH смеси, бюджет ошибок и статус вторичной
   коррекции; JATS сам по себе не закрывает T019v-03. Для Vp-ratio дополнительно
   требуется новый отдельный предрегистрированный оператор порометрии либо
   действительные обязательные входы действующего оператора: текущий прогноз
   отсутствует из-за RH, последующие блокеры P/T не исчезают. Для S117 нужны
   blank-кривая, калиброванные расход/время/сухая масса и интегральный баланс
   отдельно CO2/H2O; проскок C/C0 не равен равновесной ёмкости. Ограничения
   неполноты и независимой сверки T019v2 сохраняются до их отдельного закрытия.

Эти действия следуют из validation.json и T019v2/T023, не из подбора входов по
остаткам V. Изменение оператора или модели после раскрытия — новая версия,
с использованными сериями уже не независимая. Данных о синтезе и ресурсе эксплуатации
в этой работе не получено; вывод ограничен проверяемостью сорбционного прогноза.

## Воспроизведение и передача

Скрипт не вызывает модель, не меняет frozen-входы и не пересэмплирует ансамбль.
Сначала руководитель принимает и фиксирует код; учитываемый запуск — из чистого
дерева, без `--allow-dirty`. Команда ниже использует имеющийся locked env;
перед подготовкой среды при необходимости `UV_CACHE_DIR="$PWD/.uv-cache" uv sync --locked`.

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
uv run --locked --no-sync python scripts/run.py \\
  --name T025-h1-maps --purpose 'T025 frozen branch maps and H1 analysis' \\
  --hypothesis 'H1 H1a A1 A2 A3 A4' \\
  --input scripts/analysis/h1_maps.py \\
  --input results/prereg-v1/ensemble/summary.json \\
  --input results/prereg-v1/validation/validation.json \\
  --input reports/T015/demo.json \\
  --input docs/hypotheses.md --input docs/decisions.md \\
  --input docs/validation_protocol.md --input docs/work_order_v1.1_RU.md \\
  --input docs/prereg_status.md \\
  --input reviews/T013_implementation_report.md \\
  --input reviews/T015_revision_report.md \\
  --input reviews/T019v2_holdout_reverification.md \\
  --input reviews/T023_holdout_testability.md \\
  --output reports/T025/artifacts.sha256 \\
  --output reports/T025/analysis.json \\
  --output reports/T025/branches.json --output reports/T025/cells.csv \\
  --output reports/T025/h1_analysis.md -- \\
  .venv/bin/python scripts/analysis/h1_maps.py --run-id '{{run_id}}'
```

Для debug тот же wrapper с `--allow-dirty` перед `--`; его статус автоматически
считывается скриптом из паспорта. Нельзя выдавать текущие debug-карты за
учитываемый новый запуск. SHA-256 каждого графика и отчёта — в artifacts.sha256;
сам файл списка хешируется runner, паспорт — `runs/<run_id>/passport.json`.
Независимые проверки T025v и учитываемый запуск руководителя остаются следующими
этапами приёмки, коммиты и публикация в T025 не выполняются.
'''
    (out / 'h1_analysis.md').write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    passport_path = ROOT / 'runs' / args.run_id / 'passport.json'
    passport_path.resolve().relative_to((ROOT / 'runs').resolve())
    passport = json.loads(passport_path.read_text())
    if passport['run_id'] != args.run_id or passport['status'] not in ('running', 'debug'):
        raise ValueError('must be invoked inside scripts/run.py')
    status = 'debug' if passport['status'] == 'debug' else 'completed_analysis'
    source, validation, demo = read_json(SUMMARY), read_json(VALIDATION), read_json(DEMO)
    branches = source['branches']
    records = {}
    branch_rows = []
    for label, branch in branches.items():
        assert len(label.split('/')) == len(DIMS)
        records[label] = [cell_record(label, branch, key) for key in CELLS]
        for r in REGS:
            a, b = [branch['summary'][f'{r}_RH{rh}']['w_star_90'] for rh in (0, 70)]
            shift = a[1] < b[0] or b[1] < a[0]
            s = branch['summary'][r]
            assert shift == s['w_star_shift_resolved']
            wet = branch['summary'][r+'_RH70']
            delta = s['delta_RH70_minus_dry_95']
            h1 = wet['interior'] and wet['winner_resolved'] and shift and delta[0]*delta[1] > 0
            assert bool(h1) == s['conditional_H1']
        branch_rows.append(dict(branch=label, **dict(zip(DIMS, label.split('/'), strict=True)),
                                convergence=branch['convergence'],
                                regimes={r: branch['summary'][r] for r in REGS},
                                attempted=branch['attempted'], accepted=branch['accepted'],
                                rejected=branch['rejected']))
    states = sorted({'established', *(b['convergence']['status'] for b in branches.values())})
    groups = [aggregate(list(branches), branches, records, 'all', 'all', s) for s in states]
    for i, dimension in enumerate(DIMS):
        for level in sorted({k.split('/')[i] for k in branches}):
            labels = [k for k in branches if k.split('/')[i] == level]
            groups.extend(aggregate(labels, branches, records, dimension, level, s) for s in states)
    inputs = {p: digest(ROOT / p) for p in (SUMMARY, VALIDATION, DEMO, 'scripts/analysis/h1_maps.py',
              'docs/hypotheses.md', 'docs/decisions.md', 'docs/validation_protocol.md',
              'docs/work_order_v1.1_RU.md', 'docs/prereg_status.md',
              'reviews/T013_implementation_report.md', 'reviews/T015_revision_report.md',
              'reviews/T019v2_holdout_reverification.md', 'reviews/T023_holdout_testability.md')}
    tag_message = git('for-each-ref', '--format=%(contents)', 'refs/tags/prereg-v1')
    pinned = re.findall(r'^holdout/v1 commit: ([0-9a-f]{40})$', tag_message, re.MULTILINE)
    if len(pinned) != 1:
        raise ValueError('prereg-v1 tag message must pin exactly one holdout commit')
    holdout_sha = pinned[0]
    v = validation['series']
    result = dict(run_id=args.run_id, status=status, head=git('rev-parse', 'HEAD'),
                  source_run_id=source['run_id'], prereg_sha=git('rev-parse', 'prereg-v1^{commit}'),
                  holdout_sha=holdout_sha, inputs=inputs, extraction_ids=DATASETS,
                  quantile_levels=[.025, .5, .975], endpoint_percentiles=[0, .25, .5, .75, 1],
                  interpretation='branch counts only; no branch pooling; diagnostics are not decision rules',
                  branch_count=len(branches), groups=groups,
                  validation=dict(unique_series=len({r['series'] for r in v}), records=len(v),
                      full=len(validation['comparison_groups']['full']),
                      conditional=len(validation['comparison_groups']['conditional']),
                      statuses=dict(Counter(r['status'] for r in v))),
                  convergence=dict(statuses=dict(Counter(b['convergence']['status'] for b in branches.values())),
                      probability_pass=sum(b['convergence']['probability_checks_pass'] for b in branches.values()),
                      probability_fail=sum(not b['convergence']['probability_checks_pass'] for b in branches.values()),
                      grid_pass=sum(b['convergence']['grid_location_pass'] for b in branches.values()),
                      grid_fail=sum(not b['convergence']['grid_location_pass'] for b in branches.values())))
    out = ROOT / 'reports' / 'T025'
    out.mkdir(parents=True, exist_ok=True)
    selected = representative_labels(branches)
    maps = make_plots(out, source, groups, selected, args.run_id, status)
    result['maps'] = maps
    write_json(out / 'analysis.json', result)
    write_json(out / 'branches.json', dict(run_id=args.run_id, status=status, branches=branch_rows))
    write_csv(out / 'cells.csv', [r for rows in records.values() for r in rows])
    report(out, result, source, demo, maps)
    files = ['analysis.json', 'branches.json', 'cells.csv', 'h1_analysis.md', 'branch_fractions.png',
             *[m['path'] for m in maps]]
    (out / 'artifacts.sha256').write_text(''.join(f'{digest(out / p)}  {p}\n' for p in sorted(files)))
    print(json.dumps(dict(run_id=args.run_id, status=status, branches=len(branches), maps=len(maps),
                          checks='summary decision fields independently recomputed and consistent')))


if __name__ == '__main__':
    main()
