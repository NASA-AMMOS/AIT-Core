.PHONY: help dev-install install-python pre-commit setup-env setup test lint docs clean tox run-tests

help:
	@echo "AIT-Core Development Makefile"
	@echo "============================="
	@echo ""
	@echo "Available targets:"
	@echo "  setup-env      - Create and activate poetry virtual environment"
	@echo "  dev-install    - Install package with development dependencies"
	@echo "  install-python - Install all required Python versions via pyenv"
	@echo "  pre-commit     - Install pre-commit and pre-push hooks"
	@echo "  setup          - Run full development setup (setup-env + dev-install + pre-commit + install-python)"
	@echo "  test           - Run test suite with pytest"
	@echo "  tox            - Run full tox build (tests, docs, linting)"
	@echo "  lint           - Run linting pipeline"
	@echo "  docs           - Build documentation"
	@echo "  clean          - Remove build artifacts"
	@echo ""
	@echo "Before running 'make setup', ensure you have:"
	@echo "  - poetry installed"
	@echo "  - pyenv installed"
	@echo ""
	@echo "After setup, remember to set AIT_CONFIG:"
	@echo "  export AIT_CONFIG=/path/to/ait-core/config/config.yaml"

setup-env:
	@echo "Installing package with poetry..."
	poetry install

dev-install:
	@echo "Installing package with development dependencies..."
	poetry install

install-python:
	@echo "Installing required Python versions via pyenv..."
	cat .python-version | xargs -I{} pyenv install --skip-existing {}

pre-commit:
	@echo "Installing pre-commit and pre-push hooks..."
	pre-commit install && pre-commit install -t pre-push

setup: setup-env dev-install pre-commit install-python
	@echo ""
	@echo "Development setup complete!"
	@echo ""
	@echo "Remember to set AIT_CONFIG:"
	@echo "  export AIT_CONFIG=$$(pwd)/config/config.yaml"
	@echo ""
	@echo "Consider adding this to your shell RC file or virtual environment config."

test:
	@echo "Running test suite with pytest..."
	pytest

tox:
	@echo "Running full tox build..."
	tox

lint:
	@echo "Running linting pipeline..."
	tox -e lint

docs:
	@echo "Building documentation..."
	poetry run build_sphinx
	@echo ""
	@echo "Documentation built. Open doc/build/html/index.html to view."

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf doc/build/
	rm -rf .tox/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

run-tests:
	@echo "Running tests for specific Python version (e.g., make run-tests PY=py310)..."
	tox -e $(or $(PY),py310)
