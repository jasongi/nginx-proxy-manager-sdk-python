.PHONY: install lint test docs build

install:
	python -m pip install -e .[dev]

lint:
	black --check src tests
	flake8 src tests
	pre-commit run --all-files

test:
	pytest

docs:
	mkdocs serve

build:
	python -m build
