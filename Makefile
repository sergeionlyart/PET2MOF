UV_CACHE_DIR := $(CURDIR)/.uv-cache
export UV_CACHE_DIR
export UV_PYTHON_DOWNLOADS := never

.PHONY: env test test-ocr publish-check reproduce-demo reproduce-full report
env:
	uv sync --locked
test:
	uv run --locked --no-sync pytest
test-ocr:
	uv run --locked --no-sync pytest -m ocr
publish-check:
	uv run --locked --no-sync python scripts/publish_check.py
reproduce-demo reproduce-full report:
	@echo "not implemented yet (stage N)"
	@exit 2
