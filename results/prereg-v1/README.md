# Results of the frozen chain `prereg-v1`

Copies of ignored post-tag outputs, committed after the frozen chain completed (HEAD of this commit is no
longer `prereg-v1`). Produced at tag commit `e6dc3bd5` (`git rev-parse prereg-v1^{commit}`).

| Path | Producer (run_id) |
| --- | --- |
| `ensemble/summary.json`, `ensemble/SHA256SUMS.large` | `20261117T020350339501Z-e6dc3bd5-T018-full` (`make reproduce-full`; 360 branches × 4 × 4096, seeds 12001–12004) |
| `holdout_v1/predictions.csv`, `model_derivatives.csv`, `prediction_metadata.json` | `20261117T022431395228Z-e6dc3bd5-prereg-v1-predict` (re-run under `scripts/run.py`; byte-identical to the package hashed in `freeze.json` before disclosure) |
| `holdout_v1/freeze.json`, `observations.csv` | independent reviewer T024 (`reviews/T024_freeze_reveal.md`) |
| `validation/validation.json` | `20261117T022438705845Z-e6dc3bd5-prereg-v1-validate` (byte-identical to the first, unpassported run) |

Not committed (reproducible; hashes recorded): 360 per-branch `samples.npz` (12.3 GB; `ensemble/SHA256SUMS.large`),
per-branch `summary.json` and `map.png` (`artifact_hashes` inside `ensemble/summary.json`).
Reproduction requires a checkout of the tag: `git checkout prereg-v1 && make reproduce-full` (~18 min, ~12 GB).
