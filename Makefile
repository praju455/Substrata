PYTHON ?= python

.PHONY: setup migrate seed evaluate test lint api ui demo build

setup migrate seed evaluate test lint api ui demo build:
	$(PYTHON) scripts/dev.py $@
