# PET2MOF

Исследовательский проект о гипотезе влияния содержания PEI и влажности на рабочую ёмкость CO₂ композита на основе UiO-66 из ПЭТ. [Итоговый отчёт](reports/final_report.md) и [PDF](reports/final_report.pdf) отделяют результаты измерений, контроль модели и условный прогноз.

Научный статус H1: **данных недостаточно**. Внешнее количественное сравнение недоступно, контроль на калибровочных сериях не прошёл, формальная сходимость ансамбля не установлена. PEI@UiO-66-NH2 [S2] — отдельный контроль, а не целевой PET-derived материал.

## Этап v2 (PET-CO2-TASK-002): сухой выбор кандидатов

Ветка `task002-dry-screening`. [Краткое решение](reports/task002/decision_brief.md) ([PDF](reports/task002/decision_brief.pdf)),
[отчёт](reports/task002/final_report_task002.md) ([PDF](reports/task002/final_report_task002.pdf)),
[вклад агентов](reports/task002/agent_contributions.md). По сухим измерениям S2 (25 °C, 1 bar | 1 atm) приоритетные
кандидаты — C72 и C96 с контролем UiO-66-NH2: оба устойчиво выше контроля при отклонениях до ±5 %, различие между
ними не разрешено (нужна погрешность < 1.56 % на значение). Влажный режим, цикл и перенос на PET-derived UiO-66 не
установлены; v1 и его статус не изменены. Команды: `make task002-intake`, `make task002-screen`, `make task002-s100`,
`make report-task002`.

## Этап v3 (PET-CO2-TASK-003): перенос PEI на PET-derived UiO-66

Ветка `task003-pet-transfer`. Статус: **частично выполнено** — CO₂-ёмкость PET-derived UiO-66 в открытых источниках не
найдена, поэтому границы условны через k = q(PET-носителя)/q(аналога). [Решение](reports/task003/decision_brief.md)
([PDF](reports/task003/decision_brief.pdf)), [отчёт](reports/task003/final_report.md)
([PDF](reports/task003/final_report.pdf)), [следующий опыт](reports/task003/next_experiment.md),
[совместимость маршрутов](reports/task003/route_compatibility.md), [ревью](reports/task003/review.md),
[вклад агентов](reports/task003/agent_contributions.md). Приоритет — прямое импрегнирование PEI (R1, протокол аналога
«30PEI»), резерв — смешанный линкер PET-BDC/NH₂-BDC + PEI через GA (R2); порог переноса k* = 1.06–1.52 (R1) и 1.110 (R2),
устойчиво по всем ветвям — k ≤ 0.95. Сухой чистый CO₂, ≈298 K; влага, цикл, смесь не оценивались. Команды:
`make task003-test`, `make task003-reproduce`, `make report-task003`.

## Локальное воспроизведение

Установите Python и `uv`, затем выполните `UV_CACHE_DIR="$PWD/.uv-cache" uv sync --locked`. Проектные команды используют зафиксированное окружение; не нужны ключи или модели ИИ. Для `make publish-check` дополнительно нужны установленный `gitleaks` и Git-идентичность с адресом `@users.noreply.github.com` (см. `docs/security.md`).

```sh
make test
make test-ocr
make reproduce-demo
make report
make publish-check
```

Для полного предрегистрированного расчёта используйте отдельный чистый checkout без незакоммиченных изменений:

```sh
git checkout prereg-v1
make reproduce-full
```

`make report` собирает PDF текущей версии отчёта; тег содержит историческое состояние и может иметь прежнюю цель `report`. `make report-t015` сохраняет прежнюю цель в текущей версии. Детали и ограничения запуска — в `docs/post_tag_procedure.md` и `reports/T025/h1_analysis.md`.

## Структура и права

`docs/` — протокол и решения; `sources/` — реестр и аудит; `data/extraction/` — паспорта и проекты; `src/` и `scripts/` — код; `configs/` — входы; `results/` и `runs/` — результаты и паспорта; `reviews/` и `reports/` — проверки и отчёты. См. [sources/LICENSES.md](sources/LICENSES.md): доступность статьи не означает права перепубликации; изображения S117 не включены. Лицензия вложенного шрифта — [LICENSE_DEJAVU](reports/assets/LICENSE_DEJAVU). Права на данные рассматриваются по источникам отдельно.

## English summary

PET2MOF investigates a hypothesis about how PEI loading and humidity might affect the working CO₂ capacity of a PET-derived UiO-66 composite. Working capacity is the difference between adsorption and regeneration loadings.

