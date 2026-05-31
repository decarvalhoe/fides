P ?= violin_solo

.PHONY: install test run batch clean

install:
	python -m pip install -e ".[dev,match]"

test:
	python -m pytest

run:
	python -m fides.cli "$(IN)" -o "$(OUT)" -p $(P)

batch:
	python -m fides.cli "$(IN)" -o "$(OUT)" -p $(P) --batch

clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__ .pytest_cache *.egg-info build dist
