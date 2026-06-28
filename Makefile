.PHONY: install install-dev test lint play play-ai help

VENV ?= .venv
UV ?= uv
PY := $(VENV)/bin/python

install:
	$(UV) venv $(VENV)
	$(UV) pip install -e .

install-dev:
	$(UV) venv $(VENV)
	$(UV) pip install -e ".[dev]"

play:
	$(PY) -m chess play

play-ai:
	$(PY) -m chess play-ai

test:
	$(PY) -m pytest tests/ -v

lint:
	$(VENV)/bin/pre-commit run --all-files

.DEFAULT_GOAL := help

help:
	@echo "chess — sandbox board and minimax AI"
	@echo ""
	@echo "  make install-dev   uv venv + editable install with dev tools"
	@echo "  make play          free-play sandbox"
	@echo "  make play-ai       human vs minimax"
	@echo "  make test          pytest"
	@echo "  make lint          pre-commit"
