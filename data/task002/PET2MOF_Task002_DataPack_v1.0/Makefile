PYTHON ?= python3
.PHONY: check-data test baseline reproduce-demo publish-check
check-data:
	$(PYTHON) scripts/check_data.py
test:
	$(PYTHON) -m unittest discover -s tests -v
baseline:
	$(PYTHON) scripts/reference_baseline.py
reproduce-demo: check-data test baseline
publish-check: check-data
	$(PYTHON) -c "from pathlib import Path; p=Path('.'); assert not (p/'.env').exists(); assert not (p/'.github/workflows').exists(); print('Package-level checks only. Run the main project local secret scanner and staged/history review before push.')"
