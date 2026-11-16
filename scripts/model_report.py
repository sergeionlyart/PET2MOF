#!/usr/bin/env python3
"""Readable T013 control/screen reports from saved, hashed debug outputs only."""
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def passport_for(output):
    digest=hashlib.sha256((ROOT/output).read_bytes()).hexdigest()
    candidates=[]
    for path in (ROOT/'runs').glob('*-T013-*/passport.json'):
        p=json.loads(path.read_text())
        if p.get('exit_code')==0 and any(v['path']==output and v['sha256']==digest for v in p.get('outputs',[])):
            candidates.append((p['started_utc'],str(path.relative_to(ROOT)),p))
    if not candidates:raise RuntimeError(f'no successful matching passport for {output}')
    _,path,p=max(candidates)
    return path,p


def plots(demo, run_id):
    os.environ['MPLCONFIGDIR']=str(ROOT/'.uv-cache/matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from pet2mof.calibration.fit import load_s100
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),sharey=True)
    for ax,fit in zip(axes,demo['fits']):
        f=load_s100(ROOT,fit['interpretation'])
        for color,(series,rows) in zip(plt.cm.tab10.colors,f.groupby('series',sort=False)):
            ax.errorbar(rows.p,rows.q,yerr=rows.uptake_bound_mmol_g,fmt='o',ms=3,color=color,label=series)
            if series=='UiO-66':
                p=np.linspace(0,1.02,100);host=fit['host'];ax.plot(p,host['q_sat']*host['b']*p/(1+host['b']*p),color=color)
            for name,style in (('M1','-'),('B1','--')):
                values=[r for r in fit['models'][name]['predictions'] if r['series']==series]
                if values:ax.plot([r['p_bar'] for r in values],[r['q_predicted'] for r in values],style,color=color)
        ax.set(xlabel='absolute CO2 pressure / bar',title=fit['interpretation']+' loading (debug)');ax.grid(alpha=.2)
    axes[0].set_ylabel('CO2 / mmol per g dry composite');axes[1].legend(fontsize=8)
    fig.suptitle('T006-S100-FigS5; solid M1, dashed B1; C control (debug)\n'+run_id,fontsize=11)
    fig.tight_layout();fig.savefig(ROOT/'reports/T013/S100_control.png',dpi=160);plt.close(fig)


