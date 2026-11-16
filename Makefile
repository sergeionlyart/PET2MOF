UV_CACHE_DIR := $(CURDIR)/.uv-cache
export UV_CACHE_DIR
export UV_PYTHON_DOWNLOADS := never

.PHONY: env test test-ocr test-model publish-check reproduce-demo reproduce-full report screen-debug
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
	uv run --locked --no-sync python scripts/revision_run.py report
reproduce-full:
	@echo "not implemented yet (stage N)"
	@exit 2
