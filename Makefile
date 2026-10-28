# Offline analysis helpers. Nothing here starts Vagrant, Kubernetes or Docker.
# Python >= 3.12 is required (see DataAnalysis/requirements-offline.txt).
VENV ?= .venv
PY   := $(VENV)/bin/python

.PHONY: help analysis-venv analyze-sample analysis-offline analysis-test

help:
	@echo "analysis-venv     create $(VENV) and install the pinned offline dependencies"
	@echo "analyze-sample    summary CSV of the default committed sample -> DataAnalysis/output/ (stdlib only)"
	@echo "analysis-offline  all samples + CPU plot + tests -> DataAnalysis/output/"
	@echo "analysis-test     run the offline pytest suite"

analysis-venv:
	python3 -m venv $(VENV)
	$(PY) -m pip install -r DataAnalysis/requirements-offline.txt

analyze-sample:
	python3 DataAnalysis/analyze_sample.py

analysis-offline:
	PYTHON=$(abspath $(PY)) bash scripts/run-analysis-offline.sh

analysis-test:
	$(PY) -m pytest DataAnalysis
