# Sovereign Lattice GovCore
.DEFAULT_GOAL := help
.PHONY: help install test lint demo full clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

lint:
	ruff check govcore/ tests/

demo:
	$(PYTHON) scripts/demo.py

full: lint test

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/ .coverage

help:
	@echo "  install  |  test  |  lint  |  demo  |  full  |  clean"
