# T011 C-series

Rebuild offline with `UV_CACHE_DIR=$PWD/.uv-cache uv run --locked --no-sync python scripts/extraction/build_c_series.py`.

Each CSV has one series and exactly the requested twelve columns. Pressure is
absolute gas partial pressure in bar; capacity is mmol per g of that dry adsorbent.
`manifest.json` records input/output hashes, conversions and the role of each series.

* `C_candidate`: newly digitized carrier series; provisional until T011v.
* `context_GO`: all plotted GO series, retained separately from carrier calibration.
* `C`: S100; 48 accepted points and two NIST supplements with their own provisional status.
* `sensitivity_only`: NIST series without available primary-figure verification.

For primary calibration, require `status=verified` and the appropriate manifest
role/material. Unknown NIST errors are empty cells. RSC `nist_category_unknown`
records have unestablished experimental/simulation origin and cannot supply an
empirical fit. Table 3 author fits remain outside this isotherm directory.

Water RH is preserved in `data/extraction/digitization/T011-S106-Fig4.csv`;
absolute pressure here is derived using IAPWS saturation pressure at exactly 293 K.
Uncertainty columns are conservative digitization bounds with a 3% scale floor;
they do not include unknown experimental uncertainty.

See `reviews/T011_c_series_report.md` for access evidence and material/activation limitations.
