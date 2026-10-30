.PHONY: test lint stats

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

stats:
	uv run python scripts/graph_stats.py
