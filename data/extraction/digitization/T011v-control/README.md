# T011v independent control project

See [verification report](../../../../reviews/T011v_c_series_verification.md).

- `blind_digitize.py`: source-PDF-only rendering, independent axes, color/morphology marker localization, 12 controls for each of 19 series. No T011 input is used.
- `*.project.json`, `blind_controls.csv`, `blind_freeze.json`: source/image hashes, clipping rectangles, calibration, marker pixels and frozen 228-point control sample. Candidate counts are **not** a complete marker census.
- `*.png`: source figure renders and explicitly named annotated versions. `*-controls.png` shows blind controls; `*-T011-overlay.png` shows all T011 rows after unblinding.
- `compare.py`, `comparison_*.csv`: nearest-x comparison, including max/median differences and declared errors. Native units: bar and mmol/g for S105; RH fraction and cm3(STP)/g for S106.
- `check_ticks.py`, `calibration_tick_checks.json`: interior-tick verification of independent calibration.
- `check_normalization.py`, `normalization_checks.json`: independent conversion, schema, status, role, hash, Table 3 and byte-rebuild checks. Run the builder with `--output tmp/T011v-rebuild` first; never overwrite T011 output.
- `pre_report_findings.json`: independent conclusions saved before reading the T011 report. Its approximate plateau location was subsequently refined to RH ~0.823 in the nonblind supplemental check.
- `supplemental_missing_marker.json`: explicitly nonblind source check of a missed plateau circle, excluded from blind statistics.
- `source_manifest.json`: primary-source provenance, attribution and licenses. The primary PDFs remain in their supplied locations; IAPWS download and full-page/text intermediates are in ignored `tmp/T011v-source`.

Source figure credits: Cao et al., *Materials* 2018, 11, 589, DOI 10.3390/ma11040589; Jajko et al., *Microporous and Mesoporous Materials* 330 (2022), 111555, DOI 10.1016/j.micromeso.2021.111555. Both CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Figures are cropped/rendered and, where named, annotated. No generative editing or reconstruction was used. Formula: IAPWS SR1-86(1992), page 3, official release; unrestricted publication allowed.

Commands in the report use `UV_CACHE_DIR="$PWD/.uv-cache"`. The controls estimate graphical readout, not experimental precision. Source-specific activation and STP ambiguities remain explicit in the report. No T011 files or their statuses were changed.
