UV_CACHE_DIR := $(CURDIR)/.uv-cache
export UV_CACHE_DIR
export UV_PYTHON_DOWNLOADS := never

.PHONY: env test test-ocr test-model publish-check reproduce-demo reproduce-full report report-t015 screen-debug task002-intake task002-screen
env:
	uv sync --locked
test:
	uv run --locked --no-sync pytest
test-ocr:
	uv run --locked --no-sync pytest -m ocr
publish-check:
	uv run --locked --no-sync python scripts/publish_check.py
test-model:
	uv run --locked --no-sync pytest tests/test_model_*.py
reproduce-demo:
	uv run --locked --no-sync python scripts/revision_run.py demo
screen-debug:
	uv run --locked --no-sync python scripts/revision_run.py screen
report:
	uv run --locked --no-sync python scripts/build_final_report.py
report-t015:
	uv run --locked --no-sync python scripts/revision_run.py report
reproduce-full:
	uv run --locked --no-sync python scripts/reproduce_full.py $(REPRODUCE_FULL_ARGS)
task002-intake:
	uv run --locked --no-sync python scripts/task002/accept_pack.py
task002-screen:
	uv run --locked --no-sync python scripts/task002/screen_s2.py