def implementation(demo,path,p):
    rows=[]
    for fit in demo['fits']:
        for name,model in fit['models'].items():
            m=model['metrics'];rows.append(f"| {fit['interpretation']} | {name} | {m['RMSE']:.6f} | {m['MAE']:.6f} | {m['Bias']:.6f} | {m['mean_U']:.6f} | {m['fraction_within_U']:.1%} | {m['within_conditional_tolerances']} |")
    test_path=ROOT/'reports/T013/tests.xml'
    tests='Результаты pytest ещё не сохранены.'
    if test_path.exists():
        suites=ET.parse(test_path).getroot().findall('testsuite')
        tests='pytest: '+', '.join(f"{sum(int(s.attrib.get(k,0)) for s in suites)} {k}" for k in ('tests','failures','errors','skipped'))+'. Evidence: `reports/T013/tests.xml`.'
    host=demo['fits'][0]['host']['metrics'];cyc=demo['cycle']
    text=f'''# T013 — реализация и контрольное воспроизведение

Статус: **debug; для T016 и руководителя, не замороженный научный выпуск**.
run_id: `{p['run_id']}`; паспорт: `{path}`; исходный HEAD: `{p['commit_sha']}`.
Код изменён без коммита по поручению; точные SHA-256 кода/входов/конфигураций — в паспорте.
Время demo: {p['resources']['elapsed_seconds']:.2f} с (<120 с: {p['resources']['elapsed_seconds']<120}).
Модель/effort запрошены: gpt-6.1-sol/high. Интерфейс этой сессии не раскрывает фактически применённые настройки;
rollout-логи вне текущей директории не читались. Роль — исполнитель T013; независимый T016 ещё не выполнен.
Локальные `.agents/skills` и `.claude/rules` отсутствуют. Коммит, push и внешняя CI не выполнялись.

## Реализация и входы

`src/pet2mof/model/`: газ (1), Langmuir/DSL и аналитические интегралы IAST (2–5),
независимый контроль IAST квадратурой/корнем по составу; поры/вода (6–10);
непересекающиеся N-пулы (11–13); равновесные цели и перенос химических остатков
до периодичности (15), B1/B0 и условный тепловой баланс (16–19).
Число с неверной нормировкой, отсутствующим происхождением или несовместимым балансом
отвергается. `clip` применяется только там, где он явно задан уравнением (11).
Сухая масса композита остаётся знаменателем; давление S100 — абсолютное (D-15).

S100: `T006-S100-FigS5`, 48 собственных маркеров, из них 9 голого носителя и 39 PEI;
две перекрытые NIST-точки не добавлялись. Исходный CSV не изменён: его provisional-статус
сохранён; применение verified-решения D-15 записано в выходе. Сначала fit собственного
носителя, затем M1/B1 с одинаковой ковариацией на тех же четырёх PEI-сериях.
Происхождение каждого остатка сохранено в `reports/T013/demo.json`.
Общие осевые/экспериментальные ошибки заданы на целую изотерму, не уменьшаются на sqrt(n).
Независимые ошибки маркеров и межисполнительское расхождение учтены; принят минимум
3% полной шкалы (3.5 ммоль/г, 1 бар). Неизвестная экспериментальная ошибка —
условный сценарий 3% шкалы, **не метрологически подтверждённый допуск**.

C-PHYS: только две разрешённые DOI D-12, точные extraction_id/хеши в выходе и паспорте.
Все 8 fits (два материала × два газа × две статьи) — provisional debug.
У C2cp23839j category/ветвь unknown: совместный fit его записей — только диагностическая
альтернатива, не подтверждённый эксперимент. Номинальный цикл переносит Q носителя
из первой DOI на собственный носитель S100: это явное межпартийное допущение.
Регенерация вне температурного покрытия C — экстраполяция, а не проверенный перенос.
`verified_carriers` читает только `data/processed/c_series/manifest.yaml` со статусами
verified и SHA-256; T011v ещё не поступил. Его будущий реальный формат может потребовать
адаптера. Эта заготовка не объявлена интеграционно проверенной с отсутствующим T011v.

## Контроль S100 (единицы ошибок: ммоль CO2/г сухого композита)

| Прочтение загрузки | Модель | RMSE | MAE | Bias | mean(U) | Доля в U | Все условные критерии |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

Голый S100: RMSE={host['RMSE']:.6f}, MAE={host['MAE']:.6f}, mean(U)={host['mean_U']:.6f}.
Критерии протокола: MAE≤mean(U), ≥90% точек в U, |Bias|≤mean(U)/2.
**M1 и B1 не проходят совокупность даже условных критериев на PEI-сериях.**
Это отрицательный результат контрольного воспроизведения, не повод менять допуски.
Меньшая ошибка M1 на C не доказывает улучшение независимого прогноза.
График: `reports/T013/S100_control.png`; численные остатки, ковариация и профили — `demo.json`.

AICc считает независимые целые PEI-изотермы (4), а не 39 соседних точек.
У M1 четыре условно fitted-параметра: AICc undefined, преимущество сложности не установлено.
У B1 условный AICc рассчитан; DSL не выбирается по этим данным.
Сохранены условные профили A0, λ, Kd, κ (и B1 η0,Kd), все совместные параметры и успех решателя.
κ=f_in/(ρ_PEI V_p0), при c_conn=1; раздельные f_in, c_conn и V_p0 не установлены.
Точная ridge n_N·A0 сохранена как семейство равной likelihood; идеальный n_N не является анализом PEI.
Профили условны на fit носителя и выбранную ошибку: это не полный posterior и не
доверительные интервалы с учётом межстатейного переноса. Границы оптимизации — стресс-границы.

## Цикл, проверки и ограничения

Номинальный debug: w=0.20; адсорбция 308.15 K, 1 бар, RH=40%, сухая доля CO2=0.05;
R1 383.15 K, 1 бар, влажные yC=yW=0.001; 1800 с на стадию; τ/t=1.
M1 q_work={cyc['q_work']:.9f}; B1 q_work={demo['baseline_cycle']['q_work']:.9f} ммоль/г;
{cyc['cycles']} циклов, конечный остаток {cyc['residual']:.3g} при debug-допуске {cyc['tolerance']:.3g}.
Полные равновесные цели/остатки по шести пулам и селективность — в `demo.json`.
Численная энергия — **unknown**, формула сохранена. Конечные cp/Q в скрининге —
только стресс-допущения, не источниковые оценки энергии установки.

{tests}
Команды/evidence: `uv run --locked --no-sync pytest --ignore=tests/test_nist_isodb.py
--junitxml=reports/T013/tests.xml -q` — exit 0; `make reproduce-demo` — exit 0;
`make screen-debug` — exit 0; `make report` — exit 0; `git diff --check` — exit 0.
`python scripts/validate.py` и `python scripts/calibrate.py` без debug — ожидаемый exit 2:
нет V-файлов и verified T011v соответственно. Эти отказы не являются провалом валидации.
Проверены: бар↔кПа и сухая массовая база; сумма влажных долей;
IAST против независимой квадратуры для Langmuir/DSL и точного extended-Langmuir;
объём/N/вода; νd=min(0.5,f1+f2); w=0→носитель, RH=0→нет воды, τ=0→равновесие;
τ/t=0/0.1/1/10 и аналитический периодический предел; ужесточение точности;
B0-сокращение; отрицательный q_work не обрезается; seed PCG64; отказ без происхождения.
Исходный широкий NIST-тест исключён из запуска: он читает весь манифест, что несовместимо
со слепотой этой задачи. Не заявляется полный `make test`.

Цикл квазиравновесный: физсорбция/вода равновесны в концах стадий, химия релаксирует
от перенесённого остатка. Это не совместный кинетический интегратор и не колонна.
При удержанном бикарбонате, несовместимом с водой после переключения, сценарий
явно отклоняется с причиной, а не теряет CO2/H2O через отсечение.
Динамическая селективность, проскок, чистота продукта, насос/корпус/продувка не рассчитаны.
Обратимость воды, жёсткий объём аддукта и единый объёмный множитель — допущения.

IAPWS SR1-86(1992) реализован с URL, коэффициентами и контрольными значениями;
официальный PDF недоступен локально, сеть ограничена uv/PyPI. Независимая сверка
транскрипции с первоисточником остаётся для T016; это явно **не закрытая source-QA**.
Свойство воды ρ=1 г/см³ — отдельное debug-допущение, не реализованная IAPWS-плотность.

`validate.py` — каркас, численных V-констант нет. При отсутствии holdout сообщает понятную
ошибку; при наличии требует exact prereg-v1 и независимый freeze/hash contract.
S2: атрибуция отказа носитель→пористость→химия; moist только качественно.
D-14 переносит S106 в C: нельзя впоследствии объявлять его независимым V; проверяющий
выбирает действующий split до раскрытия. V-файлы и первоисточники не искались и не открывались.

## Сдача руководителю (семь строк)

1. Роль/задача: исполнитель OpenAI Codex, T013-implement-m1, без коммита.
2. Артефакты: model/, calibration/, configs/, demo/screen/validate, tests, эти два отчёта.
3. Контроль: `{p['run_id']}`, debug, exit={p['exit_code']}, {p['resources']['elapsed_seconds']:.2f} с.
4. Результат: M1/B1 воспроизведение PEI не проходит условные допуски; остатки сохранены.
5. Проверки: {tests}
6. Ограничения: T011v отсутствует, источниковая IAPWS-QA/T016 pending; уровень 2 только debug.
7. Приёмка: руководитель и независимый T016; научное замораживание/слияние не выполнялись.
'''
    (ROOT/'reviews/T013_implementation_report.md').write_text(text)


