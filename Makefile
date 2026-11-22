.PHONY: setup generate-data pipeline dashboard test lint format clean

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e .[dev]

generate-data:
	PYTHONPATH=src python scripts/generate_synthetic_data.py

pipeline:
	PYTHONPATH=src python scripts/run_pipeline.py

dashboard:
	PYTHONPATH=src streamlit run dashboard/app.py

test:
	PYTHONPATH=src pytest

lint:
	PYTHONPATH=src ruff check src tests scripts dashboard

format:
	PYTHONPATH=src ruff check --fix src tests scripts dashboard

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__
