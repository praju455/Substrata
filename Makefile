PYTHON ?= python

.PHONY: setup seed test lint api ui demo build

setup seed test lint api ui demo build:
	$(PYTHON) scripts/dev.py $@
