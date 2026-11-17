#!/usr/bin/env python3
"""Lead acceptance check: does S100 SI Fig. S5 (own digitization, T006) plot the same data as the
NIST ISODB digitization of S100 main Fig. 4 (Isotherm5..9, 298 K, bar)?

Nearest-neighbour match of every S5 marker to the NIST points of the same series. Equality within
the T006 digitization bound for all series at the irregular pressure grid is evidence of identity.
Usage: python scripts/checks/s5_vs_nist.py data/extraction/digitization/T006-S100-FigS5.csv
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SERIES = {"UiO-66": 5, "10PEI@UiO-66": 6, "20PEI@UiO-66": 7, "30PEI@UiO-66": 8, "40PEI@UiO-66": 9}

def main(csv_path):
    d = pd.read_csv(csv_path)
    ok = True
    for name, k in SERIES.items():
        j = json.loads((ROOT / f"data/raw/nist_isodb/isotherms/10.1021acs.iecr.5b03517.Isotherm{k}.json").read_text())
        assert j["pressureUnits"] == "bar" and j["adsorptionUnits"] == "mmol/g"
        nx = np.array([p["pressure"] * 100.0 for p in j["isotherm_data"]])  # bar -> kPa
        ny = np.array([p["species_data"][0]["adsorption"] for p in j["isotherm_data"]])
        sub = d[d.series == name]
        dx, dq, used = [], [], set()
        for _, r in sub.iterrows():
            i = int(np.argmin(np.hypot(nx - r.x_display_kPa, (ny - r.uptake_mmol_g) / 0.05)))
            used.add(i)
            dx.append(nx[i] - r.x_display_kPa); dq.append(ny[i] - r.uptake_mmol_g)
            within = abs(dx[-1]) <= r.x_bound_kPa and abs(dq[-1]) <= r.uptake_bound_mmol_g
            ok &= within
        unmatched = [(round(nx[i], 2), round(ny[i], 3)) for i in range(len(nx)) if i not in used]
        print(f"{name}: T={j['temperature']} K n_S5={len(sub)} n_NIST={len(nx)} "
              f"max|dx|={max(map(abs, dx)):.3f} kPa max|dq|={max(map(abs, dq)):.4f} mmol/g "
              f"NIST-only points={unmatched}")
    print("ALL_WITHIN_T006_BOUNDS" if ok else "SOME_OUTSIDE_BOUNDS")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
