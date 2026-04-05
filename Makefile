.PHONY: test lint coverage audit clean all test-unit test-integration test-functional

test:
	python -m pytest tests/ -v --tb=short

test-unit:
	python -m pytest tests/ -v -m unit

test-integration:
	python -m pytest tests/ -v -m integration

test-functional:
	python -m pytest tests/ -v -m functional

lint:
	python -m ruff check scripts/ tests/
	python -m ruff format --check scripts/ tests/

coverage:
	python -m pytest tests/ --cov=scripts --cov-report=term-missing --cov-report=html:docs/coverage_html

audit:
	python -m ruff check scripts/ --select S
	python -m vulture scripts/ --min-confidence 80
	python -m mypy scripts/ --ignore-missing-imports

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache docs/coverage_html .coverage

all: lint test coverage audit
