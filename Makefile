.PHONY: test lint stats oscillator report web

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

stats:
	uv run python scripts/graph_stats.py

oscillator:
	uv run python scripts/oscillator_demo.py

# milestone 6: pre-registered comparison report and sensor-lesion check
report:
	uv run python scripts/report.py --results reports/comparison
	uv run python scripts/chemotaxis_figure.py --results reports/comparison

# interactive page: web/dist/index.html (live simulation of the best trained brains)
web:
	uv run python scripts/build_web.py
