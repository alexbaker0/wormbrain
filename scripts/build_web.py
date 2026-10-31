"""Build the interactive page: web/index.html + web/sim.js + exported brains -> web/dist/.

    uv run python scripts/build_web.py      (or: make web)

For each graph (real, rewired, random) the brain with the highest test reward among
the milestone-6 runs is exported. The output is one self-contained file,
web/dist/index.html (no server, no dependencies), plus the recorded replay as
web/dist/replay.html.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from wormbrain.chemotaxis import env_config, load_run_config
from wormbrain.export import export_model

RUNS = Path("reports/comparison/runs")
TITLES = {"real": "Real connectome", "rewired": "Rewired", "random": "Random wiring"}
OUT = Path("web/dist")


def best(condition: str) -> dict:
    runs = [json.loads(p.read_text()) for p in RUNS.glob(f"{condition}_*.json")]
    return max(runs, key=lambda r: r["test"]["gaussian"]["brain"]["reward_mean"])


def main():
    cfg = load_run_config("configs/chemotaxis.yaml")
    body = env_config(cfg["env"], cfg["env_overrides"])["body"]
    models = [export_model(best(c), title, body) for c, title in TITLES.items()]
    sim = Path("web/sim.js").read_text()
    sim = re.sub(r"^export ", "", sim, flags=re.M)  # inline as a classic script
    page = Path("web/index.html").read_text()
    page = page.replace("/*__SIM__*/", sim).replace("/*__MODELS__*/", json.dumps(models))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page)
    shutil.copy("reports/replay/worm_replay.html", OUT / "replay.html")
    for m in models:
        print(f"{m['title']}: {m['run']} (test reward {m['testReward']:+.3f})")
    print(f"wrote {OUT / 'index.html'} ({(OUT / 'index.html').stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
