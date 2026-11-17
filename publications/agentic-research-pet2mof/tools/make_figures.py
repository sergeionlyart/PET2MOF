#!/usr/bin/env python3
"""Render committed evidence, without fitting models or running scientific code.

Run with the existing .venv: python -I tools/make_figures.py
Only assets/, evidence/assets_manifest.csv and tools/figure_checks.json are written.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

HERE = Path(__file__).resolve().parent
PUB = HERE.parent
REPO = HERE.parents[2]
# Keep matplotlib's writable font cache inside this task's allowed paths.
os.environ["MPLCONFIGDIR"] = str(HERE / ".mpl-cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
import matplotlib.pyplot as plt
import numpy as np

INK, BLUE, MUTED, RED, LINE, BG = "#121212", "#0755dc", "#5c5c59", "#d91922", "#d5d4ce", "#f8f7f3"
RUN_A = "20261117T044031484585Z-1acc1c2c-task002-A"
RUN_B = "20261117T045732361230Z-753cec58-task002-B"
SHAS = ("66bae26af9970c3142b72d25031c844b5461708f", "1558433614619e04102989d6b6f1479c50f364ce", "70685dc686ce22505b303a60920980a02772f019")
checks = {"inputs": {}, "figures": {}}
manifest = []
available = {f.name for f in font_manager.fontManager.ttflist}
def complete_font(name):
    if name not in available:
        return False
    glyphs = font_manager.get_font(font_manager.findfont(name)).get_charmap()
    return all(ord(c) in glyphs for c in "АБВабв₂φ₀≤≥≠∈σ−→⇄")
FONT = next(name for name in ("Arial", "Helvetica", "DejaVu Sans") if complete_font(name))
plt.rcParams.update({"font.family": FONT, "font.size": 12, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.edgecolor": LINE, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": BG, "axes.facecolor": BG, "svg.fonttype": "none",
                     "svg.hashsalt": "PET2MOF-T051", "savefig.facecolor": BG})


def committed(path: str) -> bytes:
    value = (REPO / path).read_bytes()
    stored = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=REPO, capture_output=True, check=True).stdout
    if value != stored:
        raise ValueError(f"Вход отличается от закоммиченного: {path}")
    checks["inputs"][path] = hashlib.sha256(value).hexdigest()
    return value


def rows(path: str) -> list[dict]:
    return list(csv.DictReader(committed(path).decode("utf-8").splitlines()))


def diagram(title: str, subtitle: str, height=7):
    fig, ax = plt.subplots(figsize=(12, height))
    fig.subplots_adjust(left=.04, right=.96, top=.82, bottom=.14)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    fig.text(.04, .95, title, fontsize=22, weight="bold", va="top")
    fig.text(.04, .885, subtitle, fontsize=11, color=MUTED, va="top")
    return fig, ax


def box(ax, x, y, text, *, color=INK, size=12, width=1):
    ax.text(x, y, text, ha="center", va="center", fontsize=size, color=color,
            bbox={"boxstyle": "square,pad=0.8", "facecolor": "white", "edgecolor": color, "linewidth": width})


def arrow(ax, start, end, *, color=MUTED, dashed=False, rad=0):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                               color=color, linewidth=1.2, linestyle="--" if dashed else "-",
                               connectionstyle=f"arc3,rad={rad}"))


def footer(fig, text):
    fig.text(.04, .035, text, fontsize=7.5, color=MUTED, va="bottom", linespacing=1.6)


def save(fig, no, stem, kind, title, alt, caption, sources, run_ids="не применимо", transformations="собственная схема", evidence=None):
    assets = PUB / "assets"
    assets.mkdir(exist_ok=True)
    # LICENSE is intentionally not assumed: no root LICENSE exists in this checkout.
    license_basis = "Собственная визуализация проекта; корневой LICENSE отсутствует, лицензия проекта не установлена"
    if no in (4, 5, 7):
        license_basis += "; числовые данные с атрибуцией, не копия издательского рисунка; см. sources/LICENSES.md"
    result = {}
    for extension in ("png", "svg"):
        path = assets / f"{stem}.{extension}"
        metadata = {"Software": "PET2MOF tools/make_figures.py"} if extension == "png" else {"Date": None, "Creator": "PET2MOF tools/make_figures.py"}
        fig.savefig(path, dpi=180, metadata=metadata)
        size = path.stat().st_size
        if extension == "png":
            width, height = struct.unpack(">II", path.read_bytes()[16:24])
            assert width >= 1600 and size <= 10 * 1024**2
            result[extension] = {"bytes": size, "width": width, "height": height}
        else:
            svg = path.read_text(encoding="utf-8")
            assert "<text" in svg and "<image" not in svg
            result[extension] = {"bytes": size, "editable_text": True}
        manifest.append({"asset_id": f"T051-F{no:02}-{extension}", "file": f"assets/{path.name}", "figure_no": no,
                         "type": kind, "title": title, "alt_text_ru": alt, "caption_ru": caption,
                         "data_sources": sources, "run_ids": run_ids, "script": "tools/make_figures.py",
                         "author_source": "Собственная работа PET2MOF / T051; " + sources,
                         "license_basis": license_basis, "transformations": transformations,
                         "checks": "tools/figure_checks.json; входы совпадают с HEAD; PNG ≥1600 px и ≤10 MiB; SVG с текстом"})
    checks["figures"][stem] = {"files": result, "evidence": evidence or {}}
    plt.close(fig)


def domain():
    fig, ax = diagram("1 / От отходов ПЭТ к проверяемой гипотезе", "Схема предмета исследования. Сорбция CO₂ — сухой чистый газ.")
    for x, text in ((.07, "ПЭТ"), (.35, "Деполимеризация"), (.66, "Терефталевая\nкислота (BDC)"), (.92, "UiO-66\n(Zr)")):
        box(ax, x, .83, text, size=11)
    for x1, x2 in ((.12, .23), (.48, .55), (.77, .86)):
        arrow(ax, (x1, .83), (x2, .83))
    ax.text(.5, .60, "Литературный прецедент: PET-derived UiO-66 получен (SRC-03, SRC-06)", ha="center", fontsize=12)
    arrow(ax, (.92, .73), (.79, .39))
    box(ax, .71, .28, "Модификация PEI → сорбция CO₂\nНаша гипотеза: PET-UiO-66 + PEI\nКомпозит не изготовлен", color=BLUE, size=12, width=1.5)
    box(ax, .21, .28, "Литературные аналоги\nPEI@UiO-66 (S100)\nPEI@UiO-66-NH₂ (S2)", size=11)
    ax.text(.5, .02, "Носитель ≠ композит  ·  S2 — отдельный материал, не PET-композит", ha="center", weight="bold", fontsize=12)
    footer(fig, "Источники: docs/work_order_task004_RU.md; reports/task003/next_experiment.md; SRC-03, SRC-06, S100, S2.")
    save(fig, 1, "fig01_domain", "схема", "Предмет исследования",
         "ПЭТ проходит через деполимеризацию и BDC к UiO-66. PET-носитель получен в литературе; его композит с PEI остаётся нашей непроверенной гипотезой.",
         "Рис. 1. Литературный прецедент относится к PET-derived UiO-66 (SRC-03, SRC-06); литературные аналоги S100 и S2 на обычном сырье не доказывают получение PET-композита. Носитель ≠ композит.",
         "docs/work_order_task004_RU.md;reports/task003/next_experiment.md")


def team():
    fig, ax = diagram("2 / Кто ставит задачу, выполняет и проверяет", "Роли и поток артефактов; стрелки обратной связи — пунктир.", 8)
    nodes = [( .13,.87,"Владелец\nцель и решения"),(.50,.87,"Подготовка с ChatGPT\nпоручения и данные"),(.87,.87,"Claude Code\nплан, карточки, интеграция"),
             (.87,.49,"Codex: Astra / Sol / Terra\nотдельные клоны и ветки"),(.50,.49,"Научный код\nучитываемый запуск\nпаспорт runs/<run_id>"),(.13,.49,"Независимая проверка\nдругой исполнитель"),
             (.13,.11,"Приёмка руководителем"),(.50,.11,"Отчёт"),(.87,.11,"Владелец\nследующее решение")]
    for x,y,t in nodes:
        box(ax,x,y,t,color=BLUE if "Codex" in t or "Независимая" in t else INK,size=10)
    arrow(ax,(.25,.87),(.33,.87)); arrow(ax,(.33,.9),(.25,.9))
    arrow(ax,(.66,.87),(.72,.87)); ax.text(.685,.93,"поручение",fontsize=8,ha="center")
    arrow(ax,(.87,.76),(.87,.62)); ax.text(.89,.69,"карточки",fontsize=8)
    arrow(ax,(.72,.49),(.64,.49)); arrow(ax,(.35,.49),(.28,.49))
    arrow(ax,(.13,.38),(.13,.22)); arrow(ax,(.29,.11),(.43,.11)); arrow(ax,(.57,.11),(.75,.11))
    arrow(ax,(.17,.63),(.80,.64),dashed=True,rad=-.12)
    ax.text(.48,.73,"ревью → исправление",fontsize=10,ha="center",color=MUTED)
    arrow(ax,(.98,.23),(.98,.73),dashed=True)
    ax.text(.5,-.04,"Отчёт → новое поручение владельца → следующий цикл",ha="center",fontsize=11,color=MUTED)
    footer(fig,"Источник: AGENTS.md; docs/model_policy.md; docs/work_order_task004_RU.md. Схема ролей, не журнал конкретного запуска.")
    save(fig,2,"fig02_team","схема","Команда и проверяемые артефакты",
         "Владелец задаёт цель, ChatGPT помогает подготовить поручение, Claude Code организует Codex и независимую проверку; ревью возвращает работу на исправление, отчёт ведёт к новому поручению.",
         "Рис. 2. Руководитель организует работу и принимает её; независимую проверку выполняет другой исполнитель. Научный код, учитываемый запуск и паспорт отделены от консультационной подготовки.",
         "AGENTS.md;docs/model_policy.md;docs/work_order_task004_RU.md")


def timeline():
    source="publications/agentic-research-pet2mof/evidence/agent_runs.csv"
    runs=rows(source)
    parse=lambda t: datetime.strptime(t,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    colors={"gpt-6-astra":BLUE,"gpt-6.1-sol":INK,"gpt-6.1-terra":MUTED}
    fig,ax=plt.subplots(figsize=(12,10))
    fig.subplots_adjust(left=.20,right=.97,top=.82,bottom=.19)
    fig.text(.04,.95,"3 / Три этапа: параллельность видна по запускам",fontsize=21,weight="bold",va="top")
    fig.text(.04,.895,"UTC, 16–17 ноября 2026 · каждый отрезок — один запуск исполнителя",fontsize=11,color=MUTED)
    lanes,records,labels=[],[],[]
    for stage in ("setup","TASK-001","TASK-002","TASK-003"):
        for model in colors:
            subset=sorted([r for r in runs if r["stage"]==stage and (r["actual_model"] if r["actual_model"]!="not_recorded" else r["requested_model"])==model],key=lambda r:r["started_utc"])
            ends=[]
            for r in subset:
                start,end=parse(r["started_utc"]),parse(r["finished_utc"])
                assert abs((end-start).total_seconds()-float(r["duration_s"]))<=1
                lane=next((i for i,t in enumerate(ends) if t<=start),len(ends))
                if lane==len(ends): ends.append(end)
                else: ends[lane]=end
                records.append((len(lanes)+lane,r,start,end,model))
            for n in range(len(ends)):
                lanes.append((stage,model,n))
                labels.append(f"{stage} / {model.split('-')[-1]}"+(f" · {n+1}" if n else ""))
    assert len(records)==len(runs),"Неизвестный этап/модель"
    for lane,r,start,end,model in records:
        x=mdates.date2num(start); width=mdates.date2num(end)-x
        ax.barh(lane,width,left=x,height=.62,color=colors[model],hatch="///" if r["actual_model"]=="not_recorded" else None)
        if float(r["duration_s"])>=500:
            ax.text(x+width/2,lane,r["task_id"].split("-")[0],ha="center",va="center",color="white",fontsize=6.8)
    commits=[]
    for j,sha in enumerate(SHAS):
        result=subprocess.run(["git","show","-s","--format=%ct",sha],cwd=REPO,capture_output=True,text=True,check=True)
        stamp=datetime.fromtimestamp(int(result.stdout.strip()),timezone.utc)
        commits.append({"sha":sha,"utc":stamp.isoformat()})
        ax.axvline(stamp,color=LINE,lw=1.5,zorder=0)
        ax.text(mdates.date2num(stamp),1.02,sha[:7],transform=ax.get_xaxis_transform(),ha="center",fontsize=9,color=INK)
    ax.set_yticks(range(len(lanes)),labels,fontsize=8)
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2,tz=timezone.utc))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m\n%H:%M",tz=timezone.utc))
    ax.tick_params(axis="x",labelsize=10)
    ax.set_xlabel("Время UTC")
    ax.grid(axis="x",color=LINE,lw=.5);ax.set_axisbelow(True)
    fig.legend(handles=[Line2D([0],[0],lw=7,color=c,label=m.split("-")[-1].title()) for m,c in colors.items()],loc="upper right",bbox_to_anchor=(.98,.885),ncol=3,frameon=False,fontsize=10)
    total=sum(float(r["duration_s"]) for r in runs)
    span=(max(parse(r["finished_utc"]) for r in runs)-min(parse(r["started_utc"]) for r in runs)).total_seconds()
    merged=[]
    for start,end in sorted((parse(r["started_utc"]),parse(r["finished_utc"])) for r in runs):
        if merged and start <= merged[-1][1]:
            merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:
            merged.append((start,end))
    active=sum((end-start).total_seconds() for start,end in merged)
    assert total>active
    footer(fig,f"Источник: evidence/agent_runs.csv ({len(runs)} запусков); git show %ct — время финальных коммитов.\nСумма запусков {total/3600:.2f} ч; весь интервал {span/3600:.2f} ч; хотя бы один исполнитель активен {active/3600:.2f} ч.\nПараллельность даёт сумму > активного времени, но не > всего интервала. Штриховка: модель только запрошена.\nrun_id: поле run в CSV (не научный запуск). Цвет без штриховки — фактическая модель.")
    save(fig,3,"fig03_timeline","наш учёт","Хронология исполнителей",
         f"{len(runs)} запусков на оси UTC по этапам и моделям. Полосы перекрываются; суммарно {total/3600:.2f} часа запусков за {span/3600:.2f} календарного часа; активное время {active/3600:.2f} часа. Отмечены три финальных коммита.",
         f"Рис. 3. Сумма длительностей запусков {total/3600:.2f} ч, календарный интервал {span/3600:.2f} ч, объединение активных интервалов {active/3600:.2f} ч. Параллельность подтверждена перекрытиями; требование подписи «сумма > календарного» не подтверждается CSV. Цвет — фактическая модель; штриховка — только запрошенная. Метки commit используют committer time; это не оценка скорости относительно человека.",
         "evidence/agent_runs.csv;git show -s --format=%ct " + " ".join(SHAS),"поле run в evidence/agent_runs.csv",
         "полосы started_utc–finished_utc; разнесение перекрытий по дорожкам; суммы duration_s; объединение активных интервалов",{"runs":len(runs),"total_seconds":total,"span_seconds":span,"active_seconds":active,"commits":commits})


def dry():
    source="reports/task002/A/nominal.csv";data=rows(source)
    candidates=rows("reports/task002/A/candidates.csv")
    selected={r["sample_id"] for r in candidates if r["role"]=="приоритетный кандидат"}
    assert selected=={"S2-C72","S2-C96"}
    base=float(next(r["q_dry_mmol_g"] for r in data if r["sample_id"]=="S2-BASE"))
    for r in data:
        assert r["run_id"]==RUN_A
        assert abs((float(r["q_dry_mmol_g"])/base-1)*100-float(r["gain_vs_base_pct"]))<1e-10
    fig,ax=plt.subplots(figsize=(12,7))
    fig.subplots_adjust(left=.10,right=.97,top=.78,bottom=.25)
    fig.text(.04,.95,"4 / Сухая ёмкость S2: контроль и кандидаты",fontsize=22,weight="bold",va="top")
    fig.text(.04,.88,"Измерения из литературы: S2 Table 2 (сухой чистый CO₂, 298 K, ≈1 bar; в источнике 1 bar / 1 atm) · прирост к BASE — наш расчёт",fontsize=11,color=MUTED)
    values=[float(r["q_dry_mmol_g"]) for r in data]
    ax.bar(range(len(data)),values,color=[BLUE if r["sample_id"] in selected else INK if r["sample_id"]=="S2-BASE" else MUTED for r in data],width=.62)
    ax.axhline(base,color=INK,lw=1,ls="--")
    for i,(r,q) in enumerate(zip(data,values)):
        gain=float(r["gain_vs_base_pct"])
        ax.text(i,q+.06,f"{q:.2f}\n"+("контроль" if not gain else f"{gain:+.1f} %"),ha="center",va="bottom",fontsize=11,color=BLUE if r["sample_id"] in selected else INK)
    ax.set_xticks(range(len(data)),[r["sample_id"].replace("S2-","") for r in data])
    ax.set(ylabel="Сухая q, ммоль/г",xlabel="Образцы S2 (UiO-66-NH₂ / PEI)",ylim=(0,3.95))
    ax.grid(axis="y",color=LINE,lw=.6);ax.set_axisbelow(True)
    footer(fig,f"Источник: {source}; candidates.csv · S2 Table 2, p. 3192.\nrun_id: {RUN_A}\nНет полного бюджета погрешности и исходных повторов. d = 3, 5, 10 % — назначенные сценарии, не ошибки измерения. C72/C96 не разделены при этих d.")
    save(fig,4,"fig04_task002_dry","измерения из литературы + наш расчёт","Сухое сравнение S2",
         "Столбцы S2: BASE 2.67, C48 2.75, C72 3.26, N72 2.99, C96 3.15, I96 1.87 ммоль/г. C72 и C96 выделены: +22.1 и +18.0 % к BASE; различие пары при сценарных допусках не разрешено.",
         "Рис. 4. Сухая ёмкость из S2 Table 2, прирост к BASE — наш расчёт. C72/C96 — приоритетная пара; d = 3, 5, 10 % — сценарии чувствительности, не экспериментальные погрешности. Носитель S2 — UiO-66-NH₂, не PET-UiO-66.",
         source+";reports/task002/A/candidates.csv",RUN_A,"значения q и gain из nominal.csv; выделение по candidates.csv; сверка gain с отношением к BASE",
         {r["sample_id"]:{"q":float(r["q_dry_mmol_g"]),"gain_pct":float(r["gain_vs_base_pct"]),"extraction_id":r["extraction_id"]} for r in data})


def methods():
    source="data/task002/PET2MOF_Task002_DataPack_v1.0/data/benchmark/S100_dry_isotherms.csv"
    data=rows(source); residuals=rows("reports/task002/B/check_residuals.csv"); fits=rows("reports/task002/B/langmuir_fit.csv")
    fig,axs=plt.subplots(2,3,figsize=(12,9),gridspec_kw={"height_ratios":[2.5,1]})
    fig.subplots_adjust(left=.08,right=.98,top=.80,bottom=.23,wspace=.30,hspace=.30)
    fig.text(.04,.96,"5 / Одни данные, два способа интерполяции",fontsize=22,weight="bold",va="top")
    fig.text(.04,.90,"S100, 298 K · оцифровка SI Fig. S5; внутренняя проверка одной серии",fontsize=11,color=MUTED)
    evidence={}
    for col,label in enumerate(("10PEI@UiO-66","20PEI@UiO-66","30PEI@UiO-66")):
        fit=next(r for r in fits if r["sample_label"]==label)
        fit_ids=set(fit["source_point_ids"].split(";"))
        points=sorted([r for r in data if r["point_id"] in fit_ids],key=lambda r:float(r["p_bar"]))
        control=[r for r in residuals if r["sample_label"]==label]
        assert fit["run_id"]==RUN_B and len(points)==int(fit["n_fit"])
        x=np.array([float(r["p_bar"]) for r in points]);y=np.array([float(r["q_mmol_per_g_reported"]) for r in points])
        grid=np.linspace(x.min(),x.max(),240);qs=float(fit["q_s_reported"]);b=float(fit["b_per_bar"])
        ax=axs[0,col];err=axs[1,col]
        ax.plot(x,y,color=INK,lw=1.2,label="Линейная по точкам")
        ax.plot(grid,qs*b*grid/(1+b*grid),color=BLUE,lw=1.6,label="Ленгмюр (готовая подгонка)")
        ax.scatter(x,y,color=INK,s=20,label="Точки подгонки",zorder=4)
        cx=[float(r["p_bar"]) for r in control];cy=[float(r["observed_q_reported"]) for r in control]
        digitized={r["point_id"]:r for r in data}
        ax.errorbar(cx,cy,xerr=[float(digitized[r["point_id"]]["p_digitization_halfwidth_bar"]) for r in control],
                    yerr=[float(r["q_digitization_halfwidth"]) for r in control],fmt="s",mfc="white",mec=BLUE,ecolor=MUTED,capsize=3,ms=5,label="Контроль ± оцифровка",zorder=5)
        for r in control:
            p=float(r["p_bar"]);obs=float(r["observed_q_reported"])
            assert r["run_id"]==RUN_B
            assert abs(np.interp(p,x,y)-float(r["baseline_prediction"]))<1e-10
            assert abs(qs*b*p/(1+b*p)-float(r["langmuir_prediction"]))<1e-10
            assert abs(float(r["baseline_prediction"])-obs-float(r["baseline_residual"]))<1e-10
            assert abs(float(r["langmuir_prediction"])-obs-float(r["langmuir_residual"]))<1e-10
        err.axhline(0,color=LINE,lw=1)
        for offset,key,color,marker in ((-.005,"baseline_residual",INK,"o"),(.005,"langmuir_residual",BLUE,"s")):
            err.scatter(np.array(cx)+offset,[float(r[key]) for r in control],color=color,marker=marker,s=28)
        ax.set(title=label,xlim=(0,1.08),ylim=(0,3.65));err.set(xlim=(.27,.52),ylim=(-.1,.26),xlabel="Давление, бар")
        if col==0:
            ax.set_ylabel("q, ммоль на сообщённый г*");err.set_ylabel("Расчёт − точка\nммоль/г*",fontsize=10)
        for panel in (ax,err):panel.grid(color=LINE,lw=.5);panel.set_axisbelow(True)
        evidence[label]={"fit_extraction_id":fit["extraction_id"],"qs":qs,"b":b,"checks":[{k:r[k] for k in ("point_id","baseline_residual","langmuir_residual","q_digitization_halfwidth","extraction_id")} for r in control]}
    handles,labels=axs[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",bbox_to_anchor=(.5,.115),ncol=2,frameon=False,fontsize=9)
    footer(fig,f"Источники: S100_dry_isotherms.csv; reports/task002/B/check_residuals.csv; langmuir_fit.csv.\nrun_id: {RUN_B} · *Основа сообщённого грамма не разрешена (unresolved_reported_gram).\nПолуширина оцифровки — не экспериментальная погрешность. Внутренняя проверка интерполяции, не независимая валидация.")
    save(fig,5,"fig05_methods","оцифровка графика из литературы + наш расчёт","Интерполяция и Ленгмюр",
         "Для 10/20/30PEI показаны точки подгонки, контроль с полушириной оцифровки, линейная интерполяция и готовый Ленгмюр. На нижних панелях Ленгмюр завышает контроль сильнее линейной интерполяции; проверка остаётся внутренней.",
         "Рис. 5. Оцифровка S100 SI Fig. S5: полуширины по q и p не являются погрешностями измерений. Параметры Ленгмюра и остатки прочитаны из готовых CSV; новая подгонка не выполнялась. Контроль внутри одной серии, не независимая проверка. Основа сообщённого грамма не разрешена.",
         source+";reports/task002/B/check_residuals.csv;reports/task002/B/langmuir_fit.csv",RUN_B,"готовые fit_point_ids и параметры; отрисовка формулы без оптимизации; остатки из CSV с проверкой",evidence)


def paired():
    path="reports/task003/next_experiment.md";text=committed(path).decode("utf-8")
    assert all(token in text for token in ("P0:","C0:","P1 = P0", "C1 = C0", "min(A, B)", "φ_max"))
    fig,ax=diagram("6 / Парный опыт: предложен, не проведён", "Четыре образца одной лаборатории; один PEI и одинаковый протокол модификации.",8)
    ax.text(.03,.89,"Без PEI",fontsize=11,color=MUTED);ax.text(.61,.89,"С одним и тем же PEI",fontsize=11,color=MUTED)
    box(ax,.20,.70,"P0\nPET-UiO-66",color=BLUE,size=15);box(ax,.78,.70,"P1 = P0 + PEI",color=BLUE,size=15)
    box(ax,.20,.39,"C0\nUiO-66 из коммерческого BDC",size=12);box(ax,.78,.39,"C1 = C0 + PEI",size=15)
    arrow(ax,(.34,.70),(.61,.70),color=BLUE);arrow(ax,(.42,.39),(.62,.39))
    ax.text(.49,.79,"G_P = q(P1)/q(P0)",ha="center",fontsize=12,color=BLUE)
    ax.text(.51,.46,"G_C = q(C1)/q(C0)",ha="center",fontsize=12)
    ax.text(.03,.535,"k = q(P0)/q(C0)",fontsize=11)
    ax.text(.5,.14,"G_P = G_C/k + φ(h_P − h_C/k)\nA = G_C/k;  B = A + φ_max(h_P − h_C/k)\nφ_max = min(1, G_C/h_C);  G_P ∈ [min(A, B); max(A, B)]",ha="center",va="center",fontsize=12,linespacing=1.6)
    footer(fig,"Источник: reports/task003/next_experiment.md. Не научный запуск, run_id не применим.\nГипотеза: одинаковы абсолютный PEI-вклад на грамм композита и φ. h_P, h_C — доли носителя.\nИнтервал фиксируют до измерения q(P1); попадание внутрь не определяет механизм и не измеряет φ.")
    save(fig,6,"fig06_paired_experiment","предлагаемый опыт","Четыре парных образца",
         "Две пары PET-UiO-66 и коммерческого UiO-66: P0/C0 без PEI, P1/C1 с одинаковым PEI. Отношения k, G_C, G_P проверяют условный интервал переноса; опыт предложен, не проведён.",
         "Рис. 6. Предлагаемый, не проведённый парный опыт. Совместно проверяются равенство абсолютного PEI-вклада и сохранённой доли ёмкости φ; h_P и h_C измеряют, интервал предсказывают до q(P1). Согласие с интервалом не устанавливает φ или механизм.",path)


def before_after():
    path="reviews/T044_checks/counterexamples.json"
    c=json.loads(committed(path))["T044_01_lower_guarantee"]
    text=committed("reports/task003/next_experiment.md").decode("utf-8")
    assert "h = 0.70, G_C = 1.17, k = 1.10" in text and "[1.063; 1.128]" in text
    phi=np.linspace(0,c["phi"],120)
    before=c["h"]*phi*(1-1/c["k"])+c["G_analog"]/c["k"]
    assert abs(before[-1]-c["G_PET_at_k095"])<1e-12
    h,g,k=.70,1.17,1.10;A=g/k;B=A+min(1,g/h)*(h-h/k);low,high=sorted((A,B))
    assert np.floor(low*1000)/1000==1.063 and np.ceil(high*1000)/1000==1.128
    fig,axs=plt.subplots(1,2,figsize=(12,7))
    fig.subplots_adjust(left=.08,right=.97,top=.70,bottom=.29,wspace=.30)
    fig.text(.04,.95,"7 / Проверка изменила границы вывода",fontsize=22,weight="bold",va="top")
    fig.text(.04,.88,"До: ошибочная гарантия ≥10 % при k ≤ 0.95 для любого φ",fontsize=11,color=RED)
    fig.text(.04,.83,"После: интервал условного прогноза и явный порог решения",fontsize=11,color=BLUE)
    ax=axs[0];ax.plot(phi,before,color=RED,lw=2);ax.axhline(1.10,color=INK,ls="--",lw=1)
    ax.scatter([1],[before[-1]],color=RED,zorder=3)
    ax.annotate(f"{before[-1]:.4f} < 1.10",(1,before[-1]),xytext=(.34,1.068),fontsize=11,color=RED,arrowprops={"arrowstyle":"->","color":RED})
    ax.set(xlabel="Сохранённая доля ёмкости φ",ylabel="G_PET",xlim=(0,1.06),ylim=(1.055,1.115),title="Контрпример T044")
    ax.text(.03,.97,f"k = {c['k']:.2f}; h = {c['h']:.2f}\nG = {c['G_analog']:.10f}",transform=ax.transAxes,va="top",fontsize=10)
    ax=axs[1];ax.hlines(.5,low,high,lw=8,color=BLUE);ax.plot([low,high],[.5,.5],"|",ms=22,color=BLUE)
    ax.axvline(1.10,color=INK,ls="--",lw=1)
    ax.text(low,.64,f"A = {low:.4f}",ha="center",fontsize=11);ax.text(high,.36,f"B = {high:.4f}",ha="center",fontsize=11)
    ax.text(1.10,.88,"порог 1.10",ha="center",fontsize=10)
    ax.set(xlabel="Прогноз G_P",yticks=[],xlim=(1.05,1.145),ylim=(0,1),title="Пример из нового протокола")
    ax.text(.5,.04,"h = 0.70; G_C = 1.17; k = 1.10\nИнтервал пересекает порог: гарантии нет",transform=ax.transAxes,ha="center",fontsize=10,linespacing=1.5)
    for ax in axs:ax.grid(color=LINE,lw=.5);ax.set_axisbelow(True)
    footer(fig,"Источники: reviews/T044_checks/counterexamples.json → T044_01_lower_guarantee; reports/task003/next_experiment.md.\nСлева: G_PET(φ) = hφ(1 − 1/k) + G/k; справа: A = G_C/k, B = A + φ_max(h − h/k), φ_max = 1.\nАудитный контрпример и пример предлагаемого опыта; собственного научного run_id у этих файлов нет.\nНаружу до 0.001: [1.063; 1.128]. Разные входы слева/справа: это исправление логики вывода, не повторный эксперимент.")
    save(fig,7,"fig07_before_after","наш расчёт (формула / контрпример)","До и после независимой проверки",
         f"Контрпример T044: при φ=1 коэффициент {before[-1]:.4f} ниже порога 1.10, опровергая прежнюю гарантию. Новый протокол даёт для другого примера интервал [{low:.4f}; {high:.4f}], пересекающий порог; гарантии 10 % нет.",
         "Рис. 7. Слева контрпример к ранней гарантии: k=0.95, h=0.70, G=1.0482970734, G_PET(1)=1.0666285 < 1.10. Справа другой пример исправленного протокола: h=0.70, G_C=1.17, k=1.10; интервал наружу [1.063; 1.128] пересекает порог. Это проверка формулы и границ утверждения, не новый физический результат.",
         path+";reports/task003/next_experiment.md","не применимо: аудитный контрпример и пример протокола",
         "оценка записанной формулы для изображения, без подгонки и научного перезапуска; сверка конца линии с JSON и округления с Markdown",
         {"before":{k:c[k] for k in ("h","k","G_analog","phi","G_PET_at_k095")},"after":{"h":h,"G_C":g,"k":k,"A":A,"B":B,"outward_interval":[1.063,1.128]}})


def main():
    (PUB/"assets").mkdir(exist_ok=True)
    for path in ("docs/work_order_task004_RU.md","reports/task003/next_experiment.md","AGENTS.md","docs/model_policy.md"):
        committed(path)
    domain();team();timeline();dry();methods();paired();before_after()
    fields=("asset_id","file","figure_no","type","title","alt_text_ru","caption_ru","data_sources","run_ids","script","author_source","license_basis","transformations","checks")
    with (PUB/"evidence/assets_manifest.csv").open("w",encoding="utf-8",newline="") as output:
        writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader();writer.writerows(manifest)
    checks["versions"]={"matplotlib":matplotlib.__version__,"numpy":np.__version__,"font":FONT}
    (HERE/"figure_checks.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Создано {len(manifest)} файлов: 7 PNG + 7 SVG; манифест и figure_checks.json")


if __name__=="__main__":
    main()
