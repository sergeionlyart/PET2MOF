# T019v2 independent controls

This directory contains V information. Do not disclose numerical exports or images to the model developer before `prereg-v1`.

The controls are instrument-derived source measurements, not LLM coordinate estimates: approximate image ROIs seed colour/shape template localisation; OpenCV determines the saved pixel coordinates. Synthetic marker templates and distance transforms remove connecting lines/open N2 markers. No fitted scientific curve is sampled. The readout bound is conservative and is not an experimental uncertainty. Source-only calibration uses linear image axes; STP conversion is the project convention, not a source measurement.

`source_control.py`, `source-projects.json`, `source-controls.csv`, `source-notes.json`, and the source tables were frozen before opening current T019 CSVs/projects. `blind_checkpoint.json` records hashes and prior knowledge. Initial source-only trials in `build_blind.py` / `blind-*` and `source_control-initial.py` failed visual QA and are retained, not counted. `*-accepted.png` shows the selected frozen candidates; the name does not mean verified scientific data. Unmatched/poor source-control candidates are not refitted after disclosure.

`comparison.csv` and `comparison-summary.json` contain the later comparisons. A match requires a unique nearest source-coordinate export point within six pixels; that spatial association is not an acceptance tolerance. Both strict |delta| <= u_dig and the diagnostic two combined readout uncertainties are reported. The latter is not a replacement for the required audit rule or a model tolerance. Control u_y is a conservative image readout term, not a complete experimental budget. In particular, S102-c-02 has a failed diagnostic; do not silently treat all residuals as passed.

`S2-source-tables.json` transcribes every JATS table row before disclosure; `S2-comparison.json` joins all relevant entries by printed sample name. `access*.json` records lawful source retrieval attempts. The local `S2.pdf` is a download waiting page, never treated as the article. Fresh JATS matches the passport input hash. No original layout was obtained.

`supplemental.py` / `supplemental-controls.json` check dry concentration traces after opening the T019 source exports. These are explicitly post-disclosure and do not satisfy a strict blind quota. The attempted additional triangle extraction yielded no accepted point and does not increase the frozen quota.

`finding-evidence.json` and `S103-open-circle-candidate.png` document the unconfirmed hollow-circle candidate in the S103 desorption export. Annular colour coverage alone is insufficient to establish a separate symbol in an overprinted cluster; examine the original source and neighbouring full circles.

`audit_contract.py` independently checks exact CSV headers, keys, flags, D-18 handling, all passports, schema rejection cases, all coordinate conversions and image-only uncertainty budgets, and S2 source joins. It writes only here. `contract-checks.json` records results and hashes. Private paths absent from this clone are recorded as unavailable, not falsely checked. Native raster inputs were independently recovered from the provided PDFs; the public export hashes are checked. `checks.json` records execution and checker-development failures; `post-report-read-checkpoint.json` states the failed pre-report completion-checkpoint attempt explicitly. The actual source-only checkpoint succeeded and its hashes remain unchanged.

Reproduce the read-only comparisons (do not rerun source controls to replace the frozen evidence):

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
python3 data/extraction/digitization/T019v2-control/compare.py
python3 data/extraction/digitization/T019v2-control/audit_contract.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -p no:cacheprovider --basetemp=data/extraction/digitization/T019v2-control/pytest-tmp tests/test_provenance_units.py
```

Requires the already available Python packages listed in `checks.json`, plus Pillow, PyYAML and jsonschema. Uses no model prediction/validation, external OCR, commercial credentials, CI or new dependencies. `source_control.py` contains the source-only measurement algorithm for later audit; it is not a promise that repeating a formerly blind stage restores blinding.

## Licences and credits (added by the lead)

- S102: DOI 10.1021/acs.langmuir.1c01149 — Main article closed; publisher Figshare SI CC BY-NC 4.0.
- S103: DOI 10.1038/s42004-022-00742-z — CC BY 4.0.
- S113: DOI 10.3390/membranes10070154 — CC BY 4.0.
- S117: DOI 10.1039/d1fd00017a — unknown; reuse rights not independently confirmed.

Published crops/overlays/page renders come only from S102 (Figshare SI, CC BY-NC 4.0, non-commercial reuse with attribution), S103 and S113 (CC BY 4.0, https://creativecommons.org/licenses/by/4.0/). Rendering, cropping and control-point annotation only; no generative editing.
S117 images are **not** published because a reuse licence is not established; they are kept privately by the lead and their SHA-256 are listed in `private_images_sha256.json`.

S2 access-attempt responses (`S2-access-*.html`, `S2-access-2.xml` — full-text JATS and access-denial pages) are not redistributed; they are kept privately by the lead and their SHA-256 are listed in `private_access_sha256.json`.