def screening(result,path,p):
    rows=[];associations={}
    text=[f'''# T013 — D-07 скрининг неизвестных параметров

Статус: **debug**, не продуктивный ансамбль. run_id `{p['run_id']}`; паспорт `{path}`.
Время {p['resources']['elapsed_seconds']:.2f} с. RNG {result['rng']}, numpy {result['numpy_version']}, seed {result['seed']}.
C-входы и оба прочтения загрузки — из хешированного `reports/T013/demo.json` (T006-S100-FigS5 и provisional C-PHYS).
Вывод уровня 2: **проверяемый прогноз; данных недостаточно**.

Ветки neutral, availability, bicarbonate, suppression, affinity считаются раздельно.
Стресс-диапазоны всех входов — `configs/scenarios.yaml` с единицами/происхождением;
мера: {result['sampling_measure']}.
Диапазоны выбраны для поиска зависимости, это не литературные priors.
Фиксированная сетка w=0..0.30, шаг 0.01; кандидаты 0/0.10/0.20/0.30;
RH 0/40/70, R1/R2 с общими условиями для всех w внутри выборки.
Отдельно меняются сухие/влажные теплоты (согласованно в равновесии и условной энергии),
состав N по всему симплексу, вода PEI, вода MOF, объём, сродство, τ/t и регенерация.
При изменении состава N сухой fit не повторяется: это стресс-диагностика механизма,
не C-согласованный posterior. Параметры сухого fit и профили хранятся отдельно.
Плотность воды — отдельная стресс-аппроксимация. τ/t берётся из 0/0.1/1/10.
N2-тепло включено в условную энергию; при разнонаправленных изменениях пулов энергия unknown.

| База/ветка | Попытки | Принято | Отклонено | Доля отклонений | Статус |
| --- | ---: | ---: | ---: | ---: | --- |''']
    for name,b in result['branches'].items():
        rows.append(f"| {name} | {b['attempted']} | {b['accepted']} | {b['rejected']} | {b['rejected_fraction']:.1%} | {b['status']} |")
        # Rejected branches and known inactive coordinates cannot justify a
        # source-search priority merely through chance small-sample correlation.
        if b['status']!='debug_only':continue
        branch=name.split('/')[1]
        inactive={'cp_mof','cp_pei','cp_water','Q_water','epsilon_s','epsilon_d',
                  't_ads','t_des','rho_pei'}
        if branch!='bicarbonate':inactive.update({'K_h','K_b','Q_b','h_max'})
        if branch!='availability':inactive.add('n_N')  # constant dry n_N*A0 ridge
        for condition,targets in b['rank_correlations'].items():
            other_regen='R2' if condition.startswith('R1') else 'R1'
            unrelated={'T_'+other_regen,'P_'+other_regen,'y_'+other_regen+'_C','y_'+other_regen+'_W'}
            for target,params in targets.items():
                for param,rho in params.items():
                    if param not in inactive|unrelated and abs(rho)>=.5:
                        associations.setdefault(param,[]).append((abs(rho),name,condition,target,rho))
    text+=rows
    text+=['\n## Параметры, требующие источниковых границ/различающих экспериментов\n',
           'Ниже исследовательские ассоциации |Spearman ρ|≥0.5 только в ветвях без превышения порога отказов. Это не причинные эффекты, не p-values и не доказанные H1/H1a. Из списка исключены известные по формулам неактивные координаты: cp/рекуперация, выдержка при фиксированном τ/t, параметры другого режима и отключённого механизма. Все сырые корреляции сохранены, включая случайные ассоциации неактивных координат.\n',
           '| Параметр | max abs(ρ) | Пример ветки/условия | Отклик |\n| --- | ---: | --- | --- |']
    for param,values in sorted(associations.items(),key=lambda kv:-max(v[0] for v in kv[1])):
        v=max(values)
        text.append(f'| {param} | {v[0]:.3f} | {v[1]}, {v[2]} | {v[3]} |')
    text+=['''
Для H1 сохранены все множества w*, Δ над концами (по определению Δ≥0), знаки соседних
разностей, контраст конечных составов и Δ(RH)−Δ(сухо). Для H1a — все шесть пар,
сухое равновесие и влажный q_work тех же составов; инверсии и ранги B1 сохранены.
Не вычисляются решающие P(rank=1) и доверительные вердикты из малого debug-пилота.
При >20% несовместимых наборов ветка остановлена для пересмотра совместной
параметризации; полный журнал причин/параметров сохранён, усечённый ансамбль не
выдаётся за допустимый prior. Бикарбонат при конечном времени может требовать
отложенного совместного интегратора D-08: перенос связанного CO2 без воды отвергается.

Полные выборки, причины отказов, ранги, кривые q_work, пределы тепловых сценариев,
Spearman для всех неконстантных входов/откликов — `reports/T013/screen.json`.
Перечень ассоциаций выше задаёт кандидатов для поиска источниковых границ, но при
таком малом N/отказах отсутствие ассоциации не исключает важность параметра.
Нужны измерения: временные CO2/H2O с десорбцией (τ и совместная вода), вода PEI и
известный RH (Wmax,KWP,hmax,Kh,Kb,γ), порометрия той же C-партии (Vp,f_in,c_conn),
многотемпературная PEI-серия/калориметрия (Qd,Qb,cp), N-анализ/NMR.
Продуктивные 4×4096, удвоение ансамбля/сетки и доверительные критерии протокола
не заменены этим пилотом. Окончательный вердикт H1/H1a не присваивается.
''']
    (ROOT/'reviews/T013_screening.md').write_text('\n'.join(text)+'\n')


def main():
    demo=json.loads((ROOT/'reports/T013/demo.json').read_text())
    path,p=passport_for('reports/T013/demo.json')
    plots(demo,p['run_id']);implementation(demo,path,p)
    screen_path=ROOT/'reports/T013/screen.json'
    if screen_path.exists():
        path,p=passport_for('reports/T013/screen.json');screening(json.loads(screen_path.read_text()),path,p)
    print('T013 reports updated from saved debug passports')

if __name__=='__main__':main()
