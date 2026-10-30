.PHONY: test lint stats oscillator

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

stats:
	uv run python scripts/graph_stats.py

oscillator:
	uv run python scripts/oscillator_demo.py
