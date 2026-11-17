# T011v2 independent control project

Review: [T011v2_reverification.md](../../../../reviews/T011v2_reverification.md).
Only S105/S106 C-series sources are opened. Network and external OCR are not used.

The four `*.project.json` files preserve native-image hashes, linear axis calibration,
reference symbol dimensions, search windows, measured boundary pixels, control centres
and uncertainty diagnostics. `geometric_comparison.csv` contains all 302 controls,
including all 32 T011b recoveries. `series_row` is one-based **within the named series**.
For S105, x/y units are bar and mmol/g; for S106 they are RH fraction and cm³(STP)/g.
The summary converts all series to bar and mmol/g. Controls are digitized printed
markers, not new physical measurements or values sampled from fitted curves.

This recheck is not blind to the CSV: its coordinates locate a marker's neighbourhood.
Centres are computed from source pixels by independent boundary geometry, not copied
from the CSV. Square edges have explicit outside directions; coloured symbols use
geometric edge fitting. No T011/T011b/T011v code is imported or run.

- `*-native.png`: original embedded PDF image, cropped without interpolation.
- `*-render.png`: independent PDF rendering for visual comparison.
- `*-overlay.png`: all T011 points numbered over the source (not control measurements).
- `*-census.png`: raw-source cutouts of every retained marker, numbered in series order.
- `*-recoveries.png`, `*-origin-detail.png`: detailed source evidence.
- `*-edge-evidence.png`: low-visibility boundaries (green dots), control centre (orange).
- `low_visibility_checks.json`: pre-report-read threshold/radius checks.
- `low_visibility_joint_checks.json`: subsequent joint threshold × radius check.
- `preservation_checks.json`: historical byte comparisons; full files differ in status
  and raw CSV EOL, while all non-status field bytes are preserved.
- `normalization_checks.json`, `usable_ranges.json`, `passport_range_checks.json`:
  C-only transformation and range verification, 19 series / 806 rows.
- `pre_report_findings.json`: immutable findings/evidence hashes made before opening T011b's report.
- `attempt1_*`, `attempt2_*`: failed exploratory geometry results, not source defects;
  reasons are retained. Do not use these as final control values.
- `validation.json`, `environment.json`: command outcomes, limitations and versions.

Reproduce from the repository root with the existing local Python dependencies:

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
python3 data/extraction/digitization/T011v2-control/prepare.py
python3 data/extraction/digitization/T011v2-control/geometric_check.py
python3 data/extraction/digitization/T011v2-control/check_data.py
python3 data/extraction/digitization/T011v2-control/summarize.py
python3 data/extraction/digitization/T011v2-control/extend_sensitivity.py
python3 data/extraction/digitization/T011v2-control/write_report.py
```

These commands write only this control directory, the T011v2 report, and local full-page
renders in `tmp/T011v2-pages/`. They do not change T011/T011b/T011v artifacts. The historical
sequence of independent inspection and report reading cannot be recreated merely by
rerunning the scripts. Passport/status acceptance belongs to the project lead; source
CSV statuses have not been changed by this verification task.
