APP ?= recorules
TESTS ?= ./tests
PYTHON ?= rye run python

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} \;
	find . -type d -name .cache -prune -exec rm -rf {} \;
	find . -type d -name .mypy_cache -prune -exec rm -rf {} \;
	find . -type d -name .pytest_cache -prune -exec rm -rf {} \;
	find . -type d -name .ruff_cache -prune -exec rm -rf {} \;
	find . -type d -name venv -prune -exec rm -rf {} \;

lint:
	$(PYTHON) -m ruff check ./$(APP) $(TESTS)
	$(PYTHON) -m ruff format --check ./$(APP) $(TESTS)
	$(PYTHON) -m mypy --cache-dir .cache/mypy_cache ./$(APP) $(TESTS)

lint/fix:
	$(PYTHON) -m ruff check --fix-only ./$(APP) $(TESTS)
	$(PYTHON) -m ruff format ./$(APP) $(TESTS)

run:
	$(PYTHON) -m $(APP)

setup:
	rye sync

test:
	$(PYTHON) -m pytest --rootdir=. -o cache_dir=.cache/pytest_cache $(TESTS) -s -x -v $(options)

.PHONY: $(shell grep --no-filename -E '^([a-zA-Z_-]|\/)+:' $(MAKEFILE_LIST) | sed 's/:.*//')