The scientific status of H1 is **insufficient data**. External quantitative validation cannot be performed with the available conditions, the calibration-set control did not meet all criteria, and the ensemble's formal convergence has not been established.

Everything that decides the hypothesis (code, fitted parameters, tolerances, decision rules and the held-out validation series, pinned by commit and SHA-256) was frozen in the annotated tag `prereg-v1` before the validation package was formally revealed by an independent reviewer. One known exception: the lead had seen S2 Tables 1–2 earlier, so the lead took no decision on how to read the S2 pressure (see `docs/prereg_status.md`). Of 20 held-out literature series (31 records), none was quantitatively testable under the pre-registered rules (0 full, 0 conditional comparisons): humidity, temperature uncertainty, mass basis or pressure meaning are not stated in the sources, and breakthrough curves do not give equilibrium capacities. The rules were not relaxed after this was seen.

In the frozen ensemble (360 model branches × 4 × 4096 draws, two regeneration modes, RH 0/40/70 %), no branch shows the hypothesised humidity-driven shift of the PEI optimum (`conditional_H1` 0/360), and no branch shows a robust rank inversion between dry equilibrium and humid working capacity (H1a 0/360). The only resolved interior optimum (about 20 wt % PEI, 38 branches) occurs in a single model version and a single reading of the PEI label, and its shift with humidity is not resolved at the adopted uncertainty; this does not prove that the optimum is humidity-independent. An independent clean-clone, offline reproduction reproduced all 360 ensemble sample files byte-for-byte.

The ensemble is a conditional model prediction, not a validation. Its branch frequencies describe the chosen design and should not be interpreted as probabilities for the real material. Maps and their input provenance are in `reports/T025/`.

Measurements, digitized points, published fits, simulations and project predictions are distinguished in the data provenance. The S2 PEI@UiO-66-NH2 material is a separate control, not the target PET-derived composite.

The next priorities are independent measurement of retained PEI and pore properties, a controlled humidity and composition matrix with a full uncertainty budget, and new or better documented external series. Calibration and validation must use separate batches or series.

The repository contains a locked Python environment, local tests, extraction records and run passports. The Russian final report documents limitations and reproducibility. Source-specific reuse restrictions apply; images without established redistribution rights are not included.

**Stage v2 (PET-CO2-TASK-002, branch `task002-dry-screening`).** A narrower, dry-only screening of six measured
samples from one publication (S2: UiO-66-NH₂ and its PEI modifications; dry pure CO₂, 25 °C, 1 bar | 1 atm). All
Table 1–2 cells were checked against the open source text; the comparison was recomputed independently with exact
arithmetic. Two candidates are recommended for further work, C72 and C96, with unmodified UiO-66-NH₂ as control: both
stay above the control under bounded independent deviations of up to ±5 % per value, but the difference between them
(3.5 %) is not resolved and would require per-value error below 1.56 %. These are robustness scenarios, not confidence
intervals, and no probabilities are claimed. An auxiliary check on five digitized S100 isotherms kept piecewise-linear
interpolation: a single-site Langmuir fit was worse on a pre-assigned internal pressure block (not a blind test). A
pore-volume operator defect was fixed and regression-tested. Humid behaviour, cycling, industrial readiness and transfer
to PET-derived UiO-66 are not established. See `reports/task002/`.

**Stage v3 (PET-CO2-TASK-003, branch `task003-pet-transfer`).** Status: **partially completed** — no open primary
source gives the CO₂ capacity of PET-derived UiO-66, so every boundary is conditional on k = q(PET host)/q(analog host).
A minimal mass balance (MOF + PEI + residue, η = mol CO₂ per mol PEI N, φ = retained host capacity) was applied to the
S2 (PEI@UiO-66-NH₂) and S100 (PEI@UiO-66) analogs under all unresolved composition and mass-basis readings, and
recomputed independently with exact arithmetic (124 checks, 0 discrepancies). Under the selection rule fixed before the
calculation, direct PEI impregnation (R1, following the S100 "30PEI" protocol) is preferred, with a mixed
PET-BDC/NH₂-BDC linker plus glutaraldehyde-anchored PEI (R2) as reserve; the S2 anchoring scheme itself is not applicable
to NH₂-free PET-UiO-66. A ≥ 10 % gain over the own PET host is retained for any pore blocking if k ≤ 1.06–1.52 (R1,
by S100 basis reading) or k ≤ 1.110 (R2 analog C72); robustly across all readings only if k ≤ 0.95. The S2 mass balance
does not close (18.5–25 % of composite mass is neither MOF nor PEI). This is a conditional map, not a validated
prediction; humidity, cycling, gas mixtures and synthesizability are not assessed. See `reports/task003/`.
