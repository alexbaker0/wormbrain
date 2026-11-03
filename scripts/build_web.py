"""Build the interactive page: web/index.html + web/sim.js + exported brains -> web/dist/.

    uv run python scripts/build_web.py      (or: make web)

For each graph (real, rewired, random) the brain with the highest test reward among
the milestone-6 runs is exported. The output is one self-contained file,
web/dist/index.html (no server, no dependencies; the wiring figure from
scripts/connectome_figure.py is embedded), plus the recorded replay as
web/dist/replay.html.
"""

from __future__ import annotations

import base64
import io
import json
import re
import shutil
from pathlib import Path

from PIL import Image

from wormbrain.chemotaxis import env_config, load_run_config
from wormbrain.env import PatchField
from wormbrain.export import build_brain, export_model
from wormbrain.layout import CIRCUIT, circuit_edges, circuit_members, whole_layout

RUNS = Path("reports/comparison/runs")
PATCH_RUNS = [  # (title, run file, blurb) for the food-patch world
    (
        "Symmetric body, curriculum",
        "reports/curr_sym_patch/runs/real_glu-excitatory_seed0.json",
        "symmetric body with head proprioception; learned to crawl, then to steer up a gradient, "
        "then trained only on food eaten minus energy. Straight runs between patches.",
    ),
    (
        "Usual body, curriculum",
        "reports/curr_usual_patch/runs/real_glu-inhibitory_seed1.json",
        "the usual body (independent back/belly classes), same curriculum: forages but loops.",
    ),
    (
        "No curriculum",
        "reports/patches_sym/runs/real_glu-inhibitory_seed0.json",
        "symmetric body trained only in the patch world: crawls straight but cannot steer.",
    ),
]
TITLES = {"real": "Real connectome", "rewired": "Rewired", "random": "Random wiring"}
OUT = Path("web/dist")


def best(condition: str) -> dict:
    runs = [json.loads(p.read_text()) for p in RUNS.glob(f"{condition}_*.json")]
    return max(runs, key=lambda r: r["test"]["gaussian"]["brain"]["reward_mean"])


def wiring_image(path=Path("reports/connectome/connectome.png"), width=2000) -> str:
    """The connectome figure as an embedded JPEG data URL (about 300 KB)."""
    im = Image.open(path).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    cfg = load_run_config("configs/chemotaxis.yaml")
    body = env_config(cfg["env"], cfg["env_overrides"])["body"]
    models = []
    for condition, title in TITLES.items():
        run = best(condition)
        m = export_model(run, title, body)
        m["circuitEdges"] = circuit_edges(build_brain(run).conn)  # this brain's own wiring
        models.append(m)
    patch_models = []
    for title, path, blurb in PATCH_RUNS:
        run = json.loads(Path(path).read_text())
        m = export_model(run, title, body)
        m["circuitEdges"] = circuit_edges(build_brain(run).conn)
        m["blurb"], m["testEaten"] = blurb, run["test"]["patches"]["brain"]["eaten_mean"]
        patch_models.append(m)
    world = PatchField({"half_size": 25.0, "n_patches": 24, "min_spacing": 6.0})
    world.relayout(9999)  # the held-out test layout used in the reports' figures
    real = build_brain(best("real")).conn
    x, y = whole_layout(real)  # neuron positions are shared; edges come from each brain
    members = circuit_members(real)
    layout = {
        "x": x.tolist(),
        "y": y.tolist(),
        "circuit": [{"name": c, "col": col, "row": row, "members": members[c]}
                    for c, col, row in CIRCUIT],
    }  # fmt: skip
    sim = Path("web/sim.js").read_text()
    sim = re.sub(r"^export ", "", sim, flags=re.M)  # inline as a classic script
    page = Path("web/index.html").read_text()
    page = page.replace("/*__SIM__*/", sim).replace("/*__MODELS__*/", json.dumps(models))
    page = page.replace("/*__LAYOUT__*/", json.dumps(layout))
    page = page.replace("/*__PATCH_MODELS__*/", json.dumps(patch_models))
    page = page.replace("/*__PATCHES__*/", json.dumps(world.xy.round(3).tolist()))
    page = page.replace("__WIRING__", wiring_image())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page)
    shutil.copy("reports/replay/worm_replay.html", OUT / "replay.html")
    for m in models:
        print(f"{m['title']}: {m['run']} (test reward {m['testReward']:+.3f})")
    for m in patch_models:
        print(f"{m['title']}: {m['run']} (patches eaten {m['testEaten']:.2f})")
    print(f"wrote {OUT / 'index.html'} ({(OUT / 'index.html').stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
