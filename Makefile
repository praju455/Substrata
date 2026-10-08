PYTHON ?= python

.PHONY: setup migrate seed test lint api ui demo build

setup migrate seed test lint api ui demo build:
	$(PYTHON) scripts/dev.py $@
