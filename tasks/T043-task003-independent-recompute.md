# T043-task003-independent-recompute — независимый пересчёт баланса и двух границ другим способом

| Поле | Значение |
| --- | --- |
| task_id | T043-task003-independent-recompute |
| Исполнитель | gpt-6.1-terra, reasoning effort **medium** |
| Сеть | off |
| Проверяющий | руководитель (сравнение со значениями T042 делает руководитель, не исполнитель) |
| Ограничения | Клон ветки `task003-pet-transfer` **до** влития результатов T042. Не читать и не импортировать `src/pet2mof/task003/`, `scripts/task003/`, `reports/task003/*.csv` (их в клоне нет; если появятся — не открывать). Не делать commit. Новые файлы — только `scripts/task003_independent/recompute.py`, `reports/task003/independent/` (CSV/JSON), `reviews/T043_report.md`. Linear не используется. |

Прочитать: `docs/work_order_task003_RU.md` §5; `docs/task003/analysis_plan.md` (определения §§0–3; правило выбора не
применять); входы — `data/task002/PET2MOF_Task002_DataPack_v1.0/data/primary/S2_materials.csv`, `S2_dry_CO2.csv`,
`…/data/benchmark/S100_dry_isotherms.csv`, `data/task003/extracted/S100_methods.csv`, `data/task003/eta_bounds.csv`.

Способ — **точная рациональная арифметика** (`fractions.Fraction` на десятичных строках источника) и, для порогов,
решение уравнений перебором/бисекцией (не замкнутые формулы), чтобы способ отличался от основного расчёта.

1. Состав на 1 г сухого композита для S2 C48, C72, C96, N72, I96 в ветвях s-I и s-V (план §2.1): h, w, s; проверка
   суммы = 1; воспроизведение PEI_exp авторов по W и N (N_MOF = N(BASE), N(PEI) = 30.74 мас.%).
2. Для S100: q каждой серии при 0.896 bar линейной интерполяцией между соседними точками оцифровки (точно), отношение
   G = q_PEI/q_UiO-66 в ветвях основы b-C и b-M и доли w по ветвям w-C/w-F (по `S100_methods.csv`).
3. Допустимая линия η(φ) при φ = 0 и φ = 1 для S2 C72, I96 (обе ветви s) и S100 30PEI, 40PEI (все ветви) при n_N
   для N(PEI) 30.74 и 32.52 мас.%.
4. **Граница 1:** наибольшее k, при котором `G_PET = h·φ·(1 − 1/k) + G_analog/k ≥ 1.10` при всех φ ∈ [0, 1] — бисекцией
   по k (допуск 1e-12) для S2 C72 (s-I, s-V) и S100 30PEI (все ветви). **Граница 2:** φ_crit, при котором
   q_comp = 1.10·q_host, для w = 0.20, s = 0, η = 0.20 и η = 0.30 моль/моль N, q_host = 2.67 и q_host = q_UiO-66(0.896 bar)
   S100 — бисекцией по φ.
5. Выход: `reports/task003/independent/recompute.csv` (длинный формат: quantity, case, branch, value_exact (дробь
   строкой), value_float), `recompute.json`; отчёт `reviews/T043_report.md` — метод, все случаи, замечания к
   однозначности определений плана (если что-то в плане допускает два прочтения — указать, не выбирая молча).
