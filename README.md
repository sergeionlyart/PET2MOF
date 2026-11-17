# PET2MOF

Исследовательский проект о гипотезе влияния содержания PEI и влажности на рабочую ёмкость CO₂ композита на основе UiO-66 из ПЭТ. [Итоговый отчёт](reports/final_report.md) и [PDF](reports/final_report.pdf) отделяют результаты измерений, контроль модели и условный прогноз.

Научный статус H1: **данных недостаточно**. Внешнее количественное сравнение недоступно, контроль на калибровочных сериях не прошёл, формальная сходимость ансамбля не установлена. PEI@UiO-66-NH2 [S2] — отдельный контроль, а не целевой PET-derived материал.

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
