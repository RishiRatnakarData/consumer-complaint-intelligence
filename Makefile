.PHONY: install test lint sample live clean
install:
	python -m pip install -r requirements.txt
test:
	python -m pytest -q
lint:
	ruff check src tests
sample:
	python -m src.pipeline --sample
live:
	python -m src.pipeline --limit 5000 --start-date 2024-01-01
clean:
	python -m src.pipeline --clean-output

